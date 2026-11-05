"""Abnahme Paket B1 (Zensus-Baujahr im Gitter), ohne Datenbank und ohne Netz.

Prüft daten/jahre_zellen.js über den Vertrag hinaus (den prüft pruefen/daten.py):
  1. Zellen mit Gebäuden und Summe in Potsdam (Erwartung 2.869 / 23.155, Mikrozensus-Klassen)
  2. anteile/vorherrschend sind null, wo keine Verteilung ablesbar ist; sonst Länge = Klassen, Summe ≈ 100
  3. gzip -9 ≤ 120 KB
  4. Lizenzvermerk mit Link zum Lizenztext und „Daten verändert (eigene Berechnung)“
  5. keine Gebäudekennung und keine Gebäudefärbung aus Zellklassen (keine oid, keine Datei unter daten/jahre/)
  6. Korrekturen 17 und 21: kein Pipeline-Eintrag für zensus_gebaeude_jahr, 01_vorbereiten.py gleich dem Basiszweig

Aufruf: ../kiezatlas-potsdam-west/.venv/bin/python -I pruefen/b1_jahre.py [basiszweig, Standard ausbau/p0]
"""
from __future__ import annotations

import gzip
import json
import subprocess  # nosec B404
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "daten"
fehler = 0


def pruef(ok: bool, text: str) -> None:
    global fehler
    print(f"  {'ok  ' if ok else 'FEHLT'}  {text}")
    fehler += not ok


def main() -> int:
    basis = sys.argv[1] if len(sys.argv) > 1 else "ausbau/p0"
    pfad = DATEN / "jahre_zellen.js"
    roh = pfad.read_bytes()
    text = roh.decode("utf-8")
    kopf = text[: text.index("window.KIEZ_JAHRE_ZELLEN=")]
    d = json.loads(text[text.index("=", len(kopf)) + 1:].strip().rstrip(";"))
    g, a, v, k = d["gebaeude"], d["anteile"], d["vorherrschend"], d["klassen"]

    mit = sum(1 for x in g if x is not None)
    summe = sum(x for x in g if x)
    pruef(mit == 2869 and summe == 23155, f"Potsdam: {mit} Zellen mit Gebäuden, Σ {summe} (Erwartung 2869 / 23155)")
    pruef(all(an is None for x, an in zip(g, a) if x is None), "keine Anteile in Zellen ohne Gebäude")
    falsch = [i for i, an in enumerate(a) if an is not None and (len(an) != len(k) or abs(sum(an) - 100) > 0.5)]
    pruef(not falsch, f"Anteile: Länge {len(k)}, Summe 100 ± 0,5 (Abweichungen: {falsch[:5]})")
    pruef(all(an is not None or vv is None for an, vv in zip(a, v)), "vorherrschend null, wo anteile null")
    ok_v = all(vv is None or (an[vv] == max(an) and an.count(max(an)) >= 1) for an, vv in zip(a, v) if an is not None)
    pruef(ok_v, "vorherrschend zeigt auf die größte Klasse")
    gz = len(gzip.compress(roh, 9))
    pruef(gz <= 120_000, f"gzip -9 {gz} Byte ≤ 120 KB")
    pruef("https://www.govdata.de/dl-de/by-2-0" in kopf and "Daten verändert (eigene Berechnung)" in kopf
          and all("Daten verändert (eigene Berechnung)" in q["vermerk"] and "govdata.de/dl-de/by-2-0" in q["vermerk"]
                  for q in d["quellen"].values()), "Vermerk dl-de/by-2-0 mit Link und Bearbeitungshinweis (Kopf und quellen)")
    pruef(d["beschriftung"] == "Gebäude mit Wohnraum je Zelle, nicht einzelne Gebäude", "Beschriftung „nicht einzelne Gebäude“")
    # Im Integrationszweig liegt daten/jahre/ von B4 vor; dann Basis als Bereich angeben (ausbau/p0..ausbau/b1),
    # geprüft wird, dass die Commits von B1 kein daten/jahre/ anlegen (Ergänzung I1, 05.11.2026).
    if ".." in basis:
        jahre = subprocess.run(["git", "-C", str(WURZEL), "diff", "--name-only", basis, "--", "daten/jahre"],
                               capture_output=True, text=True, check=False).stdout.strip()  # nosec B603 B607
    else:
        jahre = (DATEN / "jahre").exists()
    pruef('"oid"' not in text and not jahre, "keine Gebäude-oid, kein daten/jahre/ aus B1")

    yaml = (WURZEL / "config" / "potsdam.yaml").read_text(encoding="utf-8")
    pruef("zensus_gebaeude_jahr" not in yaml, "kein Pipeline-Eintrag zensus_gebaeude_jahr in config/potsdam.yaml (Korrektur 17)")
    diff = subprocess.run(["git", "-C", str(WURZEL), "diff", "--stat", basis, "--", "skripte/01_vorbereiten.py",
                           "skripte/02_auswerten.py", "config/potsdam.yaml", "QUELLEN.md"],
                          capture_output=True, text=True, check=False)  # nosec B603 B607
    pruef(diff.returncode == 0 and not diff.stdout.strip(),
          f"01_vorbereiten.py, 02_auswerten.py, potsdam.yaml, QUELLEN.md gleich {basis} (Korrektur 21)")
    print(f"\n{fehler} Abweichungen")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
