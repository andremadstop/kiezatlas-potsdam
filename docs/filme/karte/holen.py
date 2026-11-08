# Film „Potsdam wächst aus den Daten“: Geometrien aus der Kiezatlas-Datenbank exportieren (nur lesend).
# Aufruf aus der Repo-Wurzel:
#   python3 docs/filme/karte/holen.py --aus berichte/filme-2026-11-08/karte/daten [--psql "docker exec -i kiezatlas-potsdam-db-1 psql -U admin -d kiezatlas"]
# Kein Netzabruf. Liest die Tabellen, die die sieben Importläufe gefüllt haben (gebaeude, zensus_zelle,
# zensus_struktur, alkis_nutzung, mbjs_kita, mbjs_schule, stadtteil), alles umgerechnet nach EPSG:25833.
# Die Sitzung ist schreibgeschützt (default_transaction_read_only). Objektkennungen (oid, gitter_id,
# id_kita, schul_nr) werden nicht exportiert, nur Reihenfolge, Lage und die für den Film nötigen Felder.
import argparse
import csv
import io
import json
import os
import shlex
import subprocess
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--aus", required=True)
ap.add_argument("--psql", default=os.environ.get("KIEZ_PSQL", "docker exec -i kiezatlas-potsdam-db-1 psql -U admin -d kiezatlas"))
args = ap.parse_args()
os.makedirs(args.aus, exist_ok=True)

STADT = "(SELECT ST_Union(geom) AS g FROM stadtteil)"
# Kacheln wie die Pipeline (_kacheln: zeilenweise ab xmin/ymin): Gebäude 1000 m, Nutzung 2000 m,
# bbox aus config/potsdam.yaml (gebaeude_alkis, alkis_nutzung). prep.py prüft die bbox gegen die Konfiguration.
ABFRAGEN = {
    # Gebäude: Stadtteil (Punkt im Umriss wie skripte/02_auswerten.py), Rang in der Reihenfolge der
    # daten/gebaeude/<nr>.js (ORDER BY oid), linke untere Ecke für die Kachel, Lagepunkt zum Abgleich.
    "gebaeude.csv": """
        SELECT s.nr,
               CASE WHEN s.nr IS NULL THEN NULL ELSE row_number() OVER (PARTITION BY s.nr ORDER BY g.oid) - 1 END AS rang,
               round(ST_XMin(ST_Transform(g.geom, 25833))::numeric, 2) AS xmin,
               round(ST_YMin(ST_Transform(g.geom, 25833))::numeric, 2) AS ymin,
               round(ST_X(ST_Transform(ST_PointOnSurface(g.geom), 25833))::numeric, 2) AS px,
               round(ST_Y(ST_Transform(ST_PointOnSurface(g.geom), 25833))::numeric, 2) AS py,
               g.anzahlgs,
               CASE WHEN s.nr IS NULL THEN ST_AsGeoJSON(ST_SimplifyPreserveTopology(ST_Transform(g.geom, 25833), 0.5), 1) END AS geo
        FROM gebaeude g
        LEFT JOIN stadtteil s ON ST_Contains(s.geom, ST_PointOnSurface(g.geom))
        ORDER BY s.nr NULLS LAST, g.oid""",
    # Zensus-Zellen: 100-m-Quadrat in EPSG:3035 (wie die Grenzfall-Rechnung), nach 25833 umgerechnet.
    # in_potsdam = Mittelpunkt in einem Stadtteil; grenz = bewohnte Zelle, die die Stadtgrenze schneidet.
    "zellen.csv": f"""
        SELECT z.ew,
               EXISTS (SELECT 1 FROM stadtteil s WHERE ST_Contains(s.geom, z.geom)) AS in_potsdam,
               (coalesce(z.ew, 0) > 0
                AND ST_Intersects(ST_Expand(ST_Transform(z.geom, 3035), 50), ST_Transform(st.g, 3035))
                AND NOT ST_Within(ST_Expand(ST_Transform(z.geom, 3035), 50), ST_Transform(st.g, 3035))) AS grenz,
               EXISTS (SELECT 1 FROM zensus_struktur k WHERE k.gitter_id = z.gitter_id) AS struktur,
               ST_AsText(ST_Transform(ST_Expand(ST_Transform(z.geom, 3035), 50), 25833), 1) AS wkt
        FROM zensus_zelle z, {STADT} st
        ORDER BY z.gitter_id""",
    "struktur_anzahl.csv": "SELECT count(*) AS n FROM zensus_struktur",
    "nutzung.csv": """
        SELECT n.nutzart,
               round(ST_XMin(ST_Transform(n.geom, 25833))::numeric, 2) AS xmin,
               round(ST_YMin(ST_Transform(n.geom, 25833))::numeric, 2) AS ymin,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(ST_Transform(n.geom, 25833), 2.0), 1) AS geo
        FROM alkis_nutzung n
        ORDER BY n.oid""",
    "kita.csv": f"""
        SELECT round(ST_X(ST_Transform(k.geom, 25833))::numeric, 1) AS x,
               round(ST_Y(ST_Transform(k.geom, 25833))::numeric, 1) AS y,
               ST_Contains(st.g, k.geom) AS in_potsdam
        FROM mbjs_kita k, {STADT} st ORDER BY k.id_kita""",
    "schule.csv": f"""
        SELECT round(ST_X(ST_Transform(k.geom, 25833))::numeric, 1) AS x,
               round(ST_Y(ST_Transform(k.geom, 25833))::numeric, 1) AS y,
               ST_Contains(st.g, k.geom) AS in_potsdam
        FROM mbjs_schule k, {STADT} st ORDER BY k.schul_nr""",
    "stadtteile.csv": """
        SELECT s.nr, s.name,
               round(ST_X(ST_Transform(ST_PointOnSurface(s.geom), 25833))::numeric, 1) AS lx,
               round(ST_Y(ST_Transform(ST_PointOnSurface(s.geom), 25833))::numeric, 1) AS ly,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(ST_Transform(s.geom, 25833), 3.0), 1) AS geo
        FROM stadtteil s ORDER BY s.nr""",
}


def abfrage(sql):
    sql = " ".join(sql.split())
    skript = ("\\set ON_ERROR_STOP 1\n"
              "SET default_transaction_read_only = on;\n"
              "BEGIN READ ONLY;\n"
              f"COPY ({sql}) TO STDOUT WITH (FORMAT csv, HEADER true);\n"
              "COMMIT;\n")
    r = subprocess.run(shlex.split(args.psql) + ["-X", "-q", "-v", "ON_ERROR_STOP=1"], input=skript.encode(),
                       capture_output=True, check=False)
    if r.returncode != 0:
        sys.exit("psql: " + r.stderr.decode(errors="replace"))
    txt = r.stdout.decode()
    # SET/BEGIN/COMMIT schreiben bei -q nichts; der COPY-Block beginnt mit der Kopfzeile
    return txt


protokoll = {"stand": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "dateien": {}}
for name, sql in ABFRAGEN.items():
    t0 = time.time()
    txt = abfrage(sql)
    zeilen = list(csv.reader(io.StringIO(txt)))
    with open(os.path.join(args.aus, name), "w", encoding="utf-8", newline="") as f:
        f.write(txt)
    protokoll["dateien"][name] = {"zeilen": len(zeilen) - 1, "s": round(time.time() - t0, 1)}
    print(name, len(zeilen) - 1, "Zeilen", round(time.time() - t0, 1), "s", flush=True)
with open(os.path.join(args.aus, "export-protokoll.json"), "w", encoding="utf-8") as f:
    json.dump(protokoll, f, ensure_ascii=False, indent=1)
