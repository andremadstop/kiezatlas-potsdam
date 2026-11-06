"""Abnahme Paket A3 gegen die Datenbank (Bauplan A3, fünf Kriterien). Schreibt nichts außer TEMP-Tabellen.

Aufruf: skripte/12_osm.sh pruefen [--bericht berichte/A3_vollstaendigkeit.md]
Ausgang 0 nur, wenn alle Kriterien erfüllt sind.
"""
from __future__ import annotations

import argparse
import importlib
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "skripte"))
osm = importlib.import_module("12_osm")

OSM_TABELLEN = ("osm_poi", "netz_knoten", "netz_kante")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bericht", type=Path, default=WURZEL / "berichte" / "A3_vollstaendigkeit.md")
    a = ap.parse_args()
    ergebnisse: list[tuple[bool, str, str]] = []
    with osm.verbinden() as conn, conn.cursor() as cur:
        cur.execute(osm.PUFFER_SQL)
        # 1. keine Spalte name (auch keine Adress- oder Kontaktspalte)
        cur.execute("""SELECT column_name FROM information_schema.columns
                       WHERE table_schema = 'auswertung' AND table_name = 'osm_poi' ORDER BY ordinal_position""")
        spalten = [r[0] for r in cur.fetchall()]
        verboten = [s for s in spalten if re.search(r"name|addr|adresse|strasse|phone|telefon|mail|website", s)]
        ergebnisse.append((not verboten, "auswertung.osm_poi hat keine Spalte name",
                           f"Spalten: {', '.join(spalten)}"))
        # 2. Trefferquote im Bericht als Zahl
        if a.bericht.is_file():
            text = a.bericht.read_text(encoding="utf-8")
            quoten = {art: re.search(rf"^\| {art} \|[^\n]*\*\*(\d+,\d) %\*\*", text, re.MULTILINE)
                      for art in ("kita", "schule")}
            ok = all(quoten.values()) and "TROCKENLAUF" not in text
            beleg = ", ".join(f"{k} {m.group(1)} %" if m else f"{k} fehlt" for k, m in quoten.items())
            if "TROCKENLAUF" in text:
                beleg += " (Bericht stammt aus einem Trockenlauf)"
        else:
            ok, beleg = False, f"{a.bericht} fehlt"
        ergebnisse.append((ok, "Vollständigkeitsbericht nennt die Trefferquote für Kitas und Schulen", beleg))
        # 3./4. Netz
        kz = osm.kennzahlen(cur)
        if kz.get("knoten", 0) == 0:
            ergebnisse.append((False, "größte Komponente ≥ 95 % der Knoten im Stadtgebiet", "Netz leer"))
            ergebnisse.append((False, "≥ 98 % der bewohnten Zellmittelpunkte ≤ 150 m vom Netz", "Netz leer"))
        else:
            ergebnisse.append((kz["anteil_groesste_komponente"] >= 0.95,
                               "größte Komponente ≥ 95 % der Knoten im Stadtgebiet",
                               (f"{kz['groesste_komponente_im_stadtgebiet']} von {kz['knoten_im_stadtgebiet']} "
                                f"({100 * kz['anteil_groesste_komponente']:.2f} %), {kz['komponenten']} Komponenten")))
            ergebnisse.append((kz["anteil_zellen_le_150m"] >= 0.98,
                               "≥ 98 % der bewohnten Zellmittelpunkte ≤ 150 m vom Netz",
                               (f"{kz['zellen_le_150m']} von {kz['bewohnte_zellen']} "
                                f"({100 * kz['anteil_zellen_le_150m']:.2f} %), Median {kz['zelle_knoten_median_m']} m, "
                                f"größter {kz['zelle_knoten_max_m']} m")))
        # 5. ODbL-Kommentar
        fehlt = []
        for t in OSM_TABELLEN:
            cur.execute("SELECT obj_description(%s::regclass, 'pg_class')", (f"auswertung.{t}",))
            if "ODbL" not in (cur.fetchone()[0] or ""):
                fehlt.append(t)
        ergebnisse.append((not fehlt, "jede Tabelle mit OSM-Anteil hat den Kommentar ODbL",
                           "alle drei" if not fehlt else f"fehlt: {', '.join(fehlt)}"))
        conn.rollback()
    for ok, was, beleg in ergebnisse:
        print(f"{'✓' if ok else '✗'} {was}: {beleg}")
    return 0 if all(ok for ok, _w, _b in ergebnisse) else 1


if __name__ == "__main__":
    sys.exit(main())
