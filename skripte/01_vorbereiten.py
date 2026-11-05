"""Bereitet die lokal vorliegenden Rohdaten als CSV für die Geodaten-Import-Pipeline auf.

Kein Netzabruf: Die Stadtteile stammen aus einem Handdownload vom Open-Data-Portal Potsdam
(automatischer Abruf dort bis zur Antwort der Stadt nicht erlaubt, robots.txt sperrt /api/),
der Zensus aus den einmal geladenen Destatis-Dateien (Crawl-delay 30 eingehalten).

Ausgang: vorbereitet/stadtteile.csv  (nr; name; wkt in EPSG:4326)
         vorbereitet/zensus_potsdam.csv (gitter_id; x; y in EPSG:3035; Zählwerte je Thema)
         vorbereitet/zensus_struktur.csv (Paket A1: Strukturmerkmale für public.zensus_struktur,
             gitter_id; x; y; Spalten = Zielspalten aus config/potsdam.yaml; geaendert)
Nur Zellen im Rechteck um Potsdam (plus 100 m); welche Zelle zu welchem Stadtteil gehört,
rechnet PostGIS in der Auswertung.

Strukturmerkmale (A1): Die Destatis-Zips liegen außerhalb des Repos unter $KIEZ_DATEN/zensus/2022/
(HERKUNFT.md dort). Zählwerte: „–“ heißt laut Datensatzbeschreibung „genau Null oder auf Null
geändert“ (Cell-Key-Methode) und wird 0; das Feld steht dann in geaendert (kommagetrennt). Fehlt
eine Zelle in einer Themen-Datei, gibt es dort keine Personen bzw. Haushalte (0, kein Eintrag in
geaendert). Mittelwerte (Miete, Leerstand, Wohnfläche): Zelle fehlt = leer (kein Wert, nie 0);
„–“ = 0 und in geaendert; Zeichen KLAMMERN („Aussagewert eingeschränkt“) steht als <feld>:unsicher
in geaendert. Feine Klassen gehen nie je Zelle in eine daten/-Datei (Bauplan A1, Geheimhaltung).

Aufruf: ../kiezatlas-potsdam-west/.venv/bin/python -I skripte/01_vorbereiten.py
"""
from __future__ import annotations

import csv
import io
import json
import os
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
KIEZ_DATEN = Path(os.environ.get("KIEZ_DATEN") or WURZEL.parent / "kiezatlas-daten")
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

# Paket A1: Strukturmerkmale je 100-m-Zelle (Zensus 2022, Stichtag 15.05.2022), Ziel public.zensus_struktur.
# Thema: (Datei unter $KIEZ_DATEN/zensus/2022/, Muster im CSV-Namen, Quellspalte -> Zielspalte)
STRUKTUR_ORDNER = "zensus/2022"
STRUKTUR = {
    "alter_infr": ("Alter_in_infrastrukturellen_Altersgruppen.zip", "_100m-Gitter",
                   {"Insgesamt_Bevoelkerung": "i_ges", "Unter3": "i_u3", "a3bis5": "i_3_5", "a6bis9": "i_6_9",
                    "a10bis15": "i_10_15", "a16bis18": "i_16_18", "a19bis24": "i_19_24",
                    "a25bis39": "i_25_39", "a40bis59": "i_40_59", "a60bis66": "i_60_66",
                    "a67bis74": "i_67_74", "a75undaelter": "i_75p"}),
    "hh_groesse": ("Zensus2022_Groesse_des_privaten_Haushalts_in_Gitterzellen.zip", "_100m-Gitter",
                   {"Insgesamt_Haushalte": "hh_ges", "1_Person": "hh_1", "2_Personen": "hh_2",
                    "3_Personen": "hh_3", "4_Personen": "hh_4", "5_Personen": "hh_5",
                    "6_Personen_und_mehr": "hh_6p"}),
    "hh_typ": ("Typ_des_privaten_Haushalts_Familien.zip", "_100m-Gitter",
               {"Insgesamt_Haushalte": "ht_ges", "EinpersHH_SingleHH": "ht_single",
                "Paare_ohneKind": "ht_paar_ohne", "Paare_mitKind": "ht_paar_mit",
                "Alleinerziehende": "ht_alleinerz", "MehrpersHHohneKernfam": "ht_mehrpers"}),
    "kernfamilie": ("Typ_der_Kernfamilie_nach_Kindern.zip", "_100m-Gitter",
                    {"Insgesamt_Familie": "kf_ges", "Ehep_ohneKind": "kf_ehe_ohne",
                     "Ehep_mind_1Kind_unter18": "kf_ehe_u18", "Ehep_Kinder_ab18": "kf_ehe_ab18",
                     "EingetrLP_ohneKind": "kf_lp_ohne", "EingetrLP_mind_1Kind_unter18": "kf_lp_u18",
                     "EingetrLP_Kinder_ab18": "kf_lp_ab18", "NichtehelLG_ohneKind": "kf_nel_ohne",
                     "NichtehelLG_mind_1Kind_unter18": "kf_nel_u18", "NichtehelLG_Kinder_ab18": "kf_nel_ab18",
                     "Vater_mind_1Kind_unter18": "kf_vater_u18", "Vater_Kinder_ab18": "kf_vater_ab18",
                     "Mutter_mind_1Kind_unter18": "kf_mutter_u18", "Mutter_Kinder_ab18": "kf_mutter_ab18"}),
    "senioren": ("Seniorenstatus_eines_privaten_Haushalts.zip", "_100m-Gitter",
                 {"Insgesamt_Haushalte": "sen_ges", "HH_nurSenioren": "sen_nur", "HH_mitSenioren": "sen_mit",
                  "HH_ohneSenioren": "sen_ohne"}),
    "staat": ("Zensus2022_Staatsangehoerigkeit_Gruppen_in_Gitterzellen.zip", "_100m-Gitter",
              {"Insgesamt_Bevoelkerung": "st_ges", "Deutschland": "st_de", "Ausland_Sonstige": "st_ausland",
               "EU27_Land": "st_eu27", "Sonstiges_Europa": "st_europa", "Sonstige_Welt": "st_welt",
               "Sonstige": "st_sonst"}),
    "miete": ("Zensus2022_Durchschn_Nettokaltmiete.zip", "_100m-Gitter", {"durchschnMieteQM": "miete_qm"}),
    "leerstand": ("Leerstandsquote_in_Gitterzellen.zip", "_100m-Gitter", {"Leerstandsquote": "leer_quote"}),
    "wohnflaeche": ("Durchschnittliche_Wohnflaeche_je_Bewohner_in_Gitterzellen.zip", "_100m-Gitter",
                    {"durchschnFlaechejeBew": "wfl_je_bew"}),
}
MITTELWERTE = {"miete_qm", "leer_quote", "wfl_je_bew"}  # in config/potsdam.yaml als zahl_felder


def struktur_lesen(minx: float, miny: float, maxx: float, maxy: float) -> None:
    """Paket A1: Strukturmerkmale aus den Destatis-Zips nach vorbereitet/zensus_struktur.csv."""
    ordner = KIEZ_DATEN / STRUKTUR_ORDNER
    zellen: dict[str, dict] = {}
    for thema, (datei, muster, spalten) in STRUKTUR.items():
        with zipfile.ZipFile(ordner / datei) as z:
            namen = [n for n in z.namelist() if n.endswith(muster + ".csv")]
            assert len(namen) == 1, (datei, namen)
            with z.open(namen[0]) as roh:
                leser = csv.reader(io.TextIOWrapper(roh, encoding="utf-8"), delimiter=";")
                kopf = next(leser)
                assert kopf[0].upper() == "GITTER_ID_100M", (datei, kopf[0])
                fehlt = [k for k in spalten if k not in kopf]
                assert not fehlt, (datei, "Spalten fehlen", fehlt)
                idx = {k: kopf.index(k) for k in spalten}
                zeichen = kopf.index("werterlaeuternde_Zeichen") if "werterlaeuternde_Zeichen" in kopf else None
                n = 0
                for zeile in leser:
                    x, y = zellmitte(zeile[0])
                    if not (minx - 100 <= x <= maxx + 100 and miny - 100 <= y <= maxy + 100):
                        continue
                    c = zellen.setdefault(zeile[0], {"gitter_id": zeile[0], "x": f"{x:.0f}", "y": f"{y:.0f}",
                                                     "_geaendert": []})
                    for alt, neu in spalten.items():
                        s = zeile[idx[alt]].strip()
                        if s in GEHEIM:
                            c[neu] = "0"
                            c["_geaendert"].append(neu)
                        elif s == "":
                            raise ValueError(f"{datei}: leerer Wert in {zeile[0]} ({alt})")
                        else:
                            c[neu] = s.replace(",", ".")
                            float(c[neu])  # bricht ab, wenn Destatis ein unbekanntes Zeichen liefert
                        if zeichen is not None and zeile[zeichen].strip():
                            assert zeile[zeichen].strip() == "KLAMMERN", (datei, zeile[zeichen])
                            c["_geaendert"].append(f"{neu}:unsicher")
                    n += 1
        print(f"Zensus-Struktur {thema}: {n} Zellen im Rechteck", file=sys.stderr)

    felder = ["gitter_id", "x", "y"] + [neu for _, _, sp in STRUKTUR.values() for neu in sp.values()] \
        + ["geaendert"]
    with (AUS / "zensus_struktur.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=felder, delimiter=";", restval="0")
        w.writeheader()
        for gid in sorted(zellen):
            c = zellen[gid]
            for m in MITTELWERTE:
                c.setdefault(m, "")  # Zelle ohne Wohnungen bzw. ohne Wert: leer, nie 0
            c["geaendert"] = ",".join(c.pop("_geaendert"))
            w.writerow(c)
    print(f"Zensus-Struktur: Zellen gesamt {len(zellen)}", file=sys.stderr)


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

    struktur_lesen(minx, miny, maxx, maxy)


if __name__ == "__main__":
    main()
