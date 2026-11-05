"""Abnahme Paket B1 (Zensus-Baujahr im Gitter), ohne Datenbank und ohne Netz.

Prüft daten/jahre_zellen.js über den Vertrag hinaus (den prüft pruefen/daten.py):
  1. Zellen mit Gebäuden und Summe in Potsdam (Erwartung 2.869 / 23.155, Mikrozensus-Klassen)
  2. anteile/vorherrschend sind null, wo keine Verteilung ablesbar ist; sonst Länge = Klassen, Summe ≈ 100
  3. gzip -9 ≤ 120 KB
  4. Lizenzvermerk mit Link zum Lizenztext und „Daten verändert (eigene Berechnung)“
  5. keine Gebäudekennung und keine Gebäudefärbung aus Zellklassen (keine oid, keine Datei unter daten/jahre/)
  6. Korrekturen 17 und 21: kein Pipeline-Eintrag für zensus_gebaeude_jahr, 01_vorbereiten.py gleich der Basis
  7. Die Commits von B1 selbst (ausbau/p0...ausbau/b1, ab dem gemeinsamen Vorfahren) legen kein daten/jahre/ an und
     ändern keine der Dateien aus Korrektur 21. Läuft auf jedem Zweig, der ausbau/b1 enthält (Nachlauf N2).

Aufruf: ../kiezatlas-potsdam-west/.venv/bin/python -I pruefen/b1_jahre.py [BASIS]
  BASIS (Nachlauf N2, 05.11.2026; vorher Standard ausbau/p0, auf dem Integrationsstand dauerhaft rot, weil B4
  daten/jahre/ rechtmäßig anlegt):
    ausbau/integration (Standard)  Nachlauf: daten/jahre/ und die Dateien aus Korrektur 21 sind seit dem
                                   Integrationsstand unberührt (eingecheckt, offen, ungetrackt); dazu Prüfung 7.
    ausbau/p0                      Paketzweig ausbau/b1 selbst (daten/jahre/ darf es dort gar nicht geben).
    ausbau/p0...ausbau/b1          nur die Commits von B1, ohne offenen Stand (zwei Punkte gelten wie drei).
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


KORREKTUR_21 = ["skripte/01_vorbereiten.py", "skripte/02_auswerten.py", "config/potsdam.yaml", "QUELLEN.md"]
B1_BEREICH = ("ausbau/p0", "ausbau/b1")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(WURZEL), *args], capture_output=True, text=True, check=False)  # nosec B603 B607


def geaendert(basis: str, *pfade: str) -> list[str] | None:
    """Geänderte Dateien unter pfade gegen basis; None, wenn git scheitert.
    Bereich („a..b“ oder „a...b“): nur die Commits ab dem gemeinsamen Vorfahren, ohne offenen Stand.
    Sonst: Arbeitsstand gegen basis, eingecheckt und offen, dazu ungetrackte Dateien."""
    if ".." in basis:
        von, bis = basis.replace("...", "..").split("..", 1)
        r = git("diff", "--name-only", "-z", f"{von}...{bis}", "--", *pfade)
        return None if r.returncode else [n for n in r.stdout.split("\0") if n]
    r = git("diff", "--name-only", "-z", basis, "--", *pfade)
    u = git("ls-files", "--others", "--exclude-standard", "-z", "--", *pfade)
    if r.returncode or u.returncode:
        return None
    return sorted({n for n in (r.stdout + u.stdout).split("\0") if n})


def main() -> int:
    basis = sys.argv[1] if len(sys.argv) > 1 else "ausbau/integration"
    pfad = DATEN / "jahre_zellen.js"
    roh = pfad.read_bytes()
    text = roh.decode("utf-8")
    kopf = text[: text.index("window.KIEZ_JAHRE_ZELLEN=")]
    d = json.loads(text[text.index("=", len(kopf)) + 1:].strip().rstrip(";"))
    g, a, v, k = d["gebaeude"], d["anteile"], d["vorherrschend"], d["klassen"]

    mit = sum(1 for x in g if x is not None)
    summe = sum(x for x in g if x)
    pruef(mit == 2869 and summe == 23155, f"Potsdam: {mit} Zellen mit Gebäuden, Σ {summe} (Erwartung 2869 / 23155)")
    pruef(all(an is None for x, an in zip(g, a, strict=False) if x is None), "keine Anteile in Zellen ohne Gebäude")
    falsch = [i for i, an in enumerate(a) if an is not None and (len(an) != len(k) or abs(sum(an) - 100) > 0.5)]
    pruef(not falsch, f"Anteile: Länge {len(k)}, Summe 100 ± 0,5 (Abweichungen: {falsch[:5]})")
    pruef(all(an is not None or vv is None for an, vv in zip(a, v, strict=False)),
          "vorherrschend null, wo anteile null")
    ok_v = all(vv is None or (an[vv] == max(an) and an.count(max(an)) >= 1)
               for an, vv in zip(a, v, strict=False) if an is not None)
    pruef(ok_v, "vorherrschend zeigt auf die größte Klasse")
    gz = len(gzip.compress(roh, 9))
    pruef(gz <= 120_000, f"gzip -9 {gz} Byte ≤ 120 KB")
    pruef("https://www.govdata.de/dl-de/by-2-0" in kopf and "Daten verändert (eigene Berechnung)" in kopf
          and all("Daten verändert (eigene Berechnung)" in q["vermerk"] and "govdata.de/dl-de/by-2-0" in q["vermerk"]
                  for q in d["quellen"].values()),
          "Vermerk dl-de/by-2-0 mit Link und Bearbeitungshinweis (Kopf und quellen)")
    pruef(d["beschriftung"] == "Gebäude mit Wohnraum je Zelle, nicht einzelne Gebäude",
          "Beschriftung „nicht einzelne Gebäude“")
    pruef('"oid"' not in text, "keine Gebäude-oid in jahre_zellen.js")
    # daten/jahre/ gehört B4. Gegen ausbau/p0 auf dem Paketzweig darf es gar nicht entstehen; gegen den
    # Integrationsstand darf der Nachlauf es nicht berühren. Was B1 selbst angelegt hat, prüft Teil 7.
    jahre = geaendert(basis, "daten/jahre")
    pruef(jahre == [], f"daten/jahre/ gegen {basis} unberührt"
          + ("" if jahre == [] else f" ({'git scheiterte' if jahre is None else ', '.join(jahre[:5])})"))

    yaml = (WURZEL / "config" / "potsdam.yaml").read_text(encoding="utf-8")
    pruef("zensus_gebaeude_jahr" not in yaml,
          "kein Pipeline-Eintrag zensus_gebaeude_jahr in config/potsdam.yaml (Korrektur 17)")
    k21 = geaendert(basis, *KORREKTUR_21)
    pruef(k21 == [], f"01_vorbereiten.py, 02_auswerten.py, potsdam.yaml, QUELLEN.md gleich {basis} (Korrektur 21)"
          + ("" if k21 == [] else f": {'git scheiterte' if k21 is None else ', '.join(k21)}"))

    # 7. Commits von B1 selbst, auf jedem Zweig, der sie enthält
    von, bis = B1_BEREICH
    if all(git("rev-parse", "--verify", "-q", f"{ref}^{{commit}}").returncode == 0 for ref in B1_BEREICH):
        enthalten = git("merge-base", "--is-ancestor", bis, "HEAD").returncode == 0
        b1 = geaendert(f"{von}...{bis}", "daten/jahre", *KORREKTUR_21)
        pruef(b1 == [], f"Commits {von}...{bis}: kein daten/jahre/, keine Datei aus Korrektur 21"
              + ("" if b1 == [] else f" ({'git scheiterte' if b1 is None else ', '.join(b1[:5])})")
              + ("" if enthalten else f"; Hinweis: {bis} ist nicht in HEAD enthalten"))
    else:
        print(f"  Hinweis  Zweige {von}/{bis} fehlen, Prüfung 7 entfällt")
    print(f"\n{fehler} Abweichungen")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
