"""Schreibt die Grenzen der 19 Potsdamer Planungsräume als daten/planungsraeume.js (KIEZ_PLANUNGSRAEUME).

Integration I1 (05.11.2026): Die Versorgungsdatei daten/planer.js rechnet seit dem A6-Nachlauf auf
Planungsräumen; die Planer-Karte braucht deren Grenzen, damit die Tabelle einer Fläche zugeordnet werden
kann. Kein Netzabruf, keine Datenbank. Eingang ist der Handdownload H1 vom Open-Data-Portal der
Landeshauptstadt (robots.txt des Portals sperrt automatische Abrufe), abgelegt unter
$KIEZ_DATEN/eingang/planungsraume-in-potsdam.geojson, Lizenz laut eingang/HERKUNFT.md dl-de/by-2-0.

Bearbeitung: Grenzen vereinfacht (Douglas-Peucker, Toleranz 3 m, je gemeinsamer Grenzlinie einmal, damit
Nachbarräume lückenlos aneinanderstoßen), Koordinaten auf 5 Nachkommastellen gerundet (rund 1 m), Eigenschaften
auf nr, name und flaeche_km2 (amtliche Fläche laut Datensatz) beschränkt. Darum trägt der Vermerk „Daten verändert“.
Grund für die Vereinfachung: Die Datei lädt mit der Planer-Seite, deren Startgewicht höchstens 300 KB gz JS sein darf.
Die Schlüssel nr müssen genau die Schlüssel von daten/planer.js sein (Abbruch sonst).

Aufruf:  python3 -I skripte/17_planungsraeume_js.py [--pruefen]
         --pruefen schreibt nichts und meldet, ob daten/planungsraeume.js aktuell ist (Rückgabe 0/1).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
DATEI = "planungsraume-in-potsdam.geojson"
ZIEL = WURZEL / "daten" / "planungsraeume.js"
STELLEN = 5
TOLERANZ_M = 3.0
M_JE_GRAD = (68_000.0, 111_300.0)   # Näherung bei 52,4° N, nur für die Toleranz der Vereinfachung
STAND = "2025-12-31"   # Datenstand laut Portal (geändert 18.05.2026), siehe eingang/HERKUNFT.md
# STAND gehört zu genau diesem Handdownload. Ein neuer Download bricht ab, bis STAND und Hash von Hand nachgezogen sind.
QUELLE_SHA256 = "53ab7e66493ba81d6ba7123f1a15585c1370c66305e9b9fa37ad244fe19d3d74"
DLDE = "https://www.govdata.de/dl-de/by-2-0"
VERMERK = ("Planungsräume: Landeshauptstadt Potsdam, Open-Data-Portal, Stand 31.12.2025, dl-de/by-2-0 ("
           + DLDE + "), Daten verändert (Grenzen vereinfacht, Koordinaten gerundet, Felder ausgewählt)")


def schluessel(p: list) -> tuple:
    return (round(float(p[0]), 7), round(float(p[1]), 7))


def dp(pts: list) -> list:
    """Douglas-Peucker mit festen Endpunkten, Abstand in Metern (Näherung)."""
    if len(pts) < 3:
        return pts
    (ax, ay), (bx, by) = [(x * M_JE_GRAD[0], y * M_JE_GRAD[1]) for x, y in (pts[0], pts[-1])]
    dx, dy = bx - ax, by - ay
    laenge = (dx * dx + dy * dy) ** 0.5
    best, bi = -1.0, 0
    for i in range(1, len(pts) - 1):
        px, py = pts[i][0] * M_JE_GRAD[0], pts[i][1] * M_JE_GRAD[1]
        d = abs(dy * (px - ax) - dx * (py - ay)) / laenge if laenge else ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
        if d > best:
            best, bi = d, i
    if best <= TOLERANZ_M:
        return [pts[0], pts[-1]]
    return dp(pts[:bi + 1])[:-1] + dp(pts[bi:])


def vereinfachen(ringe: list) -> list:
    """Vereinfacht jede Grenzlinie einmal: Knoten sind Punkte, an denen die Menge der angrenzenden Räume wechselt.
    Eine Linie zwischen zwei Knoten wird in beiden Nachbarräumen gleich (ggf. umgekehrt) vereinfacht."""
    wer: dict = {}
    for i, r in enumerate(ringe):
        for p in r:
            wer.setdefault(p, set()).add(i)
    fertig: dict = {}
    aus = []
    for r in ringe:
        n = len(r)
        knoten = [j for j in range(n) if wer[r[j]] != wer[r[j - 1]] or wer[r[j]] != wer[r[(j + 1) % n]] or len(wer[r[j]]) > 2]
        if len(knoten) < 2:
            knoten = sorted(set(knoten) | {0, n // 3, 2 * n // 3})
        neu: list = []
        for a, b in zip(knoten, knoten[1:] + [knoten[0] + n]):
            kette = tuple(r[j % n] for j in range(a, b + 1))
            if kette in fertig:
                s = fertig[kette]
            elif kette[::-1] in fertig:
                s = fertig[kette[::-1]][::-1]
            else:
                s = fertig[kette] = dp(list(kette))
            neu += s[:-1]
        punkte = []
        for x, y in neu + [neu[0]]:
            p = [round(x, STELLEN), round(y, STELLEN)]
            if not punkte or punkte[-1] != p:
                punkte.append(p)
        if len(punkte) < 4:
            raise SystemExit("Ring mit weniger als 4 Punkten nach dem Vereinfachen")
        aus.append(punkte)
    return aus


def planer_schluessel() -> dict:
    t = (WURZEL / "daten" / "planer.js").read_text(encoding="utf-8")
    m = re.match(r"\s*window\.KIEZ_PLANER\s*=\s*(.*?);?\s*$", t, re.S)
    if not m:
        raise SystemExit("daten/planer.js nicht lesbar")
    P = json.loads(m.group(1))
    if P.get("raumebene") != "planungsraum":
        raise SystemExit(f"daten/planer.js rechnet auf {P.get('raumebene')}, nicht auf Planungsräumen")
    return {k: v["name"] for k, v in P["raeume"].items()}


def bauen() -> str:
    daten = Path(os.environ.get("KIEZ_DATEN") or WURZEL.parent / "kiezatlas-daten")
    roh = (daten / "eingang" / DATEI).read_bytes()
    if hashlib.sha256(roh).hexdigest() != QUELLE_SHA256:
        raise SystemExit(f"{DATEI} ist ein anderer Stand als {STAND}: "
                         "STAND und QUELLE_SHA256 nach eingang/HERKUNFT.md nachziehen")
    q = json.loads(roh)
    crs = str(((q.get("crs") or {}).get("properties") or {}).get("name") or "")
    if crs and not re.search(r"CRS84|EPSG:+4326\b", crs):
        raise SystemExit(f"Bezugssystem {crs}: erwartet EPSG:4326 (Umprojektion wie 03_planungsraeume.py hier nicht eingebaut)")
    feats, ringe = [], []
    for f in q["features"]:
        g = f["geometry"]
        if g.get("type") != "Polygon" or len(g["coordinates"]) != 1:
            raise SystemExit("erwartet je Planungsraum ein Polygon ohne Loch (Vereinfachung rechnet nur damit)")
        r = [schluessel(p) for p in g["coordinates"][0]]
        if not all(12.5 < x < 13.5 and 52.2 < y < 52.6 for x, y in r):
            raise SystemExit("Koordinaten außerhalb von Potsdam in Grad: Bezugssystem prüfen")
        ringe.append(r[:-1] if r[0] == r[-1] else r)
    for f, ring in zip(q["features"], vereinfachen(ringe)):
        p = f["properties"]
        if not {"pr", "bez", "shape_area"} <= p.keys():
            raise SystemExit(f"Felder pr, bez, shape_area erwartet, vorhanden: {sorted(p)} "
                             "(Feldnamen wie bei 03_planungsraeume.py prüfen)")
        nr, name = str(p["pr"]).strip(), str(p["bez"]).strip()
        if not re.fullmatch(r"[1-6]0[1-9]", nr):
            raise SystemExit(f"unerwartete Planungsraum-Nummer {nr!r}")
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                      "properties": {"nr": nr, "name": name,
                                     "flaeche_km2": round(float(p["shape_area"]) / 1e6, 2)}})
    feats.sort(key=lambda f: f["properties"]["nr"])
    nrn = [f["properties"]["nr"] for f in feats]
    if len(set(nrn)) != len(nrn):
        raise SystemExit("doppelte Planungsraum-Nummern")
    soll = planer_schluessel()
    ist = {f["properties"]["nr"]: f["properties"]["name"] for f in feats}
    if ist != soll:
        raise SystemExit(f"Planungsräume passen nicht zu daten/planer.js: {sorted(set(ist.items()) ^ set(soll.items()))}")
    fc = {"type": "FeatureCollection", "stand": STAND, "lizenz": "dl-de/by-2-0", "vermerk": VERMERK,
          "quelle_sha256": hashlib.sha256(roh).hexdigest(), "features": feats}
    return "window.KIEZ_PLANUNGSRAEUME=" + json.dumps(fc, ensure_ascii=False, separators=(",", ":")) + ";\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pruefen", action="store_true")
    a = ap.parse_args()
    neu = bauen()
    if a.pruefen:
        alt = ZIEL.read_text(encoding="utf-8") if ZIEL.exists() else ""
        print("aktuell" if alt == neu else "veraltet: daten/planungsraeume.js neu schreiben")
        return 0 if alt == neu else 1
    ZIEL.write_text(neu, encoding="utf-8")
    print(f"{ZIEL.relative_to(WURZEL)}: {len(neu)} Bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
