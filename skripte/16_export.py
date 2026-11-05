"""Paket A8: GIS-Export des Kiezatlas Potsdam (GeoPackage, CSV, QGIS-Projekt, Steckbriefe).

Kein Netzabruf, kein Schreiben in die Datenbank. Liest die veröffentlichten Datendateien von A6 (daten/planer.js,
daten/einrichtungen.js, daten/erreichbar.js, daten/zellen.js) und holt die genaue Geometrie in EPSG:25833 mit der
Leserolle aus der Datenbank (public.stadtteil bzw. public.planungsraum, auswertung.einrichtung,
auswertung.gruenflaeche, auswertung.haltestelle). Die Werte stammen damit aus denselben Dateien wie die Seite;
Rundung, Geheimhaltung und Unsicherheitshinweise von A6 gelten unverändert.

Ausgabe (Standard daten/export/):
  kiezatlas_potsdam.gpkg          GeoPackage EPSG:25833 ohne OSM-Anteil (dl-de/by-2-0, dl-zero-de/2.0, CC BY 4.0)
  kiezatlas_potsdam_odbl.gpkg     nur wenn *_odbl.js vorliegen (A3/A5b), Open Database License 1.0
  csv/<ebene>.csv                 dieselben Inhalte als CSV (Semikolon, UTF-8 mit BOM, Punkt als Dezimalzeichen)
  csv_odbl/<ebene>.csv            dito für die ODbL-Ebenen
  kiezatlas_potsdam.qgz           QGIS-Projekt mit relativen Pfaden und Stilen nach DESIGN.md
  stile/<ebene>.qml               dieselben Stile als Dateien (auch als Standardstil in der GPKG, layer_styles)
  steckbriefe/<nr>.html           druckbarer Steckbrief je Raumeinheit (A4, WeasyPrint, Karte nur aus eigenen Daten)
  README.md                       Lizenz, Vermerke, Methode, Ebenen und Felder
  belege/A8_export_<stand>.md     Lauf: Zahlen, Prüfsummen, was fehlt

Regeln (Prüfbericht 3, 4, 6, 15, 26): keine Adressen, keine Altersklassen je Zelle (nur Einwohner und Entfernungen),
kein OSM-Wert in der Datei ohne _odbl, jeder dl-de-Vermerk mit „Daten verändert (eigene Berechnung)“ und Link.

Aufruf (aus dem Worktree; Passwort nur aus der .env):
    set -a; . ../kiezatlas-potsdam/.env; set +a
    PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=mosidi_lesen PGPASSWORD="$LESE_PASSWORD" \\
    uv run --offline -q --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \\
        python -I skripte/16_export.py [--quelle daten] [--ziel daten/export]

Mit --quelle daten/fixtures und einem --ziel außerhalb von daten/export lässt sich der ODbL-Pfad gegen die
Beispieldaten prüfen. Fixtures nach daten/export zu schreiben, lehnt das Skript ab.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import struct
import sys
import zipfile
from html import escape
from pathlib import Path

import yaml

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "daten"
ZIEL_STANDARD = DATEN / "export"
SRID = 25833

DLDE = "https://www.govdata.de/dl-de/by-2-0"
DLZERO = "https://www.govdata.de/dl-de/zero-2-0"
ODBL = "https://opendatacommons.org/licenses/odbl/1-0/"
CCBY = "https://creativecommons.org/licenses/by/4.0/"
VERAENDERT = "Daten verändert (eigene Berechnung)"

LIZENZ_KURZ = {
    "mbjs": "dl-de/by-2-0",
    "lgb": "dl-de/by-2-0",
    "zensus": "dl-de/by-2-0",
    "vbb": "CC BY 4.0",
    "osm": "ODbL 1.0",
}
VERMERK = {
    "zensus": f"© Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 ({DLDE}), {VERAENDERT}",
    "mbjs": f"© Ministerium für Bildung, Jugend und Sport, dl-de/by-2-0 ({DLDE}), {VERAENDERT}",
    "lgb": f"© GeoBasis-DE/LGB, dl-de/by-2-0 ({DLDE}), {VERAENDERT}",
    "stadtteil": f"© Landeshauptstadt Potsdam, dl-zero-de/2.0 ({DLZERO})",
    "vbb": f"VBB Verkehrsverbund Berlin-Brandenburg GmbH, CC BY 4.0 ({CCBY}), {VERAENDERT}",
    "osm": f"© OpenStreetMap-Mitwirkende, Open Database License 1.0 ({ODBL}), {VERAENDERT}",
}

ART = {
    "kita": "Kita",
    "hort": "Hort",
    "grundschule": "Grundschule",
    "sek1": "Oberschule / Gesamtschule (Sek. I)",
    "gymnasium": "Gymnasium",
    "osz": "Oberstufenzentrum",
    "foerderschule": "Förderschule",
    "sonstige_schule": "sonstige Schule",
    "bibliothek": "Bibliothek",
    "feuerwehr": "Feuerwehr",
    "sport": "Sportstätte",
    "sonstiger_gemeinbedarf": "sonstiger Gemeinbedarf",
    "gruen": "Grünanlage oder Park",
    "oepnv": "ÖPNV",
}
# Farben nach DESIGN.md: kühle Reihe Wasser bis Tiefe, Grenzviolett nur für Grenzen; kein Orange, kein Gelb.
ART_FARBE = {
    "kita": "#1c4a5b",
    "hort": "#3b7684",
    "grundschule": "#2d5e86",
    "sek1": "#4a6f9e",
    "gymnasium": "#6d8cb8",
    "osz": "#8fa6c8",
    "foerderschule": "#4e7768",
    "sonstige_schule": "#7d998c",
    "bibliothek": "#7a3b57",
    "feuerwehr": "#9a2f2f",
    "sport": "#4d7a3c",
    "sonstiger_gemeinbedarf": "#4f5d64",
}
GRUEN_FARBE = {
    "gruenanlage": "#7fae8c",
    "park": "#5f9670",
    "freizeit": "#bccfbf",
    "kleingarten": "#c8d6c3",
    "friedhof": "#b3c2b6",
    "wald": "#a7bfa5",
}
EW_STUFEN = [  # (unten, oben, Farbe, Text); unter 10 Personen flach und grau wie auf der Seite
    (0.5, 9.5, "#cdd1cc", "1 bis 9 (unscharf)"),
    (9.5, 49.5, "#dce6e2", "10 bis 49"),
    (49.5, 99.5, "#a8c7c2", "50 bis 99"),
    (99.5, 199.5, "#6fa1a3", "100 bis 199"),
    (199.5, 349.5, "#3b7684", "200 bis 349"),
    (349.5, 100000, "#1c4a5b", "350 und mehr"),
]
INK, MUTED, LINIE, GRUND, AKZENT = "#13212a", "#4f5d64", "#cdd1cc", "#f1f2ee", "#6a2c82"

ADRESS_SPALTEN = {
    "strasse",
    "straße",
    "hausnr",
    "hausnummer",
    "adresse",
    "plz",
    "telefon",
    "fax",
    "email",
    "e_mail",
    "homepage",
    "web",
}


# ---------------------------------------------------------------------------------------------- Dateien lesen
def js_lesen(pfad: Path) -> tuple[str, dict]:
    text = pfad.read_text(encoding="utf-8")
    m = re.search(r"window\.([A-Za-z0-9_]+)\s*=\s*", text)
    if not m:
        raise SystemExit(f"{pfad}: keine Zuweisung window.NAME=")
    return text[: m.start()], json.loads(text[m.end() :].rstrip().rstrip(";"))


def optional(pfad: Path) -> dict | None:
    return js_lesen(pfad)[1] if pfad.exists() else None


def zell_ids(quelle: Path) -> list[str]:
    _, z = js_lesen(quelle / "zellen.js" if (quelle / "zellen.js").exists() else DATEN / "zellen.js")
    return [f["properties"]["id"] for f in z["features"]], {
        f["properties"]["id"]: f["properties"] for f in z["features"]
    }


# ---------------------------------------------------------------------------------------------- GeoPackage
def gp_blob(wkb: bytes, huelle: tuple[float, float, float, float] | None) -> bytes:
    """GeoPackage-Binärkopf (Version 0, Little Endian, Hülle minx maxx miny maxy oder keine) plus WKB."""
    if huelle is None:
        return b"GP" + bytes([0, 0x01]) + struct.pack("<i", SRID) + wkb
    minx, maxx, miny, maxy = huelle
    return b"GP" + bytes([0, 0x03]) + struct.pack("<i4d", SRID, minx, maxx, miny, maxy) + wkb


def punkt_wkb(x: float, y: float) -> bytes:
    return b"\x01" + struct.pack("<Idd", 1, x, y)


class GPKG:
    def __init__(self, pfad: Path, srs: dict, stand: str):
        if pfad.exists():
            pfad.unlink()
        self.pfad = pfad
        self.stand = f"{stand}T00:00:00.000Z"
        self.c = sqlite3.connect(pfad)
        c = self.c
        c.execute("PRAGMA application_id = 1196444487")  # 'GPKG'
        c.execute("PRAGMA user_version = 10400")
        c.executescript(
            """
            CREATE TABLE gpkg_spatial_ref_sys (srs_name TEXT NOT NULL, srs_id INTEGER NOT NULL PRIMARY KEY,
              organization TEXT NOT NULL, organization_coordsys_id INTEGER NOT NULL, definition TEXT NOT NULL,
              description TEXT);
            CREATE TABLE gpkg_contents (table_name TEXT NOT NULL PRIMARY KEY, data_type TEXT NOT NULL,
              identifier TEXT UNIQUE, description TEXT DEFAULT '',
              last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
              min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE, srs_id INTEGER,
              CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id));
            CREATE TABLE gpkg_geometry_columns (table_name TEXT NOT NULL, column_name TEXT NOT NULL,
              geometry_type_name TEXT NOT NULL, srs_id INTEGER NOT NULL, z TINYINT NOT NULL, m TINYINT NOT NULL,
              CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name),
              CONSTRAINT uk_gc_table_name UNIQUE (table_name),
              CONSTRAINT fk_gc_tn FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
              CONSTRAINT fk_gc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys (srs_id));
            """
        )
        c.executemany(
            "INSERT INTO gpkg_spatial_ref_sys VALUES (?,?,?,?,?,?)",
            [
                (
                    "Undefined cartesian SRS",
                    -1,
                    "NONE",
                    -1,
                    "undefined",
                    "undefined cartesian coordinate reference system",
                ),
                (
                    "Undefined geographic SRS",
                    0,
                    "NONE",
                    0,
                    "undefined",
                    "undefined geographic coordinate reference system",
                ),
                (
                    "WGS 84 geodetic",
                    4326,
                    "EPSG",
                    4326,
                    srs[4326],
                    "longitude/latitude coordinates in decimal degrees on the WGS 84 spheroid",
                ),
                ("ETRS89 / UTM zone 33N", SRID, "EPSG", SRID, srs[SRID], "ETRS89 / UTM zone 33N (EPSG:25833)"),
            ],
        )

    def ebene(
        self,
        name: str,
        titel: str,
        beschreibung: str,
        geomtyp: str | None,
        felder: list[tuple[str, str]],
        zeilen: list[list],
    ) -> None:
        """zeilen: Werte in der Reihenfolge von felder, bei Geometrie zuletzt (wkb, hülle|None)."""
        spalten = ", ".join(f'"{n}" {t}' for n, t in felder)
        geo = f', "geom" {geomtyp}' if geomtyp else ""
        self.c.execute(f'CREATE TABLE "{name}" (fid INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL{geo}, {spalten})')
        hx = [None, None, None, None]
        rows = []
        for z in zeilen:
            if geomtyp:
                wkb, huelle = z[-1]
                if huelle is None:  # Punkt
                    x, y = struct.unpack("<dd", wkb[5:21])
                    huelle_akt = (x, x, y, y)
                else:
                    huelle_akt = huelle
                hx = [
                    huelle_akt[0] if hx[0] is None else min(hx[0], huelle_akt[0]),
                    huelle_akt[1] if hx[1] is None else max(hx[1], huelle_akt[1]),
                    huelle_akt[2] if hx[2] is None else min(hx[2], huelle_akt[2]),
                    huelle_akt[3] if hx[3] is None else max(hx[3], huelle_akt[3]),
                ]
                rows.append([gp_blob(wkb, huelle), *z[:-1]])
            else:
                rows.append(list(z))
        namen = (['"geom"'] if geomtyp else []) + [f'"{n}"' for n, _ in felder]
        self.c.executemany(f'INSERT INTO "{name}" ({", ".join(namen)}) VALUES ({", ".join("?" * len(namen))})', rows)
        if geomtyp:
            self.c.execute(
                "INSERT INTO gpkg_contents VALUES (?,?,?,?,?,?,?,?,?,?)",
                (name, "features", titel, beschreibung, self.stand, hx[0], hx[2], hx[1], hx[3], SRID),
            )
            self.c.execute("INSERT INTO gpkg_geometry_columns VALUES (?,?,?,?,0,0)", (name, "geom", geomtyp, SRID))
        else:
            self.c.execute(
                "INSERT INTO gpkg_contents (table_name, data_type, identifier, description, last_change) "
                "VALUES (?,?,?,?,?)",
                (name, "attributes", titel, beschreibung, self.stand),
            )

    def stile(self, stile: dict[str, str], geometrie: dict[str, bool]) -> None:
        """QGIS-Standardstile (Tabelle layer_styles, wie QGIS sie anlegt)."""
        self.c.execute(
            """CREATE TABLE layer_styles (id INTEGER PRIMARY KEY AUTOINCREMENT, f_table_catalog TEXT(256),
               f_table_schema TEXT(256), f_table_name TEXT(256), f_geometry_column TEXT(256), styleName TEXT(30),
               styleQML TEXT, styleSLD TEXT, useAsDefault BOOLEAN, description TEXT, owner TEXT(30), ui TEXT(30),
               update_time DATETIME)"""
        )
        for name, qml in stile.items():
            self.c.execute(
                "INSERT INTO layer_styles (f_table_catalog, f_table_schema, f_table_name, f_geometry_column, "
                "styleName, styleQML, styleSLD, useAsDefault, description, owner, ui, update_time) "
                "VALUES ('', '', ?, ?, ?, ?, '', 1, ?, '', '', ?)",
                (
                    name,
                    "geom" if geometrie.get(name) else "",
                    f"kiezatlas_{name}",
                    qml,
                    "Kiezatlas Potsdam, Stil nach DESIGN.md",
                    self.stand,
                ),
            )
        self.c.execute(
            "INSERT INTO gpkg_contents (table_name, data_type, identifier, description, last_change) "
            "VALUES ('layer_styles', 'attributes', 'layer_styles', 'QGIS-Stile', ?)",
            (self.stand,),
        )

    def schliessen(self) -> None:
        self.c.commit()
        self.c.execute("VACUUM")
        self.c.close()


# ---------------------------------------------------------------------------------------------- Datenbank
def db_lesen(cur, raumebene: str, ein_ids: list[str], zellen: list[str]) -> dict:
    tab = "public.planungsraum" if raumebene == "planungsraum" else "public.stadtteil"
    d: dict = {"tab": tab}
    cur.execute("SELECT count(*) FROM public.planungsraum")
    d["planungsraum_zeilen"] = cur.fetchone()[0]
    cur.execute("SELECT srid, srtext FROM spatial_ref_sys WHERE srid IN (4326, 25833)")
    d["srs"] = dict(cur.fetchall())
    cur.execute(
        f"""SELECT nr, name, ST_AsBinary(g, 'NDR'), ST_XMin(g), ST_XMax(g), ST_YMin(g), ST_YMax(g),
                   round((ST_Area(g) / 1e6)::numeric, 3), ST_AsText(g, 2), ST_AsSVG(g, 0, 1)
            FROM (SELECT nr, name, ST_Multi(ST_Transform(geom, {SRID})) g FROM {tab}) r ORDER BY nr"""
    )
    d["raeume"] = {
        str(nr): {"name": name, "wkb": bytes(w), "huelle": (a, b, c, e), "km2": float(km2), "wkt": wkt, "svg": svg}
        for nr, name, w, a, b, c, e, km2, wkt, svg in cur.fetchall()
    }
    cur.execute(
        f"""SELECT e.id, ST_X(e.geom), ST_Y(e.geom), r.nr
            FROM auswertung.einrichtung e LEFT JOIN {tab} r ON ST_Contains(r.geom, ST_Transform(e.geom, 4326))
            WHERE e.id = ANY(%s) ORDER BY e.id""",
        (ein_ids,),
    )
    d["einrichtung"] = {i: {"x": x, "y": y, "raum": None if nr is None else str(nr)} for i, x, y, nr in cur.fetchall()}
    # Zellen: Quadrat aus der gitter_id (N/E = linke untere Ecke in EPSG:3035), Raum über den Mittelpunkt wie A6
    ost = [float(re.search(r"E(\d+)", g).group(1)) for g in zellen]
    nord = [float(re.search(r"N(\d+)", g).group(1)) for g in zellen]
    cur.execute(
        f"""WITH t AS (SELECT * FROM unnest(%s::text[], %s::float8[], %s::float8[]) WITH ORDINALITY AS t(g, e, n, i)),
                 q AS (SELECT t.i, t.g, ST_Transform(ST_MakeEnvelope(t.e, t.n, t.e + 100, t.n + 100, 3035), {SRID}) geom
                       FROM t)
            SELECT q.g, ST_AsBinary(q.geom, 'NDR'), ST_XMin(q.geom), ST_XMax(q.geom), ST_YMin(q.geom),
                   ST_YMax(q.geom), ST_AsText(q.geom, 2), ST_AsSVG(q.geom, 0, 0),
                   (SELECT r.nr FROM {tab} r JOIN public.zensus_zelle z ON ST_Contains(r.geom, z.geom)
                     WHERE z.gitter_id = q.g ORDER BY r.nr LIMIT 1)
            FROM q ORDER BY q.i""",
        (zellen, ost, nord),
    )
    d["zelle"] = {
        g: {"wkb": bytes(w), "huelle": (a, b, c, e), "wkt": wkt, "svg": svg, "raum": None if nr is None else str(nr)}
        for g, w, a, b, c, e, wkt, svg, nr in cur.fetchall()
    }
    cur.execute(
        """SELECT id, art, bez, flaeche_m2, quelle, ST_AsBinary(g, 'NDR'), ST_XMin(g), ST_XMax(g), ST_YMin(g),
                   ST_YMax(g), ST_AsText(g, 2)
            FROM (SELECT id, art, bez, flaeche_m2, quelle, ST_Multi(geom) g FROM auswertung.gruenflaeche) x
            ORDER BY id"""
    )
    d["gruen"] = [
        {
            "id": i,
            "art": a,
            "bez": b,
            "flaeche_m2": float(f),
            "quelle": q,
            "wkb": bytes(w),
            "huelle": (x1, x2, y1, y2),
            "wkt": wkt,
        }
        for i, a, b, f, q, w, x1, x2, y1, y2, wkt in cur.fetchall()
    ]
    cur.execute(
        f"""SELECT h.stop_id, h.name, h.verkehrsmittel, h.fahrten_hvz_je_richtung, h.klasse, h.in_potsdam,
                   ST_X(h.geom), ST_Y(h.geom), r.nr
            FROM auswertung.haltestelle h LEFT JOIN {tab} r ON ST_Contains(r.geom, ST_Transform(h.geom, 4326))
            ORDER BY h.stop_id"""
    )
    d["haltestelle"] = [
        {
            "stop_id": s,
            "name": n,
            "verkehrsmittel": v,
            "fahrten": None if f is None else float(f),
            "klasse": k,
            "in_potsdam": p,
            "x": x,
            "y": y,
            "raum": None if nr is None else str(nr),
        }
        for s, n, v, f, k, p, x, y, nr in cur.fetchall()
    ]
    return d


def punkte_umrechnen(cur, tab: str, lonlat: list[tuple[float, float]]) -> list[tuple[float, float, str | None]]:
    """WGS84 aus einer Datendatei nach EPSG:25833, mit Raumzuordnung (nur für Dateien ohne DB-Gegenstück)."""
    if not lonlat:
        return []
    cur.execute(
        f"""WITH t AS (SELECT * FROM unnest(%s::float8[], %s::float8[]) WITH ORDINALITY AS t(lon, lat, i))
            SELECT ST_X(ST_Transform(p, {SRID})), ST_Y(ST_Transform(p, {SRID})),
                   (SELECT r.nr FROM {tab} r WHERE ST_Contains(r.geom, p) ORDER BY r.nr LIMIT 1)
            FROM (SELECT i, ST_SetSRID(ST_Point(lon, lat), 4326) p FROM t) x ORDER BY i""",
        ([a for a, _ in lonlat], [b for _, b in lonlat]),
    )
    return [(x, y, None if nr is None else str(nr)) for x, y, nr in cur.fetchall()]


def karte_lesen(cur, tab: str, nr: str) -> dict:
    """Bausteine der Steckbrief-Karte: Ausschnitt, Nachbarn, Grünflächen, alles in EPSG:25833 als SVG-Pfad."""
    cur.execute(
        f"""WITH r AS (SELECT ST_Transform(geom, {SRID}) g FROM {tab} WHERE nr = %s),
                 b AS (SELECT ST_Expand(ST_Envelope(g),
                                        GREATEST(ST_XMax(g) - ST_XMin(g), ST_YMax(g) - ST_YMin(g)) * 0.06) h FROM r)
            SELECT ST_XMin(h), ST_YMin(h), ST_XMax(h), ST_YMax(h),
                   (SELECT string_agg(ST_AsSVG(ST_Intersection(ST_Boundary(ST_Transform(n.geom, {SRID})), b.h),
                                               0, 0), ' ')
                      FROM {tab} n WHERE n.nr <> %s AND ST_Intersects(ST_Transform(n.geom, {SRID}), b.h))
            FROM b""",
        (nr, nr),
    )
    x1, y1, x2, y2, nachbarn = cur.fetchone()
    cur.execute(
        f"""WITH b AS (SELECT ST_Expand(ST_Envelope(ST_Transform(geom, {SRID})),
                         GREATEST(ST_XMax(ST_Transform(geom, {SRID})) - ST_XMin(ST_Transform(geom, {SRID})),
                                  ST_YMax(ST_Transform(geom, {SRID})) - ST_YMin(ST_Transform(geom, {SRID}))) * 0.06) h
                       FROM {tab} WHERE nr = %s)
            SELECT g.art, ST_AsSVG(ST_SimplifyPreserveTopology(ST_Intersection(g.geom, b.h), 2), 0, 0)
            FROM auswertung.gruenflaeche g, b WHERE ST_Intersects(g.geom, b.h) ORDER BY g.id""",
        (nr,),
    )
    gruen = [(a, s) for a, s in cur.fetchall() if s]
    return {"huelle": (x1, y1, x2, y2), "nachbarn": nachbarn or "", "gruen": gruen}


# ---------------------------------------------------------------------------------------------- Kennzahlen
def kurzname(w: dict) -> str:
    k, art = w["kennzahl"], w["art"]
    if k == "anteil_in_radius" and w.get("richtwert"):
        return f"anteil_{art}_{int(w['richtwert']['wert'])}m"
    if k == "ew_je_einrichtung":
        return f"ew_je_{art}"
    if art in k:
        return k
    return f"{k}_{art}"


def titel_kennzahl(w: dict) -> str:
    k, art, zg = w["kennzahl"], w["art"], w.get("zielgruppe") or ""
    rw = w.get("richtwert") or {}
    if k == "anteil_in_radius":
        return f"{zg}: Anteil mit {ART.get(art, art)} bis {int(rw.get('wert', 0))} m Luftlinie"
    if k == "plaetze_je_kind":
        return f"Plätze je Kind ({zg})"
    if k == "plaetze_je_bedarf":
        return "Plätze je Bedarfsplatz (Krippe, Kindergarten, Hort)"
    if k == "schueler_je_kind":
        return f"Grundschüler je Kind ({zg})"
    if k == "ew_je_einrichtung":
        return f"Einwohner je Standort: {ART.get(art, art)}"
    if k == "oepnv_erschliessung":
        return "ÖPNV: Einwohner im Einzugsradius nach NVP"
    if k == "oepnv_takt":
        return "ÖPNV: Einwohner im Einzugsradius mit Soll-Takt"
    if k == "gruen_m2_je_ew":
        return "Grünanlagen und Parks im 500-m-Kreis je Einwohner"
    return f"{k} ({art})"


def richtwert_text(w: dict, quellen: dict) -> str:
    rw = w.get("richtwert")
    if not rw:
        return ""
    wert = rw["wert"]
    wert = int(wert) if isinstance(wert, float) and wert.is_integer() else wert
    teile = [f"{wert} {rw.get('einheit', '')}".strip()]
    q = quellen.get(rw.get("q"), {})
    herkunft = q.get("quelle", rw.get("q", ""))
    if rw.get("seite"):
        herkunft += f", {rw['seite']}"
    return f"{teile[0]} ({herkunft})"


def zahl(w) -> str:
    if w is None:
        return ""
    if isinstance(w, float):
        return f"{w:.2f}".replace(".", ",")
    return f"{w:,}".replace(",", ".")


# ---------------------------------------------------------------------------------------------- QGIS-Stile
def _farbe(h: str, a: int = 255) -> str:
    h = h.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a}"


def _optionen(d: dict) -> str:
    o = "".join(f'<Option type="QString" name="{escape(k)}" value="{escape(str(v))}"/>' for k, v in d.items())
    p = "".join(f'<prop k="{escape(k)}" v="{escape(str(v))}"/>' for k, v in d.items())
    return f'<Option type="Map">{o}</Option>{p}'


def _marker(name: str, farbe: str, form: str = "circle", groesse: float = 2.4) -> str:
    return (
        f'<symbol type="marker" name="{name}" alpha="1" clip_to_extent="1" force_rhr="0">'
        '<layer class="SimpleMarker" enabled="1" locked="0" pass="0">'
        + _optionen(
            {
                "name": form,
                "color": _farbe(farbe),
                "outline_color": _farbe(GRUND),
                "outline_style": "solid",
                "outline_width": "0.25",
                "outline_width_unit": "MM",
                "size": groesse,
                "size_unit": "MM",
                "angle": "0",
                "joinstyle": "miter",
                "scale_method": "diameter",
            }
        )
        + "</layer></symbol>"
    )


def _flaeche(name: str, farbe: str | None, rand: str | None, breite: float = 0.26, alpha: int = 255) -> str:
    return (
        f'<symbol type="fill" name="{name}" alpha="1" clip_to_extent="1" force_rhr="0">'
        '<layer class="SimpleFill" enabled="1" locked="0" pass="0">'
        + _optionen(
            {
                "color": _farbe(farbe or GRUND, alpha if farbe else 0),
                "style": "solid" if farbe else "no",
                "outline_color": _farbe(rand or GRUND, 255 if rand else 0),
                "outline_style": "solid" if rand else "no",
                "outline_width": breite,
                "outline_width_unit": "MM",
                "joinstyle": "miter",
                "border_width_unit": "MM",
            }
        )
        + "</layer></symbol>"
    )


def _qml(renderer: str, beschriftung: str = "") -> str:
    an = "1" if beschriftung else "0"
    return (
        "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n"
        f'<qgis version="3.34.0-Prizren" styleCategories="Symbology|Labeling" labelsEnabled="{an}">'
        f"{renderer}{beschriftung}<blendMode>0</blendMode><featureBlendMode>0</featureBlendMode>"
        "<layerOpacity>1</layerOpacity></qgis>\n"
    )


def _kategorien(attr: str, kat: list[tuple[str, str, str]]) -> str:
    c = "".join(
        f'<category value="{escape(v)}" label="{escape(t)}" symbol="{i}" render="true"/>'
        for i, (v, t, _) in enumerate(kat)
    )
    s = "".join(sym.replace('name="X"', f'name="{i}"') for i, (_, _, sym) in enumerate(kat))
    return (
        f'<renderer-v2 type="categorizedSymbol" attr="{attr}" symbollevels="0" forceraster="0" '
        f'enableorderby="0"><categories>{c}</categories><symbols>{s}</symbols></renderer-v2>'
    )


def _beschriftung(feld: str, groesse: float = 8.5, ausdruck: bool = False) -> str:
    return (
        '<labeling type="simple"><settings calloutType="simple">'
        f'<text-style fieldName="{escape(feld)}" isExpression="{1 if ausdruck else 0}" '
        f'fontFamily="Barlow Semi Condensed" namedStyle="Medium" fontSize="{groesse}" fontSizeUnit="Point" '
        f'textColor="{_farbe(INK)}" textOpacity="1" fontWeight="57" fontItalic="0" multilineHeight="1">'
        f'<text-buffer bufferDraw="1" bufferSize="0.8" bufferSizeUnits="MM" bufferColor="{_farbe(GRUND)}" '
        'bufferOpacity="0.85" bufferJoinStyle="128" bufferNoFill="1"/></text-style>'
        '<placement placement="1" placementFlags="10" dist="0" priority="5" fitInPolygonOnly="0" '
        'centroidWhole="0" centroidInside="1"/>'
        '<rendering obstacle="1" fontLimitPixelSize="0" scaleVisibility="0" drawLabels="1" '
        'displayAll="0" upsidedownLabels="0" limitNumLabels="0"/></settings></labeling>'
    )


def stile_bauen(gruen_zaehlt: set[str], ein_arten: list[str], odbl_arten: list[str]) -> dict[str, str]:
    st: dict[str, str] = {}
    st["raumeinheit"] = _qml(
        '<renderer-v2 type="singleSymbol" symbollevels="0" forceraster="0" enableorderby="0"><symbols>'
        + _flaeche("0", None, AKZENT, 0.4)
        + "</symbols></renderer-v2>",
        _beschriftung('"nr" || \' \' || "name"', 8.5, ausdruck=True),
    )
    rng = "".join(
        f'<range lower="{lo}" upper="{hi}" label="{escape(t)}" symbol="{i}" render="true"/>'
        for i, (lo, hi, _, t) in enumerate(EW_STUFEN)
    )
    syms = "".join(_flaeche(str(i), f, None) for i, (_, _, f, _) in enumerate(EW_STUFEN))
    st["zelle"] = _qml(
        '<renderer-v2 type="graduatedSymbol" attr="ew" graduatedMethod="GraduatedColor" symbollevels="0" '
        f'forceraster="0" enableorderby="0"><ranges>{rng}</ranges><symbols>{syms}</symbols></renderer-v2>'
    )
    kat = []
    for art, farbe in GRUEN_FARBE.items():
        zusatz = " (zählt für Grünversorgung)" if art in gruen_zaehlt else ""
        kat.append(
            (art, f"{art.capitalize()}{zusatz}".replace("Gruenanlage", "Grünanlage"), _flaeche("X", farbe, None))
        )
    st["gruenflaeche"] = _qml(_kategorien("art", kat))
    kat = []
    for art in ein_arten:
        form = (
            "circle"
            if art in ("kita", "hort")
            else (
                "square"
                if art in ("grundschule", "sek1", "gymnasium", "osz", "foerderschule", "sonstige_schule")
                else "diamond"
            )
        )
        kat.append((art, ART.get(art, art), _marker("X", ART_FARBE.get(art, MUTED), form)))
    st["einrichtung"] = _qml(_kategorien("art", kat))
    hk = [
        ("I", "Klasse I", "#13212a", 2.0),
        ("II", "Klasse II", "#3b5560", 1.7),
        ("III", "Klasse III", "#6d7f86", 1.4),
        ("unter III", "unter Klasse III", "#a3aeb2", 1.2),
    ]
    st["haltestelle"] = _qml(_kategorien("klasse", [(v, t, _marker("X", f, "triangle", g)) for v, t, f, g in hk]))
    if odbl_arten:
        reihe = [
            "#7a3b57",
            "#2d5e86",
            "#4d7a3c",
            "#4f5d64",
            "#3b7684",
            "#9a2f2f",
            "#6d8cb8",
            "#4e7768",
            "#1c4a5b",
            "#8fa6c8",
            "#7d998c",
            "#13212a",
        ]
        st["einrichtung_odbl"] = _qml(
            _kategorien(
                "art", [(a, a, _marker("X", reihe[i % len(reihe)], "diamond", 2.2)) for i, a in enumerate(odbl_arten)]
            )
        )
    return st


# ---------------------------------------------------------------------------------------------- QGIS-Projekt
def _srs_xml(wkt: str) -> str:
    return (
        '<spatialrefsys nativeFormat="Wkt">'
        f"<wkt>{escape(wkt)}</wkt>"
        "<proj4>+proj=utm +zone=33 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs</proj4>"
        f"<srid>{SRID}</srid><authid>EPSG:{SRID}</authid><description>ETRS89 / UTM zone 33N</description>"
        "<projectionacronym>utm</projectionacronym><ellipsoidacronym>EPSG:7019</ellipsoidacronym>"
        "<geographicflag>false</geographicflag></spatialrefsys>"
    )


def projekt_bauen(ebenen: list[dict], wkt: str, huelle: tuple, titel: str) -> str:
    """ebenen: name, titel, gpkg, geom (Point/MultiPolygon/Polygon/None), qml."""
    baum, schichten = [], []
    for e in ebenen:
        lid = f"kiezatlas_{e['name']}"
        quelle = f"./{e['gpkg']}|layername={e['name']}"
        sichtbar = "Qt::Checked" if e.get("an", True) else "Qt::Unchecked"
        baum.append(
            f'<layer-tree-layer id="{lid}" name="{escape(e["titel"])}" checked="{sichtbar}" expanded="0" '
            f'source="{escape(quelle)}" providerKey="ogr"><customproperties/></layer-tree-layer>'
        )
        qml = e.get("qml") or ""
        innen = re.sub(r"^.*?<qgis[^>]*>|</qgis>\s*$", "", qml, flags=re.S)
        an = "1" if 'labelsEnabled="1"' in qml else "0"
        if e["geom"]:
            kopf = (
                f'<maplayer type="vector" geometry="{"Point" if e["geom"] == "POINT" else "Polygon"}" '
                f'wkbType="{ {"POINT": "Point", "POLYGON": "Polygon", "MULTIPOLYGON": "MultiPolygon"}[e["geom"]] }" '
                f'labelsEnabled="{an}" hasScaleBasedVisibilityFlag="0" readOnly="0" autoRefreshEnabled="0">'
            )
            srs = f"<srs>{_srs_xml(wkt)}</srs>"
        else:
            kopf = (
                '<maplayer type="vector" geometry="No geometry" wkbType="NoGeometry" labelsEnabled="0" '
                'hasScaleBasedVisibilityFlag="0" readOnly="0">'
            )
            srs = ""
        schichten.append(
            f"{kopf}<id>{lid}</id><datasource>{escape(quelle)}</datasource>"
            f"<layername>{escape(e['titel'])}</layername>{srs}"
            f'<provider encoding="UTF-8">ogr</provider>{innen}</maplayer>'
        )
    x1, x2, y1, y2 = huelle
    return (
        "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n"
        f'<qgis projectname="{escape(titel)}" version="3.34.0-Prizren">'
        f'<homePath path=""/><title>{escape(titel)}</title>'
        f"<projectCrs>{_srs_xml(wkt)}</projectCrs>"
        f"<layer-tree-group><customproperties/>{''.join(baum)}</layer-tree-group>"
        '<mapcanvas name="theMapCanvas" annotationsVisible="1"><units>meters</units>'
        f"<extent><xmin>{x1:.0f}</xmin><ymin>{y1:.0f}</ymin><xmax>{x2:.0f}</xmax><ymax>{y2:.0f}</ymax></extent>"
        f"<rotation>0</rotation><destinationsrs>{_srs_xml(wkt)}</destinationsrs></mapcanvas>"
        f"<projectlayers>{''.join(schichten)}</projectlayers>"
        '<properties><Paths><Absolute type="bool">false</Absolute></Paths>'
        '<Measure><Ellipsoid type="QString">EPSG:7019</Ellipsoid></Measure></properties>'
        "</qgis>\n"
    )


def zip_fest(pfad: Path, dateien: dict[str, bytes]) -> None:
    """Zip mit festem Zeitstempel (gleicher Inhalt, gleiche Bytes)."""
    with zipfile.ZipFile(pfad, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, inhalt in sorted(dateien.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, inhalt)


# ---------------------------------------------------------------------------------------------- CSV
def csv_schreiben(pfad: Path, felder: list[str], zeilen: list[list]) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(felder)
        for z in zeilen:
            w.writerow(["" if v is None else (int(v) if isinstance(v, bool) else v) for v in z])


# ---------------------------------------------------------------------------------------------- Steckbrief
STECKBRIEF_CSS = """
@font-face{font-family:"Barlow";font-weight:400;src:url("../../../fonts/barlow-400-normal.woff2") format("woff2")}
@font-face{font-family:"Barlow";font-weight:500;src:url("../../../fonts/barlow-500-normal.woff2") format("woff2")}
@font-face{font-family:"Barlow";font-weight:600;src:url("../../../fonts/barlow-600-normal.woff2") format("woff2")}
@font-face{font-family:"Barlow Semi Condensed";font-weight:500;src:url("../../../fonts/barlow-semi-condensed-500-normal.woff2") format("woff2")}
@font-face{font-family:"Barlow Semi Condensed";font-weight:600;src:url("../../../fonts/barlow-semi-condensed-600-normal.woff2") format("woff2")}
:root{--ground:#f1f2ee;--ink:#13212a;--muted:#4f5d64;--line:#cdd1cc;--accent:#6a2c82}
@page{size:A4;margin:14mm 15mm 16mm;
  @bottom-left{content:string(kopf);font:500 7.5pt "Barlow Semi Condensed",sans-serif;color:#4f5d64}
  @bottom-right{content:"Seite " counter(page) " von " counter(pages);font:500 7.5pt "Barlow Semi Condensed",sans-serif;color:#4f5d64}}
*{box-sizing:border-box;border-radius:0}
html{background:#fff}
body{margin:0;font:400 9pt/1.4 "Barlow",sans-serif;color:var(--ink);font-variant-numeric:tabular-nums;
  font-feature-settings:"tnum" 1;hyphens:auto;hyphenate-character:"-"}
b,strong{font-weight:600}
.blatt{max-width:180mm;margin:0 auto}
@media screen{body{background:var(--ground);padding:16px}.blatt{background:#fff;padding:14mm 15mm}}
.kopfzeile{string-set:kopf content();font:600 7.5pt "Barlow Semi Condensed",sans-serif;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--line);padding-bottom:2mm}
h1{font:600 22pt/1.1 "Barlow Semi Condensed",sans-serif;margin:3mm 0 1mm}
h1 .nr{color:var(--accent);margin-right:2mm}
h2{font:600 11pt/1.2 "Barlow Semi Condensed",sans-serif;margin:6mm 0 2mm;padding-top:1.5mm;border-top:1px solid var(--ink)}
.lede{color:var(--muted);margin:0 0 3mm;max-width:150mm}
.zahlen{display:table;width:100%;border-collapse:collapse;margin:2mm 0 3mm}
.zahlen div{display:table-cell;padding:1.5mm 3mm 1.5mm 0;border-right:1px solid var(--line)}
.zahlen div:last-child{border-right:0}
.zahlen b{display:block;font:600 15pt/1.1 "Barlow Semi Condensed",sans-serif}
.zahlen span{font-size:7.5pt;color:var(--muted)}
figure{margin:0 0 2mm;border:1px solid var(--line)}
figure svg{display:block;width:100%;height:auto;max-height:118mm}
figcaption{font-size:7.5pt;color:var(--muted);padding:1.5mm 2mm;border-top:1px solid var(--line)}
.legende span{white-space:nowrap;margin-right:3mm}
.legende i{display:inline-block;width:2.6mm;height:2.6mm;margin-right:1mm;vertical-align:-.3mm}
table{width:100%;border-collapse:collapse;font-size:8pt;page-break-inside:auto}
th{font:600 7.5pt "Barlow Semi Condensed",sans-serif;text-align:left;color:var(--muted);border-bottom:1px solid var(--ink);padding:1mm 1.5mm 1mm 0}
td{border-bottom:1px solid var(--line);padding:1.2mm 1.5mm 1.2mm 0;vertical-align:top;hyphens:manual}
tr{page-break-inside:avoid}
td.wert{font:600 10pt "Barlow Semi Condensed",sans-serif;white-space:nowrap;text-align:right;padding-right:3mm}
td.leer{font:500 8pt "Barlow",sans-serif;color:var(--muted);white-space:normal;text-align:left}
.status{font:500 7pt "Barlow Semi Condensed",sans-serif;text-transform:uppercase;letter-spacing:.05em}
.status.orientierung{color:var(--muted)}
.status.amtlich{color:var(--ink)}
.hinweis{font-size:7.2pt;color:var(--muted)}
.quellen{font-size:7.5pt;color:var(--muted);padding-left:4mm}
.quellen li{margin-bottom:1mm}
.fuss{margin-top:5mm;font-size:7.5pt;color:var(--muted);border-top:1px solid var(--line);padding-top:2mm}
"""  # noqa: E501


def svg_karte(
    k: dict, raum_svg: str, zellen: list[tuple[str, int]], einrichtungen: list[dict], gruen_zaehlt: set[str]
) -> str:
    x1, y1, x2, y2 = k["huelle"]
    b, h = x2 - x1, y2 - y1
    s = max(b, h) / 1000  # Strichstärke relativ zum Ausschnitt
    teile = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x1:.0f} {-y2:.0f} {b:.0f} {h:.0f}" '
        f'role="img" aria-label="Karte der Raumeinheit">',
        f'<rect x="{x1:.0f}" y="{-y2:.0f}" width="{b:.0f}" height="{h:.0f}" fill="{GRUND}"/>',
    ]
    for art, pfad in k["gruen"]:
        farbe = GRUEN_FARBE.get(art, "#c8d6c3")
        teile.append(f'<path d="{pfad}" fill="{farbe}" fill-opacity="{0.85 if art in gruen_zaehlt else 0.45}"/>')
    for pfad, ew in zellen:
        farbe = next((f for lo, hi, f, _ in EW_STUFEN if lo <= ew < hi), LINIE)
        teile.append(f'<path d="{pfad}" fill="{farbe}" fill-opacity="0.9" stroke="#fff" stroke-width="{s * 0.6:.1f}"/>')
    if k["nachbarn"]:
        teile.append(
            f'<path d="{k["nachbarn"]}" fill="none" stroke="{MUTED}" stroke-width="{s * 1.2:.1f}" '
            f'stroke-dasharray="{s * 6:.0f} {s * 4:.0f}"/>'
        )
    teile.append(
        f'<path d="{raum_svg}" fill="none" stroke="{AKZENT}" stroke-width="{s * 3:.1f}" stroke-linejoin="round"/>'
    )
    r = s * 7
    for e in einrichtungen:
        if not (x1 <= e["x"] <= x2 and y1 <= e["y"] <= y2):
            continue
        farbe = ART_FARBE.get(e["art"], MUTED)
        if e["art"] in ("kita", "hort"):
            teile.append(
                f'<circle cx="{e["x"]:.0f}" cy="{-e["y"]:.0f}" r="{r:.0f}" fill="{farbe}" '
                f'stroke="#fff" stroke-width="{s * 1.5:.1f}"/>'
            )
        else:
            teile.append(
                f'<rect x="{e["x"] - r:.0f}" y="{-e["y"] - r:.0f}" width="{2 * r:.0f}" height="{2 * r:.0f}" '
                f'fill="{farbe}" stroke="#fff" stroke-width="{s * 1.5:.1f}"/>'
            )
    # Maßstabsleiste: runde Länge um ein Fünftel der Breite
    lang = next(v for v in (100, 200, 250, 500, 1000, 2000, 2500, 5000) if v >= b / 6)
    mx, my = x1 + b * 0.04, -y1 - h * 0.05
    teile.append(f'<rect x="{mx:.0f}" y="{my - s * 4:.0f}" width="{lang}" height="{s * 4:.0f}" fill="{INK}"/>')
    teile.append(
        f'<text x="{mx:.0f}" y="{my - s * 9:.0f}" font-family="Barlow Semi Condensed" font-weight="500" '
        f'font-size="{s * 22:.0f}" fill="{INK}">{lang if lang < 1000 else lang // 1000} '
        f"{'m' if lang < 1000 else 'km'}</text>"
    )
    teile.append("</svg>")
    return "".join(teile)


def steckbrief(
    nr: str,
    raum: dict,
    planer: dict,
    karte_svg: str,
    ein_liste: list[dict],
    kopf_zahlen: dict,
    raumebene: str,
    ebene_lizenz: str,
) -> str:
    quellen = planer["quellen"]
    ebene_text = "Planungsraum" if raumebene == "planungsraum" else "Stadtteil"
    zeilen = []
    for w in raum["werte"]:
        titel = titel_kennzahl(w)
        if w.get("wert") is None:
            wert_html = '<td class="wert leer">keine Aussage</td>'
        else:
            einheit = w.get("einheit", "")
            einheit = "" if einheit in ("Plätze je Kind", "Schüler je Kind", "Plätze je Bedarfsplatz") else einheit
            wert_html = f'<td class="wert">{escape(zahl(w["wert"]))}{(" " + escape(einheit)) if einheit else ""}</td>'
        zusatz = " · vorläufig, ohne Schulbezirk" if w.get("vorlaeufig") else ""
        q = quellen.get(w.get("q"), {})
        zeilen.append(
            f'<tr><td><b>{escape(titel)}</b><br><span class="status {escape(w["status"])}">{escape(w["status"])}'
            f'{zusatz}</span><br><span class="hinweis">{escape(w.get("unsicherheit") or "")}</span></td>'
            f'{wert_html}<td class="hinweis">{escape(richtwert_text(w, quellen))}</td>'
            f'<td class="hinweis">{escape(q.get("quelle", w.get("q", "")))}<br>'
            f"Stand: {escape(w.get('stand', ''))}</td></tr>"
        )
    zaehl: dict[str, list] = {}
    for e in ein_liste:
        z = zaehl.setdefault(e["art"], [0, 0, 0])
        z[0] += 1
        z[1] += e.get("plaetze") or 0
        z[2] += e.get("schueler") or 0
    ein_zeilen = (
        "".join(
            f'<tr><td><i style="display:inline-block;width:2.4mm;height:2.4mm;background:{ART_FARBE.get(a, MUTED)};'
            f'{"border-radius:50%" if a in ("kita", "hort") else ""};margin-right:1.5mm"></i>'
            f"{escape(ART.get(a, a))}</td>"
            f'<td class="wert">{n}</td><td class="wert">{zahl(p) if p else ""}</td>'
            f'<td class="wert">{zahl(sch) if sch else ""}</td></tr>'
            for a, (n, p, sch) in sorted(zaehl.items(), key=lambda t: list(ART).index(t[0]) if t[0] in ART else 99)
        )
        or '<tr><td colspan="4">Keine Einrichtung in der Raumeinheit.</td></tr>'
    )
    benutzt = sorted(
        {w.get("q") for w in raum["werte"]} | {(w.get("richtwert") or {}).get("q") for w in raum["werte"]} - {None}
    )
    q_html = "".join(
        f"<li><b>{escape(quellen[k].get('quelle', k))}</b>. {escape(quellen[k].get('vermerk', ''))}</li>"
        for k in benutzt
        if k in quellen
    )
    if "zensus" not in benutzt and "zensus" in quellen:
        q_html = (
            f"<li><b>{escape(quellen['zensus']['quelle'])}</b>. {escape(quellen['zensus']['vermerk'])}</li>" + q_html
        )
    q_html += f"<li><b>Grenze der Raumeinheit</b>. {escape(ebene_lizenz)}</li>"
    leg = "".join(f'<span><i style="background:{f}"></i>{escape(t)} EW</span>' for _, _, f, t in EW_STUFEN)
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(nr)} {escape(raum["name"])}: Steckbrief Kiezatlas Potsdam</title>
<style>{STECKBRIEF_CSS}</style></head>
<body><div class="blatt">
<div class="kopfzeile">Kiezatlas Potsdam · Steckbrief {escape(ebene_text)} {escape(nr)} {escape(raum["name"])}</div>
<h1><span class="nr">{escape(nr)}</span>{escape(raum["name"])}</h1>
<p class="lede">{escape(ebene_text)} der Landeshauptstadt Potsdam. Versorgung mit Kita, Schule, Gemeinbedarf, ÖPNV
und Grün in Luftlinie, berechnet aus offenen amtlichen Daten. Jeder Wert steht mit Status, Maßstab, Quelle und
Unsicherheit. Stand der Auswertung {escape(planer["stand"])}.</p>
<div class="zahlen">
<div><b>{zahl(raum["ew"])}</b><span>Einwohner (Zensus 15.05.2022, auf 10 gerundet)</span></div>
<div><b>{zahl(kopf_zahlen["km2"])}</b><span>Fläche in km²</span></div>
<div><b>{kopf_zahlen["zellen"]}</b><span>bewohnte 100-m-Zellen</span></div>
<div><b>{len(ein_liste)}</b><span>Einrichtungen in der Raumeinheit</span></div>
</div>
<figure>{karte_svg}
<figcaption class="legende">Violett: Grenze der Raumeinheit, gestrichelt: Nachbarn. Zellen nach Einwohnern:
{leg}. Grün: Grünanlagen und Parks (kräftig, zählen für die Grünversorgung), Wald, Kleingärten, Friedhöfe und
Freizeitflächen (blass). Kreis: Kita oder Hort, Quadrat: Schule und Gemeinbedarf. Karte nur aus eigenen Daten,
EPSG:25833.</figcaption></figure>
<h2>Versorgung</h2>
<table><thead><tr><th style="width:52%">Kennzahl, Status, Unsicherheit</th><th style="width:14%;text-align:right">Wert</th>
<th style="width:17%">Maßstab</th><th style="width:17%">Quelle</th></tr></thead><tbody>
{"".join(zeilen)}
</tbody></table>
<h2>Einrichtungen in der Raumeinheit</h2>
<table><thead><tr><th>Art</th><th style="text-align:right">Standorte</th><th style="text-align:right">Plätze</th>
<th style="text-align:right">Schüler</th></tr></thead><tbody>{ein_zeilen}</tbody></table>
<p class="hinweis">Plätze laut Betriebserlaubnis (MBJS), je Kita einmal am Hauptstandort. Gemeinbedarf aus
ALKIS-Gebäudefunktionen nur als Lage, ohne Kapazität. Ohne Adressen.</p>
<h2>Lesehilfe</h2>
<p class="hinweis"><b>amtlich</b>: Maßstab aus einem Potsdamer Dokument mit gelesener Fundstelle, bei Werten ohne
Maßstab nur amtliche Daten. <b>orientierung</b>: Maßstab ohne Primärbeleg, ungelesene Fundstelle oder Berliner
Methode, kein Richtwert. <b>vorläufig</b>: Grundschulwerte ohne Schulbezirk. <b>keine Aussage</b>: der Grund
steht im ersten Satz des Hinweises daneben. Einwohner und Kinder stammen aus dem
Zensus 2022 (Stichtag 15.05.2022, Cell-Key-Verfahren: kleine Werte sind verändert, Summen vieler Zellen weichen
ab); Neubau danach fehlt. Entfernungen in Luftlinie vom Zellmittelpunkt, aussagekräftig auf rund 50 m.
Werte aus feinen Altersklassen gibt es erst ab 100 Einwohnern, unter 20 Personen der Zielgruppe steht keine
Aussage.</p>
<h2>Quellen und Lizenzen</h2>
<ul class="quellen">{q_html}</ul>
<p class="fuss">Kiezatlas Potsdam, Stiebitz Souverain Systems UG (haftungsbeschränkt). Erzeugt mit
skripte/16_export.py aus daten/planer.js (Stand {escape(planer["stand"])}). Daten zum Weiterverwenden:
kiezatlas_potsdam.gpkg und csv/ im selben Ordner wie dieser Steckbrief, Beschreibung in README.md.</p>
</div></body></html>
"""  # noqa: E501


# ---------------------------------------------------------------------------------------------- Hauptteil
def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quelle", default=str(DATEN), help="Ordner mit planer.js, einrichtungen.js, erreichbar.js")
    ap.add_argument("--ziel", default=str(ZIEL_STANDARD))
    ap.add_argument(
        "--raum-lizenz",
        default=None,
        help="Vermerk der Planungsraum-Grenzen (Pflicht, sobald planer.js je Planungsraum rechnet)",
    )
    ap.add_argument("--ohne-beleg", action="store_true", help="keinen Beleg unter belege/ schreiben")
    a = ap.parse_args()
    quelle, ziel = Path(a.quelle).resolve(), Path(a.ziel).resolve()

    planer = js_lesen(quelle / "planer.js")[1]
    ein = js_lesen(quelle / "einrichtungen.js")[1]
    err = js_lesen(quelle / "erreichbar.js")[1]
    ein_odbl = optional(quelle / "einrichtungen_odbl.js")
    err_fuss = optional(quelle / "erreichbar_fuss_odbl.js")
    planer_fuss = optional(quelle / "planer_fuss_odbl.js")
    fixture = any((x or {}).get("fixture") for x in (planer, ein, err, ein_odbl, err_fuss, planer_fuss))
    if fixture and ziel == ZIEL_STANDARD.resolve():
        raise SystemExit("Beispieldaten (fixture: true) gehen nie nach daten/export. --ziel außerhalb wählen.")
    ids, zprops = zell_ids(quelle)
    if (err["anzahl"], err["erste_id"], err["letzte_id"]) != (len(ids), ids[0], ids[-1]):
        raise SystemExit("erreichbar.js passt nicht zur Reihenfolge von zellen.js")
    raumebene = planer["raumebene"]
    rw = yaml.safe_load((WURZEL / "config" / "richtwerte.yaml").read_text(encoding="utf-8"))
    gruen_zaehlt = {k for k, v in rw["gruen_definition"]["arten"].items() if v.get("zaehlt_vorschlag")}

    import psycopg

    with psycopg.connect() as con:
        con.read_only = True
        with con.cursor() as cur:
            d = db_lesen(cur, raumebene, [f["properties"]["id"] for f in ein["features"]], ids)
            if (d["planungsraum_zeilen"] > 0) != (raumebene == "planungsraum"):
                raise SystemExit("public.planungsraum und planer.js passen nicht zusammen; erst A6 neu laufen lassen.")
            if raumebene == "planungsraum" and not a.raum_lizenz:
                raise SystemExit("Planungsräume: --raum-lizenz mit dem Vermerk aus dem Handdownload (H1) angeben.")
            raum_vermerk = a.raum_lizenz or VERMERK["stadtteil"]
            fehlend = [f for f in ein["features"] if f["properties"]["id"] not in d["einrichtung"]]
            if fehlend and not fixture:
                raise SystemExit(f"{len(fehlend)} Einrichtungen aus einrichtungen.js fehlen in auswertung.einrichtung")
            umger = punkte_umrechnen(cur, d["tab"], [tuple(f["geometry"]["coordinates"]) for f in fehlend])
            for f, (x, y, nr) in zip(fehlend, umger):
                d["einrichtung"][f["properties"]["id"]] = {"x": x, "y": y, "raum": nr}
            odbl_punkte = punkte_umrechnen(
                cur, d["tab"], [tuple(f["geometry"]["coordinates"]) for f in (ein_odbl or {}).get("features", [])]
            )
            karten = {nr: karte_lesen(cur, d["tab"], nr) for nr in planer["raeume"]}
    if set(planer["raeume"]) - set(d["raeume"]):
        raise SystemExit(f"Raumeinheiten ohne Geometrie: {sorted(set(planer['raeume']) - set(d['raeume']))}")

    ziel.mkdir(parents=True, exist_ok=True)
    stand = planer["stand"]
    meldungen: list[str] = []

    # ------------------------------------------------------------------ Ebenen ohne OSM
    # einrichtung
    e_felder = [
        ("id", "TEXT"),
        ("art", "TEXT"),
        ("art_text", "TEXT"),
        ("unterart", "TEXT"),
        ("name", "TEXT"),
        ("plaetze", "INTEGER"),
        ("schueler", "INTEGER"),
        ("schueler_stand", "TEXT"),
        ("status", "TEXT"),
        ("in_potsdam", "BOOLEAN"),
        ("raum_nr", "TEXT"),
        ("quelle", "TEXT"),
        ("stand", "TEXT"),
        ("lizenz", "TEXT"),
    ]
    e_zeilen = []
    for f in ein["features"]:
        p = f["properties"]
        g = d["einrichtung"][p["id"]]
        e_zeilen.append(
            [
                p["id"],
                p["art"],
                ART.get(p["art"], p["art"]),
                p.get("unterart"),
                p.get("name"),
                p.get("plaetze"),
                p.get("schueler"),
                p.get("schueler_stand"),
                p["status"],
                bool(p["in_potsdam"]),
                g["raum"],
                p["q"],
                ein["stand"],
                (ein["quellen"].get(p["q"]) or {}).get("lizenz") or LIZENZ_KURZ[p["q"]],
                (punkt_wkb(round(g["x"], 2), round(g["y"], 2)), None),
            ]
        )
    # raumeinheit (breit) und versorgung (lang)
    spalten_breit: list[str] = []
    for r in planer["raeume"].values():
        for w in r["werte"]:
            k = kurzname(w)
            if k not in spalten_breit:
                spalten_breit.append(k)
    for r in planer["raeume"].values():
        namen = [kurzname(w) for w in r["werte"]]
        if len(namen) != len(set(namen)):
            raise SystemExit(f"Kurznamen nicht eindeutig: {namen}")
    r_felder = (
        [
            ("nr", "TEXT"),
            ("name", "TEXT"),
            ("raumebene", "TEXT"),
            ("ew", "INTEGER"),
            ("flaeche_km2", "REAL"),
            ("zellen", "INTEGER"),
        ]
        + [(k, "REAL") for k in spalten_breit]
        + [("stand", "TEXT"), ("vermerk_grenze", "TEXT")]
    )
    zellen_je_raum: dict[str, int] = {}
    for g in ids:
        nr = d["zelle"][g]["raum"]
        if nr and zprops[g].get("ew"):
            zellen_je_raum[nr] = zellen_je_raum.get(nr, 0) + 1
    r_zeilen = []
    for nr, r in planer["raeume"].items():
        werte = {kurzname(w): w.get("wert") for w in r["werte"]}
        geo = d["raeume"][nr]
        r_zeilen.append(
            [nr, r["name"], raumebene, r["ew"], geo["km2"], zellen_je_raum.get(nr, 0)]
            + [werte.get(k) for k in spalten_breit]
            + [stand, raum_vermerk, (geo["wkb"], geo["huelle"])]
        )
    v_felder = [
        ("raum_nr", "TEXT"),
        ("raum_name", "TEXT"),
        ("raumebene", "TEXT"),
        ("spalte", "TEXT"),
        ("kennzahl", "TEXT"),
        ("art", "TEXT"),
        ("titel", "TEXT"),
        ("zielgruppe", "TEXT"),
        ("wert", "REAL"),
        ("einheit", "TEXT"),
        ("methode", "TEXT"),
        ("status", "TEXT"),
        ("vorlaeufig", "BOOLEAN"),
        ("richtwert", "REAL"),
        ("richtwert_einheit", "TEXT"),
        ("richtwert_quelle", "TEXT"),
        ("richtwert_fundstelle", "TEXT"),
        ("unsicherheit", "TEXT"),
        ("quelle", "TEXT"),
        ("stand", "TEXT"),
        ("vermerk", "TEXT"),
        ("prognose", "TEXT"),
    ]

    def versorgung_zeilen(pl: dict) -> list[list]:
        aus = []
        for nr, r in pl["raeume"].items():
            for w in r["werte"]:
                rwt = w.get("richtwert") or {}
                q = pl["quellen"].get(w.get("q"), {})
                aus.append(
                    [
                        nr,
                        r["name"],
                        pl["raumebene"],
                        kurzname(w),
                        w["kennzahl"],
                        w["art"],
                        titel_kennzahl(w),
                        w.get("zielgruppe"),
                        w.get("wert"),
                        w.get("einheit"),
                        w.get("methode"),
                        w.get("status"),
                        bool(w.get("vorlaeufig", False)),
                        rwt.get("wert"),
                        rwt.get("einheit"),
                        (pl["quellen"].get(rwt.get("q"), {}) or {}).get("quelle", rwt.get("q")),
                        rwt.get("seite"),
                        w.get("unsicherheit"),
                        q.get("quelle", w.get("q")),
                        w.get("stand"),
                        q.get("vermerk"),
                        json.dumps(w["prognose"], ensure_ascii=False) if w.get("prognose") else None,
                    ]
                )
        return aus

    v_zeilen = versorgung_zeilen(planer)
    # zelle: nur Einwohner und Entfernungen (keine Altersklassen, Korrektur 6 und A6-Geheimhaltung)
    arten = err["arten"]
    z_felder = (
        [("gitter_id", "TEXT"), ("stadtteil", "TEXT"), ("raum_nr", "TEXT"), ("ew", "INTEGER")]
        + [(f"m_{art}", "INTEGER") for art in arten]
        + [("stand", "TEXT"), ("lizenz", "TEXT")]
    )
    z_vermerk = f"{VERMERK['zensus']}; Entfernungen: {VERMERK['mbjs']}; {VERMERK['lgb']}"
    z_zeilen = []
    for i, g in enumerate(ids):
        p = zprops[g]
        dz = d["zelle"][g]
        z_zeilen.append(
            [g, p.get("st"), dz["raum"], p.get("ew")]
            + [err["werte"][art][i] for art in arten]
            + [err["stand"], "dl-de/by-2-0", (dz["wkb"], dz["huelle"])]
        )
    abweichend = [g for g in ids if raumebene == "stadtteil" and d["zelle"][g]["raum"] != zprops[g].get("st")]
    meldungen.append(
        f"Zellen: Raum aus der Datenbank weicht bei {len(abweichend)} von {len(ids)} Zellen von "
        f"zellen.js ab{(' (' + ', '.join(abweichend[:5]) + ')') if abweichend else ''}"
    )
    # gruenflaeche
    g_felder = [
        ("id", "TEXT"),
        ("art", "TEXT"),
        ("bez", "TEXT"),
        ("flaeche_m2", "REAL"),
        ("zaehlt_gruenversorgung", "BOOLEAN"),
        ("quelle", "TEXT"),
        ("stand", "TEXT"),
        ("lizenz", "TEXT"),
    ]
    g_zeilen = [
        [
            g["id"],
            g["art"],
            g["bez"],
            g["flaeche_m2"],
            g["art"] in gruen_zaehlt,
            g["quelle"],
            stand,
            "dl-de/by-2-0",
            (g["wkb"], g["huelle"]),
        ]
        for g in d["gruen"]
    ]
    # haltestelle
    h_felder = [
        ("stop_id", "TEXT"),
        ("name", "TEXT"),
        ("verkehrsmittel", "TEXT"),
        ("fahrten_hvz_je_richtung", "REAL"),
        ("klasse", "TEXT"),
        ("in_potsdam", "BOOLEAN"),
        ("raum_nr", "TEXT"),
        ("stand", "TEXT"),
        ("lizenz", "TEXT"),
    ]
    h_zeilen = [
        [
            h["stop_id"],
            h["name"],
            h["verkehrsmittel"],
            h["fahrten"],
            h["klasse"],
            h["in_potsdam"],
            h["raum"],
            stand,
            "CC BY 4.0",
            (punkt_wkb(round(h["x"], 2), round(h["y"], 2)), None),
        ]
        for h in d["haltestelle"]
    ]
    # lizenz
    l_felder = [("ebene", "TEXT"), ("lizenz", "TEXT"), ("vermerk", "TEXT"), ("lizenztext", "TEXT")]
    l_zeilen = [
        [
            "raumeinheit (Grenzen)",
            "dl-zero-de/2.0" if raumebene == "stadtteil" else "laut Handdownload H1",
            raum_vermerk,
            DLZERO if raumebene == "stadtteil" else "",
        ],
        [
            "raumeinheit, versorgung (Werte)",
            "dl-de/by-2-0; ÖPNV-Werte CC BY 4.0",
            f"{VERMERK['zensus']}; {VERMERK['mbjs']}; {VERMERK['lgb']}; {VERMERK['vbb']}",
            DLDE,
        ],
        ["einrichtung", "dl-de/by-2-0", f"{VERMERK['mbjs']}; {VERMERK['lgb']}", DLDE],
        ["zelle", "dl-de/by-2-0", z_vermerk, DLDE],
        ["gruenflaeche", "dl-de/by-2-0", VERMERK["lgb"], DLDE],
        ["haltestelle", "CC BY 4.0", VERMERK["vbb"], CCBY],
    ]

    ebenen = [
        ("raumeinheit", "Raumeinheiten mit Versorgungswerten", "MULTIPOLYGON", r_felder, r_zeilen),
        ("versorgung", "Versorgung je Raumeinheit (eine Zeile je Wert)", None, v_felder, v_zeilen),
        ("einrichtung", "Einrichtungen (MBJS, ALKIS)", "POINT", e_felder, e_zeilen),
        ("zelle", "Zensus-Zellen 100 m: Einwohner und Luftlinie", "POLYGON", z_felder, z_zeilen),
        ("gruenflaeche", "Grünflächen (ALKIS-Nutzung)", "MULTIPOLYGON", g_felder, g_zeilen),
        ("haltestelle", "Haltestellen (VBB-GTFS)", "POINT", h_felder, h_zeilen),
        ("lizenz", "Lizenzen und Vermerke je Ebene", None, l_felder, l_zeilen),
    ]
    beschreibung = {
        "raumeinheit": f"Je {raumebene}. Werte aus daten/planer.js (A6), Luftlinie. {planer['hinweis']}",
        "versorgung": "Alle Werte aus daten/planer.js mit Status, Maßstab, Unsicherheit und Quelle.",
        "einrichtung": ein["hinweis"],
        "zelle": "Bewohnte 100-m-Zellen des Zensus 2022: nur Einwohner und Luftlinie zum nächsten Standort je Art "
        "(Meter, auf 10 m gerundet). " + err["hinweis"],
        "gruenflaeche": "ALKIS-Nutzung. zaehlt_gruenversorgung = Grünanlage oder Park (config/richtwerte.yaml).",
        "haltestelle": "Haltestellen mit Taktklasse nach NVP 2019 (A4).",
        "lizenz": "Lizenz und Vermerk je Ebene.",
    }
    gpkg_pfad = ziel / "kiezatlas_potsdam.gpkg"
    gp = GPKG(gpkg_pfad, d["srs"], stand)
    for name, titel, geom, felder, zeilen in ebenen:
        gp.ebene(name, titel, beschreibung[name], geom, felder, zeilen)
    stile = stile_bauen(
        gruen_zaehlt,
        sorted({f["properties"]["art"] for f in ein["features"]}, key=lambda a: list(ART).index(a) if a in ART else 99),
        [],
    )
    gp.stile(stile, {n: g is not None for n, _, g, _, _ in ebenen})
    gp.schliessen()
    # CSV
    for name, _, geom, felder, zeilen in ebenen:
        namen = [n for n, _ in felder]
        if geom == "POINT":
            out = [z[:-1] + list(struct.unpack("<dd", z[-1][0][5:21])) for z in zeilen]
            csv_schreiben(ziel / "csv" / f"{name}.csv", namen + ["x", "y"], out)
        elif geom:
            if name == "raumeinheit":
                wkt = [d["raeume"][z[0]]["wkt"] for z in zeilen]
            elif name == "zelle":
                wkt = [d["zelle"][z[0]]["wkt"] for z in zeilen]
            else:
                wkt = [g["wkt"] for g in d["gruen"]]
            csv_schreiben(ziel / "csv" / f"{name}.csv", namen + ["wkt"], [z[:-1] + [w] for z, w in zip(zeilen, wkt)])
        else:
            csv_schreiben(ziel / "csv" / f"{name}.csv", namen, zeilen)
    # Stile als Dateien
    (ziel / "stile").mkdir(exist_ok=True)
    for name, qml in stile.items():
        (ziel / "stile" / f"{name}.qml").write_text(qml, encoding="utf-8")

    # ------------------------------------------------------------------ ODbL (nur wenn A3/A5b geliefert haben)
    odbl_pfad = ziel / "kiezatlas_potsdam_odbl.gpkg"
    odbl_ebenen = []
    odbl_stile: dict[str, str] = {}
    if ein_odbl and ein_odbl.get("features"):
        felder = [
            ("id", "TEXT"),
            ("art", "TEXT"),
            ("unterart", "TEXT"),
            ("raum_nr", "TEXT"),
            ("stand", "TEXT"),
            ("lizenz", "TEXT"),
        ]
        zeilen = [
            [
                f["properties"]["id"],
                f["properties"]["art"],
                f["properties"].get("unterart"),
                nr,
                ein_odbl["stand"],
                "ODbL 1.0",
                (punkt_wkb(round(x, 2), round(y, 2)), None),
            ]
            for f, (x, y, nr) in zip(ein_odbl["features"], odbl_punkte)
        ]
        odbl_ebenen.append(
            ("einrichtung_odbl", "Einrichtungen aus OpenStreetMap (ohne Namen)", "POINT", felder, zeilen)
        )
    if err_fuss:
        if (err_fuss["anzahl"], err_fuss["erste_id"], err_fuss["letzte_id"]) != (len(ids), ids[0], ids[-1]):
            raise SystemExit("erreichbar_fuss_odbl.js passt nicht zur Reihenfolge von zellen.js")
        fa = err_fuss["arten"]
        einheit = err_fuss.get("einheit", "m")
        felder = (
            [("gitter_id", "TEXT"), ("raum_nr", "TEXT"), ("ew", "INTEGER")]
            + [(f"fuss_{art}_{einheit}", "INTEGER") for art in fa]
            + [("stand", "TEXT"), ("lizenz", "TEXT")]
        )
        zeilen = [
            [g, d["zelle"][g]["raum"], zprops[g].get("ew")]
            + [err_fuss["werte"][art][i] for art in fa]
            + [err_fuss["stand"], "ODbL 1.0", (d["zelle"][g]["wkb"], d["zelle"][g]["huelle"])]
            for i, g in enumerate(ids)
        ]
        odbl_ebenen.append(("zelle_fuss_odbl", "Zellen: Fußweg zum nächsten Standort", "POLYGON", felder, zeilen))
    if planer_fuss:
        odbl_ebenen.append(
            (
                "versorgung_fuss_odbl",
                "Versorgung je Raumeinheit, Fußweg",
                None,
                v_felder,
                versorgung_zeilen(planer_fuss),
            )
        )
    if odbl_ebenen:
        go = GPKG(odbl_pfad, d["srs"], stand)
        for name, titel, geom, felder, zeilen in odbl_ebenen:
            go.ebene(name, titel, f"Abgeleitet aus OpenStreetMap. {VERMERK['osm']}", geom, felder, zeilen)
        go.ebene(
            "lizenz",
            "Lizenz",
            "Open Database License 1.0",
            None,
            l_felder,
            [[n, "ODbL 1.0", VERMERK["osm"], ODBL] for n, *_ in odbl_ebenen],
        )
        if ein_odbl and ein_odbl.get("features"):
            odbl_stile = {
                "einrichtung_odbl": stile_bauen(
                    gruen_zaehlt, [], sorted({f["properties"]["art"] for f in ein_odbl["features"]})
                )["einrichtung_odbl"]
            }
        go.stile(odbl_stile, {n: g is not None for n, _, g, _, _ in odbl_ebenen})
        go.schliessen()
        for name, _, geom, felder, zeilen in odbl_ebenen:
            namen = [n for n, _ in felder]
            if geom == "POINT":
                out = [z[:-1] + list(struct.unpack("<dd", z[-1][0][5:21])) for z in zeilen]
                csv_schreiben(ziel / "csv_odbl" / f"{name}.csv", namen + ["x", "y"], out)
            elif geom:
                csv_schreiben(
                    ziel / "csv_odbl" / f"{name}.csv",
                    namen + ["wkt"],
                    [z[:-1] + [d["zelle"][z[0]]["wkt"]] for z in zeilen],
                )
            else:
                csv_schreiben(ziel / "csv_odbl" / f"{name}.csv", namen, zeilen)
        for name, qml in odbl_stile.items():
            (ziel / "stile" / f"{name}.qml").write_text(qml, encoding="utf-8")
        meldungen.append(f"ODbL: {', '.join(n for n, *_ in odbl_ebenen)} geschrieben")
    else:
        if odbl_pfad.exists():
            odbl_pfad.unlink()
        meldungen.append("ODbL: keine *_odbl.js in der Quelle (A3/A5b leer, H5 fehlt), keine _odbl-Datei")

    # ------------------------------------------------------------------ QGIS-Projekt
    pe = [
        {
            "name": "einrichtung",
            "titel": "Einrichtungen",
            "gpkg": gpkg_pfad.name,
            "geom": "POINT",
            "qml": stile["einrichtung"],
        },
        {
            "name": "haltestelle",
            "titel": "Haltestellen (NVP-Klasse)",
            "gpkg": gpkg_pfad.name,
            "geom": "POINT",
            "qml": stile["haltestelle"],
            "an": False,
        },
        {
            "name": "raumeinheit",
            "titel": "Raumeinheiten",
            "gpkg": gpkg_pfad.name,
            "geom": "MULTIPOLYGON",
            "qml": stile["raumeinheit"],
        },
        {
            "name": "zelle",
            "titel": "Zensus-Zellen (Einwohner)",
            "gpkg": gpkg_pfad.name,
            "geom": "POLYGON",
            "qml": stile["zelle"],
        },
        {
            "name": "gruenflaeche",
            "titel": "Grünflächen",
            "gpkg": gpkg_pfad.name,
            "geom": "MULTIPOLYGON",
            "qml": stile["gruenflaeche"],
        },
        {"name": "versorgung", "titel": "Versorgung (Tabelle)", "gpkg": gpkg_pfad.name, "geom": None},
        {"name": "lizenz", "titel": "Lizenzen (Tabelle)", "gpkg": gpkg_pfad.name, "geom": None},
    ]
    for name, titel, geom, *_ in odbl_ebenen:
        pe.append(
            {
                "name": name,
                "titel": f"{titel} (ODbL)",
                "gpkg": odbl_pfad.name,
                "geom": geom,
                "qml": stile.get(name) or (odbl_stile or {}).get(name),
                "an": False,
            }
        )
    alle = [r[-1][1] for r in r_zeilen]
    huelle = (min(h[0] for h in alle), max(h[1] for h in alle), min(h[2] for h in alle), max(h[3] for h in alle))
    qgs = projekt_bauen(pe, d["srs"][SRID], huelle, "Kiezatlas Potsdam")
    zip_fest(ziel / "kiezatlas_potsdam.qgz", {"kiezatlas_potsdam.qgs": qgs.encode("utf-8")})

    # ------------------------------------------------------------------ Steckbriefe
    sb = ziel / "steckbriefe"
    sb.mkdir(exist_ok=True)
    for alt in sb.glob("*.html"):
        alt.unlink()
    pkt = [
        {
            "art": f["properties"]["art"],
            "plaetze": f["properties"].get("plaetze"),
            "schueler": f["properties"].get("schueler"),
            **d["einrichtung"][f["properties"]["id"]],
        }
        for f in ein["features"]
    ]
    for nr, r in planer["raeume"].items():
        zellen = [
            (d["zelle"][g]["svg"], zprops[g]["ew"]) for g in ids if d["zelle"][g]["raum"] == nr and zprops[g].get("ew")
        ]
        karte = svg_karte(karten[nr], d["raeume"][nr]["svg"], zellen, pkt, gruen_zaehlt)
        drin = [p for p in pkt if p["raum"] == nr]
        html_text = steckbrief(
            nr, r, planer, karte, drin, {"km2": d["raeume"][nr]["km2"], "zellen": len(zellen)}, raumebene, raum_vermerk
        )
        (sb / f"{nr}.html").write_text(html_text, encoding="utf-8")

    # ------------------------------------------------------------------ README
    readme_schreiben(ziel, planer, ebenen, odbl_ebenen, raumebene, raum_vermerk, err, gruen_zaehlt)

    # ------------------------------------------------------------------ Beleg
    dateien = sorted(p for p in ziel.rglob("*") if p.is_file())
    zeilen_beleg = [
        f"| `{p.relative_to(ziel)}` | {p.stat().st_size:,} | `{md5(p)}` |".replace(",", ".") for p in dateien
    ]
    zaehler = {n: len(z) for n, _, _, _, z in ebenen} | {n: len(z) for n, _, _, _, z in odbl_ebenen}
    text = (
        f"# Beleg A8: GIS-Export, Lauf mit Stand {stand}\n\n"
        f"Quelle: `{quelle.relative_to(WURZEL) if quelle.is_relative_to(WURZEL) else quelle}`, Ziel: "
        f"`{ziel.relative_to(WURZEL) if ziel.is_relative_to(WURZEL) else ziel}`, Raumebene: {raumebene}.\n\n"
        "## Ebenen und Zeilen\n\n" + "\n".join(f"- {n}: {z}" for n, z in zaehler.items()) + "\n\n"
        "## Meldungen\n\n" + "\n".join(f"- {m}" for m in meldungen) + "\n\n"
        "## Dateien\n\n| Datei | Bytes | MD5 |\n|---|---|---|\n" + "\n".join(zeilen_beleg) + "\n"
    )
    print(text)
    if not a.ohne_beleg and not fixture:
        (WURZEL / "belege" / f"A8_export_{stand.replace('-', '')}.md").write_text(text, encoding="utf-8")
    return 0


def readme_schreiben(
    ziel: Path,
    planer: dict,
    ebenen: list,
    odbl_ebenen: list,
    raumebene: str,
    raum_vermerk: str,
    err: dict,
    gruen_zaehlt: set[str],
) -> None:
    def feldliste(felder):
        return ", ".join(f"`{n}`" for n, _ in felder)

    zeilen = "\n".join(
        f"| `{n}` | {'Tabelle' if g is None else g} | {len(z)} | {feldliste(f)} |" for n, _, g, f, z in ebenen
    )
    odbl = (
        "\n".join(
            f"| `{n}` | {'Tabelle' if g is None else g} | {len(z)} | {feldliste(f)} |" for n, _, g, f, z in odbl_ebenen
        )
        if odbl_ebenen
        else "| – | – | – | noch nicht erzeugt: OSM-Auszug (Handdownload) und Fußwegnetz fehlen |"
    )
    text = f"""# Kiezatlas Potsdam: Daten zum Weiterverwenden

Stand der Auswertung {planer["stand"]}. Erzeugt mit `skripte/16_export.py` aus denselben Datendateien wie die
Seite (`daten/planer.js`, `daten/einrichtungen.js`, `daten/erreichbar.js`, `daten/zellen.js`) und der Geometrie aus
der Projektdatenbank. Raumebene: **{"Planungsraum" if raumebene == "planungsraum" else "Stadtteil (32 Stadtteile; Planungsräume folgen, sobald die Grenzen vorliegen)"}**.

## Dateien

| Datei | Inhalt | Lizenz |
|---|---|---|
| `kiezatlas_potsdam.gpkg` | GeoPackage, EPSG:25833 (ETRS89 / UTM 33N), ohne Anteil aus OpenStreetMap | je Ebene, siehe unten und Tabelle `lizenz` |
| `kiezatlas_potsdam_odbl.gpkg` | Ebenen aus OpenStreetMap (Fußweg, weitere Einrichtungen) | Open Database License 1.0 |
| `csv/*.csv` | dieselben Ebenen als CSV | wie die GeoPackage-Ebene |
| `csv_odbl/*.csv` | die ODbL-Ebenen als CSV | Open Database License 1.0 |
| `kiezatlas_potsdam.qgz` | QGIS-Projekt (relative Pfade, liegt neben der GPKG) | Apache-2.0 (Projektdatei) |
| `stile/*.qml` | QGIS-Stile; dieselben Stile stehen als Standardstil in der GPKG (`layer_styles`) | Apache-2.0 |
| `steckbriefe/<nr>.html` | druckbarer Steckbrief je Raumeinheit (A4) | wie die Werte |

Jede Zeile trägt in `lizenz` das Kürzel ihrer Lizenz; der vollständige Vermerk steht in der Tabelle `lizenz`
(GPKG und `csv/lizenz.csv`) und unten.

CSV: Trennzeichen Semikolon, UTF-8 mit BOM, Dezimalpunkt. Punkte mit Spalten `x`, `y`, Flächen mit `wkt`, beides
in EPSG:25833 auf 1 cm. Wahrheitswerte als 1 und 0.

## Ebenen ohne OpenStreetMap (`kiezatlas_potsdam.gpkg`, `csv/`)

| Ebene | Geometrie | Zeilen | Felder |
|---|---|---|---|
{zeilen}

- `raumeinheit`: Grenzen mit Einwohnern und je Kennzahl einer Spalte (Kurzname wie in `versorgung.spalte`).
- `versorgung`: jede Kennzahl als eigene Zeile mit `status`, `vorlaeufig`, Maßstab (`richtwert`, Quelle,
  Fundstelle), `unsicherheit`, Quelle und Stand. Die Breitform in `raumeinheit` enthält nur die Zahl; lesen Sie
  die Zahl immer mit dieser Zeile.
- `einrichtung`: Kitas, Horte und Schulen (MBJS) mit Plätzen bzw. Schülern, Gemeinbedarf aus ALKIS nur als Lage.
  `raum_nr` ist leer bei Standorten außerhalb Potsdams (sie zählen bei den Entfernungen mit).
- `zelle`: bewohnte 100-m-Zellen des Zensus 2022 mit Einwohnern und der Luftlinie in Metern zum nächsten
  Standort je Art (`m_<art>`, auf 10 m gerundet; leer = Zelle ohne Einwohner). Keine Altersklassen je Zelle.
- `gruenflaeche`: ALKIS-Nutzung; `zaehlt_gruenversorgung` = {", ".join(sorted(gruen_zaehlt))}.
- `haltestelle`: Haltestellen mit Fahrten in der Hauptverkehrszeit und Taktklasse nach NVP 2019.

## Ebenen aus OpenStreetMap (`kiezatlas_potsdam_odbl.gpkg`, `csv_odbl/`)

| Ebene | Geometrie | Zeilen | Felder |
|---|---|---|---|
{odbl}

Diese Ebenen sind aus OpenStreetMap abgeleitet und stehen unter der Open Database License 1.0
({ODBL}), © OpenStreetMap-Mitwirkende. Wer sie verändert und weitergibt, gibt die veränderte Datenbank
unter derselben Lizenz weiter. Sie liegen absichtlich in einer eigenen Datei, damit die übrigen Daten frei von
dieser Bedingung bleiben.

## Lizenzen und Vermerke

Bei Weitergabe oder Veröffentlichung den Vermerk der genutzten Ebenen übernehmen:

- **Grenzen der Raumeinheiten:** {raum_vermerk}
- **Einwohner, Zellen:** {VERMERK["zensus"]}
- **Kitas, Horte, Schulen:** {VERMERK["mbjs"]}
- **Gemeinbedarf, Grünflächen:** {VERMERK["lgb"]}
- **Haltestellen, ÖPNV-Werte:** {VERMERK["vbb"]}
- **Ebenen mit _odbl:** {VERMERK["osm"]}

Die Maßstäbe (Nahverkehrsplan 2019, Baulandmodell 2019, Schülerfahrtkostensatzung, Umweltatlas Berlin) sind als
Zahl mit Fundstelle übernommen, nicht als Text. Der Code des Kiezatlas steht unter Apache-2.0, die Daten nicht.

## Methode in Kürze

- **Einwohner und Kinder:** Zensus 2022, 100-m-Gitter, Stichtag 15.05.2022. Das Cell-Key-Verfahren verändert
  kleine Werte; Summen vieler Zellen weichen deshalb ab. Einwohner je Raumeinheit auf 10 gerundet. Werte aus
  feinen Altersklassen nur für Raumeinheiten ab 100 Einwohnern, unter 20 Personen der Zielgruppe kein Wert.
  Neubau nach dem Stichtag (u. a. Krampnitz, Bornstedter Feld, Golm) fehlt.
- **Entfernung:** Luftlinie vom Zellmittelpunkt (bis 71 m vom Wohnort) zum nächsten Standort, aussagekräftig auf
  rund 50 m. Standorte in Brandenburg außerhalb der Stadt zählen mit, Berlin nicht; am Stadtrand ist der Wert
  deshalb teils nur eine Obergrenze.
- **Zuordnung zur Raumeinheit:** über den Zellmittelpunkt bzw. den Standort.
- **Status:** `amtlich` = Maßstab aus einem Potsdamer Dokument mit gelesener Fundstelle, bei Werten ohne Maßstab
  nur amtliche Daten. `orientierung` = Maßstab ohne Primärbeleg, Fundstelle nicht gelesen oder Berliner Methode;
  kein Richtwert. `vorlaeufig` = Grundschulwert ohne Schulbezirk.
- **Kita:** Kapazität laut Betriebserlaubnis, nicht Belegung; Kinder 2022, Plätze 2026. Tagespflege fehlt.
- **Grün:** vereinfachte Berliner Methode (Grünanlagen und Parks aus ALKIS im 500-m-Kreis je Einwohner), ohne
  Mindestgröße; SPSG-Parks lassen sich nicht abgrenzen und zählen mit.

Ausführlich: `config/richtwerte.yaml`, `QUELLEN.md` und die Methodenseite des Kiezatlas.

## Datenschutz

Keine Adressen, keine Kontaktdaten, keine Personendaten. Je Zelle nur Einwohnerzahl und Entfernungen, keine
Alters-, Haushalts- oder Staatsangehörigkeitsklassen. Einrichtungen aus OpenStreetMap ohne Namen.

## In QGIS öffnen

`kiezatlas_potsdam.qgz` neben `kiezatlas_potsdam.gpkg` liegen lassen und öffnen. Alternativ die GPKG per
Ziehen und Ablegen laden; QGIS übernimmt die hinterlegten Stile. Schriften der Beschriftung: Barlow Semi
Condensed (fehlt sie, nimmt QGIS eine Ersatzschrift).

## Steckbriefe drucken

Die Steckbriefe sind HTML für den Druck (A4) und laufen mit WeasyPrint (Python, mit installiertem `weasyprint`):

```
python -c "from weasyprint import HTML; \\
  from weasyprint.text.fonts import FontConfiguration as F; f=F(); \\
  HTML('daten/export/steckbriefe/13.html').write_pdf('13.pdf', font_config=f)"
```

Die Schriften kommen aus `fonts/` des Repositorys (relativer Pfad); im Browser über „Drucken“ geht es ebenso.
"""  # noqa: E501
    (ziel / "README.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
