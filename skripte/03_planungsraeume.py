"""Bereitet den Handdownload der Potsdamer Planungsräume (H1) als CSV für die Pipeline auf.

Kein Netzabruf. Eingang: GeoJSON vom Open-Data-Portal (Handdownload durch Andre, robots.txt des
Portals sperrt automatische Abrufe), abgelegt unter $KIEZ_DATEN/eingang/. Die Feldnamen des
Datensatzes sind vor dem Eingang nicht bekannt, deshalb als Parameter.

Ausgang: vorbereitet/planungsraeume.csv (nr; name; wkt in EPSG:4326), geladen per
    skripte/lauf.sh --nur planungsraeume
Aufruf:
    ../kiezatlas-potsdam-west/.venv/bin/python -I skripte/03_planungsraeume.py \
        --datei planungsraume-in-potsdam.geojson --nr-feld <feld> --name-feld <feld>
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from shapely.geometry import MultiPolygon, shape

WURZEL = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--datei", required=True, help="Dateiname unter $KIEZ_DATEN/eingang/")
    ap.add_argument("--nr-feld", required=True)
    ap.add_argument("--name-feld", required=True)
    a = ap.parse_args()
    daten = Path(os.environ.get("KIEZ_DATEN") or WURZEL.parent / "kiezatlas-daten")
    quelle = json.loads((daten / "eingang" / a.datei).read_text(encoding="utf-8"))
    aus = WURZEL / "vorbereitet" / "planungsraeume.csv"
    aus.parent.mkdir(exist_ok=True)
    n = 0
    with aus.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["nr", "name", "wkt"])
        for feat in quelle["features"]:
            p = feat.get("properties") or {}
            g = shape(feat["geometry"])
            if g.geom_type == "Polygon":
                g = MultiPolygon([g])
            w.writerow([str(p[a.nr_feld]).strip(), str(p.get(a.name_feld) or "").strip(), g.wkt])
            n += 1
    print(f"{n} Planungsräume -> {aus}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
