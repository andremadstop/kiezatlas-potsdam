"""Kiezatlas Potsdam, Paket B5: Bauzeiten als GeoPackage (EPSG:25833) für QGIS/ArcGIS.

Liest nur Dateien aus dem Repo (daten/jahre_zellen.js von B1, daten/zellen.js, daten/stadtteile.js),
kein Netz, keine Datenbank. Schreibt daten/download/bauzeiten.gpkg mit drei Tabellen:

  zellen      100-m-Zellen mit Gebäuden mit Wohnraum, Quadrat exakt aus der gitter_id (EPSG:3035)
              nach EPSG:25833 umgerechnet; Werte wie die Zell-CSV der Daten-Seite
  stadtteile  genäherte Mischung je Stadtteil, gerundet wie die Stadtteil-CSV der Daten-Seite
              (Anteile ganze Prozent, Gebäudezahlen auf 10); Geometrie aus daten/stadtteile.js
  hinweis     Quelle, Lizenz, Vermerk, Lizenztext, Stand (Pflicht bei Weitergabe)

Keine Adressen, kein OSM, keine Angaben zu einzelnen Gebäuden.

GeoPackage ohne GDAL: SQLite mit den Pflichttabellen aus OGC 12-128r18 (gpkg_spatial_ref_sys,
gpkg_contents, gpkg_geometry_columns), Geometrie als GeoPackageBinary (Kopf "GP", Hüllrechteck, WKB).

Aufruf (aus dem Repo, mit -I):  ../kiezatlas-potsdam-west/.venv/bin/python -I skripte/25_jahre_gpkg.py
"""
import json
import math
import os
import re
import sqlite3
import struct
import sys
import tempfile

from pyproj import CRS, Transformer
import numpy as np
import shapely
from shapely import to_wkb
from shapely.geometry import MultiPolygon, Polygon, shape

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.path.join(WURZEL, "daten", "download", "bauzeiten.gpkg")
WENIG_MINDEST = 50  # wie MINDEST in jahre.js: weniger Gebäude bekannter Bauzeit -> vergleichbar = 0
LIZENZTEXT = "https://www.govdata.de/dl-de/by-2-0"
SRS = 25833


def lies_js(name):
    t = open(os.path.join(WURZEL, "daten", name), encoding="utf-8").read()
    t = re.sub(r"^\s*/\*.*?\*/\s*", "", t, flags=re.S)
    return json.loads(t[t.index("=") + 1:].strip().rstrip(";"))


def rund_halb(x):
    """wie Math.round in JavaScript (halbe Werte aufwärts), nicht Pythons Bankrundung"""
    return int(math.floor(x + 0.5))


def slug(s):
    s = re.sub(r"^vor ", "vor_", s)
    s = re.sub(r"^ab ", "ab_", s)
    return re.sub(r"\s+", "_", s.replace("–", "_"))


def gp_blob(geom):
    """GeoPackageBinary: Magic, Version 0, Flags (Little Endian, Hüllrechteck [minx,maxx,miny,maxy]), srs_id, Hülle, WKB"""
    minx, miny, maxx, maxy = geom.bounds
    kopf = b"GP" + bytes([0, 0b00000011]) + struct.pack("<i", SRS) + struct.pack("<4d", minx, maxx, miny, maxy)
    return kopf + to_wkb(geom, byte_order=1)


def main():
    J = lies_js("jahre_zellen.js")
    Z = lies_js("zellen.js")
    ST = lies_js("stadtteile.js")
    if J.get("fixture"):
        sys.exit("jahre_zellen.js ist eine Fixture, kein Export")
    feats = Z["features"]
    n = J["anzahl"]
    if len(feats) != n or feats[0]["properties"]["id"] != J["erste_id"] or feats[-1]["properties"]["id"] != J["letzte_id"]:
        sys.exit("jahre_zellen.js passt nicht zu zellen.js (anzahl/erste_id/letzte_id)")
    KL = J["klassen"]
    spalten = ["anteil_" + slug(k) for k in KL]
    q = J["quellen"][next(iter(J["quellen"]))]

    def umrechner(von):
        tr = Transformer.from_crs(von, SRS, always_xy=True)
        return lambda xy: np.column_stack(tr.transform(xy[:, 0], xy[:, 1]))
    nach25833, aus4326 = umrechner(3035), umrechner(4326)

    # ---------- Zellen
    zellen = []
    raum = {}
    for i, f in enumerate(feats):
        g = J["gebaeude"][i]
        if g is None:
            continue
        a = J["anteile"][i]
        v = J["vorherrschend"][i]
        p = f["properties"]
        m = re.fullmatch(r"CRS3035RES100mN(\d+)E(\d+)", p["id"])
        y0, x0 = int(m.group(1)), int(m.group(2))  # Zensus-Gitter: Koordinate der linken unteren Ecke
        quadrat = Polygon([(x0, y0), (x0 + 100, y0), (x0 + 100, y0 + 100), (x0, y0 + 100), (x0, y0)])
        zellen.append({
            "geom": shapely.transform(quadrat, nach25833), "gitter_id": p["id"], "stadtteil": p["st"], "gebaeude": g,
            "anteile": a, "vorherrschend": None if v is None else KL[v], "klassen_geheim": 1 if a is None else 0,
        })
        r = raum.setdefault(p["st"], {"g": 0, "gk": 0, "z": 0, "c": [0.0] * len(KL)})
        r["g"] += g
        r["z"] += 1
        if a is not None:
            summe = sum(a) or 1
            r["gk"] += g
            for k, w in enumerate(a):
                r["c"][k] += g * w / summe

    # ---------- Stadtteile (gleiche Näherung wie jahre.js: rechnen/anteil)
    teile = {f["properties"]["nr"]: f for f in ST["features"]}
    stadtteile = []
    for nr in sorted(raum, key=int):
        r = raum[nr]
        geo = shapely.transform(shape(teile[nr]["geometry"]), aus4326)
        if isinstance(geo, Polygon):
            geo = MultiPolygon([geo])
        anteile = [None if not r["gk"] else rund_halb(100 * c / r["gk"]) for c in r["c"]]
        stadtteile.append({
            "geom": geo, "nr": nr, "name": teile[nr]["properties"]["name"],
            "gebaeude_rund": rund_halb(r["g"] / 10) * 10, "zellen": r["z"],
            "gebaeude_ohne_klassen_rund": rund_halb((r["g"] - r["gk"]) / 10) * 10,
            "anteile": anteile, "vergleichbar": 1 if r["gk"] >= WENIG_MINDEST else 0,
        })

    # ---------- Schreiben (erst in eine Nachbardatei, dann umbenennen)
    os.makedirs(os.path.dirname(ZIEL), exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".gpkg", dir=os.path.dirname(ZIEL))
    os.close(fd)
    os.remove(tmp)
    db = sqlite3.connect(tmp)
    db.execute("PRAGMA application_id = 1196444487")  # 0x47504B47 'GPKG'
    db.execute("PRAGMA user_version = 10400")
    db.executescript("""
    CREATE TABLE gpkg_spatial_ref_sys (srs_name TEXT NOT NULL, srs_id INTEGER PRIMARY KEY, organization TEXT NOT NULL,
      organization_coordsys_id INTEGER NOT NULL, definition TEXT NOT NULL, description TEXT);
    CREATE TABLE gpkg_contents (table_name TEXT NOT NULL PRIMARY KEY, data_type TEXT NOT NULL, identifier TEXT UNIQUE,
      description TEXT DEFAULT '', last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE, srs_id INTEGER,
      CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id));
    CREATE TABLE gpkg_geometry_columns (table_name TEXT NOT NULL, column_name TEXT NOT NULL, geometry_type_name TEXT NOT NULL,
      srs_id INTEGER NOT NULL, z TINYINT NOT NULL, m TINYINT NOT NULL,
      CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name),
      CONSTRAINT fk_gc_tn FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
      CONSTRAINT fk_gc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys (srs_id));
    """)
    db.executemany("INSERT INTO gpkg_spatial_ref_sys VALUES (?,?,?,?,?,?)", [
        ("Undefined cartesian SRS", -1, "NONE", -1, "undefined", "undefined cartesian coordinate reference system"),
        ("Undefined geographic SRS", 0, "NONE", 0, "undefined", "undefined geographic coordinate reference system"),
        ("WGS 84 geodetic", 4326, "EPSG", 4326, CRS.from_epsg(4326).to_wkt("WKT1_GDAL"), "longitude/latitude coordinates in decimal degrees on the WGS 84 spheroid"),
        ("ETRS89 / UTM zone 33N", SRS, "EPSG", SRS, CRS.from_epsg(SRS).to_wkt("WKT1_GDAL"), "ETRS89 / UTM zone 33N"),
    ])
    stand = J["stand"] + "T00:00:00.000Z"
    vermerk = q["vermerk"]

    def tabelle(name, ident, beschreibung, spalten_sql, zeilen, werte):
        db.execute(f"CREATE TABLE {name} (fid INTEGER PRIMARY KEY AUTOINCREMENT, geom {'MULTIPOLYGON' if name == 'stadtteile' else 'POLYGON'}, {spalten_sql})")
        platz = ",".join("?" * (1 + len(werte(zeilen[0]))))
        db.executemany(f"INSERT INTO {name} (geom, {', '.join(c.split()[0] for c in spalten_sql.split(', '))}) VALUES ({platz})",
                       [(gp_blob(z["geom"]),) + tuple(werte(z)) for z in zeilen])
        b = [min(z["geom"].bounds[0] for z in zeilen), min(z["geom"].bounds[1] for z in zeilen),
             max(z["geom"].bounds[2] for z in zeilen), max(z["geom"].bounds[3] for z in zeilen)]
        db.execute("INSERT INTO gpkg_contents VALUES (?,?,?,?,?,?,?,?,?,?)", (name, "features", ident, beschreibung, stand, *b, SRS))
        db.execute("INSERT INTO gpkg_geometry_columns VALUES (?,?,?,?,0,0)", (name, "geom", "MULTIPOLYGON" if name == "stadtteile" else "POLYGON", SRS))

    anteil_sql = ", ".join(s + " REAL" for s in spalten)
    tabelle("zellen", "Bauzeiten je 100-m-Zelle",
            J["beschriftung"] + ". " + q["quelle"] + ". " + vermerk + ".",
            "gitter_id TEXT, stadtteil TEXT, gebaeude INTEGER, " + anteil_sql + ", vorherrschend TEXT, klassen_geheim INTEGER",
            zellen,
            lambda z: [z["gitter_id"], z["stadtteil"], z["gebaeude"]] + (z["anteile"] or [None] * len(KL)) + [z["vorherrschend"], z["klassen_geheim"]])
    tabelle("stadtteile", "Bauzeiten je Stadtteil, genähert",
            "Genäherte Mischung je Stadtteil (Zellanteile mit der Gebäudezahl gewichtet), Anteile ganze Prozent, Gebäudezahlen auf 10 gerundet; "
            "vergleichbar = 0: weniger als %d Gebäude mit bekannter Bauzeit. Stadtteilgrenzen © Landeshauptstadt Potsdam, dl-zero-de/2.0. %s." % (WENIG_MINDEST, vermerk),
            "nr TEXT, name TEXT, gebaeude_rund INTEGER, zellen INTEGER, gebaeude_ohne_klassen_rund INTEGER, "
            + ", ".join(s + " INTEGER" for s in spalten) + ", vergleichbar INTEGER",
            stadtteile,
            lambda z: [z["nr"], z["name"], z["gebaeude_rund"], z["zellen"], z["gebaeude_ohne_klassen_rund"]] + z["anteile"] + [z["vergleichbar"]])
    db.execute("CREATE TABLE hinweis (id INTEGER PRIMARY KEY, schluessel TEXT, wert TEXT)")
    db.executemany("INSERT INTO hinweis (schluessel, wert) VALUES (?,?)", [
        ("titel", "Kiezatlas Potsdam: Bauzeiten"), ("stand", J["stand"]), ("beschriftung", J["beschriftung"]),
        ("quelle", q["quelle"]), ("lizenz", q["lizenz"]), ("lizenztext", LIZENZTEXT), ("vermerk", vermerk),
        ("stadtteilgrenzen", "© Landeshauptstadt Potsdam, dl-zero-de/2.0"),
        ("hinweis", J.get("hinweis", "")), ("koordinaten", "ETRS89 / UTM zone 33N (EPSG:25833)"),
        ("inhalt", "Keine Daten aus OpenStreetMap, keine Adressen, keine Angaben zu einzelnen Gebäuden."),
    ])
    db.execute("INSERT INTO gpkg_contents (table_name, data_type, identifier, description, last_change) VALUES (?,?,?,?,?)",
               ("hinweis", "attributes", "Quelle und Lizenz", "Namensnennung bei Weitergabe: " + vermerk, stand))
    db.commit()
    db.execute("VACUUM")
    db.close()
    os.replace(tmp, ZIEL)
    print(f"{os.path.relpath(ZIEL, WURZEL)}: {len(zellen)} Zellen, {len(stadtteile)} Stadtteile, {os.path.getsize(ZIEL) // 1024} KB")


if __name__ == "__main__":
    main()
