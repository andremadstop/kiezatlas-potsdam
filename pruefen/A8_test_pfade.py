"""Pfadtests Paket A8: ODbL-Pfad gegen Fixtures, Sperre für Fixtures in daten/export, Gegenproben der Prüfung.

Was mit den heutigen Daten nicht läuft oder nicht auffallen kann, wird hier erzwungen:
  1. 16_export.py mit --quelle daten/fixtures ohne --ziel bricht ab (Beispieldaten nie nach daten/export).
  2. 16_export.py mit --quelle daten/fixtures --ziel <tmp> schreibt kiezatlas_potsdam_odbl.gpkg und csv_odbl/;
     A8_export.py --odbl-erwartet ist dagegen grün (ODbL nur in der _odbl-Datei, Vermerke, ohne Namen).
  3. Gegenproben: eine Kopie des echten Exports wird gezielt verdorben (Altersklasse je Zelle, Adresse im
     Namen, OSM-Vermerk in der dl-de-Datei, Fußweg-Methode, Kontaktspalte, Orange im Stil); A8_export.py muss
     jeden Fehler melden.
Braucht die Leserolle in der Umgebung (wie 16_export.py). Aufruf: python -I pruefen/A8_test_pfade.py
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
EXPORT = WURZEL / "skripte" / "16_export.py"
PRUEF = WURZEL / "pruefen" / "A8_export.py"
fehler: list[str] = []


def lauf(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", *args], capture_output=True, text=True, cwd=WURZEL)


def erwarte(ok: bool, text: str) -> None:
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def main() -> int:
    print("[1] Fixtures nie nach daten/export")
    r = lauf(str(EXPORT), "--quelle", "daten/fixtures")
    erwarte(r.returncode != 0 and "fixture" in (r.stderr + r.stdout), "Abbruch mit Hinweis auf fixture")
    erwarte(not (WURZEL / "daten" / "export" / "kiezatlas_potsdam_odbl.gpkg").exists(), "daten/export ohne _odbl-Datei")
    r = lauf(str(EXPORT), "--quelle", "daten/fixtures", "--ziel", "daten/export/probe")
    erwarte(
        r.returncode != 0 and not (WURZEL / "daten" / "export" / "probe").exists(),
        "auch kein Unterordner von daten/export (Abbruch, nichts angelegt)",
    )

    with tempfile.TemporaryDirectory(prefix="a8_") as tmp:
        tmp = Path(tmp)
        print("[2] ODbL-Pfad gegen Fixtures")
        r = lauf(str(EXPORT), "--quelle", "daten/fixtures", "--ziel", str(tmp / "fix"), "--ohne-beleg")
        erwarte(r.returncode == 0, f"Export der Fixtures läuft ({r.stderr.strip()[-200:]})")
        erwarte((tmp / "fix" / "kiezatlas_potsdam_odbl.gpkg").exists(), "kiezatlas_potsdam_odbl.gpkg geschrieben")
        erwarte(
            sorted(p.name for p in (tmp / "fix" / "csv_odbl").glob("*.csv"))
            == ["einrichtung_odbl.csv", "versorgung_fuss_odbl.csv", "zelle_fuss_odbl.csv"],
            "csv_odbl/ mit drei Ebenen",
        )
        r = lauf(str(PRUEF), "--quelle", "daten/fixtures", "--ziel", str(tmp / "fix"), "--odbl-erwartet")
        erwarte(
            r.returncode == 0,
            "A8_export.py --odbl-erwartet gegen den Fixture-Export: 0 Befunde"
            + ("" if r.returncode == 0 else " | " + " | ".join(z for z in r.stdout.splitlines() if "FEHLT" in z)[:600]),
        )

        r = lauf(str(EXPORT), "--ziel", str(tmp / "fix"), "--ohne-beleg")
        fix = tmp / "fix"
        erwarte(
            r.returncode == 0
            and not (fix / "kiezatlas_potsdam_odbl.gpkg").exists()
            and not (fix / "csv_odbl").exists()
            and not (fix / "stile" / "einrichtung_odbl.qml").exists(),
            "Lauf ohne ODbL-Daten in denselben Ordner räumt _odbl.gpkg, csv_odbl/ und den ODbL-Stil ab",
        )
        print("[3] Gegenproben: verdorbene Kopie des echten Exports")
        faelle = [
            ("Altersklasse je Zelle", 'ALTER TABLE zelle ADD COLUMN "i_u3" INTEGER', "Positivliste"),
            ("Adresse im Namen", "UPDATE einrichtung SET name = 'Kita Musterstraße 12' WHERE fid = 1", "Hausnummer"),
            ("PLZ im Namen", "UPDATE einrichtung SET name = 'Kita 14467 Potsdam' WHERE fid = 2", "Hausnummer"),
            (
                "OSM-Vermerk",
                "UPDATE gpkg_contents SET description = description || ' © OpenStreetMap' "
                "WHERE table_name = 'gruenflaeche'",
                "kein OpenStreetMap",
            ),
            ("Fußweg-Methode", "UPDATE versorgung SET methode = 'fussweg' WHERE fid = 1", "Methode nur luftlinie"),
            ("Kontaktspalte", 'ALTER TABLE haltestelle ADD COLUMN "telefon" TEXT', "Kontaktspalte"),
            ("Wert verändert", "UPDATE versorgung SET wert = wert + 1 WHERE fid = 1", "wie planer.js"),
            ("falsches SRS", "UPDATE gpkg_geometry_columns SET srs_id = 4326 WHERE table_name = 'zelle'", "SRS 25833"),
            (
                "Orange im Stil",
                "UPDATE layer_styles SET styleQML = replace(styleQML, '28,74,91,255', '230,120,20,255') "
                "WHERE f_table_name = 'einrichtung'",
                "Orange",
            ),
        ]
        for titel, sql, erwartet in faelle:
            kopie = tmp / "k"
            if kopie.exists():
                shutil.rmtree(kopie)
            shutil.copytree(WURZEL / "daten" / "export", kopie)
            c = sqlite3.connect(kopie / "kiezatlas_potsdam.gpkg")
            c.execute(sql)
            c.commit()
            c.close()
            r = lauf(str(PRUEF), "--ziel", str(kopie))
            treffer = [zeile for zeile in r.stdout.splitlines() if "FEHLT" in zeile and erwartet in zeile]
            erwarte(
                r.returncode != 0 and bool(treffer),
                f"{titel}: gemeldet ({(treffer or ['nicht gemeldet'])[0].strip()[:110]})",
            )
        print("[4] Gegenproben in CSV und Steckbriefen")
        # Steckbriefe je Raumeinheit (Stadtteile oder Planungsräume): die ersten beiden vorhandenen nehmen
        sb = sorted(p.name for p in (WURZEL / "daten" / "export" / "steckbriefe").glob("*.html"))
        if len(sb) < 2:
            erwarte(False, f"mindestens zwei Steckbriefe in daten/export/steckbriefe ({len(sb)})")
            print(f"\n{len(fehler)} Befunde")
            return 1
        erst, zweit = f"steckbriefe/{sb[0]}", f"steckbriefe/{sb[1]}"
        faelle_text = [
            ("Adresse in CSV", "csv/einrichtung.csv", "Grundschule", "Grundschule Lindenstraße 5", "Hausnummer"),
            ("OSM in CSV", "csv/gruenflaeche.csv", "dl-de/by-2-0", "© OpenStreetMap", "csv/: kein OSM"),
            ("Zahl fehlt in CSV", "csv/zelle.csv", ";dl-de/by-2-0", ";dl-de/by-2-0", "Werte wie GPKG"),
            (
                "OSM im Steckbrief",
                erst,
                "Quellen und Lizenzen",
                "Quellen, OpenStreetMap",
                "steckbriefe/",
            ),
            (
                "Platzhalter im Steckbrief",
                erst,
                "Lesehilfe</h2>",
                "Lesehilfe</h2><p>None</p>",
                "Platzhalter",
            ),
            (
                "Telefon im Steckbrief",
                zweit,
                "Lesehilfe</h2>",
                "Lesehilfe</h2><p>0331 2891234</p>",
                "Telefon",
            ),
        ]
        for titel, datei, alt, neu, erwartet in faelle_text:
            kopie = tmp / "k"
            if kopie.exists():
                shutil.rmtree(kopie)
            shutil.copytree(WURZEL / "daten" / "export", kopie)
            p = kopie / datei
            text = p.read_text(encoding="utf-8-sig" if datei.endswith(".csv") else "utf-8")
            if titel == "Zahl fehlt in CSV":  # erste Entfernung der ersten Zeile leeren
                kopf, erste, rest = text.split("\n", 2)
                felder = erste.split(";")
                felder[4] = ""
                text = "\n".join([kopf, ";".join(felder), rest])
            else:
                text = text.replace(alt, neu, 1)
            p.write_text(text, encoding="utf-8-sig" if datei.endswith(".csv") else "utf-8")
            r = lauf(str(PRUEF), "--ziel", str(kopie))
            treffer = [zeile for zeile in r.stdout.splitlines() if "FEHLT" in zeile and erwartet in zeile]
            erwarte(
                r.returncode != 0 and bool(treffer) and "Traceback" not in r.stderr,
                f"{titel}: gemeldet ({(treffer or ['nicht gemeldet: ' + r.stderr[-150:]])[0].strip()[:110]})",
            )
    print(f"\n{len(fehler)} Befunde")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
