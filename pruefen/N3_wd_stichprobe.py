"""N3: Handstichprobe der Wikidata-Zuordnung (B2) – zieht 20 Zuordnungen geschichtet und legt sie zum Ansehen vor.

Liest die interne Zuordnungsliste, die `skripte/22_jahre_genau.py --detail` außerhalb des Repos schreibt
($KIEZ_DATEN/wikidata_zuordnung/2026-11-05/zuordnung.csv, Bezeichnungen können Adressen enthalten), und holt je
Zeile aus der Datenbank: ALKIS-Funktion des Gebäudes, ob der Wikidata-Punkt im Umriss liegt (sonst Abstand in m),
Zahl der BLDAM-Gebäude der Denkmal-ID und ob das Gebäude Wohnraum hat.

Schichten (fester Seed, erstes Argument, Vorgabe 2211): 6 × ID mit einem Gebäude, 4 × ID mit 2 bis 4
Gebäuden, 7 × Koordinate,
3 × Koordinate nach Ensemble-ID (mehr als 4 BLDAM-Gebäude), aufgefüllt aus „Koordinate“, falls zu wenige.

Ausgabe: die volle Tabelle mit Bezeichnung nur nach $KIEZ_DATEN/wikidata_zuordnung/2026-11-05/stichprobe_seed<SEED>.csv;
auf stdout dieselben Zeilen ohne Bezeichnung und ohne oid (für belege/), bei Gebäuden mit Wohnraum zusätzlich ohne
Objekt, Denkmal-ID, Fläche und Jahr (nur die Bauzeitklasse). Das Urteil trägt der Mensch ein.

Aufruf wie skripte/22_jahre_genau.py (PG*-Umgebung als kiezatlas_rechnen, KIEZ_DATEN gesetzt).
"""
from __future__ import annotations

import csv
import os
import random
import sys
from pathlib import Path

import psycopg

WURZEL = Path(__file__).resolve().parent.parent
KIEZ_DATEN = Path(os.environ.get("KIEZ_DATEN", WURZEL.parent / "kiezatlas-daten"))
ORDNER = KIEZ_DATEN / "wikidata_zuordnung/2026-11-05"
SNAPSHOT = "auswertung.gebaeude_stand_20261105"
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 2211  # Durchgang 1: 2211, Durchgang 2: 2212


KLASSEN = [(1918, "vor 1919"), (1948, "1919–1948"), (1978, "1949–1978"), (1990, "1979–1990"), (2000, "1991–2000"),
           (2010, "2001–2010"), (2019, "2011–2019"), (9999, "ab 2020")]


def klasse_text(von, bis) -> str:
    """Bauzeitklasse (Mikrozensus-Klassen wie daten/jahre/) zu einer Spanne, sonst „(intern)“."""
    jahre = [int(j) for j in (von, bis) if str(j or "").strip().isdigit()]
    ks = {next(k for g, k in KLASSEN if j <= g) for j in jahre}
    return f"Klasse {ks.pop()}" if len(ks) == 1 else "(intern)"


def main() -> int:
    zeilen = list(csv.DictReader((ORDNER / "zuordnung.csv").open(encoding="utf-8")))
    with psycopg.connect("") as conn, conn.cursor() as cur:
        cur.execute("""SELECT split_part(beleg_url, '#', 2), count(DISTINCT oid_bezug) FROM auswertung.jahr_beleg
                       WHERE quelle LIKE 'BLDAM%' GROUP BY 1""")
        bldam_n = dict(cur.fetchall())
        for z in zeilen:
            z["bldam_gebaeude"] = bldam_n.get(z["midas"], 0)
        rng = random.Random(SEED)
        schichten = [
            ("ID, ein Gebäude", [z for z in zeilen if z["weg"] == "ID" and z["oids_je_id"] == "1"], 6),
            ("ID, 2 bis 4 Gebäude", [z for z in zeilen if z["weg"] == "ID" and z["oids_je_id"] != "1"], 4),
            ("Koordinate nach Ensemble-ID",
             [z for z in zeilen if z["weg"] == "Koordinate" and z["bldam_gebaeude"] > 4], 3),
            ("Koordinate", [z for z in zeilen if z["weg"] == "Koordinate" and z["bldam_gebaeude"] <= 4], 7),
        ]
        probe = []
        for name, menge, n in schichten:
            menge = sorted(menge, key=lambda z: (z["item"], z["oid"]))
            gezogen = rng.sample(menge, min(n, len(menge)))
            probe += [dict(z, schicht=name) for z in gezogen]
        if len(probe) < 20:  # auffüllen aus „Koordinate“
            rest = [z for z in schichten[3][1] if z not in probe]
            probe += [dict(z, schicht="Koordinate") for z in rng.sample(rest, 20 - len(probe))]
        for z in probe:
            cur.execute(f"""SELECT coalesce(g.funktion, ''), (g.funktion ~* 'wohn' OR g.funktion = 'Forsthaus'),
                                   CASE WHEN %(ns)s::float8 IS NULL THEN NULL
                                        ELSE ST_Intersects(g.geom, ST_SetSRID(ST_MakePoint(%(ew)s, %(ns)s), 4326)) END,
                                   CASE WHEN %(ns)s::float8 IS NULL THEN NULL
                                        ELSE round(ST_Distance(g.geom::geography, ST_SetSRID(
                                             ST_MakePoint(%(ew)s, %(ns)s), 4326)::geography)::numeric, 0) END,
                                   round(ST_Area(g.geom::geography)::numeric, 0)
                            FROM {SNAPSHOT} g WHERE g.oid = %(oid)s""",
                        {"oid": z["oid"], "ew": float(z["ew"]) if z["ew"] else None,
                         "ns": float(z["ns"]) if z["ns"] else None})
            funk, wohn, im, ab, fl = cur.fetchone()
            z.update(funktion=funk, wohnraum=bool(wohn), punkt_im_umriss=im, abstand_m=ab, flaeche_m2=fl)
    felder = ["nr", "schicht", "item", "label", "midas", "weg", "oids_je_id", "bldam_gebaeude", "funktion",
              "wohnraum", "punkt_im_umriss", "abstand_m", "flaeche_m2", "von", "bis", "genau", "oid"]
    with (ORDNER / f"stichprobe_seed{SEED}.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=felder, extrasaction="ignore")
        w.writeheader()
        for i, z in enumerate(probe, 1):
            w.writerow(dict(z, nr=i))
    oeffentlich = [f for f in felder if f not in ("label", "oid")]
    print("\t".join(oeffentlich))
    for i, z in enumerate(probe, 1):
        z = dict(z, nr=i)
        if z["wohnraum"]:
            # Korrektur 6: bei Wohnraum weder Objekt noch Jahr noch Fläche in die Repo-Fassung (über die Fläche ließe
            # sich das Gebäude in daten/jahre/ wiederfinden); statt des Jahrs nur die Bauzeitklasse
            z.update(item="(intern)", midas="(intern)", flaeche_m2="(intern)",
                     von=klasse_text(z["von"], z["bis"]), bis="")
        print("\t".join(str(z.get(f, "")) for f in oeffentlich))
    return 0


if __name__ == "__main__":
    sys.exit(main())
