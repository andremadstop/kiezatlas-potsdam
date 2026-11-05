"""Schreibt eine winzige OSM-PBF als Prüfdatei für Paket A3 (kein Netz, keine echten OSM-Daten).

Die Objekte sind erfunden und liegen in Potsdam-West (um 13,03° O / 52,39° N), damit ein Trockenlauf
gegen die Datenbank sie in den Puffer um das Stadtgebiet legt. Kodiert wie Osmium bzw. osmconvert:
zlib-Blöcke, DenseNodes mit DenseInfo (wird beim Lesen übersprungen), Ways, Relations.

Inhalt (was die Tests erwarten, steht in ERWARTET):
- Gitter aus 3 x 3 Knoten mit Wohnstraßen und Fußwegen (zusammenhängend)
- nicht begehbar: Autobahn, Radweg ohne foot, Fußweg mit access=private, Weg mit foot=no
- begehbar: Radweg mit foot=designated, Treppe
- Einrichtungen: Arzt mit Name (Name darf nirgends ankommen), Apotheke als Fläche, Supermarkt als
  Multipolygon-Relation, Pflegeheim, betreutes Wohnen (social_facility), Tafel (keine Pflege),
  Spielplatz als Punkt und dieselbe Fläche (Dublette), privater Spielplatz, Kita, Schule als Fläche
- ein Knoten weit außerhalb (fällt aus dem Leserechteck)

Aufruf: python -I pruefen/a3_pbf_schreiben.py ZIELDATEI
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

# ------------------------------------------------------------------------------------- Protobuf


def _varint(n: int) -> bytes:
    if n < 0:
        n += 1 << 64
    aus = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            aus.append(b | 0x80)
        else:
            aus.append(b)
            return bytes(aus)


def _zz(n: int) -> int:
    return (n << 1) ^ (n >> 63)


def feld_varint(nr: int, wert: int) -> bytes:
    return _varint(nr << 3) + _varint(wert)


def feld_bytes(nr: int, daten: bytes) -> bytes:
    return _varint((nr << 3) | 2) + _varint(len(daten)) + daten


def gepackt(nr: int, werte: list[int]) -> bytes:
    return feld_bytes(nr, b"".join(_varint(w) for w in werte))


def delta(werte: list[int]) -> list[int]:
    aus, vorher = [], 0
    for w in werte:
        aus.append(w - vorher)
        vorher = w
    return aus


# ------------------------------------------------------------------------------------- Inhalt

B0, L0 = 52.390, 13.030   # Ursprung des Gitters
SCHRITT = 0.001           # rund 111 m (Breite) bzw. 68 m (Länge)

KNOTEN: dict[int, tuple[float, float, dict]] = {}   # id -> (lon, lat, tags)
WEGE: dict[int, tuple[list[int], dict]] = {}
RELATIONEN: dict[int, tuple[list[tuple[int, int, str]], dict]] = {}   # (typ 0/1/2, ref, rolle)


def k(nid: int, lon: float, lat: float, **tags) -> None:
    KNOTEN[nid] = (lon, lat, {kk.replace("__", ":"): v for kk, v in tags.items()})


def w(wid: int, refs: list[int], **tags) -> None:
    WEGE[wid] = (refs, {kk.replace("__", ":"): v for kk, v in tags.items()})


# Gitter 3 x 3: ids 1..9, Zeile r, Spalte c -> 1 + 3r + c
for r in range(3):
    for c in range(3):
        k(1 + 3 * r + c, L0 + c * SCHRITT, B0 + r * SCHRITT)
w(100, [1, 2, 3], highway="residential", name="Beispielstraße")
w(101, [4, 5, 6], highway="footway")
w(102, [7, 8, 9], highway="living_street")
w(103, [1, 4, 7], highway="path", foot="yes")
w(104, [3, 6, 9], highway="steps")
w(105, [2, 5, 8], highway="cycleway", foot="designated")
w(106, [5, 5, 2], highway="service")          # Schleife 5-5 entfällt, Kante 5-2 doppelt zu Weg 105

# nicht begehbar (eigene Knoten 20..29)
for i, (dl, db) in enumerate([(0.004, 0), (0.005, 0), (0.004, 0.001), (0.005, 0.001), (0.004, 0.002),
                              (0.005, 0.002), (0.004, 0.003), (0.005, 0.003)]):
    k(20 + i, L0 + dl, B0 + db)
w(110, [20, 21], highway="motorway")
w(111, [22, 23], highway="cycleway")
w(112, [24, 25], highway="footway", access="private")
w(113, [26, 27], highway="track", foot="no")

# Weg über den Rand des Leserechtecks: Knoten 30 drin (mit Gitter verbunden), 31 weit draußen
k(30, L0 - SCHRITT, B0)
k(31, 10.0, 50.0)
w(114, [1, 30, 31], highway="footway")

# Einrichtungen
k(40, L0 + 0.0005, B0 + 0.0005, amenity="doctors", name="Praxis Dr. Beispiel",
  healthcare="doctor", healthcare__speciality="general")
for i, (dl, db) in enumerate([(0, 0), (0.0002, 0), (0.0002, 0.0002), (0, 0.0002)]):
    k(41 + i, L0 + 0.0012 + dl, B0 + 0.0012 + db)
w(120, [41, 42, 43, 44, 41], amenity="pharmacy", name="Beispiel-Apotheke", building="yes")
for i, (dl, db) in enumerate([(0, 0), (0.0003, 0), (0.0003, 0.0003), (0, 0.0003)]):
    k(45 + i, L0 + 0.0015 + dl, B0 + 0.0016 + db)
w(121, [45, 46, 47, 48], building="retail")     # Mitglied, ohne Einrichtungs-Tags
w(122, [48, 45], barrier="wall")                # zweites Mitglied, schließt den Ring
RELATIONEN[200] = ([(1, 121, "outer"), (1, 122, "outer")],
                   {"type": "multipolygon", "shop": "supermarket", "name": "Beispielmarkt"})
k(50, L0 + 0.0021, B0 + 0.0001, amenity="nursing_home", name="Haus Beispiel")
k(51, L0 + 0.0021, B0 + 0.0011, amenity="social_facility", social_facility="assisted_living")
k(52, L0 + 0.0021, B0 + 0.0019, amenity="social_facility", social_facility="food_bank")
k(53, L0 + 0.0006, B0 + 0.0016, leisure="playground")
for i, (dl, db) in enumerate([(0, 0), (0.0002, 0), (0.0002, 0.0001), (0, 0.0001)]):
    k(54 + i, L0 + 0.0005 + dl, B0 + 0.0015 + db)
w(123, [54, 55, 56, 57, 54], leisure="playground")       # Dublette zu Knoten 53
k(58, L0 + 0.0001, B0 + 0.0021, leisure="playground", access="private")
k(59, L0 + 0.0011, B0 + 0.0021, amenity="kindergarten", name="Kita Beispiel")
for i, (dl, db) in enumerate([(0, 0), (0.0004, 0), (0.0004, 0.0003), (0, 0.0003)]):
    k(60 + i, L0 + 0.0030 + dl, B0 + 0.0002 + db)
w(124, [60, 61, 62, 63, 60], amenity="school", name="Beispielschule")
k(99, 13.5, 53.5, amenity="pharmacy")          # außerhalb des Leserechtecks

ERWARTET = {
    "netz_wege": {100, 101, 102, 103, 104, 105, 106, 114},
    "nicht_netz": {110, 111, 112, 113},
    # Kanten: Zeilen 3*2, Spalten 3*2 (davon 103, 104, 105), 106 nur 5-2 (doppelt), 114: 1-30 (30-31 fehlt)
    "kanten": 6 + 6 + 1,
    "knoten": 10,
    "pois": {"n40": "arzt", "w120": "apotheke", "r200": "supermarkt", "n50": "pflege", "n51": "pflege",
             "n53": "spielplatz", "w123": "spielplatz"},
    "pois_nach_dublette": {"n40", "w120", "r200", "n50", "n51", "n53"},
    "bildung": {"n59": "kita", "w124": "schule"},
}


def tags_kodieren(tags: dict, st: dict[str, int]) -> tuple[list[int], list[int]]:
    return [st[k_] for k_ in tags], [st[v] for v in tags.values()]


def block_bauen(granularitaet: int = 100) -> bytes:
    strings = [""]
    for _lo, _la, t in KNOTEN.values():
        strings += list(t) + list(t.values())
    for _r, t in WEGE.values():
        strings += list(t) + list(t.values())
    for m, t in RELATIONEN.values():
        strings += list(t) + list(t.values()) + [ro for _ty, _re, ro in m]
    reihe = list(dict.fromkeys(strings))
    st = {s: i for i, s in enumerate(reihe)}
    stringtable = b"".join(feld_bytes(1, s.encode()) for s in reihe)

    # DenseNodes (Knoten unsortiert ablegen: der Leser sortiert selbst, wie bei der GDAL-Testdatei)
    ids = sorted(KNOTEN, reverse=True)
    lat = [round(KNOTEN[i][1] * 1e9 / granularitaet) for i in ids]
    lon = [round(KNOTEN[i][0] * 1e9 / granularitaet) for i in ids]
    kv: list[int] = []
    for i in ids:
        kk, vv = tags_kodieren(KNOTEN[i][2], st)
        for a, b in zip(kk, vv):
            kv += [a, b]
        kv.append(0)
    denseinfo = gepackt(1, [1] * len(ids)) + gepackt(2, [_zz(x) for x in delta([1_700_000_000] * len(ids))])
    dense = (gepackt(1, [_zz(x) for x in delta(ids)]) + feld_bytes(5, denseinfo)
             + gepackt(8, [_zz(x) for x in delta(lat)]) + gepackt(9, [_zz(x) for x in delta(lon)])
             + gepackt(10, kv))
    gruppe_k = feld_bytes(2, dense)
    # Ways
    gruppe_w = b""
    for wid, (refs, t) in WEGE.items():
        kk, vv = tags_kodieren(t, st)
        gruppe_w += feld_bytes(3, feld_varint(1, wid) + gepackt(2, kk) + gepackt(3, vv)
                               + gepackt(8, [_zz(x) for x in delta(refs)]))
    # Relations
    gruppe_r = b""
    for rid, (m, t) in RELATIONEN.items():
        kk, vv = tags_kodieren(t, st)
        gruppe_r += feld_bytes(4, feld_varint(1, rid) + gepackt(2, kk) + gepackt(3, vv)
                               + gepackt(8, [st[ro] for _ty, _re, ro in m])
                               + gepackt(9, [_zz(x) for x in delta([re for _ty, re, _ro in m])])
                               + gepackt(10, [ty for ty, _re, _ro in m]))
    return (feld_bytes(1, stringtable) + feld_bytes(2, gruppe_k) + feld_bytes(2, gruppe_w)
            + feld_bytes(2, gruppe_r) + feld_varint(17, granularitaet))


def blob(typ: str, daten: bytes) -> bytes:
    z = zlib.compress(daten, 9)
    b = feld_varint(2, len(daten)) + feld_bytes(3, z)
    h = feld_bytes(1, typ.encode()) + feld_varint(3, len(b))
    return struct.pack(">I", len(h)) + h + b


def kopf_bauen() -> bytes:
    bbox = (feld_varint(1, _zz(int(13.0 * 1e9))) + feld_varint(2, _zz(int(13.1 * 1e9)))
            + feld_varint(3, _zz(int(52.42 * 1e9))) + feld_varint(4, _zz(int(52.38 * 1e9))))
    return (feld_bytes(1, bbox) + feld_bytes(4, b"OsmSchema-V0.6") + feld_bytes(4, b"DenseNodes")
            + feld_bytes(16, b"kiezatlas a3_pbf_schreiben") + feld_varint(32, 1_793_836_800))


def schreiben(ziel: Path) -> Path:
    ziel.write_bytes(blob("OSMHeader", kopf_bauen()) + blob("OSMData", block_bauen()))
    return ziel


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Aufruf: python -I pruefen/a3_pbf_schreiben.py ZIELDATEI")
    print(schreiben(Path(sys.argv[1])))
