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
import re
import sys
import warnings
from pathlib import Path

from pyproj import Transformer
from shapely import force_2d
from shapely.geometry import MultiPolygon, shape
from shapely.ops import transform

WURZEL = Path(__file__).resolve().parent.parent
warnings.filterwarnings("ignore", category=DeprecationWarning)   # shapely.ops.transform, wie 01_vorbereiten.py


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
    # Bezugssystem: GeoJSON ist EPSG:4326; manche Exporte tragen ein crs-Element (z. B. EPSG:25833)
    crs = str(((quelle.get("crs") or {}).get("properties") or {}).get("name") or "")
    epsg = re.search(r"EPSG:+(\d+)", crs)
    nach_4326 = None
    if epsg and epsg.group(1) not in ("4326", "4258", "CRS84"):
        nach_4326 = Transformer.from_crs(int(epsg.group(1)), 4326, always_xy=True).transform
    n = 0
    with aus.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["nr", "name", "wkt"])
        for i, feat in enumerate(quelle["features"]):
            p = feat.get("properties") or {}
            nr = str(p.get(a.nr_feld) or "").strip()
            if not nr or len(nr) > 10:
                raise SystemExit(f"Objekt {i}: Feld {a.nr_feld} fehlt oder ist länger als 10 Zeichen ({nr!r})")
            if not feat.get("geometry"):
                raise SystemExit(f"Objekt {i} ({nr}): ohne Geometrie")
            g = force_2d(shape(feat["geometry"]))
            if nach_4326:
                g = transform(nach_4326, g)
            if g.geom_type == "Polygon":
                g = MultiPolygon([g])
            if g.geom_type != "MultiPolygon":
                raise SystemExit(f"Objekt {i} ({nr}): {g.geom_type} statt Fläche")
            x0, y0, x1, y1 = g.bounds
            if not (12.5 < x0 and x1 < 13.5 and 52.2 < y0 and y1 < 52.7):
                raise SystemExit(f"Objekt {i} ({nr}): liegt nicht bei Potsdam (Bezugssystem prüfen): {g.bounds}")
            w.writerow([nr, str(p.get(a.name_feld) or "").strip(), g.wkt])
            n += 1
    print(f"{n} Planungsräume -> {aus}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
