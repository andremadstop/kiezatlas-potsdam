"""Kiezatlas-Maschine in ein Stadt-Repository holen und prüfen.

Die Maschine ist der ortsunabhängige Teil des Kiezatlas (Laufzeit-Module, Seitenrahmen, Seitengenerator). Sie liegt
in einem eigenen Repository; jede Stadt (Kraków, Potsdam …) enthält eine Kopie zu einem festen Commit, damit ihr
Repository und ihr Archiv für sich allein vollständig sind. Welche Dateien zur Maschine gehören, steht in
MASCHINE.txt im Maschinen-Repository. Welcher Stand in einer Stadt liegt, steht dort in MASCHINE.lock (Commit und
SHA256 je Datei).

Regel: Dateien der Maschine werden in der Stadt nicht von Hand geändert. Änderungen entstehen im
Maschinen-Repository und kommen über `holen` in die Städte.

Aufruf (nur Python-Standardbibliothek und git, kein Netz):
  python3 -I skripte/maschine.py holen --commit <rev> [--von <pfad>]
      Dateien aus MASCHINE.txt im Maschinen-Repository (Pfad --von, sonst $KIEZ_MASCHINE, sonst ../kiezatlas) zum
      Commit <rev> in dieses Repository schreiben und MASCHINE.lock neu schreiben. Die Arbeitskopie der Maschine wird
      nicht gelesen, nur der Commit.
  python3 -I skripte/maschine.py pruefen
      Jede Datei aus MASCHINE.lock mit ihrer Prüfsumme vergleichen. Rückgabe 1, wenn eine fehlt oder abweicht.
  python3 -I skripte/maschine.py liste
      Im Maschinen-Repository selbst: prüfen, dass jede Datei aus MASCHINE.txt existiert und eingecheckt ist.
Rückgabe 0 = gut, 1 = Abweichung, 2 = falscher Aufruf oder Maschine nicht lesbar.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
LISTE = "MASCHINE.txt"
SPERRE = WURZEL / "MASCHINE.lock"
KOPF = "# Kiezatlas-Maschine: Kopie zu festem Commit. Nicht von Hand ändern; neu holen mit skripte/maschine.py holen."


def sha256(daten: bytes) -> str:
    return hashlib.sha256(daten).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def dateien_aus(text: str) -> list[str]:
    out = []
    for z in text.splitlines():
        z = z.strip()
        if not z or z.startswith("#"):
            continue
        if z.startswith("/") or ".." in Path(z).parts:
            raise ValueError(f"unzulässiger Pfad in {LISTE}: {z}")
        out.append(z)
    if len(set(out)) != len(out):
        raise ValueError(f"doppelte Einträge in {LISTE}")
    return out


def holen(von: Path, rev: str) -> int:
    try:
        commit = git(von, "rev-parse", "--verify", rev + "^{commit}").decode().strip()
        liste = dateien_aus(git(von, "show", f"{commit}:{LISTE}").decode("utf-8"))
    except (OSError, subprocess.CalledProcessError, ValueError) as e:
        print(f"Maschine unter {von} nicht lesbar: {e}", file=sys.stderr)
        return 2
    alt = set(gesperrt().keys()) if SPERRE.exists() else set()
    zeilen = [KOPF, f"commit: {commit}"]
    for pfad in liste:
        daten = git(von, "show", f"{commit}:{pfad}")
        ziel = WURZEL / pfad
        ziel.parent.mkdir(parents=True, exist_ok=True)
        if not ziel.exists() or ziel.read_bytes() != daten:
            ziel.write_bytes(daten)
            print(f"  geschrieben  {pfad}")
        zeilen.append(f"{sha256(daten)}  {pfad}")
    weg = sorted(alt - set(liste))
    for pfad in weg:
        print(f"  nicht mehr Teil der Maschine (bleibt liegen, bitte prüfen): {pfad}")
    SPERRE.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    print(f"Maschine {commit[:12]} geholt: {len(liste)} Dateien, MASCHINE.lock geschrieben")
    return 0


def gesperrt() -> dict[str, str]:
    out = {}
    for z in SPERRE.read_text(encoding="utf-8").splitlines():
        if not z or z.startswith("#") or z.startswith("commit:"):
            continue
        summe, pfad = z.split("  ", 1)
        out[pfad] = summe
    return out


def pruefen() -> int:
    if not SPERRE.exists():
        print("MASCHINE.lock fehlt", file=sys.stderr)
        return 2
    commit = next((z.split(":", 1)[1].strip() for z in SPERRE.read_text(encoding="utf-8").splitlines()
                   if z.startswith("commit:")), "?")
    befunde = 0
    eintraege = gesperrt()
    for pfad, summe in eintraege.items():
        p = WURZEL / pfad
        if not p.is_file():
            print(f"  FEHLT     {pfad}")
            befunde += 1
        elif sha256(p.read_bytes()) != summe:
            print(f"  GEÄNDERT  {pfad} (Maschinendatei in der Stadt geändert; Änderung gehört ins Maschinen-Repository)")
            befunde += 1
    print(f"Maschine {commit[:12]}: {len(eintraege)} Dateien, {befunde} Abweichungen")
    return 1 if befunde else 0


def liste() -> int:
    try:
        eintraege = dateien_aus((WURZEL / LISTE).read_text(encoding="utf-8"))
        verfolgt = set(git(WURZEL, "ls-files").decode("utf-8").splitlines())
    except (OSError, subprocess.CalledProcessError, ValueError) as e:
        print(f"{LISTE} nicht lesbar: {e}", file=sys.stderr)
        return 2
    befunde = [p for p in eintraege if not (WURZEL / p).is_file() or p not in verfolgt]
    for p in befunde:
        print(f"  fehlt oder nicht eingecheckt: {p}")
    print(f"{LISTE}: {len(eintraege)} Dateien, {len(befunde)} Befunde")
    return 1 if befunde else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = ap.add_subparsers(dest="befehl", required=True)
    h = sub.add_parser("holen")
    h.add_argument("--commit", required=True)
    h.add_argument("--von", default=os.environ.get("KIEZ_MASCHINE", str(WURZEL.parent / "kiezatlas")))
    sub.add_parser("pruefen")
    sub.add_parser("liste")
    a = ap.parse_args()
    if a.befehl == "holen":
        return holen(Path(a.von).resolve(), a.commit)
    if a.befehl == "pruefen":
        return pruefen()
    return liste()


if __name__ == "__main__":
    sys.exit(main())
