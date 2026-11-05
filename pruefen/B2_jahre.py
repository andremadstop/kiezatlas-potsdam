"""Prüfung Paket B2 (genaue Jahre): Abnahmekriterien direkt gegen Datenbank, Abrufprotokoll und Dateien.

  1. Jede Zeile in auswertung.jahr_beleg hat quelle, lizenz und beleg_url (nicht NULL, nicht leer)
  2. Umbau nie als Baujahr: Feld- und Satzregeln an festen Fällen; Wikipedia-, OSM-
     und BLDAM-Zeilen nur als Prüfspalte (nur_pruefung = true); jedes oid_bezug steht im Snapshot
     (Die Handstichprobe von 20 Einträgen steht im Bericht berichte/B2_genaue_jahre.md.)
  3. Zahl genau datierter Gebäude (Prüfspalte und Kaskade getrennt, keine Schwelle)
  4. Im Abrufprotokoll keine Anfrage auf /w/, /sparql, /search oder /api/
  5. Keine Adressen und keine Beschreibungstexte in den B2-Dateien im Repo (berichte/B2_*, quellen-b2.md) und
     keine B2-Ausgabe unter daten/

Aufruf wie skripte/22_jahre_genau.py (PG*-Umgebung als kiezatlas_rechnen):
    uv run -q --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \\
        python -I pruefen/B2_jahre.py
Exit 0 nur, wenn alle Punkte bestehen.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import psycopg

WURZEL = Path(__file__).resolve().parent.parent
KIEZ_DATEN = Path(os.environ.get("KIEZ_DATEN", WURZEL.parent / "kiezatlas-daten"))
PROTOKOLL = KIEZ_DATEN / "abrufprotokoll.tsv"
SNAPSHOT = "auswertung.gebaeude_stand_20261105"
GESPERRT = re.compile(r"/w/|/sparql|/search|/api/|api\.github\.com|raw\.githubusercontent\.com|overpass-api|"
                      r"opendata\.potsdam\.de|nominatim|taginfo|geofabrik|bbbike")
B2_DATEIEN = [*sorted((WURZEL / "berichte").glob("B2_*")), WURZEL / "quellen-b2.md",
              *sorted((WURZEL / "belege").glob("N3_*"))]
ADRESSE = re.compile(r"\b[A-ZÄÖÜ][a-zäöüß-]+(straße|str\.|allee|weg|platz|ring|damm|gasse|ufer|chaussee)\s+\d+",
                     re.IGNORECASE)

fehler: list[str] = []


def pruefe(ok: bool, text: str) -> None:
    print(("ok    " if ok else "FEHLT ") + text)
    if not ok:
        fehler.append(text)


def main() -> int:
    with psycopg.connect("") as conn, conn.cursor() as cur:
        # 1. Pflichtfelder
        cur.execute("""SELECT count(*),
                              count(*) FILTER (WHERE coalesce(trim(quelle), '') = '' OR coalesce(trim(lizenz), '') = ''
                                                  OR coalesce(trim(beleg_url), '') = '')
                       FROM auswertung.jahr_beleg""")
        n, leer = cur.fetchone()
        pruefe(n > 0 and leer == 0, f"jahr_beleg: {n} Zeilen, davon {leer} ohne quelle/lizenz/beleg_url")

        # 2. Umbau nie als Bau, Lizenzgrenzen, Snapshot-Bezug
        # „Umbau nie als Baujahr“ belegt die Handstichprobe im Bericht; hier nur die Regeln selbst an festen Fällen
        sys.path.insert(0, str(WURZEL / "skripte"))
        regeln = __import__("22_jahre_genau")
        faelle = {"1739, Umbau 1851/1890": [(1739, 1739, "bau"), (1851, 1890, "umbau")],
                  "1781 (rekonstruiert 1956/7)": [(1781, 1781, "unklar"), (1956, 1957, "umbau")],
                  "1847–1849 Um- und Erweiterungsbau": [(1847, 1849, "umbau")],
                  "1765 (1783 aus statischen Gründen erneuert)": [(1765, 1765, "bau"), (1783, 1783, "umbau")],
                  "vor 1874": [(None, 1874, "bau")]}
        falsch = [f for f, soll in faelle.items() if [b[:3] for b in regeln.belege_aus_feld(f)] != soll]
        pruefe(not falsch, f"Feldregel an {len(faelle)} festen Fällen (Umbau nie als Bau): {len(falsch)} falsch")
        satz = regeln.belege_aus_text("", "Der vorgelagerte Säulengang entstand 1842/43 nach Entwürfen von Persius.")
        pruefe(all(b[2] != "bau" for b in satz), "Jahr eines Bauteils wird nicht zum Baujahr")
        cur.execute("""SELECT count(*) FROM auswertung.jahr_beleg
                       WHERE NOT nur_pruefung AND (quelle ~* '(wikipedia|openstreetmap|\\mosm\\M|bldam)'
                                                   OR lizenz ~* '(by-sa|odbl|ungeklärt)')""")
        pruefe(cur.fetchone()[0] == 0, "Wikipedia/OSM/BLDAM nur mit nur_pruefung = true")
        cur.execute(f"""SELECT count(*) FROM auswertung.jahr_beleg b
                        WHERE oid_bezug IS NULL
                           OR NOT EXISTS (SELECT 1 FROM {SNAPSHOT} g WHERE g.oid = b.oid_bezug)""")
        pruefe(cur.fetchone()[0] == 0, "jedes oid_bezug steht im Snapshot gebaeude_stand_20261105")
        cur.execute("""SELECT count(*) FROM auswertung.jahr_beleg
                       WHERE art = 'bau' AND jahr_von IS NULL AND jahr_bis IS NULL""")
        pruefe(cur.fetchone()[0] == 0, "jede Bau-Zeile hat mindestens jahr_von oder jahr_bis")
        cur.execute("""SELECT count(*) FROM auswertung.jahr_beleg
                       WHERE genau AND (art <> 'bau' OR jahr_von IS NULL OR jahr_bis IS NULL
                                        OR jahr_bis - jahr_von > 3)""")
        pruefe(cur.fetchone()[0] == 0, "genau nur bei art 'bau' mit Spanne ≤ 3 Jahre")

        # 2b. Wikidata (N3): Ensemble-Regel nur am Anfang der Bezeichnung, mehrere Jahre je Objekt nie genau,
        # Zeilen CC0 und in der Kaskade zugelassen
        ens = {"Louis-Nathan-Allee 5": False, "Allee nach Sanssouci 7": False, "Sparkasse Luisenplatz": False,
               "Park Babelsberg": True, "Friedhof Bornstedt": True, "Muschelgrotte im Neuen Garten": False}
        falsch = [k for k, soll in ens.items() if bool(regeln.WD_ENSEMBLE.search(k)) != soll]
        pruefe(not falsch, f"Wikidata-Ensembleregel an {len(ens)} festen Fällen: {falsch or 'alle richtig'}")
        cur.execute("""SELECT count(*), count(*) FILTER (WHERE nur_pruefung OR lizenz <> 'CC0 1.0'
                                                         OR beleg_url !~ '^http://www\\.wikidata\\.org/entity/Q[0-9]+$')
                       FROM auswertung.jahr_beleg WHERE quelle = 'Wikidata'""")
        n_wd, schlecht = cur.fetchone()
        pruefe(n_wd > 0 and schlecht == 0, f"Wikidata: {n_wd} Zeilen, {schlecht} nicht CC0/zugelassen/mit Objekt-URL")
        cur.execute("""SELECT count(*) FROM (SELECT beleg_url FROM auswertung.jahr_beleg WHERE quelle = 'Wikidata'
                       GROUP BY beleg_url HAVING bool_or(genau)
                          AND count(DISTINCT (jahr_von, jahr_bis)) > 1) x""")
        pruefe(cur.fetchone()[0] == 0, "Wikidata: kein Objekt mit mehreren Jahren trägt ein genaues Jahr")

        # 3. Zahl genau datierter Gebäude
        cur.execute("""SELECT count(DISTINCT oid_bezug) FILTER (WHERE nur_pruefung),
                              count(DISTINCT oid_bezug) FILTER (WHERE NOT nur_pruefung)
                       FROM auswertung.jahr_beleg WHERE art = 'bau' AND genau""")
        pr, ka = cur.fetchone()
        pruefe(True, f"genau datierte Gebäude: {pr} in der Prüfspalte, {ka} für die Kaskade (keine Schwelle)")

    # 4. Abrufprotokoll
    zeilen = PROTOKOLL.read_text(encoding="utf-8").splitlines()[1:]
    treffer = [z.split("\t")[2] for z in zeilen if len(z.split("\t")) > 2 and GESPERRT.search(z.split("\t")[2])]
    pruefe(not treffer, f"Abrufprotokoll: {len(zeilen)} Anfragen, davon {len(treffer)} auf gesperrte Wege")

    # 5. Keine Adressen und Texte in B2-Dateien, keine B2-Ausgabe in daten/
    for d in B2_DATEIEN:
        if not d.exists():
            pruefe(False, f"{d.relative_to(WURZEL)} fehlt")
            continue
        t = d.read_text(encoding="utf-8")
        adr = ADRESSE.findall(t)
        pruefe(not adr, f"{d.relative_to(WURZEL)}: {len(adr)} Adressmuster")
        pruefe("Baumeister:" not in t and "Baujahr:" not in t, f"{d.relative_to(WURZEL)}: keine Beschreibungstexte")
    b2_daten = [p for p in (WURZEL / "daten").rglob("*")
                if p.is_file() and re.search(r"beleg|denkmal|jahr_genau", p.name)]
    pruefe(not b2_daten, f"keine B2-Ausgabe unter daten/ ({len(b2_daten)} Dateien)")

    print(f"\n{len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
