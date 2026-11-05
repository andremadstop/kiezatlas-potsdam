"""Prüfung Paket A8 (GIS-Export): GeoPackage, CSV, QGIS-Projekt, Steckbriefe gegen die Abnahme.

Prüft ein Export-Verzeichnis (Standard daten/export/):
  1. GeoPackage gültig: application_id, user_version, integrity_check, Pflichttabellen, jede Geometrie mit
     GP-Kopf, SRS 25833 (Kopf, gpkg_geometry_columns, gpkg_contents), WKB-Typ wie erklärt, Hülle im Kopf =
     Hülle aus den Koordinaten, Lage im Raum Potsdam, gpkg_contents-Hülle umfasst alle Objekte.
  2. Inhalt = Quelle: Zeilen und Werte gegen daten/planer.js, einrichtungen.js, erreichbar.js, zellen.js
     (jede Zahl, jede Zelle), CSV = GPKG (Zeilen, Spalten, Werte), optional Zählung gegen die Datenbank.
  3. Keine Adresse: keine Adress- oder Kontaktspalte, kein Wert mit Hausnummer, PLZ, Telefon oder E-Mail
     (GPKG, CSV, Steckbriefe), keine Namen mit Personenbezug (Tagespflege, Frau, Herr).
  4. Keine feinere Altersklasse je Zelle: Spalten der Zellebene exakt nach Positivliste; keine Feldnamen der
     feinen Zensusklassen (pruefen/daten.py) in irgendeiner Tabelle oder CSV.
  5. Kein OSM in den Dateien ohne _odbl: keine Quelle osm, keine Methode fussweg, kein „OpenStreetMap“ oder
     „ODbL“ in GPKG, csv/, Steckbriefen; _odbl-Dateien (falls vorhanden) tragen den ODbL-Vermerk.
  6. Vermerke: jeder dl-de-Vermerk mit „Daten verändert (eigene Berechnung)“ und Link; README nennt alle.
  7. QGIS: .qgz enthält ein wohlgeformtes .qgs, jede Ebene zeigt auf eine vorhandene Datei und Tabelle,
     Stile (Dateien und layer_styles) wohlgeformt, Klassenfelder vorhanden, jede vorkommende Kategorie hat
     eine eigene Farbe, keine Orange- oder Gelbtöne.
  8. Steckbriefe: einer je Raumeinheit, Werte wie planer.js, keine Platzhalter (None, nan, undefined), keine
     Gedankenstrich-Ketten.

Aufruf: python -I pruefen/A8_export.py [--ziel daten/export] [--quelle daten] [--odbl-erwartet]
Mit PGHOST/PGUSER/PGPASSWORD (Leserolle) werden zusätzlich die Zeilen gegen die Datenbank gezählt.
Rückgabe 0 = 0 Befunde.
"""

from __future__ import annotations

import argparse
import colorsys
import csv
import importlib.util
import os
import re
import sqlite3
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
befunde: list[str] = []


def pruef(ok: bool, text: str) -> bool:
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        befunde.append(text)
    return ok


sys.dont_write_bytecode = True  # kein __pycache__ im Worktree
_spec = importlib.util.spec_from_file_location("p0_daten", WURZEL / "pruefen" / "daten.py")
p0 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p0)
FEINE_KLASSEN = p0.FEINE_KLASSEN
ADRESSFELDER = p0.ADRESSFELDER | {"plz", "postleitzahl", "ort_strasse", "anschrift", "web", "url_web", "mail"}
# Bestehende fünf Altersklassen und alle anderen Zensusmerkmale gehören nicht in die Zellebene des Exports
ZENSUS_ZELLE_SPALTEN = {"a_ges", "a_u18", "a_18_29", "a_30_49", "a_50_64", "a_65p", "d_alter", "q_u18", "q_65p"}

ADRESS_MUSTER = [
    re.compile(r"\b\d{5}\s+Potsdam\b"),
    re.compile(r"(stra(ß|ss)e|str\.|weg|allee|platz|damm|ring|chaussee|ufer|gasse)\s+\d+\s?[a-z]?\b", re.I),
    re.compile(r"\b0\d{2,4}[ /-]?\d{3,}[ -]?\d*\b(?=\D|$)"),
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
]
# Amtliche Einrichtungsnamen (MBJS), die eine Anschrift als Namen tragen. Kein Adressfeld, kein Personenbezug;
# derselbe Name steht in daten/einrichtungen.js (A6). Jede Ausnahme einzeln, mit id, damit neue Treffer auffallen.
NAMENS_AUSNAHMEN = {"KTS004377": 'Hort"Am Schulplatz 1"', "KTS004427": "KinderGarten Schulplatz 1"}
PERSON_MUSTER = re.compile(r"Tagespflege|Tagesmutter|Tagesvater|\bFrau\b|\bHerr\b")
OSM_MUSTER = re.compile(r"OpenStreetMap|\bODbL\b|fussweg|osm_id")


def js(p: Path):
    return p0.js_lesen(p)[2]


# ------------------------------------------------------------------------------------------- WKB
def wkb_lesen(b: bytes, o: int = 0):
    """Gibt (typ, [koordinaten], offset) zurück; Punkt, Polygon, Multipolygon (Little Endian)."""
    if b[o] != 1:
        raise ValueError("WKB nicht Little Endian")
    (typ,) = struct.unpack_from("<I", b, o + 1)
    o += 5
    pk = []
    if typ == 1:
        pk.append(struct.unpack_from("<dd", b, o))
        return typ, pk, o + 16
    if typ == 3:
        (ringe,) = struct.unpack_from("<I", b, o)
        o += 4
        for _ in range(ringe):
            (n,) = struct.unpack_from("<I", b, o)
            o += 4
            pk.extend(struct.unpack_from("<dd", b, o + 16 * i) for i in range(n))
            o += 16 * n
        return typ, pk, o
    if typ == 6:
        (n,) = struct.unpack_from("<I", b, o)
        o += 4
        for _ in range(n):
            t, k, o = wkb_lesen(b, o)
            if t != 3:
                raise ValueError("Multipolygon mit Nicht-Polygon")
            pk.extend(k)
        return typ, pk, o
    raise ValueError(f"WKB-Typ {typ} nicht erwartet")


TYPNR = {"POINT": 1, "POLYGON": 3, "MULTIPOLYGON": 6}


def gpkg_pruefen(pfad: Path, erwartet_odbl: bool) -> dict:
    print(f"\n[1] GeoPackage {pfad.name}")
    c = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
    pruef(c.execute("PRAGMA application_id").fetchone()[0] == 0x47504B47, "application_id = GPKG")
    pruef(c.execute("PRAGMA user_version").fetchone()[0] in (10200, 10300, 10400), "user_version 1.2 bis 1.4")
    pruef(c.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "integrity_check ok")
    pruef(c.execute("PRAGMA foreign_key_check").fetchall() == [], "foreign_key_check leer")
    tabellen = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for t in ("gpkg_spatial_ref_sys", "gpkg_contents", "gpkg_geometry_columns"):
        pruef(t in tabellen, f"Pflichttabelle {t}")
    srs = {
        r[0]: r[1]
        for r in c.execute("SELECT srs_id, organization || ':' || organization_coordsys_id FROM gpkg_spatial_ref_sys")
    }
    pruef(srs.get(25833) == "EPSG:25833" and {-1, 0, 4326} <= set(srs), "SRS -1, 0, 4326, 25833 eingetragen")
    inhalt = {
        r[0]: r
        for r in c.execute(
            "SELECT table_name, data_type, identifier, description, min_x, min_y, "
            "max_x, max_y, srs_id FROM gpkg_contents"
        )
    }
    geom = {
        r[0]: (r[1], r[2], r[3])
        for r in c.execute("SELECT table_name, column_name, geometry_type_name, srs_id FROM gpkg_geometry_columns")
    }
    pruef(set(inhalt) <= tabellen, "jede Zeile in gpkg_contents hat eine Tabelle")
    erg = {"tabellen": {}, "spalten": {}, "text": []}
    for name, (_, dtype, *_rest) in sorted(inhalt.items()):
        spalten = [r[1] for r in c.execute(f'PRAGMA table_info("{name}")')]
        erg["spalten"][name] = spalten
        zeilen = c.execute(f'SELECT * FROM "{name}"').fetchall()
        erg["tabellen"][name] = (spalten, zeilen)
        for z in zeilen:
            erg["text"].extend(str(v) for v in z if isinstance(v, str))
        erg["text"].extend(str(v) for v in inhalt[name][2:4] if v)
        if dtype != "features":
            continue
        spalte, typ, srid = geom[name]
        pruef(srid == 25833 and inhalt[name][8] == 25833, f"{name}: SRS 25833 in gpkg_contents und geometry_columns")
        gi = spalten.index(spalte)
        fehler, lagefehler, huellfehler = [], 0, 0
        gx1 = gy1 = 1e18
        gx2 = gy2 = -1e18
        for z in zeilen:
            b = z[gi]
            try:
                if b[:2] != b"GP" or b[2] != 0:
                    raise ValueError("Kopf")
                flags = b[3]
                (s,) = struct.unpack_from("<i", b, 4)
                if s != 25833:
                    raise ValueError(f"srs {s}")
                env = (flags >> 1) & 7
                o = 8 + (32 if env == 1 else 0)
                t, pk, ende = wkb_lesen(b, o)
                if ende != len(b):
                    raise ValueError("Rest nach WKB")
                if t != TYPNR[typ]:
                    raise ValueError(f"WKB {t} statt {typ}")
                xs, ys = [p[0] for p in pk], [p[1] for p in pk]
                if env == 1:
                    h = struct.unpack_from("<4d", b, 8)
                    if max(abs(h[0] - min(xs)), abs(h[1] - max(xs)), abs(h[2] - min(ys)), abs(h[3] - max(ys))) > 1e-6:
                        huellfehler += 1
                elif typ != "POINT":
                    raise ValueError("Fläche ohne Hülle")
                if not (340000 <= min(xs) and max(xs) <= 400000 and 5770000 <= min(ys) and max(ys) <= 5850000):
                    lagefehler += 1
                gx1, gx2, gy1, gy2 = min(gx1, min(xs)), max(gx2, max(xs)), min(gy1, min(ys)), max(gy2, max(ys))
            except (ValueError, struct.error, TypeError) as e:
                fehler.append(str(e))
        pruef(
            not fehler,
            f"{name}: {len(zeilen)} Geometrien mit GP-Kopf, SRS 25833, WKB {typ}"
            + (f" ({len(fehler)} Fehler, z. B. {fehler[0]})" if fehler else ""),
        )
        pruef(huellfehler == 0, f"{name}: Hülle im Kopf = Hülle der Koordinaten")
        pruef(lagefehler == 0, f"{name}: alle Objekte im Raum Potsdam (x 340-400 km, y 5770-5850 km)")
        _, _, _, _, x1, y1, x2, y2, _ = inhalt[name]
        pruef(
            zeilen and x1 <= gx1 + 1e-6 and y1 <= gy1 + 1e-6 and x2 >= gx2 - 1e-6 and y2 >= gy2 - 1e-6,
            f"{name}: Hülle in gpkg_contents umfasst alle Objekte",
        )
    erg["contents"] = inhalt
    erg["c"] = c
    return erg


# ------------------------------------------------------------------------------------------- Hauptteil
def zahl_gleich(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    try:
        if isinstance(b, bool) or isinstance(a, bool):
            return int(a) == int(b)
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return False


def csv_lesen(p: Path) -> tuple[list[str], list[list[str]]]:
    with p.open(encoding="utf-8-sig", newline="") as f:
        r = list(csv.reader(f, delimiter=";"))
    return r[0], r[1:]


def farben(text: str) -> list[str]:
    hexe = re.findall(r"#([0-9a-fA-F]{6})\b", text)
    rgb = re.findall(r'value="(\d{1,3}),(\d{1,3}),(\d{1,3}),\d{1,3}"', text)
    aus = [h.lower() for h in hexe] + [f"{int(r):02x}{int(g):02x}{int(b):02x}" for r, g, b in rgb]
    return aus


def orange_gelb(h: str) -> bool:
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    return 15 / 360 <= hue <= 70 / 360 and sat > 0.25 and 0.15 < light < 0.95


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ziel", default=str(WURZEL / "daten" / "export"))
    ap.add_argument("--quelle", default=str(WURZEL / "daten"))
    ap.add_argument("--odbl-erwartet", action="store_true")
    a = ap.parse_args()
    ziel, quelle = Path(a.ziel), Path(a.quelle)
    planer = js(quelle / "planer.js")
    ein = js(quelle / "einrichtungen.js")
    err = js(quelle / "erreichbar.js")
    zellen = js(quelle / "zellen.js" if (quelle / "zellen.js").exists() else WURZEL / "daten" / "zellen.js")
    ids = [f["properties"]["id"] for f in zellen["features"]]
    zp = {f["properties"]["id"]: f["properties"] for f in zellen["features"]}

    haupt = ziel / "kiezatlas_potsdam.gpkg"
    odbl = ziel / "kiezatlas_potsdam_odbl.gpkg"
    pruef(haupt.exists(), "kiezatlas_potsdam.gpkg vorhanden")
    g = gpkg_pruefen(haupt, False)
    T = g["tabellen"]

    print("\n[2] Inhalt gegen die Quelldateien")
    erwartet = {
        "raumeinheit": len(planer["raeume"]),
        "versorgung": sum(len(r["werte"]) for r in planer["raeume"].values()),
        "einrichtung": len(ein["features"]),
        "zelle": len(ids),
    }
    for name, n in erwartet.items():
        pruef(len(T[name][1]) == n, f"{name}: {len(T[name][1])} Zeilen, Quelle {n}")
    # versorgung: jede Zahl, Status, vorläufig
    sp, zeilen = T["versorgung"]
    ix = {s: i for i, s in enumerate(sp)}
    quellwerte = [(nr, w) for nr, r in planer["raeume"].items() for w in r["werte"]]
    abw = 0
    for z, (nr, w) in zip(zeilen, quellwerte):
        if not (
            z[ix["raum_nr"]] == nr
            and z[ix["kennzahl"]] == w["kennzahl"]
            and z[ix["art"]] == w["art"]
            and zahl_gleich(z[ix["wert"]], w.get("wert"))
            and z[ix["status"]] == w["status"]
            and bool(z[ix["vorlaeufig"]]) == bool(w.get("vorlaeufig", False))
            and z[ix["unsicherheit"]] == w.get("unsicherheit")
            and zahl_gleich(z[ix["richtwert"]], (w.get("richtwert") or {}).get("wert"))
        ):
            abw += 1
    pruef(
        abw == 0, f"versorgung: alle {len(quellwerte)} Werte mit Status, vorläufig, Maßstab, Unsicherheit wie planer.js"
    )
    pruef(
        all(z[ix["status"]] in ("amtlich", "orientierung") for z in zeilen),
        "versorgung: Status nur amtlich/orientierung",
    )
    gs = [z for z in zeilen if z[ix["art"]] == "grundschule"]
    pruef(
        gs and all(z[ix["vorlaeufig"]] == 1 for z in gs),
        f"versorgung: {len(gs)} Grundschulwerte alle vorläufig (ohne H2)",
    )
    pruef(all(z[ix["unsicherheit"]] for z in zeilen), "versorgung: jeder Wert mit Unsicherheitshinweis")
    # raumeinheit breit
    sp, zeilen = T["raumeinheit"]
    ix = {s: i for i, s in enumerate(sp)}
    abw = 0
    for z in zeilen:
        r = planer["raeume"][z[ix["nr"]]]
        if z[ix["ew"]] != r["ew"] or z[ix["name"]] != r["name"]:
            abw += 1
        vs = [v for v in T["versorgung"][1] if v[T["versorgung"][0].index("raum_nr")] == z[ix["nr"]]]
        for v in vs:
            if not zahl_gleich(z[ix[v[T["versorgung"][0].index("spalte")]]], v[T["versorgung"][0].index("wert")]):
                abw += 1
    pruef(abw == 0, "raumeinheit: Name, Einwohner und jede Kennzahlspalte wie versorgung bzw. planer.js")
    pruef(
        all(z[ix["ew"]] is None or z[ix["ew"]] % planer["rundung"]["ew"] == 0 for z in zeilen),
        f"raumeinheit: Einwohner auf {planer['rundung']['ew']} gerundet",
    )
    # einrichtung
    sp, zeilen = T["einrichtung"]
    ix = {s: i for i, s in enumerate(sp)}
    abw = 0
    for z, f in zip(zeilen, ein["features"]):
        p = f["properties"]
        if any(
            not zahl_gleich(z[ix[k]], p.get(k)) if k in ("plaetze", "schueler", "in_potsdam") else z[ix[k]] != p.get(k)
            for k in ("id", "art", "unterart", "name", "plaetze", "schueler", "schueler_stand", "status", "in_potsdam")
        ):
            abw += 1
    pruef(abw == 0, "einrichtung: alle Felder wie einrichtungen.js")
    pruef(all(z[ix["name"]] is None for z in zeilen if z[ix["quelle"]] == "lgb"), "einrichtung: ALKIS-Lagen ohne Namen")
    # zelle
    sp, zeilen = T["zelle"]
    ix = {s: i for i, s in enumerate(sp)}
    abw = 0
    for i, (z, gid) in enumerate(zip(zeilen, ids)):
        if z[ix["gitter_id"]] != gid or z[ix["ew"]] != zp[gid].get("ew") or z[ix["stadtteil"]] != zp[gid].get("st"):
            abw += 1
        for art in err["arten"]:
            if not zahl_gleich(z[ix[f"m_{art}"]], err["werte"][art][i]):
                abw += 1
    pruef(
        abw == 0,
        f"zelle: gitter_id, Einwohner, Stadtteil und {len(err['arten'])} Entfernungen je Zelle "
        "wie zellen.js/erreichbar.js",
    )
    # CSV = GPKG
    for name, (sp, zeilen) in T.items():
        if name == "layer_styles":
            continue
        p = ziel / "csv" / f"{name}.csv"
        if not pruef(p.exists(), f"csv/{name}.csv vorhanden"):
            continue
        kopf, cz = csv_lesen(p)
        ohne = [s for s in sp if s not in ("fid", "geom")]
        pruef(kopf[: len(ohne)] == ohne, f"csv/{name}.csv: Spalten wie GPKG")
        pruef(len(cz) == len(zeilen), f"csv/{name}.csv: {len(cz)} Zeilen wie GPKG")
        abw = 0
        for gz, c in zip(zeilen, cz):
            for k, wert in zip(ohne, c):
                v = gz[sp.index(k)]
                if v is None:
                    abw += wert != ""
                elif isinstance(v, (int, float)):
                    abw += not zahl_gleich(v, wert)
                else:
                    abw += str(v) != wert
        pruef(abw == 0, f"csv/{name}.csv: Werte wie GPKG")
    # Datenbank (optional)
    fixture = bool(planer.get("fixture"))
    if os.environ.get("PGUSER") and not fixture:
        try:
            import psycopg

            with psycopg.connect() as con:
                con.read_only = True
                for name, sql in (
                    ("gruenflaeche", "SELECT count(*) FROM auswertung.gruenflaeche"),
                    ("haltestelle", "SELECT count(*) FROM auswertung.haltestelle"),
                    ("einrichtung", "SELECT count(*) FROM auswertung.einrichtung"),
                    ("stadtteil", "SELECT count(*) FROM public.stadtteil"),
                ):
                    n = con.execute(sql).fetchone()[0]
                    pruef(len(T[name][1]) == n, f"{name}: {len(T[name][1])} Zeilen, Datenbank {n}")
                # Lage der Einrichtungen: GPKG gegen Datenbank und gegen die WGS84-Koordinaten der Datei
                sp, zeilen = T["einrichtung"]
                xy = {z[sp.index("id")]: struct.unpack_from("<dd", z[sp.index("geom")], 13) for z in zeilen}
                ll = {f["properties"]["id"]: f["geometry"]["coordinates"] for f in ein["features"]}
                k = list(xy)
                d = con.execute(
                    """SELECT max(ST_Distance(ST_SetSRID(ST_Point(x, y), 25833),
                                              ST_Transform(ST_SetSRID(ST_Point(lon, lat), 4326), 25833)))
                       FROM unnest(%s::float8[], %s::float8[], %s::float8[], %s::float8[]) AS t(x, y, lon, lat)""",
                    ([xy[i][0] for i in k], [xy[i][1] for i in k], [ll[i][0] for i in k], [ll[i][1] for i in k]),
                ).fetchone()[0]
                pruef(
                    d < 2.0, f"einrichtung: Lage weicht höchstens {d:.2f} m von einrichtungen.js ab (Rundung 5 Stellen)"
                )
        except Exception as e:  # noqa: BLE001
            pruef(False, f"Datenbankvergleich: {e}")
    else:
        print("  --    Datenbankvergleich ausgelassen (keine PG-Umgebung oder Beispieldaten)")

    print("\n[3] Keine Adresse, keine Kontakte, kein Personenbezug")
    alle_spalten = {s.lower() for sp in g["spalten"].values() for s in sp}
    for p in (ziel / "csv").glob("*.csv"):
        alle_spalten |= {s.lower() for s in csv_lesen(p)[0]}
    pruef(
        not (alle_spalten & ADRESSFELDER), f"keine Adress- oder Kontaktspalte ({sorted(alle_spalten & ADRESSFELDER)})"
    )
    texte = [t for t in g["text"] if not t.lstrip().startswith(("<!DOCTYPE qgis", "<qgis"))]
    for p in (ziel / "csv").glob("*.csv"):
        _, cz = csv_lesen(p)
        texte.extend(v for z in cz for v in z if v and not v.startswith(("POLYGON", "MULTIPOLYGON")))
    for p in sorted((ziel / "steckbriefe").glob("*.html")):
        t = re.sub(r"<svg.*?</svg>", "", p.read_text(encoding="utf-8"), flags=re.S)
        t = re.sub(r"<style>.*?</style>", "", t, flags=re.S)
        texte.append(re.sub(r"<[^>]+>", " ", t))
    ein_sp, ein_z = T["einrichtung"]
    amtlich = {
        z[ein_sp.index("id")]: z[ein_sp.index("name")] for z in ein_z if z[ein_sp.index("id")] in NAMENS_AUSNAHMEN
    }
    pruef(
        fixture or amtlich == NAMENS_AUSNAHMEN,
        f"Ausnahmen amtlicher Einrichtungsnamen stimmen ({len(NAMENS_AUSNAHMEN)} Stück)",
    )
    bereinigt = []
    for t in texte:
        for n in NAMENS_AUSNAHMEN.values():
            t = t.replace(n, "").replace(n.replace('"', '""'), "")
        bereinigt.append(t)
    treffer = sorted({m.group(0) for t in bereinigt for mu in ADRESS_MUSTER for m in mu.finditer(t)})
    pruef(
        not treffer,
        f"kein Wert mit Hausnummer, PLZ, Telefon oder E-Mail ({treffer[:8]}); Ausnahme nur die "
        f"{len(NAMENS_AUSNAHMEN)} amtlichen Namen {sorted(NAMENS_AUSNAHMEN.values())}",
    )
    namen = [z[T["einrichtung"][0].index("name")] or "" for z in T["einrichtung"][1]]
    pers = sorted({n for n in namen if PERSON_MUSTER.search(n)})
    pruef(not pers, f"keine Einrichtungsnamen mit Personenbezug ({pers[:5]})")

    print("\n[4] Keine feinere Altersklasse je Zelle")
    erlaubt = {"fid", "geom", "gitter_id", "stadtteil", "raum_nr", "ew", "stand", "lizenz"} | {
        f"m_{a}" for a in err["arten"]
    }
    pruef(
        set(g["spalten"]["zelle"]) == erlaubt,
        f"zelle: Spalten exakt {len(erlaubt)} nach Positivliste "
        f"(fremd: {sorted(set(g['spalten']['zelle']) - erlaubt)})",
    )
    pruef(
        not (set(csv_lesen(ziel / "csv" / "zelle.csv")[0]) - erlaubt - {"wkt"}), "csv/zelle.csv: nur erlaubte Spalten"
    )
    pruef(
        not (alle_spalten & FEINE_KLASSEN),
        f"kein Feldname einer feinen Zensusklasse in GPKG oder CSV ({sorted(alle_spalten & FEINE_KLASSEN)})",
    )
    pruef(not (set(g["spalten"]["zelle"]) & ZENSUS_ZELLE_SPALTEN), "zelle: auch keine der fünf Altersklassen je Zelle")

    print("\n[5] Kein OSM in den Dateien ohne _odbl")
    pruef(
        not any(OSM_MUSTER.search(t) for t in g["text"]),
        "kiezatlas_potsdam.gpkg: kein OpenStreetMap, ODbL, fussweg, osm_id",
    )
    erlaubte_q = None if fixture else {"mbjs", "lgb"}
    pruef(
        all(
            z[T["einrichtung"][0].index("quelle")] != "osm"
            and (erlaubte_q is None or z[T["einrichtung"][0].index("quelle")] in erlaubte_q)
            for z in T["einrichtung"][1]
        ),
        "einrichtung: Quellen nur mbjs und lgb (Fixtures: nicht osm)",
    )
    pruef(
        all(z[T["versorgung"][0].index("methode")] == "luftlinie" for z in T["versorgung"][1]),
        "versorgung: Methode nur luftlinie",
    )
    osm_csv = [p.name for p in (ziel / "csv").glob("*.csv") if OSM_MUSTER.search(p.read_text(encoding="utf-8-sig"))]
    pruef(not osm_csv, f"csv/: kein OSM-Wert ({osm_csv})")
    osm_sb = [p.name for p in (ziel / "steckbriefe").glob("*.html") if OSM_MUSTER.search(p.read_text(encoding="utf-8"))]
    pruef(not osm_sb, f"steckbriefe/: kein OSM-Wert ({osm_sb[:3]})")
    pruef(not any(p.name.endswith("_odbl.csv") for p in (ziel / "csv").glob("*")), "csv/ ohne _odbl-Datei")
    if odbl.exists() or a.odbl_erwartet:
        if pruef(odbl.exists(), "kiezatlas_potsdam_odbl.gpkg vorhanden"):
            go = gpkg_pruefen(odbl, True)
            lz = go["tabellen"]["lizenz"][1]
            pruef(
                lz and all("OpenStreetMap" in z[3] and "odbl/1-0" in z[3] for z in lz),
                "_odbl.gpkg: Lizenztabelle mit ODbL-Vermerk und Link",
            )
            pruef(
                all(
                    "OpenStreetMap" in (r[3] or "")
                    for n, r in go["contents"].items()
                    if n not in ("lizenz", "layer_styles")
                ),
                "_odbl.gpkg: jede Ebene mit ODbL-Vermerk in der Beschreibung",
            )
            pruef(
                all(n.endswith("_odbl") for n in go["contents"] if n not in ("lizenz", "layer_styles")),
                "_odbl.gpkg: Ebenennamen enden auf _odbl",
            )
            pruef(
                all(p.name.endswith("_odbl.csv") for p in (ziel / "csv_odbl").glob("*.csv") if p.name != "lizenz.csv"),
                "csv_odbl/: nur _odbl-Dateien",
            )
            if "einrichtung_odbl" in go["tabellen"]:
                pruef("name" not in go["spalten"]["einrichtung_odbl"], "einrichtung_odbl: ohne Namen")
    else:
        print("  --    keine _odbl-Datei (A3/A5b leer); ODbL-Pfad mit --odbl-erwartet gegen Fixtures prüfen")

    print("\n[6] Vermerke")
    lz = T["lizenz"]
    li = lz[0].index("vermerk")
    for z in lz[1]:
        v = z[li]
        if "dl-de/by-2-0" in v:
            teile = [s for s in v.split("; ") if "dl-de/by-2-0" in s]
            pruef(
                all(
                    "Daten verändert (eigene Berechnung)" in s and "(https://www.govdata.de/dl-de/by-2-0)" in s
                    for s in teile
                ),
                f"lizenz {z[lz[0].index('ebene')]}: jeder dl-de-Vermerk mit „Daten verändert (eigene Berechnung)“ "
                "und Link",
            )
        if "CC BY 4.0" in v:
            pruef(
                "creativecommons.org/licenses/by/4.0" in v, f"lizenz {z[lz[0].index('ebene')]}: CC-BY-Vermerk mit Link"
            )
    readme = (ziel / "README.md").read_text(encoding="utf-8")
    for k in (
        "Statistische Ämter des Bundes und der Länder",
        "Ministerium für Bildung, Jugend und Sport",
        "GeoBasis-DE/LGB",
        "VBB Verkehrsverbund",
        "OpenStreetMap-Mitwirkende",
        "Daten verändert (eigene Berechnung)",
        "https://www.govdata.de/dl-de/by-2-0",
        "EPSG:25833",
        "Cell-Key",
        "15.05.2022",
        "orientierung",
        "vorlaeufig",
        "Keine Adressen",
    ):
        pruef(k in readme, f"README nennt „{k}“")
    lic_codes = {
        z[sp.index("lizenz")] for name, (sp, zz) in T.items() if "lizenz" in sp and name != "lizenz" for z in zz
    }
    pruef(
        lic_codes <= {"dl-de/by-2-0", "CC BY 4.0"},
        f"Lizenzkürzel je Zeile nur dl-de/by-2-0 und CC BY 4.0 ({sorted(lic_codes)})",
    )

    print("\n[7] QGIS-Projekt und Stile")
    qgz = ziel / "kiezatlas_potsdam.qgz"
    with zipfile.ZipFile(qgz) as z:
        namen_zip = z.namelist()
        pruef(len([n for n in namen_zip if n.endswith(".qgs")]) == 1, f".qgz enthält genau ein .qgs ({namen_zip})")
        qgs = z.read([n for n in namen_zip if n.endswith(".qgs")][0]).decode("utf-8")
    try:
        root = ET.fromstring(qgs.split("\n", 1)[1])
        pruef(True, ".qgs wohlgeformt")
    except ET.ParseError as e:
        root = None
        pruef(False, f".qgs wohlgeformt ({e})")
    if root is not None:
        pruef(root.findtext("projectCrs/spatialrefsys/authid") == "EPSG:25833", "Projekt-KBS EPSG:25833")
        pruef(root.findtext("properties/Paths/Absolute") == "false", "relative Pfade")
        ml = root.findall("projectlayers/maplayer")
        pruef(
            len(ml) == len(root.findall("layer-tree-group/layer-tree-layer")) and ml,
            f"{len(ml)} Ebenen im Baum und in projectlayers",
        )
        for m in ml:
            ds = m.findtext("datasource")
            datei, _, lname = ds.partition("|layername=")
            ziel_gpkg = (qgz.parent / datei).resolve()
            ok = ziel_gpkg.exists()
            if ok:
                cc = sqlite3.connect(f"file:{ziel_gpkg}?mode=ro", uri=True)
                ok = cc.execute("SELECT 1 FROM gpkg_contents WHERE table_name=?", (lname,)).fetchone() is not None
                felder = {r[1] for r in cc.execute(f'PRAGMA table_info("{lname}")')}
                r2 = m.find("renderer-v2")
                if r2 is not None and r2.get("attr"):
                    pruef(r2.get("attr") in felder, f"Ebene {lname}: Klassenfeld {r2.get('attr')} vorhanden")
                    if r2.get("type") == "categorizedSymbol":
                        werte = {r[0] for r in cc.execute(f'SELECT DISTINCT "{r2.get("attr")}" FROM "{lname}"')}
                        kat = {c.get("value") for c in r2.findall("categories/category")}
                        pruef(
                            werte <= kat,
                            f"Ebene {lname}: jede vorkommende Kategorie hat ein Symbol ({sorted(werte - kat)})",
                        )
                        syms = r2.findall("symbols/symbol")
                        f_sym = [farben(ET.tostring(s, encoding="unicode"))[0] for s in syms]
                        pruef(
                            len(set(f_sym)) == len(f_sym) or lname == "gruenflaeche",
                            f"Ebene {lname}: eigene Farbe je Kategorie",
                        )
                cc.close()
            pruef(ok, f"Ebene {m.findtext('layername')}: {ds} vorhanden")
    for p in sorted((ziel / "stile").glob("*.qml")):
        t = p.read_text(encoding="utf-8")
        try:
            ET.fromstring(t.split("\n", 1)[1])
            pruef(True, f"stile/{p.name} wohlgeformt")
        except ET.ParseError as e:
            pruef(False, f"stile/{p.name} wohlgeformt ({e})")
    st = g["tabellen"].get("layer_styles")
    if pruef(st is not None, "GPKG: Tabelle layer_styles"):
        sp, zeilen = st
        for z in zeilen:
            qml = z[sp.index("styleQML")]
            name = z[sp.index("f_table_name")]
            pruef(
                qml == (ziel / "stile" / f"{name}.qml").read_text(encoding="utf-8")
                and z[sp.index("useAsDefault")] == 1,
                f"layer_styles {name}: Standardstil = stile/{name}.qml",
            )
    alle_farben = farben(qgs) + [
        f for p in (ziel / "stile").glob("*.qml") for f in farben(p.read_text(encoding="utf-8"))
    ]
    alle_farben += [f for p in (ziel / "steckbriefe").glob("*.html") for f in farben(p.read_text(encoding="utf-8"))]
    if st is not None:
        alle_farben += [f for z in st[1] for f in farben(z[st[0].index("styleQML")])]
    og = sorted({f for f in alle_farben if orange_gelb(f)})
    pruef(not og, f"keine Orange- oder Gelbtöne in Stilen (Dateien, layer_styles), Projekt und Steckbriefen ({og})")

    print("\n[8] Steckbriefe")
    sb = sorted((ziel / "steckbriefe").glob("*.html"))
    pruef({p.stem for p in sb} == set(planer["raeume"]), f"{len(sb)} Steckbriefe, einer je Raumeinheit")
    platz, strich, werte_fehlen, fremd = [], [], [], []
    from html import escape as _esc

    for p in sb:
        t = p.read_text(encoding="utf-8")
        sichtbar = re.sub(r"<(style|svg).*?</\1>", "", t, flags=re.S)
        # Texte aus planer.js (A6) wörtlich übernommen: Platzhalter darin sind ein Befund für A6, nicht für A8
        for w in planer["raeume"][p.stem]["werte"]:
            u = _esc(w.get("unsicherheit") or "")
            if u and re.search(r"\bNone\b|\bnan\b|\bundefined\b", u):
                fremd.append(f"{p.stem}:{w['kennzahl']}")
            sichtbar = sichtbar.replace(u, "")
            erster = _esc((w.get("unsicherheit") or "").split(". ")[0].rstrip("."))
            if erster:
                sichtbar = sichtbar.replace(erster, "")
        sichtbar = re.sub(r"<[^>]+>", " ", sichtbar)
        if re.search(r"\bNone\b|\bnan\b|\bundefined\b|\bnull\b", sichtbar):
            platz.append(p.name)
        if "—" in sichtbar or re.search(r"\s–\s.*\s–\s", sichtbar):
            strich.append(p.name)
        r = planer["raeume"][p.stem]
        for w in r["werte"]:
            if w.get("wert") is None:
                continue
            v = w["wert"]
            txt = f"{v:.2f}".replace(".", ",") if isinstance(v, float) else f"{v:,}".replace(",", ".")
            if f">{txt}" not in t:
                werte_fehlen.append(f"{p.stem}:{w['kennzahl']}:{txt}")
        if "<svg" not in t or "@page" not in t:
            platz.append(p.name + " (Karte oder @page fehlt)")
    pruef(not platz, f"keine Platzhalter, Karte und @page vorhanden ({platz[:3]})")
    if fremd:
        print(f"  HINWEIS planer.js (A6) enthält Platzhalter in unsicherheit, wörtlich übernommen: {fremd}")
    pruef(not strich, f"keine Gedankenstriche oder Strich-Ketten ({strich[:3]})")
    pruef(not werte_fehlen, f"jede Zahl aus planer.js steht im Steckbrief ({werte_fehlen[:3]})")

    print(f"\n{len(befunde)} Befunde")
    for b in befunde:
        print("  - " + b)
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
