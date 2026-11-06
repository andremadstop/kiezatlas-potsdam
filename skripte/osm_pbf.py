"""Liest OpenStreetMap-PBF-Dateien offline, ohne pyosmium (Paket A3).

Warum ein eigener Leser: pyosmium und pyrosm sind auf der Workstation nicht installiert, und ein
Nachinstallieren aus dem Paketindex ist für diesen Lauf nicht vorgesehen. Das PBF-Format ist klein
und offen beschrieben (https://wiki.openstreetmap.org/wiki/PBF_Format, osmformat.proto und
fileformat.proto). Dieser Leser deckt genau das ab, was der Kiezatlas braucht:

- Blöcke ohne Kompression oder mit zlib (BBBike und Geofabrik schreiben zlib). lzma, lz4 und zstd
  lehnt er mit einer klaren Meldung ab.
- DenseNodes und einfache Nodes, Ways, Relations. Metadaten (Info, DenseInfo, Changesets) werden
  übersprungen.
- Gepackte Felder werden mit numpy dekodiert (Varint, ZigZag, Delta), der Rest in reinem Python.

Speicher: Koordinaten werden nur für Knoten im Suchrechteck behalten (numpy-Felder, nicht dict).
Geprüft gegen eine fremd erzeugte PBF (GDAL-Testdatei sample.osm.pbf, Abgleich mit dem OSM-Treiber
von GDAL, belege/A3_pbf_leser_gegenprobe.txt) und mit pruefen/a3_test_osm.py.
"""
from __future__ import annotations

import struct
import zlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# ------------------------------------------------------------------------------------- Protobuf

_MAX_BLOB_HEADER = 64 * 1024
_MAX_BLOB = 32 * 1024 * 1024


def _varint(buf: memoryview | bytes, pos: int) -> tuple[int, int]:
    """Ein Varint ab pos; gibt (wert, neue_pos)."""
    ergebnis = 0
    schiebe = 0
    while True:
        b = buf[pos]
        pos += 1
        ergebnis |= (b & 0x7F) << schiebe
        if b < 0x80:
            return ergebnis, pos
        schiebe += 7
        if schiebe > 70:
            raise ValueError("Varint zu lang (beschädigte Datei)")


def felder(buf: memoryview | bytes) -> Iterator[tuple[int, int, object]]:
    """Zerlegt eine Protobuf-Nachricht in (feldnummer, drahttyp, wert).

    Drahttyp 0: int (Varint), 2: memoryview (Länge vorangestellt), 1/5: int (fest 64/32 Bit).
    """
    buf = memoryview(buf)
    pos = 0
    n = len(buf)
    while pos < n:
        schluessel, pos = _varint(buf, pos)
        nr, typ = schluessel >> 3, schluessel & 7
        if typ == 0:
            wert, pos = _varint(buf, pos)
        elif typ == 2:
            laenge, pos = _varint(buf, pos)
            if pos + laenge > n:
                raise ValueError("Feld länger als die Nachricht (beschädigte Datei)")
            wert = buf[pos:pos + laenge]
            pos += laenge
        elif typ == 1:
            wert = struct.unpack_from("<Q", buf, pos)[0]
            pos += 8
        elif typ == 5:
            wert = struct.unpack_from("<I", buf, pos)[0]
            pos += 4
        else:
            raise ValueError(f"Drahttyp {typ} wird nicht unterstützt")
        yield nr, typ, wert


def _varints_py(b: bytes | memoryview) -> list[int]:
    werte = []
    pos = 0
    n = len(b)
    while pos < n:
        w, pos = _varint(b, pos)
        werte.append(w)
    return werte


def varints(b: bytes | memoryview) -> np.ndarray:
    """Gepackte Varints als uint64-Feld (vektorisiert)."""
    a = np.frombuffer(b, dtype=np.uint8)
    if a.size == 0:
        return np.zeros(0, dtype=np.uint64)
    if a.size < 24:
        return np.array(_varints_py(b), dtype=np.uint64)
    if a[-1] >= 0x80:
        raise ValueError("gepacktes Feld endet mitten in einem Varint")
    ende = np.flatnonzero(a < 0x80)
    start = np.empty_like(ende)
    start[0] = 0
    start[1:] = ende[:-1] + 1
    laenge = ende - start + 1
    if laenge.max() > 10:
        raise ValueError("Varint zu lang (beschädigte Datei)")
    werte = np.zeros(ende.size, dtype=np.uint64)
    for k in range(int(laenge.max())):
        m = laenge > k
        werte[m] |= (a[start[m] + k] & 0x7F).astype(np.uint64) << np.uint64(7 * k)
    return werte


def zigzag(w: np.ndarray) -> np.ndarray:
    """sint64 aus ZigZag-Kodierung."""
    w = w.astype(np.uint64)
    return (w >> np.uint64(1)).astype(np.int64) ^ -((w & np.uint64(1)).astype(np.int64))


def als_int64(w: np.ndarray) -> np.ndarray:
    """int32/int64 (negativ als Zweierkomplement über 64 Bit kodiert)."""
    return w.astype(np.uint64).view(np.int64)


def _gepackt(werte_typ_paare: list[tuple[int, object]]) -> np.ndarray:
    """Sammelt ein repeated-Feld, gepackt (Typ 2) oder einzeln (Typ 0)."""
    teile = []
    for typ, wert in werte_typ_paare:
        if typ == 2:
            teile.append(varints(wert))
        elif typ == 0:
            teile.append(np.array([wert], dtype=np.uint64))
    if not teile:
        return np.zeros(0, dtype=np.uint64)
    return teile[0] if len(teile) == 1 else np.concatenate(teile)


# ------------------------------------------------------------------------------------- Datei

def bloecke(pfad: str | Path) -> Iterator[tuple[str, bytes]]:
    """Liefert (typ, entpackte Nutzdaten) je Block: 'OSMHeader' oder 'OSMData'."""
    with open(pfad, "rb") as f:
        while True:
            kopf = f.read(4)
            if not kopf:
                return
            if len(kopf) < 4:
                raise ValueError("Datei endet mitten in einer Blocklänge")
            hl = struct.unpack(">I", kopf)[0]
            if hl > _MAX_BLOB_HEADER:
                raise ValueError(f"BlobHeader mit {hl} Byte (Grenze {_MAX_BLOB_HEADER}): keine PBF-Datei?")
            bh = f.read(hl)
            typ, groesse = "", 0
            for nr, _t, wert in felder(bh):
                if nr == 1:
                    typ = bytes(wert).decode("utf-8")
                elif nr == 3:
                    groesse = wert
            if groesse > _MAX_BLOB:
                raise ValueError(f"Blob mit {groesse} Byte (Grenze {_MAX_BLOB})")
            blob = f.read(groesse)
            if len(blob) < groesse:
                raise ValueError("Datei endet mitten in einem Block")
            roh = None
            roh_groesse = None
            for nr, _t, wert in felder(blob):
                if nr == 1:
                    roh = bytes(wert)
                elif nr == 2:
                    roh_groesse = wert
                elif nr == 3:
                    roh = zlib.decompress(bytes(wert))
                elif nr in (4, 5, 6, 7):
                    namen = {4: "lzma", 5: "bzip2", 6: "lz4", 7: "zstd"}
                    raise ValueError(f"Block mit {namen[nr]}-Kompression: wird nicht unterstützt "
                                     "(BBBike/Geofabrik liefern zlib)")
            if roh is None:
                raise ValueError("Block ohne Daten")
            if roh_groesse is not None and len(roh) != roh_groesse:
                raise ValueError("entpackte Größe stimmt nicht mit raw_size überein")
            yield typ, roh


@dataclass
class Kopf:
    links: float | None = None
    rechts: float | None = None
    oben: float | None = None
    unten: float | None = None
    pflicht: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)
    programm: str = ""
    quelle: str = ""
    zeitstempel: int | None = None   # osmosis_replication_timestamp (Sekunden seit 1970)


def lies_kopf(daten: bytes) -> Kopf:
    k = Kopf()
    for nr, typ, wert in felder(daten):
        if nr == 1 and typ == 2:
            for bnr, _bt, bw in felder(wert):
                v = int(zigzag(np.array([bw], dtype=np.uint64))[0]) * 1e-9
                if bnr == 1:
                    k.links = v
                elif bnr == 2:
                    k.rechts = v
                elif bnr == 3:
                    k.oben = v
                elif bnr == 4:
                    k.unten = v
        elif nr == 4:
            k.pflicht.append(bytes(wert).decode("utf-8"))
        elif nr == 5:
            k.optional.append(bytes(wert).decode("utf-8"))
        elif nr == 16:
            k.programm = bytes(wert).decode("utf-8", "replace")
        elif nr == 17:
            k.quelle = bytes(wert).decode("utf-8", "replace")
        elif nr == 32:
            k.zeitstempel = wert
    unbekannt = [p for p in k.pflicht if p not in ("OsmSchema-V0.6", "DenseNodes", "HistoricalInformation")]
    if unbekannt:
        raise ValueError(f"PBF verlangt unbekannte Merkmale: {unbekannt}")
    return k


# ------------------------------------------------------------------------------------- Inhalt

Tags = dict[str, str]


@dataclass
class Ergebnis:
    kopf: Kopf | None
    knoten_id: np.ndarray       # int64, sortiert
    knoten_lon: np.ndarray      # float64
    knoten_lat: np.ndarray      # float64
    getaggte_knoten: list[tuple[int, float, float, Tags]]
    wege: list[tuple[int, Tags, np.ndarray]]
    relationen: list[tuple[int, Tags, list[tuple[str, int, str]]]]
    knoten_gesamt: int = 0
    wege_gesamt: int = 0
    relationen_gesamt: int = 0
    ausdehnung: tuple[float, float, float, float] | None = None   # aller gelesenen Knoten

    def koordinaten(self, ids: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(lon, lat, gefunden) für Knoten-IDs; gefunden=False außerhalb des Rechtecks."""
        ids = np.asarray(ids, dtype=np.int64)
        if self.knoten_id.size == 0:
            leer = np.full(ids.shape, np.nan)
            return leer, leer.copy(), np.zeros(ids.shape, dtype=bool)
        i = np.searchsorted(self.knoten_id, ids)
        i_sicher = np.minimum(i, self.knoten_id.size - 1)
        gefunden = self.knoten_id[i_sicher] == ids
        lon = np.where(gefunden, self.knoten_lon[i_sicher], np.nan)
        lat = np.where(gefunden, self.knoten_lat[i_sicher], np.nan)
        return lon, lat, gefunden


def _tags(keys: np.ndarray, vals: np.ndarray, st: list[str]) -> Tags:
    return {st[int(k)]: st[int(v)] for k, v in zip(keys, vals)}


def lies(pfad: str | Path, *,
         rechteck: tuple[float, float, float, float] | None,
         knoten_wahl: Callable[[Tags], bool],
         weg_wahl: Callable[[Tags], bool],
         relation_wahl: Callable[[Tags], bool],
         knoten_lesen: bool = True,
         weg_ids: set[int] | None = None) -> Ergebnis:
    """Liest eine PBF-Datei in einem Durchgang.

    rechteck: (west, sued, ost, nord) in Grad; Koordinaten werden nur dafür behalten (None = alle).
    knoten_wahl/weg_wahl/relation_wahl: welche Objekte samt Tags zurückkommen. Getaggte Knoten
    außerhalb des Rechtecks entfallen. Wege und Relationen kommen unabhängig von der Lage zurück
    (ihre Knoten außerhalb haben dann keine Koordinate).
    knoten_lesen=False überspringt alle Knoten (zweiter Durchgang nur für Wege).
    weg_ids: Wege mit diesen IDs kommen auch ohne Tags oder ohne Treffer in weg_wahl zurück
    (Mitglieder von Multipolygon-Relationen, die erst nach den Wegen in der Datei stehen).
    """
    kopf = None
    ids_teile: list[np.ndarray] = []
    lon_teile: list[np.ndarray] = []
    lat_teile: list[np.ndarray] = []
    getaggt: list[tuple[int, float, float, Tags]] = []
    wege: list[tuple[int, Tags, np.ndarray]] = []
    relationen: list[tuple[int, Tags, list[tuple[str, int, str]]]] = []
    zaehler = {"k": 0, "w": 0, "r": 0}
    ausd = [np.inf, np.inf, -np.inf, -np.inf]

    for typ, daten in bloecke(pfad):
        if typ == "OSMHeader":
            kopf = lies_kopf(daten)
            continue
        if typ != "OSMData":
            continue   # unbekannte Blöcke laut Spezifikation überspringen
        st: list[str] = []
        granularitaet, lat_off, lon_off = 100, 0, 0
        gruppen = []
        for nr, _t, wert in felder(daten):
            if nr == 1:
                st = [bytes(s).decode("utf-8", "replace") for snr, _st, s in felder(wert) if snr == 1]
            elif nr == 2:
                gruppen.append(wert)
            elif nr == 17:
                granularitaet = wert
            elif nr == 19:
                lat_off = int(als_int64(np.array([wert], dtype=np.uint64))[0])
            elif nr == 20:
                lon_off = int(als_int64(np.array([wert], dtype=np.uint64))[0])

        for gruppe in gruppen:
            for gnr, _gt, gw in felder(gruppe):
                if gnr in (1, 2) and not knoten_lesen:
                    continue
                if gnr == 2:          # DenseNodes
                    teile: dict[int, list] = {1: [], 8: [], 9: [], 10: []}
                    for dnr, dt, dw in felder(gw):
                        if dnr in teile:
                            teile[dnr].append((dt, dw))
                    kid = np.cumsum(zigzag(_gepackt(teile[1])))
                    lat = (lat_off + granularitaet * np.cumsum(zigzag(_gepackt(teile[8])))) * 1e-9
                    lon = (lon_off + granularitaet * np.cumsum(zigzag(_gepackt(teile[9])))) * 1e-9
                    if not (kid.size == lat.size == lon.size):
                        raise ValueError("DenseNodes: id, lat und lon unterschiedlich lang")
                    zaehler["k"] += kid.size
                    if kid.size:
                        ausd[0] = min(ausd[0], float(lon.min()))
                        ausd[1] = min(ausd[1], float(lat.min()))
                        ausd[2] = max(ausd[2], float(lon.max()))
                        ausd[3] = max(ausd[3], float(lat.max()))
                    if rechteck is None:
                        drin = np.ones(kid.size, dtype=bool)
                    else:
                        w, s, o, n = rechteck
                        drin = (lon >= w) & (lon <= o) & (lat >= s) & (lat <= n)
                    ids_teile.append(kid[drin])
                    lon_teile.append(lon[drin])
                    lat_teile.append(lat[drin])
                    kv = als_int64(_gepackt(teile[10]))
                    if kv.size:
                        nullen = np.flatnonzero(kv == 0)
                        if nullen.size != kid.size:
                            raise ValueError("DenseNodes: keys_vals passt nicht zur Knotenzahl")
                        anfang = np.empty_like(nullen)
                        anfang[0] = 0
                        anfang[1:] = nullen[:-1] + 1
                        mit_tags = np.flatnonzero((nullen > anfang) & drin)
                        for i in mit_tags:
                            paar = kv[anfang[i]:nullen[i]]
                            t = _tags(paar[0::2], paar[1::2], st)
                            if knoten_wahl(t):
                                getaggt.append((int(kid[i]), float(lon[i]), float(lat[i]), t))
                elif gnr == 1:        # einzelner Node
                    nid = 0
                    keys = vals = np.zeros(0, dtype=np.uint64)
                    la = lo = 0
                    k_teile, v_teile = [], []
                    for nnr, nt, nw in felder(gw):
                        if nnr == 1:
                            nid = int(zigzag(np.array([nw], dtype=np.uint64))[0])
                        elif nnr == 2:
                            k_teile.append((nt, nw))
                        elif nnr == 3:
                            v_teile.append((nt, nw))
                        elif nnr == 8:
                            la = int(zigzag(np.array([nw], dtype=np.uint64))[0])
                        elif nnr == 9:
                            lo = int(zigzag(np.array([nw], dtype=np.uint64))[0])
                    keys, vals = _gepackt(k_teile), _gepackt(v_teile)
                    flat = (lat_off + granularitaet * la) * 1e-9
                    flon = (lon_off + granularitaet * lo) * 1e-9
                    zaehler["k"] += 1
                    ausd[0], ausd[1] = min(ausd[0], flon), min(ausd[1], flat)
                    ausd[2], ausd[3] = max(ausd[2], flon), max(ausd[3], flat)
                    if rechteck is None or (rechteck[0] <= flon <= rechteck[2] and rechteck[1] <= flat <= rechteck[3]):
                        ids_teile.append(np.array([nid], dtype=np.int64))
                        lon_teile.append(np.array([flon]))
                        lat_teile.append(np.array([flat]))
                        if keys.size:
                            t = _tags(keys, vals, st)
                            if knoten_wahl(t):
                                getaggt.append((nid, flon, flat, t))
                elif gnr == 3:        # Way
                    zaehler["w"] += 1
                    wid = 0
                    k_teile, v_teile, r_teile = [], [], []
                    for wnr, wt, ww in felder(gw):
                        if wnr == 1:
                            wid = ww
                        elif wnr == 2:
                            k_teile.append((wt, ww))
                        elif wnr == 3:
                            v_teile.append((wt, ww))
                        elif wnr == 8:
                            r_teile.append((wt, ww))
                    wid = int(als_int64(np.array([wid], dtype=np.uint64))[0])
                    extra = weg_ids is not None and wid in weg_ids
                    keys = _gepackt(k_teile)
                    if keys.size == 0 and not extra:
                        continue
                    t = _tags(keys, _gepackt(v_teile), st)
                    if extra or weg_wahl(t):
                        refs = np.cumsum(zigzag(_gepackt(r_teile)))
                        wege.append((wid, t, refs))
                elif gnr == 4:        # Relation
                    zaehler["r"] += 1
                    rid = 0
                    k_teile, v_teile, rol_teile, mem_teile, typ_teile = [], [], [], [], []
                    for rnr, rt, rw in felder(gw):
                        if rnr == 1:
                            rid = rw
                        elif rnr == 2:
                            k_teile.append((rt, rw))
                        elif rnr == 3:
                            v_teile.append((rt, rw))
                        elif rnr == 8:
                            rol_teile.append((rt, rw))
                        elif rnr == 9:
                            mem_teile.append((rt, rw))
                        elif rnr == 10:
                            typ_teile.append((rt, rw))
                    keys = _gepackt(k_teile)
                    if keys.size == 0:
                        continue
                    t = _tags(keys, _gepackt(v_teile), st)
                    if relation_wahl(t):
                        rollen = als_int64(_gepackt(rol_teile))
                        mitglieder = np.cumsum(zigzag(_gepackt(mem_teile)))
                        typen = _gepackt(typ_teile)
                        art = {0: "n", 1: "w", 2: "r"}
                        liste = [(art.get(int(ty), "?"), int(m), st[int(ro)])
                                 for ty, m, ro in zip(typen, mitglieder, rollen)]
                        relationen.append((int(als_int64(np.array([rid], dtype=np.uint64))[0]), t, liste))
                # 5 = Changesets: überspringen

    if ids_teile:
        ids = np.concatenate(ids_teile)
        lon = np.concatenate(lon_teile)
        lat = np.concatenate(lat_teile)
        ordnung = np.argsort(ids, kind="stable")
        ids, lon, lat = ids[ordnung], lon[ordnung], lat[ordnung]
        if ids.size > 1 and np.any(ids[1:] == ids[:-1]):
            raise ValueError("Knoten-ID mehrfach in der Datei")
    else:
        ids = np.zeros(0, dtype=np.int64)
        lon = np.zeros(0)
        lat = np.zeros(0)
    return Ergebnis(
        kopf=kopf, knoten_id=ids, knoten_lon=lon, knoten_lat=lat,
        getaggte_knoten=getaggt, wege=wege, relationen=relationen,
        knoten_gesamt=zaehler["k"], wege_gesamt=zaehler["w"], relationen_gesamt=zaehler["r"],
        ausdehnung=None if zaehler["k"] == 0 else (ausd[0], ausd[1], ausd[2], ausd[3]),
    )
