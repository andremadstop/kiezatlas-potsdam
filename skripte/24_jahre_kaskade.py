"""Gebäudejahre: Kaskade, Schätzung, Rücktest (Paket B4, Bauplan 05.11.2026 mit Prüfbericht).

Je Gebäude des Snapshots auswertung.gebaeude_stand_20261105 (nur die 52.309 Gebäude in den 32
Stadtteilen, Zuordnung wie 02_auswerten.py über einen Punkt im Umriss) eine Bauzeitklasse mit Quelle
oder „nicht datiert“. Stufen, die erste Stufe mit Ergebnis gewinnt:

  1  genaues Jahr aus auswertung.jahr_beleg (B2), nur Zeilen mit nur_pruefung = false
     (OSM, Wikipedia und die BLDAM-Liste sind nur Prüfwerte: E1, Korrektur 5, E8)
  2  Luftbildklammer aus auswertung.jahr_klammer (B3), nur wenn ausgerollt (Quelle ohne „nicht ausgerollt“)
  3  Blocktyp: belegte Bauzeit einer Großsiedlung (config/blocktypen.geojson, Beleg je Gebiet),
     nur für Wohngebäude im Gebiet, die der Bauform des Gebiets entsprechen
  4  Zensus 2022, Gebäude mit Wohnraum nach Baujahr (Mikrozensus-Klassen): je 100-m-Zelle auf die
     Wohngebäude der Zelle verteilt, gelenkt von der Gebäudeform (ALKIS-NAS, B0); Geheimhaltungslücken
     der Zelle aus dem Rest der 1-km-Zelle aufgefüllt
  5  Nachbarn: häufigste Klasse der Gebäude aus Stufe 1 bis 4 im Umkreis von 100 m (mindestens 3)
  6  nicht datiert: Nebengebäude (E5) und alles ohne Stufe 1 bis 5

Datenschutz (Korrektur 6): ALKIS führt keine Zahl der Wohneinheiten. Deshalb trägt kein Gebäude mit
Wohnraum ein Einzeljahr, außer es ist ein Denkmal aus einer freigegebenen Quelle (derzeit keine);
veröffentlicht wird dann nur die Klasse. Keine Adressen, keine oid in daten/jahre/.

Unterbefehle:
  blocktypen   zieht die Gebietsgrenzen der Großsiedlungen aus ALKIS und schreibt config/blocktypen.geojson
  rechnen      Kaskade: schreibt auswertung.gebaeude_jahr und daten/jahre/<nr>.js (KIEZ_JAHR_<nr>)
  ruecktest    Rücktest und Summenprüfung nach pruefen/B4_protokoll.md: berichte/B4_holdout.md

Kein Netzabruf. Rolle kiezatlas_rechnen (schreibt nur auswertung.gebaeude_jahr, Zwischenstand in TEMP).
Aufruf (aus dem Repo-Wurzelverzeichnis, Passwort nur per Umgebung):
  set -a; . ../kiezatlas-potsdam/.env; set +a
  PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=kiezatlas_rechnen PGPASSWORD="$RECHNEN_PASSWORD" \\
    uv run -q --offline --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \\
    python -I skripte/24_jahre_kaskade.py rechnen
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import psycopg

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "daten"
BLOCKTYPEN = WURZEL / "config" / "blocktypen.geojson"
BERICHT = WURZEL / "berichte" / "B4_holdout.md"
KIEZ_DATEN = Path(os.environ.get("KIEZ_DATEN") or (WURZEL.parent / "kiezatlas-daten"))
REFERENZ_B3 = KIEZ_DATEN / "luftbild_lgb" / "2026-11-05" / "referenz" / "referenz.csv"
SNAPSHOT = "auswertung.gebaeude_stand_20261105"

# Bauzeitklassen: Mikrozensus-Klassen des Zensus 2022 (wie daten/jahre_zellen.js und die Fixture für B5)
KLASSEN = ["vor 1919", "1919–1948", "1949–1978", "1979–1990", "1991–2000", "2001–2010", "2011–2019", "ab 2020"]
KLASSEN_DB = ["vor_1919", "1919_1948", "1949_1978", "1979_1990", "1991_2000", "2001_2010", "2011_2019", "ab_2020"]
SPANNE = [(None, 1918), (1919, 1948), (1949, 1978), (1979, 1990), (1991, 2000), (2001, 2010), (2011, 2019),
          (2020, None)]

# Gebäude mit Wohnraum (wie „Gebäude mit Wohnraum“ im Zensus): ALKIS-Funktion enthält „wohn“
# (Wohnhaus, Wohngebäude …, … mit Wohnen, Wohn- und Geschäftsgebäude, Wohnheim, land- und
# forstwirtschaftliches Wohngebäude) oder ist ein Forsthaus. Wochenend- und Ferienhäuser nicht.
WOHNRAUM_SQL = "(s.funktion ~* 'wohn' OR s.funktion = 'Forsthaus')"
# Nebengebäude (E5): grau, nicht datiert. „Nach Quellenlage nicht zu spezifizieren“ und
# „Land- und forstwirtschaftliches Betriebsgebäude“ haben im Snapshot eine mittlere Grundfläche von 25 m²
# (wie Schuppen), sie zählen deshalb hierher.
NEBEN = {
    "Garage", "Gebäude zur Freizeitgestaltung", "Schuppen", "Gartenhaus", "Gebäude zum Parken", "Tiefgarage",
    "Überdachung", "Umformer", "Durchfahrt im Gebäude", "Durchfahrt an überbautem Verkehrsweg",
    "Treibhaus, Gewächshaus", "Schornstein", "Schornstein im Gebäude", "Toilette", "Keller", "Solarzellen",
    "Tank", "Silo", "Wasserbehälter", "Mast", "Funkmast", "Kran", "Nach Quellenlage nicht zu spezifizieren",
    "Land- und forstwirtschaftliches Betriebsgebäude", "Gebäude für Vorratshaltung",
}
NACHBAR_RADIUS = 100.0   # m, Mittelpunktabstand
NACHBAR_MIN = 3
NACHBAR_MAX = 10

Q_TEXT = {
    "beleg": "genaues Jahr mit Beleg (B2, freigegebene Quelle)",
    "klammer": "Luftbildklammer (B3, ausgerollt)",
    "blocktyp": "Blocktyp: belegte Bauzeit der Großsiedlung, geschätzt",
    "zensus": "Zensus 2022 je 100-m-Zelle, nach Gebäudeform verteilt, geschätzt",
    "nachbarn": "Klasse der Nachbargebäude bis 100 m, geschätzt",
}
LGB = ("© GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)")
ZENSUS = ("© Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 "
          "(https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)")
QUELLEN_JS = {
    "zensus": {"quelle": "Zensus 2022, Gebäude mit Wohnraum nach Baujahr (Mikrozensus-Klassen), 100-m- und 1-km-Gitter, "
                         "je Zelle auf die Gebäude verteilt nach Gebäudeform aus ALKIS",
               "lizenz": "dl-de/by-2-0", "vermerk": f"{ZENSUS}; Gebäudeform {LGB}",
               "url": "https://www.zensus2022.de/", "stand": "2022-05-15"},
    "blocktyp": {"quelle": "Bauzeit der Großsiedlung nach Landeshauptstadt Potsdam, Broschüre „Potsdamer Platte“ (2008), "
                           "S. 72; Gebietsgrenzen eigene Abgrenzung aus ALKIS (config/blocktypen.geojson)",
                 "lizenz": "Bauzeiten als Fakten übernommen; Gebäude dl-de/by-2-0",
                 "vermerk": f"Bauzeiten: Landeshauptstadt Potsdam, „Potsdamer Platte“, Juli 2008; Gebäude {LGB}"},
    "nachbarn": {"quelle": "häufigste Bauzeitklasse der datierten Nachbargebäude im Umkreis von 100 m",
                 "lizenz": "dl-de/by-2-0", "vermerk": f"{ZENSUS}; {LGB}"},
    "umrisse": {"quelle": "ALKIS vereinfacht, Gebäude (Snapshot 05.11.2026)", "lizenz": "dl-de/by-2-0", "vermerk": LGB,
                "url": "https://isk.geobasis-bb.de/ows/alkis_vereinf_wfs", "stand": "2026-11-05"},
}
HINWEIS = ("Bauzeit je Gebäude als Klasse. Fast alle Angaben sind Schätzungen: Zensus 2022 je 100-m-Zelle nach "
           "Gebäudeform auf die Gebäude verteilt, belegte Bauzeiten der Großsiedlungen, Nachbargebäude. Sie sagen "
           "nichts Sicheres über ein einzelnes Gebäude oder Grundstück. Die Zensuswerte sind durch das "
           "Geheimhaltungsverfahren leicht verändert. Wohngebäude tragen kein Einzeljahr. Nebengebäude (Garagen, "
           "Lauben, Schuppen) sind nicht datiert. Trefferquoten des Rücktests stehen auf der Methodenseite.")


def klasse_von_spanne(von: int | None, bis: int | None) -> int | None:
    """Klasse, in der die Jahresspanne ganz liegt; sonst None."""
    treffer = [i for i, (a, b) in enumerate(SPANNE)
               if (a is None or (von is not None and von >= a)) and (b is None or (bis is not None and bis <= b))]
    return treffer[0] if len(treffer) == 1 else None


def klasse_mehrheit(von: int, bis: int) -> int:
    """Klasse mit den meisten Jahren der Spanne (Blocktypen); bei Gleichstand die frühere."""
    zahl = Counter(next(i for i, (a, b) in enumerate(SPANNE) if (a is None or j >= a) and (b is None or j <= b))
                   for j in range(von, bis + 1))
    return max(sorted(zahl), key=lambda k: zahl[k])


def verbinden() -> psycopg.Connection:
    return psycopg.connect("", application_name="kiezatlas-B4")


# ------------------------------------------------------------------------------------------ Blocktypen
# Belegte Bauzeiten der Großsiedlungen (Broschüre „Potsdamer Platte“, Landeshauptstadt Potsdam 2008,
# Tabelle S. 72 der Druckzählung = PDF-Seite 73, Stand 31.12.2006; Rohdatei und Seiten:
# $KIEZ_DATEN/potsdamer_platte/2026-11-05/HERKUNFT.md). Gebietsgrenze: Cluster der Wohngebäude im
# Stadtteil, die der in der Broschüre beschriebenen Bauform entsprechen (Höhe, Dachform).
GEBIETE = [
    {"gebiet": "Waldstadt I", "stadtteile": ["64"], "von": 1960, "bis": 1964, "flach": False, "dach": "Satteldach",
     "hoehe_min": 10.0, "flaeche_ha_beleg": 44.9,
     "beleg": "„Potsdamer Platte“ (2008), S. 72: Entstehungszeitraum 1960–64, 44,9 ha; S. 17: vorwiegend "
              "viergeschossig, ziegelgedeckte Satteldächer"},
    {"gebiet": "Potsdam-West und Auf dem Kiewitt", "stadtteile": ["32"], "von": 1966, "bis": 1975, "flach": True,
     "hoehe_min": 11.0, "flaeche_ha_beleg": 35.0,
     "beleg": "„Potsdamer Platte“ (2008), S. 72: Auf dem Kiewitt 1966–73 (8,6 ha), Potsdam-West 1971–75 (26,4 ha)"},
    {"gebiet": "Am Stern", "stadtteile": ["71"], "von": 1971, "bis": 1979, "flach": True, "hoehe_min": 11.0,
     "flaeche_ha_beleg": 114.3,
     "beleg": "„Potsdamer Platte“ (2008), S. 72: 1971–79, 114,3 ha; S. 27: fünf-, elf- und 15-geschossige "
              "Wohngebäude, daneben kleinteilige Bebauung der 50er und 60er Jahre"},
    {"gebiet": "Zentrum Ost", "stadtteile": ["43"], "von": 1972, "bis": 1975, "flach": True, "hoehe_min": 11.0,
     "flaeche_ha_beleg": 33.5,
     "beleg": "„Potsdamer Platte“ (2008), S. 72: 1972–75, Erweiterung 1985–87 (nicht getrennt abgegrenzt), 33,5 ha"},
    {"gebiet": "Waldstadt II", "stadtteile": ["65"], "von": 1977, "bis": 1986, "flach": True, "hoehe_min": 11.0,
     "flaeche_ha_beleg": 87.3,
     "beleg": "„Potsdamer Platte“ (2008), S. 72: 1977–86, 87,3 ha; S. 26: überwiegend fünfgeschossig"},
    {"gebiet": "Am Schlaatz", "stadtteile": ["63"], "von": 1980, "bis": 1987, "flach": True, "hoehe_min": 11.0,
     "flaeche_ha_beleg": 76.2,
     "beleg": "„Potsdamer Platte“ (2008), S. 72: 1980–87, 76,2 ha; S. 28: zumeist fünfgeschossig"},
    {"gebiet": "Drewitz", "stadtteile": ["72"], "von": 1986, "bis": 1991, "flach": True, "hoehe_min": 11.0,
     "flaeche_ha_beleg": 37.7,
     "beleg": "„Potsdamer Platte“ (2008), S. 72: 1986–91, 37,7 ha; S. 29: fünfgeschossige Wohnblocks, 1989 "
              "noch nicht fertig"},
    {"gebiet": "Kirchsteigfeld", "stadtteile": ["73"], "von": 1990, "bis": 1999, "flach": False, "dach": None,
     "hoehe_min": 9.0, "flaeche_ha_beleg": None,
     "beleg": "„Potsdamer Platte“ (2008), S. 29: letzter Bauabschnitt des Neubaugebiets Drewitz in den 90er "
              "Jahren als Kirchsteigfeld verwirklicht, ohne Platte"},
]
# Nicht aufgenommen: Zentrum Süd (1960–65) und Wilhelm-Külz-Straße (1976–83). Beide liegen in der
# Historischen Innenstadt zwischen älteren und neueren Bauten gleicher Form; eine Grenze lässt sich aus
# den Gebäudedaten nicht sicher ziehen. Sie bleiben bei Stufe 4 (Zensus).

NAS_BESTE = ("(SELECT DISTINCT ON (oid_bezug) oid_bezug, dachform, bauweise, objekthoehe FROM auswertung.alkis_nas_gebaeude "
             "WHERE oid_bezug IS NOT NULL ORDER BY oid_bezug, ueberlappung DESC NULLS LAST, gml_id)")


def form_bedingung(g: dict) -> tuple[str, list]:
    teile, werte = [f"{WOHNRAUM_SQL}", "n.objekthoehe >= %s"], [g["hoehe_min"]]
    if g.get("flach"):
        teile.append("n.dachform = 'Flachdach'")
    elif g.get("dach"):
        teile.append("n.dachform = %s")
        werte.append(g["dach"])
    return " AND ".join(teile), werte


def blocktypen_ziehen() -> None:
    feats = []
    with verbinden() as conn, conn.cursor() as cur:
        for g in GEBIETE:
            bed, werte = form_bedingung(g)
            cur.execute(f"""
                WITH k AS (SELECT s.oid, ST_Transform(s.geom, 25833) AS g
                           FROM {SNAPSHOT} s
                           JOIN public.stadtteil t ON t.nr = ANY(%s) AND ST_Contains(t.geom, ST_PointOnSurface(s.geom))
                           JOIN {NAS_BESTE} n ON n.oid_bezug = s.oid
                           WHERE {bed}),
                     c AS (SELECT g, ST_ClusterDBSCAN(g, eps := 40, minpoints := 1) OVER () AS cl FROM k),
                     h AS (SELECT cl, count(*) AS n, ST_Buffer(ST_Union(ST_ConcaveHull(ST_Collect(g), 0.3), ST_Union(g)), 15) AS hg
                           FROM c GROUP BY cl HAVING count(*) >= 4),
                     u AS (SELECT ST_Intersection(ST_Union(hg),
                                  (SELECT ST_Transform(ST_Union(geom), 25833) FROM public.stadtteil WHERE nr = ANY(%s))) AS ug,
                                  sum(n) AS n, count(*) AS cluster FROM h)
                SELECT ST_AsGeoJSON(ST_Transform(ST_Multi(ST_CollectionExtract(ug, 3)), 4326), 6),
                       round((ST_Area(ug) / 10000.0)::numeric, 1), n, cluster FROM u""",
                        [g["stadtteile"], *werte, g["stadtteile"]])
            gj, ha, n, cluster = cur.fetchone()
            k = klasse_mehrheit(g["von"], g["bis"])
            regel = (f"Gebäude mit Wohnraum, Objekthöhe ab {g['hoehe_min']:g} m"
                     + (", Flachdach" if g.get("flach") else (f", {g['dach']}" if g.get("dach") else ""))
                     + "; Cluster ab 4 Gebäuden (Abstand bis 40 m), Hülle mit 15 m Rand, im Stadtteil")
            feats.append({"type": "Feature", "geometry": json.loads(gj),
                          "properties": {"gebiet": g["gebiet"], "stadtteile": g["stadtteile"], "von": g["von"],
                                         "bis": g["bis"], "klasse": KLASSEN[k], "beleg": g["beleg"],
                                         "flaeche_ha_beleg": g["flaeche_ha_beleg"], "flaeche_ha_polygon": float(ha),
                                         "gebaeude_form": int(n), "cluster": int(cluster),
                                         "form": {"hoehe_min": g["hoehe_min"], "flachdach": bool(g.get("flach")),
                                                  "dachform": g.get("dach")},
                                         "regel": regel}})
            print(f"  {g['gebiet']}: {n} Gebäude in {cluster} Clustern, {ha} ha (Beleg {g['flaeche_ha_beleg']} ha), "
                  f"Klasse {KLASSEN[k]}", file=sys.stderr)
    inhalt = {"type": "FeatureCollection",
              "name": "Blocktypen der Potsdamer Großsiedlungen (Paket B4)",
              "stand": date.today().isoformat(),
              "hinweis": ("Gebietsgrenzen eigene Abgrenzung aus ALKIS-Gebäuden (© GeoBasis-DE/LGB, dl-de/by-2-0, "
                          "https://www.govdata.de/dl-de/by-2-0, Daten verändert (eigene Berechnung)). Bauzeiten als "
                          "Fakten aus Landeshauptstadt Potsdam, „Potsdamer Platte“ (2008); kein Text übernommen. "
                          "Klasse = Mikrozensus-Klasse mit den meisten Jahren der Bauzeit. Zentrum Süd und "
                          "Wilhelm-Külz-Straße nicht aufgenommen (Grenze nicht sicher abgrenzbar)."),
              "features": feats}
    BLOCKTYPEN.write_text(json.dumps(inhalt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"geschrieben: {BLOCKTYPEN.relative_to(WURZEL)}", file=sys.stderr)


# ------------------------------------------------------------------------------------------ Merkmale
def h_stufe(h) -> str:
    if h is None:
        return "?"
    for grenze, name in ((4, "<4"), (7, "4-7"), (10, "7-10"), (13, "10-13"), (17, "13-17"), (25, "17-25")):
        if h < grenze:
            return name
    return ">=25"


def f_stufe(f: float) -> str:
    for grenze, name in ((60, "<60"), (100, "60-100"), (150, "100-150"), (250, "150-250"), (500, "250-500"),
                         (1000, "500-1000")):
        if f < grenze:
            return name
    return ">=1000"


def t_gruppe(funktion: str) -> str:
    if funktion == "Wohnhaus":
        return "wohnhaus"
    if funktion == "Wohnheim":
        return "wohnheim"
    if funktion.startswith(("Wohngebäude mit", "Wohn- und")) or "mit Wohnen" in funktion:
        return "gemischt"
    return "sonst"


def merkmale(b: dict) -> dict:
    return {"d": b["dachform"] or "?", "h": h_stufe(b["hoehe"]), "f": f_stufe(b["flaeche"]),
            "w": b["bauweise"] or "?", "t": t_gruppe(b["funktion"])}


# ------------------------------------------------------------------------------------------ Laden
def gebaeude_laden(cur) -> dict[str, dict]:
    cur.execute(f"""
        SELECT s.oid, t.nr, s.funktion, {WOHNRAUM_SQL} AS wohnraum, n.dachform, n.bauweise, n.objekthoehe,
               ST_Area(ST_Transform(s.geom, 25833)),
               ST_X(ST_Transform(p.p, 25833)), ST_Y(ST_Transform(p.p, 25833)),
               ST_X(ST_Transform(p.p, 3035)), ST_Y(ST_Transform(p.p, 3035))
        FROM {SNAPSHOT} s
        CROSS JOIN LATERAL (SELECT ST_PointOnSurface(s.geom) AS p) p
        JOIN public.stadtteil t ON ST_Contains(t.geom, p.p)
        LEFT JOIN {NAS_BESTE} n ON n.oid_bezug = s.oid""")
    geb = {}
    for oid, nr, funktion, wohnraum, dach, bauweise, hoehe, fl, x, y, x3, y3 in cur.fetchall():
        funktion = funktion or ""
        geb[oid] = {"oid": oid, "nr": nr, "funktion": funktion, "wohnraum": bool(wohnraum),
                    "neben": (not wohnraum) and funktion in NEBEN, "dachform": dach, "bauweise": bauweise,
                    "hoehe": float(hoehe) if hoehe is not None else None, "flaeche": float(fl), "x": x, "y": y,
                    "zelle": f"CRS3035RES100mN{math.floor(y3 / 100) * 100}E{math.floor(x3 / 100) * 100}",
                    "km": f"CRS3035RES1000mN{math.floor(y3 / 1000) * 1000}E{math.floor(x3 / 1000) * 1000}"}
    return geb


def zensus_laden(cur) -> tuple[dict, dict, set]:
    """100-m-Zellen {id: {'T': insgesamt, 'n': [8], 'g': [8 bool]}}, 1-km-Zellen {id: [8]}, km ganz in der Stadt."""
    cur.execute("""SELECT gitter_id, raster, klasse, anzahl, geaendert FROM auswertung.zensus_gebaeude_jahr
                   WHERE merkmal = 'mz_klassen'""")
    z100: dict = {}
    z1k: dict = {}
    for gid, raster, klasse, anzahl, geaendert in cur.fetchall():
        if raster == "100m":
            z = z100.setdefault(gid, {"T": 0, "n": [0] * 8, "g": [False] * 8})
            if klasse == "insgesamt":
                z["T"] = anzahl
            else:
                i = KLASSEN_DB.index(klasse)
                z["n"][i], z["g"][i] = anzahl, geaendert
        elif klasse != "insgesamt":
            z1k.setdefault(gid, [0] * 8)[KLASSEN_DB.index(klasse)] = anzahl
    # 1-km-Zellen, deren Quadrat ganz in der Stadt liegt (nur dort ist 1 km − Σ 100 m ein sauberer Rest)
    cur.execute("""WITH s AS (SELECT ST_Transform(ST_Union(geom), 3035) AS g FROM public.stadtteil),
                        k AS (SELECT DISTINCT gitter_id FROM auswertung.zensus_gebaeude_jahr WHERE raster = '1km')
                   SELECT k.gitter_id FROM k, s WHERE ST_Within(ST_MakeEnvelope(
                        substring(k.gitter_id from 'E([0-9]+)')::int, substring(k.gitter_id from 'N([0-9]+)')::int,
                        substring(k.gitter_id from 'E([0-9]+)')::int + 1000, substring(k.gitter_id from 'N([0-9]+)')::int + 1000,
                        3035), s.g)""")
    innen = {r[0] for r in cur.fetchall()}
    return z100, z1k, innen


def km_von(zelle: str) -> str:
    n = int(re.search(r"N(\d+)", zelle).group(1))
    e = int(re.search(r"E(\d+)", zelle).group(1))
    return f"CRS3035RES1000mN{n // 1000 * 1000}E{e // 1000 * 1000}"


def zellanteile(z100: dict, z1k: dict, innen: set) -> tuple[dict, dict]:
    """Anteile je Klasse und 100-m-Zelle; Geheimhaltungslücke aus dem Rest der 1-km-Zelle aufgefüllt."""
    rest_km: dict = {}
    summe_km: dict = defaultdict(lambda: [0] * 8)
    for gid, z in z100.items():
        for i in range(8):
            summe_km[km_von(gid)][i] += z["n"][i]
    for km, werte in z1k.items():
        if km in innen:
            rest_km[km] = [max(0, werte[i] - summe_km[km][i]) for i in range(8)]
    stadt_rest = [sum(r[i] for r in rest_km.values()) for i in range(8)]
    anteile, herkunft = {}, Counter()
    for gid, z in z100.items():
        if z["T"] <= 0:
            continue
        n = [float(v) for v in z["n"]]
        luecke = z["T"] - sum(n)
        if luecke > 0:
            km = km_von(gid)
            gew = [rest_km[km][i] if (km in rest_km and z["g"][i]) else 0 for i in range(8)]
            if sum(gew) > 0:
                herkunft["km_rest"] += 1
            else:
                gew = [stadt_rest[i] if z["g"][i] else 0 for i in range(8)]
                if sum(gew) > 0:
                    herkunft["stadt_rest"] += 1
                else:
                    gew = n[:] if sum(n) > 0 else [1.0] * 8
                    herkunft["eigene_klassen"] += 1
            s = sum(gew)
            n = [n[i] + luecke * gew[i] / s for i in range(8)]
        else:
            herkunft["ohne_luecke"] += 1
        s = sum(n)
        anteile[gid] = [v / s for v in n]
    return anteile, dict(herkunft)


def groesster_rest(anteile: list[float], gesamt: int) -> list[int]:
    roh = [a * gesamt for a in anteile]
    ganz = [math.floor(r) for r in roh]
    fehlt = gesamt - sum(ganz)
    for i in sorted(range(len(roh)), key=lambda i: (-(roh[i] - ganz[i]), i))[:fehlt]:
        ganz[i] += 1
    return ganz


class Formmodell:
    """Naiver Bayes über die Gebäudeform, gelernt in „reinen“ Zellen (eine Klasse ≥ 85 %, keine Lücke)."""

    def __init__(self, geb: dict, z100: dict, anteile: dict):
        self.zahl = [Counter() for _ in range(8)]
        self.n = [0] * 8
        self.werte = defaultdict(set)
        rein = {}
        for gid, z in z100.items():
            if z["T"] >= 4 and sum(z["n"]) >= z["T"] and gid in anteile:
                k = max(range(8), key=lambda i: anteile[gid][i])
                if anteile[gid][k] >= 0.85:
                    rein[gid] = k
        self.reine_zellen = len(rein)
        for b in geb.values():
            if b["wohnraum"] and b["zelle"] in rein:
                k = rein[b["zelle"]]
                self.n[k] += 1
                for f, v in merkmale(b).items():
                    self.zahl[k][(f, v)] += 1
                    self.werte[f].add(v)
        for b in geb.values():
            for f, v in merkmale(b).items():
                self.werte[f].add(v)

    def log_l(self, b: dict) -> list[float]:
        m = merkmale(b)
        return [sum(math.log((self.zahl[k][(f, v)] + 1) / (self.n[k] + len(self.werte[f]))) for f, v in m.items())
                for k in range(8)]


def zensus_verteilen(geb: dict, wohn_je_zelle: dict, anteile: dict, zensus_t: dict[str, int], modell: Formmodell,
                     vorgabe: dict[str, int]) -> tuple[dict[str, int], list[str]]:
    """Je Zelle Kapazitäten aus den Anteilen, gierige Zuteilung nach Formwahrscheinlichkeit.
    vorgabe: oid -> Klasse aus Stufe 1-3 (verbraucht Kapazität, wird nicht neu zugeteilt).
    Rückgabe: oid -> Klasse und die Liste der Gebäude ohne Platz (mehr ALKIS-Gebäude als Zensus-Gebäude)."""
    ergebnis, ueberzahl = {}, []
    for zelle, oids in wohn_je_zelle.items():
        if zelle not in anteile:
            continue
        ziel = min(len(oids), zensus_t[zelle])
        kap = groesster_rest(anteile[zelle], ziel)
        frei = []
        for oid in oids:
            if oid in vorgabe:
                k = vorgabe[oid]
                if kap[k] > 0:
                    kap[k] -= 1
                elif sum(kap) > 0:   # Vorgabe größer als der Zensus: am nächsten liegende Klasse verbraucht
                    nah = min((i for i in range(8) if kap[i] > 0), key=lambda i: (abs(i - k), i))
                    kap[nah] -= 1
            else:
                frei.append(oid)
        paare = []
        for oid in frei:
            ll = modell.log_l(geb[oid])
            m = max(ll[i] for i in range(8))
            z = sum(math.exp(ll[i] - m) * anteile[zelle][i] for i in range(8)) or 1.0
            for i in range(8):
                paare.append((-(math.exp(ll[i] - m) * anteile[zelle][i] / z), oid, i))
        paare.sort()
        for _, oid, i in paare:
            if oid in ergebnis or kap[i] <= 0:
                continue
            ergebnis[oid] = i
            kap[i] -= 1
        ueberzahl.extend(oid for oid in frei if oid not in ergebnis)
    return ergebnis, ueberzahl


def nachbarn(geb: dict, datiert: dict[str, int], kandidaten: list[str]) -> dict[str, int]:
    gitter = defaultdict(list)
    for oid in datiert:
        b = geb[oid]
        gitter[(int(b["x"] // NACHBAR_RADIUS), int(b["y"] // NACHBAR_RADIUS))].append(oid)
    ergebnis = {}
    for oid in kandidaten:
        b = geb[oid]
        gx, gy = int(b["x"] // NACHBAR_RADIUS), int(b["y"] // NACHBAR_RADIUS)
        nahe = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for o in gitter.get((gx + dx, gy + dy), ()):
                    if o == oid:
                        continue
                    d = math.hypot(geb[o]["x"] - b["x"], geb[o]["y"] - b["y"])
                    if d <= NACHBAR_RADIUS:
                        nahe.append((d, o))
        nahe.sort()
        nahe = nahe[:NACHBAR_MAX]
        if len(nahe) < NACHBAR_MIN:
            continue
        zahl = Counter(datiert[o] for _, o in nahe)
        beste = max(zahl.values())
        kandid = {k for k, v in zahl.items() if v == beste}
        ergebnis[oid] = next(datiert[o] for _, o in nahe if datiert[o] in kandid)
    return ergebnis


# ------------------------------------------------------------------------------------------ Kaskade
def blocktyp_zuordnen(cur) -> dict[str, tuple[int, str]]:
    daten = json.loads(BLOCKTYPEN.read_text(encoding="utf-8"))
    cur.execute("CREATE TEMP TABLE b4_blocktyp (gebiet text, klasse int, geom geometry(MultiPolygon, 4326), "
                "hoehe_min numeric, flach boolean, dach text) ON COMMIT DROP")
    for f in daten["features"]:
        p = f["properties"]
        cur.execute("INSERT INTO b4_blocktyp VALUES (%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s, %s, %s)",
                    (p["gebiet"], KLASSEN.index(p["klasse"]), json.dumps(f["geometry"]), p["form"]["hoehe_min"],
                     p["form"]["flachdach"], p["form"]["dachform"]))
    cur.execute(f"""
        SELECT DISTINCT ON (s.oid) s.oid, b.klasse, b.gebiet
        FROM {SNAPSHOT} s JOIN b4_blocktyp b ON ST_Contains(b.geom, ST_PointOnSurface(s.geom))
        JOIN {NAS_BESTE} n ON n.oid_bezug = s.oid
        WHERE {WOHNRAUM_SQL} AND n.objekthoehe >= b.hoehe_min
          AND (NOT b.flach OR n.dachform = 'Flachdach') AND (b.dach IS NULL OR n.dachform = b.dach)
        ORDER BY s.oid, b.gebiet""")
    return {oid: (k, gebiet) for oid, k, gebiet in cur.fetchall()}


def stufen_1_2(cur, geb: dict) -> tuple[dict, dict, set]:
    """Stufe 1 (freigegebene genaue Jahre) und 2 (ausgerollte Klammern). Denkmal nur aus freigegebener Quelle."""
    cur.execute("""SELECT oid_bezug, jahr_von, jahr_bis, quelle FROM auswertung.jahr_beleg
                   WHERE NOT nur_pruefung AND genau AND art = 'bau' AND oid_bezug IS NOT NULL
                     AND quelle !~* '(openstreetmap|wikipedia|\\mosm\\M|bldam|denkmalliste)'
                     AND lizenz !~* '(odbl|by-sa|ungeklärt)'""")
    stufe1 = {}
    for oid, von, bis, quelle in cur.fetchall():
        if oid in geb and von is not None:
            stufe1.setdefault(oid, []).append((von, bis or von, quelle))
    s1 = {}
    for oid, rows in stufe1.items():
        von, bis = min(r[0] for r in rows), max(r[1] for r in rows)
        k = klasse_von_spanne(von, bis)
        if k is not None:
            s1[oid] = (von if von == bis else None, k, rows[0][2])
    cur.execute("""SELECT DISTINCT oid_bezug FROM auswertung.jahr_beleg
                   WHERE NOT nur_pruefung AND quelle ~* '(denkmal|bldam|ddb)' AND lizenz !~* '(ungeklärt|by-sa|odbl)'""")
    denkmal = {r[0] for r in cur.fetchall()}
    cur.execute("""SELECT oid_bezug, nicht_vor, nicht_nach, quelle FROM auswertung.jahr_klammer
                   WHERE quelle !~* 'nicht ausgerollt'""")
    s2 = {}
    for oid, nv, nn, quelle in cur.fetchall():
        k = klasse_von_spanne(nv, nn)
        if oid in geb and k is not None and oid not in s1:
            s2[oid] = (k, quelle)
    return s1, s2, denkmal


def kaskade(cur) -> dict:
    geb = gebaeude_laden(cur)
    z100, z1k, innen = zensus_laden(cur)
    anteile, herkunft = zellanteile(z100, z1k, innen)
    zensus_t = {gid: z["T"] for gid, z in z100.items()}
    modell = Formmodell(geb, z100, anteile)
    s1, s2, denkmal = stufen_1_2(cur, geb)
    s3_roh = blocktyp_zuordnen(cur)
    s3 = {oid: v for oid, v in s3_roh.items() if oid in geb and oid not in s1 and oid not in s2}

    wohn_je_zelle = defaultdict(list)
    for oid, b in geb.items():
        if b["wohnraum"]:
            wohn_je_zelle[b["zelle"]].append(oid)
    for oids in wohn_je_zelle.values():
        oids.sort()
    vorgabe = {oid: v[1] for oid, v in s1.items()} | {oid: v[0] for oid, v in s2.items()} | \
              {oid: v[0] for oid, v in s3.items()}
    s4, ueberzahl = zensus_verteilen(geb, wohn_je_zelle, anteile, zensus_t, modell, vorgabe)
    # Gegenrechnung ohne Vorgabe (für den Rücktest von Stufe 3: Zensus allein an den Blocktyp-Gebäuden)
    s4_frei, _ = zensus_verteilen(geb, wohn_je_zelle, anteile, zensus_t, modell, {})

    datiert = {oid: v[1] for oid, v in s1.items()} | {oid: v[0] for oid, v in s2.items()} | \
              {oid: v[0] for oid, v in s3.items()} | s4
    kandidaten = sorted(oid for oid, b in geb.items() if oid not in datiert and not b["neben"])
    s5 = nachbarn(geb, datiert, kandidaten)

    zeilen = {}
    for oid, b in geb.items():
        if oid in s1:
            j, k, q = s1[oid]
            jahr_frei = j if (not b["wohnraum"] or oid in denkmal) else None
            zeilen[oid] = (jahr_frei, k, True, f"{Q_TEXT['beleg']}: {q}", 1)
        elif oid in s2:
            zeilen[oid] = (None, s2[oid][0], False, f"{Q_TEXT['klammer']}: {s2[oid][1]}", 2)
        elif oid in s3:
            k, gebiet = s3[oid]
            zeilen[oid] = (None, k, False, f"{Q_TEXT['blocktyp']} ({gebiet})", 3)
        elif oid in s4:
            zeilen[oid] = (None, s4[oid], False, Q_TEXT["zensus"], 4)
        elif oid in s5:
            zeilen[oid] = (None, s5[oid], False, Q_TEXT["nachbarn"], 5)
        else:
            zeilen[oid] = (None, None, False, None, 6)
    return {"geb": geb, "zeilen": zeilen, "s4_frei": s4_frei, "ueberzahl": set(ueberzahl), "denkmal": denkmal,
            "anteile_herkunft": herkunft, "reine_zellen": modell.reine_zellen, "z100": z100,
            "wohn_ohne_zelle": sum(len(o) for z, o in wohn_je_zelle.items() if z not in anteile)}


def rechnen() -> None:
    with verbinden() as conn, conn.cursor() as cur:
        e = kaskade(cur)
        geb, zeilen = e["geb"], e["zeilen"]
        cur.execute("TRUNCATE auswertung.gebaeude_jahr")
        with cur.copy("COPY auswertung.gebaeude_jahr (oid, j, j_klasse, genau, quelle, stufe) FROM STDIN") as cp:
            for oid in sorted(zeilen):
                j, k, genau, q, s = zeilen[oid]
                cp.write_row((oid, j, KLASSEN[k] if k is not None else None, genau, q, s))
        # Ausgabe je Stadtteil, Umrisse wie daten/gebaeude/<nr>.js
        cur.execute("SELECT nr FROM public.stadtteil ORDER BY nr")
        teile = [r[0] for r in cur.fetchall()]
        groessen = {}
        for nr in teile:
            cur.execute(f"""SELECT s.oid, ST_AsGeoJSON(ST_SimplifyPreserveTopology(s.geom, 0.000005), 6)
                            FROM {SNAPSHOT} s JOIN public.stadtteil t ON t.nr = %s
                                 AND ST_Contains(t.geom, ST_PointOnSurface(s.geom)) ORDER BY s.oid""", (nr,))
            feats = []
            for oid, gj in cur.fetchall():
                j, k, _genau, _q, s = zeilen[oid]
                g = "belegt" if s in (1, 2) else ("nicht_datiert" if s == 6 else "geschaetzt")
                q = {1: "beleg", 2: "klammer", 3: "blocktyp", 4: "zensus", 5: "nachbarn"}.get(s)
                feats.append({"type": "Feature", "geometry": json.loads(gj),
                              "properties": {"j": j, "k": k, "g": g, "q": q, "s": s}})
            genutzt = {f["properties"]["q"] for f in feats} - {None}
            quellen = {k: v for k, v in QUELLEN_JS.items() if k in genutzt or k == "umrisse"}
            inhalt = {"type": "FeatureCollection", "stand": date.today().isoformat(), "klassen": KLASSEN,
                      "hinweis": HINWEIS, "quellen": quellen, "features": feats}
            pfad = DATEN / "jahre" / f"{nr}.js"
            pfad.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(inhalt, ensure_ascii=False, separators=(",", ":"))
            pfad.write_text(f"window.KIEZ_JAHR_{nr}={text};\n", encoding="utf-8")
            groessen[nr] = len(gzip.compress(pfad.read_bytes(), 9))
    stufe = Counter(z[4] for z in zeilen.values())
    print(f"Gebäude: {len(geb)}; je Stufe: {dict(sorted(stufe.items()))}; Überzahl: {len(e['ueberzahl'])}; "
          f"Wohngebäude ohne Zensuszelle: {e['wohn_ohne_zelle']}; reine Zellen: {e['reine_zellen']}; "
          f"Lücken aufgefüllt: {e['anteile_herkunft']}", file=sys.stderr)
    nr_max = max(groessen, key=groessen.get)
    print(f"größte Datei: daten/jahre/{nr_max}.js {groessen[nr_max] / 1024:.0f} KB gz", file=sys.stderr)


# ------------------------------------------------------------------------------------------ Rücktest
def abstand(k: int, von: int | None, bis: int | None) -> int:
    """Jahre zwischen Klassenspanne und Wahrheitsspanne (0 bei Überschneidung; offene Ränder offen)."""
    a, b = SPANNE[k]
    if bis is not None and a is not None and bis < a:
        return a - bis
    if von is not None and b is not None and von > b:
        return von - b
    return 0


FLUEGE = [1953, 1996, 2007, 2012, 2015, 2018, 2021, 2024]


def referenzen(cur, geb: dict) -> list[dict]:
    """Prüfgebäude mit bekannter Bauzeit (nur intern, nie veröffentlicht; Bericht nur mit Zählungen)."""
    cur.execute("""SELECT oid_bezug, min(jahr_von), max(coalesce(jahr_bis, jahr_von)) FROM auswertung.jahr_beleg
                   WHERE quelle ILIKE 'Wikipedia%%' AND art = 'bau' AND genau AND oid_bezug IS NOT NULL
                   GROUP BY oid_bezug""")
    ref = []
    for oid, von, bis in cur.fetchall():
        if oid in geb and von is not None and bis - von <= 20:
            ref.append({"oid": oid, "von": von, "bis": bis, "satz": "Wikipedia-Denkmalliste (Prüfspalte B2)"})
    if REFERENZ_B3.exists():
        with REFERENZ_B3.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if r["unklar"] == "1" or r["oid"] not in geb:
                    continue
                k = int(r["k_ref"])
                if not 0 <= k < len(FLUEGE):
                    continue
                von = None if (k == 0 or r["frueher_moeglich"] == "1") else FLUEGE[k - 1]
                ref.append({"oid": r["oid"], "von": von, "bis": FLUEGE[k],
                            "satz": "Sichtprüfung Luftbilder Bornstedt (B3-Referenz)"})
    return ref


def wahr_klasse(von, bis) -> str:
    k = klasse_von_spanne(von, bis)
    return KLASSEN[k] if k is not None else "mehrdeutig (Spanne über Klassengrenze)"


def tabelle(zeilen: list[list], kopf: list[str]) -> str:
    out = ["| " + " | ".join(kopf) + " |", "|" + "|".join("---" if i == 0 else "---:" for i in range(len(kopf))) + "|"]
    out += ["| " + " | ".join(str(z) for z in zeile) + " |" for zeile in zeilen]
    return "\n".join(out)


def quote(t: int, n: int) -> str:
    return f"{t} von {n} ({100 * t / n:.1f} %)".replace(".", ",") if n else "–"


def median(werte: list[int]) -> str:
    return f"{statistics.median(werte):g}".replace(".", ",") if werte else "–"


def auswerten_gruppe(paare: list[tuple[int | None, dict]]) -> list:
    """paare: (geschätzte Klasse oder None, Referenz)."""
    mit = [(k, r) for k, r in paare if k is not None]
    treffer = [abstand(k, r["von"], r["bis"]) == 0 for k, r in mit]
    ab = [abstand(k, r["von"], r["bis"]) for k, r in mit]
    fehl = [a for a in ab if a > 0]
    return [len(paare), len(paare) - len(mit), quote(sum(treffer), len(mit)), median(ab), median(fehl)]


def runden10(v: float) -> str:
    return f"{int(round(v / 10.0) * 10):,}".replace(",", ".")


def ruecktest() -> None:
    with verbinden() as conn, conn.cursor() as cur:
        e = kaskade(cur)
        geb, zeilen = e["geb"], e["zeilen"]
        ref = referenzen(cur, geb)
        # Zensus je Stadtteil und Klasse (100-m-Zellen mit Mittelpunkt im Stadtteil), Mikrozensus und Jahrzehnte
        cur.execute("""SELECT t.nr, z.merkmal, z.klasse, sum(z.anzahl)
                       FROM auswertung.zensus_gebaeude_jahr z
                       JOIN public.zensus_zelle c ON c.gitter_id = z.gitter_id
                       JOIN public.stadtteil t ON ST_Contains(t.geom, c.geom)
                       WHERE z.raster = '100m' GROUP BY 1, 2, 3""")
        zst = defaultdict(dict)
        for nr, merkmal, klasse, summe in cur.fetchall():
            zst[(nr, merkmal)][klasse] = int(summe)
        cur.execute("SELECT nr, name FROM public.stadtteil ORDER BY nr")
        namen = dict(cur.fetchall())
        cur.execute("""SELECT z.gitter_id, z.klasse, z.anzahl FROM auswertung.zensus_gebaeude_jahr z
                       WHERE z.raster = '100m' AND z.merkmal = 'jahrzehnte'""")
        jz = defaultdict(dict)
        for gid, klasse, anzahl in cur.fetchall():
            jz[gid][klasse] = anzahl

    L = []
    stufe = Counter(z[4] for z in zeilen.values())
    L.append("# B4: Kaskade der Gebäudejahre, Rücktest und Summenprüfung\n")
    L.append(f"Stand {date.today().isoformat()}. Erzeugt von `skripte/24_jahre_kaskade.py ruecktest`. Regeln vorab "
             "festgelegt in `pruefen/B4_protokoll.md`. Dieser Bericht enthält nur Zählungen, keine Gebäudekennungen "
             "und keine Adressen. Zensuswerte je Stadtteil sind auf 10 gerundet; sie sind durch das "
             "Geheimhaltungsverfahren (Cell-Key) verändert, Summen aus vielen Zellen sind absolut ungenauer als "
             "jede einzelne Zelle.\n")
    L.append("**Korrekturen nach Lauf 1** (Codefehler, Regeln unverändert; Lauf 1 liegt als "
             "`berichte/B4_holdout_lauf1.md` bei):\n")
    L.append("1. Die Gebietshülle der Blocktypen enthielt nicht alle Gebäude ihres Clusters (`ST_ConcaveHull` über "
             "Umrisse); jetzt Hülle vereinigt mit den Umrissen, dann 15 m Rand. Lauf 1: Am Stern 133 statt 148 "
             "Gebäude.")
    L.append("2. Die Jahrzehnte-Gegenprobe zählte „Waldstadt II“ bei „Waldstadt I“ mit (Teilwortsuche); jetzt "
             "genauer Gebietsname.\n")
    L.append("## Abdeckung der Kaskade\n")
    namen_st = {1: "1 genaues Jahr (B2, freigegeben)", 2: "2 Luftbildklammer (B3, ausgerollt)",
                3: "3 Blocktyp Großsiedlung", 4: "4 Zensus-Verteilung", 5: "5 Nachbarn", 6: "6 nicht datiert"}
    wohn = Counter(z[4] for o, z in zeilen.items() if geb[o]["wohnraum"])
    neben = Counter(z[4] for o, z in zeilen.items() if geb[o]["neben"])
    L.append(tabelle([[namen_st[s], f"{stufe[s]:,}".replace(",", "."), f"{wohn[s]:,}".replace(",", "."),
                       f"{neben[s]:,}".replace(",", ".")] for s in range(1, 7)] +
                     [["Summe", f"{len(zeilen):,}".replace(",", "."), f"{sum(wohn.values()):,}".replace(",", "."),
                       f"{sum(neben.values()):,}".replace(",", ".")]],
                     ["Stufe", "Gebäude", "davon mit Wohnraum", "davon Nebengebäude"]))
    L.append("")
    mit_jahr = sum(1 for z in zeilen.values() if z[0] is not None)
    L.append(f"- Stufe 1: {stufe[1]} Gebäude, Stufe 2: {stufe[2]} Gebäude. Stufe 1 nimmt nur Zeilen aus "
             "`auswertung.jahr_beleg` ohne `nur_pruefung` (OSM, Wikipedia und BLDAM-Liste sind Prüfwerte; DDB-API H8 "
             "und Wikidata-Export H9 fehlen, BLDAM-Lizenz offen, E8). Stufe 2 nimmt nur ausgerollte Klammern "
             f"(B3: nicht ausgerollt). Gebäude mit Einzeljahr `j`: {mit_jahr}.")
    L.append(f"- Wohngebäude in Zellen ohne Zensuswert: {e['wohn_ohne_zelle']}; Wohngebäude über der Zensuszahl ihrer "
             f"Zelle (mehr ALKIS-Umrisse als Zensus-Gebäude, auch Neubau nach dem 15.05.2022): {len(e['ueberzahl'])}. "
             "Beide gehen an Stufe 5.")
    L.append(f"- Geheimhaltungslücken der 100-m-Zellen aufgefüllt aus: {e['anteile_herkunft']} "
             "(km_rest = Rest der 1-km-Zelle, nur Zellen ganz in der Stadt; stadt_rest = Rest aller solcher "
             "1-km-Zellen; eigene_klassen = Klassen der Zelle selbst).")
    L.append(f"- Formmodell gelernt in {e['reine_zellen']} reinen Zellen (eine Klasse ≥ 85 %, keine Lücke, "
             "mindestens 4 Gebäude).\n")

    # Rücktest
    L.append("## Rücktest\n")
    L.append("Die Prüfgebäude gehen in keine Stufe ein: Wikipedia-Jahre sind nur Prüfspalte (Korrektur 5), die "
             "B3-Referenz stammt aus einer Sichtprüfung von Luftbildern. Gemessen wird die Klasse aus der Kaskade "
             "gegen die bekannte Bauzeit. **Treffer** = geschätzte Klasse überschneidet die bekannte Spanne. "
             "**Abstand** = Jahre zwischen Klassenspanne und bekannter Spanne (0 bei Treffer; „vor 1919“ und "
             "„ab 2020“ sind nach einer Seite offen).\n")
    satz_namen = sorted({r["satz"] for r in ref})
    for satz in satz_namen:
        rs = [r for r in ref if r["satz"] == satz]
        L.append(f"### {satz}: {len(rs)} Gebäude\n")
        L.append("Je Stufe:\n")
        zeilen_t = []
        for s in range(1, 7):
            paare = [(zeilen[r["oid"]][1], r) for r in rs if zeilen[r["oid"]][4] == s]
            if paare:
                zeilen_t.append([namen_st[s], *auswerten_gruppe(paare)])
        alle = [(zeilen[r["oid"]][1], r) for r in rs]
        zeilen_t.append(["alle Stufen", *auswerten_gruppe(alle)])
        L.append(tabelle(zeilen_t, ["Stufe", "n", "ohne Klasse", "Treffer", "Median Abstand (J.)",
                                    "Median Abstand der Fehlgriffe (J.)"]))
        L.append("\nJe bekannter Bauzeit (alle Stufen):\n")
        gruppen = defaultdict(list)
        for k, r in alle:
            gruppen[wahr_klasse(r["von"], r["bis"])].append((k, r))
        reihen = [g for g in KLASSEN if g in gruppen] + [g for g in gruppen if g not in KLASSEN]
        L.append(tabelle([[g, *auswerten_gruppe(gruppen[g])] for g in reihen],
                         ["bekannte Bauzeit", "n", "ohne Klasse", "Treffer", "Median Abstand (J.)",
                          "Median Abstand der Fehlgriffe (J.)"]))
        L.append("")
    # Stufe 4 frei an den Blocktyp-Gebäuden
    s3 = [o for o, z in zeilen.items() if z[4] == 3]
    paare = [(e["s4_frei"].get(o), {"von": SPANNE[zeilen[o][1]][0], "bis": SPANNE[zeilen[o][1]][1]}) for o in s3]
    L.append("### Gegenprobe: Zensus-Verteilung allein an den Blocktyp-Gebäuden\n")
    L.append("Stufe 4 ohne Vorgabe aus Stufe 3 gerechnet und gegen die Blocktyp-Klasse gestellt. Beide sind "
             "Schätzungen, das ist kein Rücktest gegen bekannte Jahre, sondern zeigt, wie weit Zensus und Blocktyp "
             "übereinstimmen.\n")
    L.append(tabelle([["Blocktyp-Gebäude", *auswerten_gruppe(paare)]],
                     ["Menge", "n", "ohne Zensusklasse", "gleiche Klasse", "Median Abstand (J.)",
                      "Median Abstand der Abweichungen (J.)"]))
    L.append("\nZum Vergleich Berlin (visinage, Methodenvorbild): 61,4 % Treffer über alle Schätzungen, Zensus "
             "46,7 %, Blocktyp 37,6 %, Nachbarn 23,8 %. Potsdam hat kein Gegenstück zur Berliner "
             "Gebäudealterskarte 1992/93 und keine ausgerollte Luftbildklammer.\n")
    L.append("**Lesart.** Die Quoten sind nicht mit Berlin vergleichbar und gelten nicht für die ganze Stadt:")
    L.append("- Die Wikipedia-Prüfgebäude sind Denkmale, fast alle vor 1919, meist in Altbau-Zellen, in denen der "
             "Zensus selbst fast nur „vor 1919“ zeigt. Dort ist die Klasse leicht zu treffen.")
    L.append("- Die Bornstedter Referenz deckt nur einen Stadtteil ab; viele ihrer Spannen liegen über einer "
             "Klassengrenze („mehrdeutig“) und zählen als Treffer, wenn eine der beiden Klassen stimmt.")
    L.append("- Für 1919 bis 1990 gibt es kaum unabhängige Prüfgebäude (1919–1948: wenige Wikipedia-Einträge, "
             "1949–1990: höchstens einzelne). Dort bleibt nur die Gegenprobe Zensus gegen Blocktyp.")
    L.append("- Das Maß selbst ist großzügiger als in Berlin: acht Mikrozensus-Klassen statt Jahrzehnten, eine davon "
             "30 Jahre breit (1949–1978), und eine Spanne über eine Klassengrenze zählt als Treffer, wenn eine der "
             "beiden Klassen stimmt. Ob Potsdam unter Berlins 61,4 % liegt (Erwartung im Bauplan), lässt sich mit "
             "diesem Maß nicht prüfen; die Quoten hier sind nicht „besser als Berlin“.")
    L.append("- Für die Seite heißt das: Jede Angabe bleibt „geschätzt“, und die Methodenseite nennt die Quoten "
             "zusammen mit n und Prüfsatz, nie als eine Zahl.\n")

    # Summenprüfung
    L.append("## Summenprüfung gegen den Zensus (Korrektur 7)\n")
    L.append("Stufe 4 verteilt die Zensuszahlen selbst; ein Vergleich der Stufe 4 mit dem Zensus prüft nichts und "
             "steht hier nur zur Information. Geprüft werden die Stufen 1 bis 3, die ohne Zensus entstehen: Je "
             "Stadtteil und Klasse darf ihre Zahl die Zensuszahl höchstens um 10 % übersteigen. Weil „–“-Werte "
             "als 0 zählen, gilt eine Überschreitung als erklärbar, wenn sie unter 110 % von Zensusklasse plus "
             "Geheimhaltungslücke des Stadtteils bleibt. Der Vergleich mit der Potsdamer Baualter-Statistik (H4) "
             "ist blockiert: Die Datei fehlt in `eingang/`.\n")
    rows, verletzt, erklaert, geprueft = [], 0, 0, 0
    for nr in sorted(namen):
        z = zst.get((nr, "mz_klassen"), {})
        if not z:
            continue
        luecke = max(0, z.get("insgesamt", 0) - sum(z.get(k, 0) for k in KLASSEN_DB))
        n13 = Counter(zl[1] for o, zl in zeilen.items() if geb[o]["nr"] == nr and zl[4] in (1, 2, 3))
        for k, n in sorted(n13.items()):
            geprueft += 1
            zk = z.get(KLASSEN_DB[k], 0)
            if n <= 1.1 * zk:
                urteil = "eingehalten"
            elif n <= 1.1 * (zk + luecke):
                urteil, erklaert = "nur mit Geheimhaltungslücke erklärbar", erklaert + 1
            else:
                urteil, verletzt = "überschritten", verletzt + 1
            rows.append([f"{nr} {namen[nr]}", KLASSEN[k], n, runden10(zk), runden10(luecke),
                         f"{100 * n / zk:.0f} %" if zk else "–", urteil])
    L.append(tabelle(rows, ["Stadtteil", "Klasse", "Stufe 1–3 (Gebäude)", "Zensus (gerundet)",
                            "Lücke Stadtteil (gerundet)", "Anteil", "Urteil"]))
    L.append(f"\nGeprüft: {geprueft} Paare aus Stadtteil und Klasse; eingehalten {geprueft - verletzt - erklaert}, "
             f"nur mit Lücke erklärbar {erklaert}, überschritten {verletzt}.\n")
    L.append("Hinweis: ALKIS zählt Umrisse, der Zensus Gebäude (ein Plattenbau-Riegel kann ein Umriss oder mehrere "
             "Gebäude sein). Eine Überschreitung kann daher auch aus der Zählweise kommen.\n")

    # Jahrzehnte in den Zellen der Blocktyp-Gebiete
    L.append("### Blocktyp-Gebiete gegen die Zensus-Jahrzehnte ihrer Zellen\n")
    L.append("Je Gebiet: Zensus-Gebäude (Jahrzehnte) in den 100-m-Zellen, in denen Blocktyp-Gebäude liegen, und "
             "der Anteil in den Jahrzehnten der belegten Bauzeit. Unabhängig von Stufe 3 (andere Datei, andere "
             "Klassengrenzen).\n")
    gebiete = json.loads(BLOCKTYPEN.read_text(encoding="utf-8"))["features"]
    jz_klassen = {"vor_1919": (None, 1918), "1919_1949": (1919, 1949), "1950_1959": (1950, 1959),
                  "1960_1969": (1960, 1969), "1970_1979": (1970, 1979), "1980_1989": (1980, 1989),
                  "1990_1999": (1990, 1999), "2000_2009": (2000, 2009), "2010_2015": (2010, 2015),
                  "ab_2016": (2016, None)}
    rows = []
    for f in gebiete:
        p = f["properties"]
        im_gebiet = [o for o, zl in zeilen.items() if zl[4] == 3 and zl[3].endswith(f"({p['gebiet']})")]
        zellen = {geb[o]["zelle"] for o in im_gebiet}
        n_geb = len(im_gebiet)
        ges = sum(jz[c].get("insgesamt", 0) for c in zellen if c in jz)
        passend = [k for k, (a, b) in jz_klassen.items()
                   if (a is None or p["bis"] >= a) and (b is None or p["von"] <= b)]
        im = sum(jz[c].get(k, 0) for c in zellen if c in jz for k in passend)
        rows.append([p["gebiet"], f"{p['von']}–{p['bis']}", p["klasse"], n_geb, len(zellen), runden10(ges),
                     ", ".join(k.replace("_", "–") for k in passend), f"{100 * im / ges:.0f} %" if ges else "–",
                     f"{p['flaeche_ha_polygon']:g}".replace(".", ","),
                     f"{p['flaeche_ha_beleg']:g}".replace(".", ",") if p["flaeche_ha_beleg"] else "–"])
    L.append(tabelle(rows, ["Gebiet", "Bauzeit (Beleg)", "Klasse", "Blocktyp-Gebäude", "Zellen",
                            "Zensus-Gebäude (gerundet)", "Jahrzehnte der Bauzeit", "Anteil darin",
                            "Fläche Polygon (ha)", "Fläche Beleg (ha)"]))
    L.append("\nDie Polygonfläche umfasst nur die Cluster der Bauform, die Belegfläche das ganze Neubaugebiet.\n")

    # Stufe 4 zur Information
    L.append("### Kaskade gesamt gegen den Zensus, Stadt (Gebäude mit Wohnraum)\n")
    L.append("Stufe 4 trifft die Zensuszahlen je Zelle nach Bauart, das ist für sie keine Prüfung. Die Summe über alle "
             "Stufen weicht trotzdem ab, aus zwei Gründen: Stufe 5 (Nachbarn) datiert Wohngebäude über der Zensuszahl "
             "ihrer Zelle, vor allem in der Altstadt, wo ein Block in viele ALKIS-Umrisse zerfällt; und ein "
             "Plattenbau-Riegel ist oft ein Umriss, aber mehrere Zensus-Gebäude, das verkleinert die Zahl der zu "
             "verteilenden Plätze. Folge für die Karte: Bauten vor 1919 erscheinen häufiger, DDR-Bauten seltener als "
             "im Zensus.\n")
    zs = Counter()
    for (nr, merkmal), z in zst.items():
        if merkmal == "mz_klassen":
            for k in KLASSEN_DB:
                zs[k] += z.get(k, 0)
    alle_k = Counter(zl[1] for o, zl in zeilen.items() if zl[1] is not None and geb[o]["wohnraum"])
    je_stufe = {st: Counter(zl[1] for o, zl in zeilen.items() if zl[4] == st and geb[o]["wohnraum"]) for st in (3, 4, 5)}

    def zahl(v: int) -> str:
        return f"{v:,}".replace(",", ".")

    L.append(tabelle([[KLASSEN[i], runden10(zs[KLASSEN_DB[i]]), zahl(alle_k[i]),
                       f"{100 * (alle_k[i] - zs[KLASSEN_DB[i]]) / zs[KLASSEN_DB[i]]:+.0f} %" if zs[KLASSEN_DB[i]] else "–",
                       zahl(je_stufe[3][i]), zahl(je_stufe[4][i]), zahl(je_stufe[5][i])] for i in range(8)],
                     ["Klasse", "Zensus (gerundet)", "Kaskade gesamt", "Abweichung", "davon Stufe 3", "Stufe 4",
                      "Stufe 5"]))
    L.append("")
    BERICHT.parent.mkdir(parents=True, exist_ok=True)
    BERICHT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"geschrieben: {BERICHT.relative_to(WURZEL)} ({len(ref)} Prüfgebäude)", file=sys.stderr)


if __name__ == "__main__":
    befehl = sys.argv[1] if len(sys.argv) > 1 else ""
    if befehl == "blocktypen":
        blocktypen_ziehen()
    elif befehl == "rechnen":
        rechnen()
    elif befehl == "ruecktest":
        ruecktest()
    else:
        sys.exit("Aufruf: 24_jahre_kaskade.py blocktypen | rechnen | ruecktest")
