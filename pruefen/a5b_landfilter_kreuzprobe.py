"""A5b, Landesfilter E7: Wie gut ordnet „Land der nächsten VBB-Haltestelle“ einen Ort Berlin oder Brandenburg zu?

Kreuzprobe ohne Datenbank: Für jeden Haltepunkt im Rechteck um Potsdam (lon 12,85 bis 13,25, lat 52,30 bis 52,53)
wird das Land des nächsten Haltepunkts einer anderen Station bestimmt (die eigene Station bleibt außen vor) und mit
dem eigenen Kreisschlüssel im DHID verglichen. Fehler gibt es nur dort, wo zwei Stationen beiderseits der Grenze
näher beieinander liegen als an Stationen des eigenen Landes.

Aufruf (offline):
    uv run -q --offline --no-project --with numpy --with scipy \
        python -I pruefen/a5b_landfilter_kreuzprobe.py [GTFS.zip]
Ohne Argument: neuester $KIEZ_DATEN/vbb_gtfs/<stand>/GTFS.zip. Ausgang 0 = Fehlerquote unter 2 %.
"""
from __future__ import annotations

import importlib
import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "skripte"))
fw = importlib.import_module("14b_fussweg")

RECHTECK = (12.85, 52.30, 13.25, 52.53)
GRENZE_FEHLERQUOTE = 0.02


def station_je_halt(pfad: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Wie fw.halte_land, dazu die Station (die ersten drei DHID-Teile) je Haltepunkt."""
    import csv
    import io
    import zipfile
    xy, land, station = [], [], []
    k = math.cos(math.radians(52.4))
    with zipfile.ZipFile(pfad) as z, z.open("stops.txt") as f:
        for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", newline="")):
            teile = (row.get("stop_id") or "").split(":")
            if len(teile) < 3 or teile[0] != "de" or (row.get("location_type") or "0") != "0":
                continue
            if teile[1][:2] not in (fw.LAND_BERLIN, fw.LAND_BRANDENBURG):
                continue
            try:
                lon, lat = float(row["stop_lon"]), float(row["stop_lat"])
            except (KeyError, TypeError, ValueError):
                continue
            xy.append((lon * 111320 * k, lat * 110574))     # genähert in Metern, reicht für Nachbarschaft
            land.append(teile[1][:2])
            station.append(":".join(teile[:3]))
    return np.array(xy), np.array(land), np.array(station)


def main() -> int:
    pfad = Path(sys.argv[1]) if len(sys.argv) > 1 else fw.gtfs_pfad()
    if pfad is None:
        print("VBB-GTFS fehlt", file=sys.stderr)
        return 2
    xy, land, station = station_je_halt(pfad)
    k = math.cos(math.radians(52.4))
    x0, y0, x1, y1 = (RECHTECK[0] * 111320 * k, RECHTECK[1] * 110574, RECHTECK[2] * 111320 * k,
                      RECHTECK[3] * 110574)
    im = np.flatnonzero((xy[:, 0] > x0) & (xy[:, 0] < x1) & (xy[:, 1] > y0) & (xy[:, 1] < y1))
    baum = cKDTree(xy)
    _, nb = baum.query(xy[im], k=40)
    geschaetzt = []
    for r, j in enumerate(im):
        andere = [c for c in nb[r] if station[c] != station[j]]
        geschaetzt.append(land[andere[0]] if andere else land[j])
    geschaetzt = np.array(geschaetzt)
    eigen = land[im]
    falsch = int((geschaetzt != eigen).sum())
    # Wie nah liegen die Fehltreffer am anderen Land? Abstand zum nächsten Haltepunkt des anderen Landes
    fremd = {lnd: cKDTree(xy[land != lnd]) for lnd in (fw.LAND_BERLIN, fw.LAND_BRANDENBURG)}
    abstand = sorted(float(fremd[land[j]].query(xy[j])[0]) for j in im[geschaetzt != eigen])
    quote = falsch / max(len(im), 1)
    print(f"GTFS: {pfad}")
    print(f"Haltepunkte im Rechteck: {len(im)} (Berlin {int((eigen == fw.LAND_BERLIN).sum())}, "
          f"Brandenburg {int((eigen == fw.LAND_BRANDENBURG).sum())})")
    print(f"falsch zugeordnet: {falsch} ({100 * quote:.1f} %): Berlin als Brandenburg "
          f"{int(((eigen == fw.LAND_BERLIN) & (geschaetzt == fw.LAND_BRANDENBURG)).sum())}, Brandenburg als Berlin "
          f"{int(((eigen == fw.LAND_BRANDENBURG) & (geschaetzt == fw.LAND_BERLIN)).sum())}")
    if abstand:
        print(f"Fehltreffer: Abstand zum nächsten Haltepunkt des anderen Landes {abstand[0]:.0f} bis "
              f"{abstand[-1]:.0f} m (Median {float(np.median(abstand)):.0f} m)")
    return 0 if quote < GRENZE_FEHLERQUOTE else 1


if __name__ == "__main__":
    sys.exit(main())
