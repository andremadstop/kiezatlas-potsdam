"""Bereitet die lokal vorliegenden Rohdaten als CSV für die Geodaten-Import-Pipeline auf.

Kein Netzabruf: Die Stadtteile stammen aus einem Handdownload vom Open-Data-Portal Potsdam
(automatischer Abruf dort bis zur Antwort der Stadt nicht erlaubt, robots.txt sperrt /api/),
der Zensus aus den einmal geladenen Destatis-Dateien (Crawl-delay 30 eingehalten).

Ausgang: vorbereitet/stadtteile.csv  (nr; name; wkt in EPSG:4326)
         vorbereitet/zensus_potsdam.csv (gitter_id; x; y in EPSG:3035; Zählwerte je Thema)
Nur Zellen im Rechteck um Potsdam (plus 100 m); welche Zelle zu welchem Stadtteil gehört,
rechnet PostGIS in der Auswertung.

Aufruf: ../kiezatlas-potsdam-west/.venv/bin/python -I skripte/01_vorbereiten.py
"""
from __future__ import annotations

import csv
import io
import json
import subprocess  # nosec B404
import sys
import zipfile
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import MultiPolygon, shape
import warnings

from shapely.ops import transform, unary_union

warnings.filterwarnings("ignore", category=DeprecationWarning)

WURZEL = Path(__file__).resolve().parent.parent
ROH = WURZEL / "rohdaten"
AUS = WURZEL / "vorbereitet"
nach_3035 = Transformer.from_crs(4326, 3035, always_xy=True).transform

# Thema: (Datei, Muster im CSV-Namen, Kodierung, Quellspalte -> Zielspalte)
ZENSUS = {
    "bev": ("Zensus2022_Bevoelkerungszahl.zip", "100m-Gitter", "utf-8", {"Einwohner": "ew"}),
    "alter": ("Alter_in_5_Altersklassen.zip", "100m-Gitter", "utf-8",
              {"Insgesamt_Bevoelkerung": "a_ges", "Unter18": "a_u18", "a18bis29": "a_18_29",
               "a30bis49": "a_30_49", "a50bis64": "a_50_64", "a65undaelter": "a_65p"}),
    "dalter": ("Durchschnittsalter_in_Gitterzellen.zip", "100m-Gitter", "utf-8",
               {"Durchschnittsalter": "d_alter"}),
    "heiz": ("Zensus2022_Heizungsart.zip", "100m-Gitter", "cp1252",
             {"Insgesamt_Heizungsart": "h_ges", "Fernheizung": "h_fern", "Etagenheizung": "h_etage",
              "Blockheizung": "h_block", "Zentralheizung": "h_zentral",
              "Einzel_Mehrraumoefen": "h_oefen", "keine_Heizung": "h_keine"}),
    "energie": ("Zensus2022_Energietraeger.zip", "100m-Gitter", "cp1252",
                {"Insgesamt_Energietraeger": "e_ges", "Gas": "e_gas", "Heizoel": "e_oel",
                 "Holz_Holzpellets": "e_holz", "Biomasse_Biogas": "e_bio",
                 "Solar_Geothermie_Waermepumpen": "e_wp", "Strom": "e_strom", "Kohle": "e_kohle",
                 "Fernwaerme": "e_fern", "kein_Energietraeger": "e_kein"}),
    "baujahr": ("Wohnungen_mod_MZ_Baujahresklassen_in_Gitterzellen.zip",
                "Mikrozensusbaujahresklassen_100m", "utf-8",
                {"Insgesamt_Wohnungen": "w_ges", "vor_1919": "w_v1919", "a1919_bis_1948": "w_1919_48",
                 "a1949_bis_1978": "w_1949_78", "a1979_bis_1990": "w_1979_90",
                 "a1991_bis_2000": "w_1991_00", "a2001_bis_2013": "w_2001_13",
                 "a2014_bis_2019": "w_2014_19", "a2020_und_spaeter": "w_2020p"}),
}
GEHEIM = {"–", "-", "—"}


def zellmitte(gitter_id: str) -> tuple[float, float]:
    """CRS3035RES100mN2689100E4337000: linke untere Ecke in EPSG:3035, Mitte = +50 m."""
    n = gitter_id.index("N")
    e = gitter_id.index("E", n)
    return float(gitter_id[e + 1:]) + 50, float(gitter_id[n + 1:e]) + 50


def wert(roh: str, spalte: str) -> str:
    """Zählwerte: geheim gehalten (–) zählt als 0, wie bei Summen über Gitterzellen üblich.
    Durchschnittsalter: geheim heißt unbekannt (leer), nicht 0."""
    s = roh.strip()
    if s in GEHEIM or s == "":
        return "" if spalte == "d_alter" else "0"
    return s.replace(",", ".")


def main() -> None:
    AUS.mkdir(exist_ok=True)
    d = json.loads((ROH / "stadtteile.geojson").read_text(encoding="utf-8"))
    with (AUS / "stadtteile.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["nr", "name", "wkt"])
        for ft in sorted(d["features"], key=lambda ft: ft["properties"]["st"]):
            g = shape(ft["geometry"])
            g = g if isinstance(g, MultiPolygon) else MultiPolygon([g])
            w.writerow([ft["properties"]["st"], ft["properties"]["stadtteil"], g.wkt])
    stadt = transform(nach_3035, unary_union([shape(ft["geometry"]) for ft in d["features"]]))
    minx, miny, maxx, maxy = stadt.bounds
    print(f"Stadtteile: {len(d['features'])}", file=sys.stderr)

    zellen: dict[str, dict] = {}
    for thema, (datei, muster, kod, spalten) in ZENSUS.items():
        archiv = ROH / "zensus" / datei
        if zipfile.is_zipfile(archiv):
            z = zipfile.ZipFile(archiv)
            name = next(n for n in z.namelist() if muster in n and n.endswith(".csv"))
            roh = z.open(name)
        else:  # Destatis liefert manche Dateien als 7z mit .zip-Endung
            roh = subprocess.Popen(["7z", "e", "-so", str(archiv), f"*{muster}*.csv"],  # noqa: S603,S607
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
        leser = csv.reader(io.TextIOWrapper(roh, encoding=kod), delimiter=";")
        kopf = next(leser)
        assert kopf[0].upper().startswith("GITTER_ID_100M"), (datei, kopf[0])
        idx = {k: kopf.index(k) for k in spalten}
        n = 0
        for zeile in leser:
            x, y = zellmitte(zeile[0])  # nicht jede Datei hat Spalten für den Mittelpunkt
            if not (minx - 100 <= x <= maxx + 100 and miny - 100 <= y <= maxy + 100):
                continue
            c = zellen.setdefault(zeile[0], {"gitter_id": zeile[0], "x": f"{x:.0f}", "y": f"{y:.0f}"})
            for alt, neu in spalten.items():
                c[neu] = wert(zeile[idx[alt]], neu)
            n += 1
        print(f"Zensus {thema}: {n} Zellen im Rechteck", file=sys.stderr)

    felder = ["gitter_id", "x", "y"] + [neu for _, _, _, sp in ZENSUS.values() for neu in sp.values()]
    with (AUS / "zensus_potsdam.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=felder, delimiter=";", restval="0")
        w.writeheader()
        for gid in sorted(zellen):
            c = zellen[gid]
            c.setdefault("d_alter", "")
            w.writerow(c)
    print(f"Zellen gesamt: {len(zellen)}", file=sys.stderr)


if __name__ == "__main__":
    main()
