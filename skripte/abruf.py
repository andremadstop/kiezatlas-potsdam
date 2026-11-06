"""Einzelabruf einer Datei mit Mindestabstand je Rechner und Abrufprotokoll.

Jede Anfrage zählt als Abruf, auch robots.txt, HEAD oder eine Weiterleitung. Das Werkzeug liest
deshalb vor jeder Anfrage das gemeinsame Protokoll $KIEZ_DATEN/abrufprotokoll.tsv, wartet, bis
der Abstand zur letzten Anfrage an denselben Rechner erreicht ist, und trägt die neue Anfrage ein
(Zeit UTC, Rechner, URL, Status, Bytes, SHA256, Ziel). Weiterleitungen werden nicht verfolgt,
außer mit --gleicher-rechner auf denselben Rechner (dann mit erneutem Abstand).

Aufruf (Python aus der Projektumgebung, ohne Fremdpakete):
    python -I skripte/abruf.py --abstand 30 URL ZIELDATEI [--max-mb 100] [--gleicher-rechner]
Rückgabe: 0 gespeichert, 3 Weiterleitung nicht verfolgt, 4 HTTP- oder Netzfehler, 5 zu groß.
Gleichzeitige Aufrufe warten aufeinander (Sperre auf abrufprotokoll.lock), damit der Abstand auch
bei langen Downloads hält; jeder Versuch steht im Protokoll, auch ein abgebrochener.

Verbotene Rechner (Abrufregeln des Ausbaus, siehe QUELLEN.md) lehnt das Werkzeug ab.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

KENNUNG = "kiezatlas-potsdam (+https://github.com/andremadstop/kiezatlas-potsdam)"
VERBOTEN = ("opendata.potsdam.de", "overpass-api.de", "query.wikidata.org", "www.wikidata.org",
            "taginfo", "nominatim", "download.geofabrik.de", "download.bbbike.org",
            "api.github.com", "raw.githubusercontent.com")


def daten_ordner() -> Path:
    return Path(os.environ.get("KIEZ_DATEN") or Path(__file__).resolve().parents[2] / "kiezatlas-daten")


class OhneWeiterleitung(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):  # noqa: D102
        return None


def letzte_anfrage(protokoll: Path, rechner: str) -> float | None:
    if not protokoll.exists():
        return None
    zuletzt = None
    for zeile in protokoll.read_text(encoding="utf-8").splitlines()[1:]:
        teile = zeile.split("\t")
        if len(teile) > 1 and teile[1] == rechner:
            zuletzt = datetime.fromisoformat(teile[0]).timestamp()
    return zuletzt


def eintragen(protokoll: Path, zeit: datetime, rechner: str, url: str, status, n: int, sha: str,
              ziel: str) -> None:
    neu = not protokoll.exists()
    with protokoll.open("a", encoding="utf-8") as f:
        if neu:
            f.write("zeit_utc\trechner\turl\tstatus\tbytes\tsha256\tziel\n")
        f.write(f"{zeit.isoformat(timespec='seconds')}\t{rechner}\t{url}\t{status}\t{n}\t{sha}\t{ziel}\n")


def holen(url: str, ziel: Path, abstand: float, max_mb: float, protokoll: Path) -> tuple[int, str | None]:
    rechner = urlsplit(url).hostname or ""
    if urlsplit(url).scheme != "https":
        raise SystemExit(f"nur https: {url}")
    if any(v in rechner for v in VERBOTEN):
        raise SystemExit(f"Rechner {rechner} ist für automatische Abrufe gesperrt")
    zuletzt = letzte_anfrage(protokoll, rechner)
    if zuletzt is not None:
        warten = zuletzt + abstand - time.time()
        if warten > 0:
            print(f"warte {warten:.0f} s (Abstand {abstand:g} s zu {rechner})", file=sys.stderr)
            time.sleep(warten)
    oeffner = urllib.request.build_opener(OhneWeiterleitung)
    anfrage = urllib.request.Request(url, headers={"User-Agent": KENNUNG})
    zeit = datetime.now(UTC)
    teil = ziel.with_name(ziel.name + ".teil")
    h, n = hashlib.sha256(), 0
    try:
        with oeffner.open(anfrage, timeout=120) as r:
            laenge = int(r.headers.get("Content-Length") or 0)
            if laenge > max_mb * 1024 * 1024:
                eintragen(protokoll, zeit, rechner, url, f"{r.status} zu groß ({laenge})", 0, "", "")
                return 5, None
            ziel.parent.mkdir(parents=True, exist_ok=True)
            with teil.open("wb") as f:
                while stueck := r.read(1 << 16):
                    n += len(stueck)
                    if n > max_mb * 1024 * 1024:
                        f.close()
                        teil.unlink()
                        eintragen(protokoll, zeit, rechner, url, f"{r.status} abgebrochen > {max_mb} MB", n, "", "")
                        return 5, None
                    h.update(stueck)
                    f.write(stueck)
            status = r.status
    except urllib.error.HTTPError as e:
        if teil.exists():
            teil.unlink()
        if 300 <= e.code < 400:
            ort = urljoin(url, e.headers.get("Location", ""))
            eintragen(protokoll, zeit, rechner, url, f"{e.code} -> {ort}", 0, "", "")
            return 3, ort
        eintragen(protokoll, zeit, rechner, url, e.code, 0, "", "")
        return 4, None
    except (OSError, KeyboardInterrupt) as e:  # URLError, Zeitüberschreitung, TLS, Abbruch: zählt als Abruf
        if teil.exists():
            teil.unlink()
        eintragen(protokoll, zeit, rechner, url, f"Fehler {type(e).__name__}", n, "", "")
        if isinstance(e, KeyboardInterrupt):
            raise
        print(f"Fehler: {e}", file=sys.stderr)
        return 4, None
    teil.replace(ziel)
    eintragen(protokoll, zeit, rechner, url, status, n, h.hexdigest(), str(ziel))
    print(f"{status} {n} Bytes sha256={h.hexdigest()} -> {ziel}")
    return 0, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url")
    ap.add_argument("ziel", type=Path)
    ap.add_argument("--abstand", type=float, required=True, help="Mindestabstand in s je Rechner")
    ap.add_argument("--max-mb", type=float, default=100)
    ap.add_argument("--gleicher-rechner", action="store_true",
                    help="Weiterleitung verfolgen, wenn sie auf denselben Rechner zeigt")
    a = ap.parse_args()
    protokoll = daten_ordner() / "abrufprotokoll.tsv"
    protokoll.parent.mkdir(parents=True, exist_ok=True)
    url = a.url
    with (protokoll.parent / "abrufprotokoll.lock").open("w") as sperre:
        fcntl.flock(sperre, fcntl.LOCK_EX)
        for _ in range(3):
            code, ort = holen(url, a.ziel, a.abstand, a.max_mb, protokoll)
            if code != 3:
                return code
            print(f"Weiterleitung auf {ort}", file=sys.stderr)
            if not (a.gleicher_rechner and urlsplit(ort).hostname == urlsplit(url).hostname):
                return 3
            url = ort
    return 3


if __name__ == "__main__":
    sys.exit(main())
