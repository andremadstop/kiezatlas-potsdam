"""Abnahme B3 (Luftbild-Pilot): prüft Bericht, Abrufprotokoll, Entscheidung, Datenbank und Repo-Dateien.

Aufruf (Passwort nur aus der .env):
    set -a; . ../kiezatlas-potsdam/.env; set +a
    PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=kiezatlas_rechnen PGPASSWORD="$RECHNEN_PASSWORD" \\
    KIEZ_DATEN=../kiezatlas-daten uv run -q --offline --no-project --with "psycopg[binary]" python -I pruefen/B3_pilot.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from itertools import pairwise
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
KIEZ_DATEN = Path(os.environ.get("KIEZ_DATEN", WURZEL.parent / "kiezatlas-daten"))
ABLAGE = KIEZ_DATEN / "luftbild_lgb" / "2026-11-05"
fehler = 0


def pruefe(ok: bool, text: str) -> None:
    global fehler
    print(("ok    " if ok else "FEHLER") + "  " + text)
    fehler += not ok


bericht = (WURZEL / "berichte" / "B3_pilot.md").read_text(encoding="utf-8")
m = re.search(r"trifft\s+bei (\d+) von (\d+) \(([\d,]+) %\)", bericht)
pruefe(bool(m) and int(m.group(2)) >= 50, f"Bericht nennt Trefferquote und Zahl der Prüfgebäude: {m.groups() if m else None}")
pruefe("Ausrollen: nein" in bericht or "Ausrollen: ja" in bericht, "Bericht dokumentiert die Entscheidung")
protokoll = (WURZEL / "pruefen" / "B3_protokoll.md").read_text(encoding="utf-8")
pruefe("## 9. Ergebnis und Entscheidung" in protokoll and "nicht ausgerollt" in protokoll,
       "Protokoll dokumentiert die Entscheidung (§9)")

# Abrufprotokoll: alle Anfragen an isk.geobasis-bb.de mit >= 10 s Abstand, alle Luftbild-Dateien protokolliert
zeiten, luftbild = [], set()
for zeile in (KIEZ_DATEN / "abrufprotokoll.tsv").read_text(encoding="utf-8").splitlines()[1:]:
    t = zeile.split("\t")
    # nur die Anfragen von B3: WMS (mapproxy) und die robots.txt-Prüfung direkt davor (10:27 UTC)
    if len(t) > 6 and t[1] == "isk.geobasis-bb.de" and (
            "/mapproxy/" in t[2] or (t[2].endswith("/robots.txt") and t[0].startswith("2026-11-05T10:27"))):
        zeiten.append(datetime.fromisoformat(t[0]))
        if "luftbild_lgb/2026-11-05/" in t[6]:
            luftbild.add(t[6].split("luftbild_lgb/2026-11-05/")[1])
abstaende = [(b - a).total_seconds() for a, b in pairwise(zeiten)]
kleinster = min(abstaende) if abstaende else float("nan")
pruefe(bool(abstaende) and kleinster >= 10.0,
       f"Abrufprotokoll, B3-Anfragen an isk.geobasis-bb.de: {len(zeiten)}, kleinster Abstand {kleinster:.1f} s")
dateien = {str(p.relative_to(ABLAGE)) for p in ABLAGE.rglob("*")
           if p.is_file() and p.name != "HERKUNFT.md" and "referenz" not in p.parts}
pruefe(dateien <= luftbild, f"alle {len(dateien)} Luftbild-Dateien stehen im Abrufprotokoll")
herkunft = (ABLAGE / "HERKUNFT.md").read_text(encoding="utf-8") if (ABLAGE / "HERKUNFT.md").exists() else ""
pruefe(all(s in herkunft for s in ("dl-de/by-2-0", "robots", "SHA256", "Abrufdatum")), "HERKUNFT.md vollständig")

# Datenbank
import psycopg

with psycopg.connect() as con, con.cursor() as cur:
    cur.execute("SELECT quelle, count(*) FROM auswertung.jahr_klammer WHERE quelle LIKE 'LGB DOP-Zeitreihe%' GROUP BY 1")
    zeilen = cur.fetchall()
    pruefe(len(zeilen) == 1 and ("nicht ausgerollt" in zeilen[0][0]) == ("Ausrollen: nein" in bericht),
           f"jahr_klammer-Quelle passt zur Entscheidung: {zeilen}")
    cur.execute("SELECT count(*) FROM auswertung.jahr_klammer j LEFT JOIN auswertung.gebaeude_stand_20261105 g "
                "ON g.oid = j.oid_bezug WHERE j.quelle LIKE 'LGB DOP-Zeitreihe%' AND g.oid IS NULL")
    pruefe(cur.fetchone()[0] == 0, "jede Klammer verweist auf ein Gebäude im Snapshot")
    cur.execute("SELECT count(*) FROM auswertung.jahr_klammer WHERE quelle LIKE 'LGB DOP-Zeitreihe%' "
                "AND (nicht_nach NOT IN (1953,1996,2007,2012,2015,2018,2021,2024) "
                "OR (nicht_vor IS NOT NULL AND nicht_vor >= nicht_nach))")
    pruefe(cur.fetchone()[0] == 0, "Klammern nur aus Flugjahren, nicht_vor < nicht_nach")

# Repo: keine Gebäudekennungen oder Adressen in den B3-Dateien
b3 = subprocess.run(["git", "-C", str(WURZEL), "ls-files", "skripte/23_*", "pruefen/B3_*", "berichte/B3_*",
                     "quellen-b3.md"], capture_output=True, text=True, check=True).stdout.split()
treffer = [f for f in b3 if re.search(r"DEBBAL[0-9A-Za-z]{10}", (WURZEL / f).read_text(encoding="utf-8"))]
pruefe(not treffer, f"keine ALKIS-oid in {len(b3)} B3-Dateien im Repo {treffer}")
pruefe("aktualit" not in (WURZEL / "skripte" / "23_luftbild_pilot.py").read_text(encoding="utf-8"),
       "aktualit wird nicht benutzt")

print(f"\n{fehler} Fehler")
sys.exit(1 if fehler else 0)
