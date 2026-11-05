"""Nachlauf N4: Grundschuleinzugsgebiete der LHP als interne Prüfspalte (Plausibilität der Grundschulwerte).

Die Datei $KIEZ_DATEN/eingang/grundschuleinzugsgebiete.geojson steht unter den „Nutzungsbedingungen der LHP“, nicht
unter dl-de. Solange diese Bedingungen nicht geprüft sind, geht nichts Geometrisches und nichts daraus Abgeleitetes
in veröffentlichte Dateien (daten/, Export, Belege im Repo). Dieses Skript rechnet deshalb nur intern und schreibt sein
Ergebnis nach $KIEZ_DATEN/intern/ (außerhalb des Repos). Auf der Konsole meldet es nur, ob es gelaufen ist und wohin
es geschrieben hat.

Was geprüft wird, je Planungsraum (Raumebene von skripte/15_planer.py):
  - Kinder 6 bis 9 (Zensus 2022, Summe der Klassen je Zelle, Zuordnung über den Zellmittelpunkt)
  - davon in einem Einzugsgebiet ohne eigenen MBJS-Grundschulstandort (Standort im Gebiet)
  - der Grundschulwert aus daten/planer.js (Anteil bis 1.000 m und 2.000 m Luftlinie) daneben
  - Lage des strittigen Standorts MBJS 103512 im Verhältnis zu den Gebieten (Pestalozza-Fall)
Auffällig ist ein Raum, in dem viele Kinder in Gebieten ohne Standort wohnen, der Radiuswert aber hoch ist (oder
umgekehrt). Das ist ein Hinweis, keine Korrektur: Schulbezirke von 2018, Stand ungeprüft.

Aufruf (Leserolle, offline):
    set -a; . ../kiezatlas-potsdam/.env; set +a
    PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=mosidi_lesen PGPASSWORD="$LESE_PASSWORD" \\
    KIEZ_DATEN=../kiezatlas-daten uv run -q --offline --no-project \\
        --with-requirements ../geodaten-import-pipeline/requirements.txt --with shapely \\
        python -I pruefen/n4_einzugsgebiete.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
WURZEL = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("planer15", WURZEL / "skripte" / "15_planer.py")
PLANER = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PLANER)
DATEI = "grundschuleinzugsgebiete.geojson"
STRITTIG = "103512"


def main() -> int:
    import psycopg
    from shapely.geometry import Point, shape
    from shapely.strtree import STRtree

    basis = Path(os.environ.get("KIEZ_DATEN", WURZEL.parent / "kiezatlas-daten")).resolve()
    quelle = basis / "eingang" / DATEI
    ziel_ordner = basis / "intern"
    if WURZEL.resolve() in ziel_ordner.parents or ziel_ordner == WURZEL.resolve():
        raise SystemExit(f"{ziel_ordner} liegt im Repo; LHP-Ableitungen nie ins Repo schreiben")
    if not quelle.exists():
        print(f"{quelle} fehlt: Prüfspalte Einzugsgebiete nicht gerechnet")
        return 0
    fc = json.loads(quelle.read_text(encoding="utf-8"))
    gebiete = [(str(f["properties"].get("schuleinzu")), shape(f["geometry"])) for f in fc["features"]]
    baum = STRtree([g for _, g in gebiete])

    def gebiet(lon: float, lat: float) -> str | None:
        p = Point(lon, lat)
        for i in baum.query(p):
            if gebiete[int(i)][1].contains(p):
                return gebiete[int(i)][0]
        return None

    with psycopg.connect() as con, con.cursor() as cur:
        con.read_only = True
        ebene, tab, par, herkunft = PLANER.raumquelle(cur)
        cur.execute(
            f"""SELECT r.nr, ST_X(ST_Transform(s.geom, 4326)), ST_Y(ST_Transform(s.geom, 4326)), s.i_6_9
                FROM public.zensus_struktur s JOIN {tab} r ON ST_Contains(r.geom, s.geom)""",
            par or None,
        )
        kinder = cur.fetchall()
        cur.execute("""SELECT id, name, ST_X(ST_Transform(geom, 4326)), ST_Y(ST_Transform(geom, 4326)), in_potsdam
                       FROM auswertung.einrichtung WHERE art = 'grundschule' ORDER BY id""")
        schulen = cur.fetchall()
        cur.execute("""SELECT g.oid, ST_X(ST_Centroid(g.geom)), ST_Y(ST_Centroid(g.geom))
                       FROM public.gebaeude g WHERE g.funktion = 'Allgemein bildende Schule'""")
        alkis_schulen = cur.fetchall()

    standorte = defaultdict(list)
    for i, name, lon, lat, _drin in schulen:
        if i == STRITTIG:
            continue
        g = gebiet(lon, lat)
        if g:
            standorte[g].append(f"{i} {name}")
    alkis_je_gebiet = defaultdict(int)
    for _oid, lon, lat in alkis_schulen:
        g = gebiet(lon, lat)
        if g:
            alkis_je_gebiet[g] += 1

    P = PLANER.json.loads((WURZEL / "daten" / "planer.js").read_text(encoding="utf-8").split("=", 1)[1].rstrip(";\n"))
    gs = defaultdict(dict)
    for nr, r in P["raeume"].items():
        for w in r["werte"]:
            if w["kennzahl"] == "anteil_in_radius" and w["art"] == "grundschule":
                gs[nr][int(float(w["richtwert"]["wert"]))] = w["wert"]

    je_raum = defaultdict(lambda: {"k": 0, "ohne": 0, "gebiete": set()})
    for nr, lon, lat, k in kinder:
        nr = str(nr)
        g = gebiet(lon, lat)
        je_raum[nr]["k"] += k or 0
        if g is None or not standorte.get(g):
            je_raum[nr]["ohne"] += k or 0
        if g:
            je_raum[nr]["gebiete"].add(g)

    lage = {}
    for i, name, lon, lat, _ in schulen:
        if i == STRITTIG:
            lage = {"name": name, "gebiet": gebiet(lon, lat)}
    zeilen = [
        f"# N4 Prüfspalte Grundschuleinzugsgebiete ({date.today().isoformat()}), NUR INTERN",
        "",
        f"Quelle: `{quelle}` (LHP, Nutzungsbedingungen der LHP, nicht geprüft; Stand laut Plan 2018). "
        "Nicht veröffentlichen, nicht ins Repo.",
        f"Raumebene: {ebene} ({herkunft}). Kinder 6 bis 9: Zensus 2022, Summe der Klassen, Zellmittelpunkt.",
        "",
        "## Gebiete ohne MBJS-Grundschulstandort (strittiger Standort 103512 nicht mitgezählt)",
        "",
    ]
    ohne_gebiet = sorted((g for g, _ in gebiete if not standorte.get(g)), key=lambda x: (len(x), x))
    for g in ohne_gebiet:
        zeilen.append(f"- Gebiet {g}: {alkis_je_gebiet.get(g, 0)} ALKIS-Gebäude „Allgemein bildende Schule“")
    def ka(v) -> str:
        return "k. A." if v is None else f"{v} %"

    zeilen += [
        "",
        f"Strittiger Standort {STRITTIG} ({lage.get('name')}): MBJS-Punkt liegt in Gebiet {lage.get('gebiet')}.",
        "",
        "## Je Raumeinheit",
        "",
        "| Raum | Kinder 6–9 | davon in Gebiet ohne Standort | Anteil | GS ≤ 1.000 m | GS ≤ 2.000 m | Gebiete |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for nr in sorted(je_raum):
        x = je_raum[nr]
        ant = PLANER.prozent(x["ohne"], x["k"])
        zeilen.append(
            f"| {nr} | {x['k']} | {x['ohne']} | {ka(ant)} | "
            f"{ka(gs[nr].get(1000))} | {ka(gs[nr].get(2000))} | "
            f"{', '.join(sorted(x['gebiete'], key=lambda s: (len(s), s)))} |"
        )
    zeilen += [
        "",
        "Lesart: hoher Anteil „in Gebiet ohne Standort“ bei hohem Radiuswert ist widersprüchlich und wäre zu klären; "
        "niedriger Radiuswert bei Gebiet ohne Standort passt zusammen (Kinder müssen in ein Nachbargebiet).",
    ]
    ziel_ordner.mkdir(parents=True, exist_ok=True)
    ziel = ziel_ordner / f"N4_einzugsgebiete_{date.today().strftime('%Y%m%d')}.md"
    ziel.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    print(f"Prüfspalte Einzugsgebiete gerechnet ({len(gebiete)} Gebiete, {len(je_raum)} Raumeinheiten); "
          f"Ergebnis nur intern: {ziel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
