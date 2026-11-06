"""Gegenprobe des eigenen PBF-Lesers (skripte/osm_pbf.py) gegen den OSM-Treiber von GDAL.

Braucht eine Python-Umgebung mit pyogrio und shapely (GDAL mit OSM-Treiber), zum Beispiel die venv von
prettymaps-potsdam. Vergleicht für jede Linie und jeden Punkt, die GDAL liefert, die Koordinaten mit dem
eigenen Leser (gleiche Knotenzahl, größte Abweichung in Grad). Kein Netz.

Aufruf (05.11.2026, Ergebnis in belege/A3_pbf_leser_gegenprobe.txt):
    OSM_USE_CUSTOM_INDEXING=NO ~/localWorkspace/prettymaps-potsdam/.venv/bin/python -I \
        pruefen/a3_gegenprobe_gdal.py ~/localWorkspace/prettymaps-potsdam/.venv/lib/python3.13/site-packages/pyogrio/tests/fixtures/sample.osm.pbf
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pyogrio
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skripte"))
import osm_pbf


def main() -> int:
    pfad = sys.argv[1]
    e = osm_pbf.lies(pfad, rechteck=None, knoten_wahl=lambda t: True, weg_wahl=lambda t: True,
                     relation_wahl=lambda t: True)
    print(f"Datei {Path(pfad).name}: Programm {e.kopf.programm!r}, Pflicht {e.kopf.pflicht}, "
          f"optional {e.kopf.optional}")
    print(f"eigener Leser: {e.knoten_gesamt} Knoten, {e.wege_gesamt} Wege, {e.relationen_gesamt} Relationen, "
          f"{len(e.getaggte_knoten)} getaggte Knoten")
    punkte = {i: (lo, la) for i, lo, la, _t in e.getaggte_knoten}
    wege = {w: r for w, _t, r in e.wege}
    fehler = 0
    for schicht in ("points", "lines"):
        meta, _idx, geoms, felder = pyogrio.raw.read(pfad, layer=schicht)
        oid = felder[meta["fields"].tolist().index("osm_id")]
        n, max_d = 0, 0.0
        for i, g in enumerate(shapely.from_wkb(geoms)):
            c = shapely.get_coordinates(g)
            if schicht == "points":
                lo, la = punkte[int(oid[i])]
                d = max(abs(lo - c[0, 0]), abs(la - c[0, 1]))
            else:
                refs = wege[int(oid[i])]
                lon, lat, ok = e.koordinaten(refs)
                if len(c) != len(refs) or not ok.all():
                    fehler += 1
                    continue
                d = float(max(np.abs(c[:, 0] - lon).max(), np.abs(c[:, 1] - lat).max()))
            max_d = max(max_d, d)
            n += 1
        print(f"GDAL-Schicht {schicht}: {n} Objekte verglichen, größte Abweichung {max_d:.2e} Grad")
    print(f"Abweichende Knotenzahl oder fehlende Knoten: {fehler}")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
