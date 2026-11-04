"""Auswertung des Kiezatlas Potsdam in PostGIS und Ausgabe für index.html.

Liest, was die Geodaten-Import-Pipeline in die Datenbank geladen hat (Stadtteile, Zensus-Gitter,
ALKIS-Gebäude), ordnet Zellen und Gebäude den Stadtteilen zu und rechnet die Kennzahlen je
Stadtteil und für die ganze Stadt in SQL. Läuft mit der Leserolle (nur SELECT).

Ausgang: daten/stadtteile.js, daten/zellen.js, daten/kennzahlen.js (+ .json),
         daten/gebaeude/<nr>.js (Gebäude je Stadtteil, werden in der Seite erst bei Auswahl geladen)
Aufruf:  skripte/lauf.sh (oder mit PG*-Umgebung: python skripte/02_auswerten.py)
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import psycopg

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "daten"

ZAEHL = ["ew", "a_ges", "a_u18", "a_18_29", "a_30_49", "a_50_64", "a_65p",
         "h_ges", "h_fern", "h_etage", "h_block", "h_zentral", "h_oefen", "h_keine",
         "e_ges", "e_gas", "e_oel", "e_holz", "e_bio", "e_wp", "e_strom", "e_kohle", "e_fern", "e_kein",
         "w_ges", "w_v1919", "w_1919_48", "w_1949_78", "w_1979_90", "w_1991_00", "w_2001_13",
         "w_2014_19", "w_2020p"]
# Gegenproben aus amtlichen Veröffentlichungen, von Hand übernommen (keine Rechengrößen; anderer
# Stichtag und andere Zählweise als der Zensus, kleine Unterschiede sind zu erwarten)
GEGENPROBE = {
    "stadt": {"einwohner": 185137, "stichtag": "31.12.2025", "art": "Bevölkerungsstand (Fortschreibung)",
              "quelle": "Statistische Ämter des Bundes und der Länder, Regionaldatenbank, Tabelle 12411-01-01-5-B, Potsdam (12054000)",
              "url": "https://www.regionalstatistik.de/genesis/online?operation=table&code=12411-01-01-5-B"},
    "32": {"einwohner": 8221, "stichtag": "31.12.2022", "art": "Einwohner mit Hauptwohnung (Melderegister)",
           "quelle": "Landeshauptstadt Potsdam, Statistischer Informationsdienst 1/2023, Stadtteile im Blick 2022, S. 26",
           "url": "https://www.potsdam.de/system/files/document/Statistischer_Infodienst_1_2023_Stadtteile_im_Blick_2022_online.pdf"},
}
ZENSUS_Q = ("Zensus 2022, Stichtag 15.05.2022, 100-m-Gitter; © Statistische Ämter des Bundes und der "
            "Länder, {jahr}, dl-de/by-2-0; eigene Auswertung")


def js_datei(pfad: Path, variable: str, inhalt) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(inhalt, ensure_ascii=False, separators=(",", ":"))
    pfad.write_text(f"window.{variable}={text};\n", encoding="utf-8")


def anteil(t, g):
    return round(100 * t / g, 1) if g else None


def kennzahlen(s: dict, gebaeude: dict) -> dict:
    """Kacheln und Verteilungen aus den Summen eines Gebiets (Stadtteil oder Stadt)."""
    def v(k):
        return int(s.get(k) or 0)
    return {
        "zellen": v("zellen"),
        "kacheln": [
            {"id": "einwohner", "titel": "Einwohnerinnen und Einwohner", "wert": v("ew"), "einheit": "Personen",
             "anzeige": "summe", "quelle": ZENSUS_Q.format(jahr=2024) + " (Bevölkerungszahl)"},
            {"id": "u18", "titel": "unter 18 Jahre", "wert": anteil(v("a_u18"), v("a_ges")), "einheit": "%",
             "anzeige": "anteil", "zaehler": v("a_u18"), "nenner": v("a_ges"),
             "quelle": ZENSUS_Q.format(jahr=2025) + " (Alter in 5 Altersklassen)"},
            {"id": "65p", "titel": "65 Jahre und älter", "wert": anteil(v("a_65p"), v("a_ges")), "einheit": "%",
             "anzeige": "anteil", "zaehler": v("a_65p"), "nenner": v("a_ges"),
             "quelle": ZENSUS_Q.format(jahr=2025) + " (Alter in 5 Altersklassen)"},
            {"id": "altbau", "titel": "Wohnungen in Gebäuden von vor 1949",
             "wert": anteil(v("w_v1919") + v("w_1919_48"), v("w_ges")), "einheit": "%", "anzeige": "anteil",
             "zaehler": v("w_v1919") + v("w_1919_48"), "nenner": v("w_ges"),
             "quelle": ZENSUS_Q.format(jahr=2025) + " (Wohnungen nach modifizierten Mikrozensus-Baujahresklassen)"},
            {"id": "fernwaerme", "titel": "Wohnungen mit Fernwärme", "wert": anteil(v("e_fern"), v("e_ges")),
             "einheit": "%", "anzeige": "anteil", "zaehler": v("e_fern"), "nenner": v("e_ges"),
             "quelle": ZENSUS_Q.format(jahr=2024) + " (Energieträger der Heizung)"},
        ],
        "verteilungen": {
            "alter": {"quelle": ZENSUS_Q.format(jahr=2025) + " (Alter in 5 Altersklassen)", "einheit": "Personen",
                      "insgesamt": v("a_ges"),
                      "werte": [["unter 18", v("a_u18")], ["18–29", v("a_18_29")], ["30–49", v("a_30_49")],
                                ["50–64", v("a_50_64")], ["65 und älter", v("a_65p")]]},
            "baujahr": {"quelle": ZENSUS_Q.format(jahr=2025) + " (Wohnungen nach modifizierten Mikrozensus-Baujahresklassen)",
                        "einheit": "Wohnungen", "insgesamt": v("w_ges"),
                        "werte": [["vor 1919", v("w_v1919")], ["1919–1948", v("w_1919_48")],
                                  ["1949–1978", v("w_1949_78")], ["1979–1990", v("w_1979_90")],
                                  ["1991–2000", v("w_1991_00")], ["2001–2013", v("w_2001_13")],
                                  ["2014–2019", v("w_2014_19")], ["2020–2022", v("w_2020p")]]},
            "heizung": {"quelle": ZENSUS_Q.format(jahr=2024) + " (Überwiegende Heizungsart)", "einheit": "Wohnungen",
                        "insgesamt": v("h_ges"),
                        "werte": [["Fernheizung", v("h_fern")], ["Zentralheizung", v("h_zentral")],
                                  ["Etagenheizung", v("h_etage")], ["Blockheizung", v("h_block")],
                                  ["Einzel- oder Mehrraumöfen", v("h_oefen")], ["keine Heizung", v("h_keine")]]},
            "energie": {"quelle": ZENSUS_Q.format(jahr=2024) + " (Energieträger der Heizung)", "einheit": "Wohnungen",
                        "insgesamt": v("e_ges"),
                        "werte": [["Fernwärme", v("e_fern")], ["Gas", v("e_gas")], ["Heizöl", v("e_oel")],
                                  ["Wärmepumpe, Solar, Geothermie", v("e_wp")], ["Holz, Pellets", v("e_holz")],
                                  ["Strom", v("e_strom")], ["Biomasse, Biogas", v("e_bio")], ["Kohle", v("e_kohle")],
                                  ["kein Energieträger", v("e_kein")]]},
        },
        "gebaeude": gebaeude,
    }


def main() -> None:
    DATEN.mkdir(exist_ok=True)
    summen = ", ".join(f"sum(z.{k}) AS {k}" for k in ZAEHL)
    with psycopg.connect("") as conn, conn.cursor() as cur:
        # Stadtteile mit Fläche (Ellipsoid) und Beschriftungspunkt
        cur.execute("""SELECT nr, name, round((ST_Area(geom::geography) / 1e6)::numeric, 2),
                              ST_AsGeoJSON(geom, 6), ST_X(ST_PointOnSurface(geom)), ST_Y(ST_PointOnSurface(geom))
                       FROM stadtteil ORDER BY nr::int""")
        teile = [{"nr": r[0], "name": r[1], "flaeche_km2": float(r[2]), "geom": json.loads(r[3]),
                  "punkt": [round(r[4], 5), round(r[5], 5)]} for r in cur.fetchall()]
        js_datei(DATEN / "stadtteile.js", "KIEZ_STADTTEILE", {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": t["geom"],
             "properties": {"nr": t["nr"], "name": t["name"], "flaeche_km2": t["flaeche_km2"],
                            "bezirk": int(t["nr"]) // 10, "lx": t["punkt"][0], "ly": t["punkt"][1]}}
            for t in teile]})

        # Zellen: Mittelpunkt im Stadtteil; Quadrat aus dem Mittelpunkt in EPSG:3035
        cur.execute("""SELECT z.gitter_id, s.nr, z.ew, z.a_ges, z.a_u18, z.a_65p, z.d_alter, z.w_ges,
                              z.w_v1919 + z.w_1919_48, z.e_ges, z.e_fern,
                              ST_AsGeoJSON(ST_Transform(ST_Expand(ST_Transform(z.geom, 3035), 50), 4326), 6)
                       FROM zensus_zelle z JOIN stadtteil s ON ST_Contains(s.geom, z.geom)
                       ORDER BY z.gitter_id""")
        feats = []
        for gid, nr, ew, a_ges, u18, a65, dalter, w_ges, alt, e_ges, fern, geom in cur.fetchall():
            feats.append({"type": "Feature", "geometry": json.loads(geom), "properties": {
                "id": gid, "st": nr, "ew": ew, "d_alter": float(dalter) if dalter is not None else None,
                "q_u18": anteil(u18, a_ges), "q_65p": anteil(a65, a_ges),
                "q_v1949": anteil(alt, w_ges), "q_fern": anteil(fern, e_ges), "w_ges": w_ges, "a_ges": a_ges}})
        js_datei(DATEN / "zellen.js", "KIEZ_ZELLEN", {"type": "FeatureCollection", "features": feats})

        # Summen je Stadtteil und für die Stadt (Zellen nur einmal: jede liegt in höchstens einem Teil)
        cur.execute(f"""SELECT s.nr, count(*) AS zellen, {summen}
                        FROM zensus_zelle z JOIN stadtteil s ON ST_Contains(s.geom, z.geom) GROUP BY s.nr""")
        spalten = [d.name for d in cur.description]
        je_teil = {r[0]: dict(zip(spalten, r, strict=True)) for r in cur.fetchall()}
        stadt = {k: sum(int(t.get(k) or 0) for t in je_teil.values()) for k in ["zellen", *ZAEHL]}

        # Gebäude je Stadtteil (Lage über einen Punkt im Umriss)
        cur.execute("""SELECT s.nr, count(*), count(*) FILTER (WHERE g.funktion ILIKE 'Wohn%%'),
                              round(avg(g.anzahlgs)::numeric, 1)
                       FROM gebaeude g JOIN stadtteil s ON ST_Contains(s.geom, ST_PointOnSurface(g.geom))
                       GROUP BY s.nr""")
        geb = {r[0]: {"anzahl": r[1], "wohngebaeude": r[2],
                      "geschosse_mittel": float(r[3]) if r[3] is not None else None} for r in cur.fetchall()}
        cur.execute("SELECT count(*) FROM gebaeude")
        geb_gesamt_rechteck = cur.fetchone()[0]

        for t in teile:
            cur.execute("""SELECT ST_AsGeoJSON(ST_SimplifyPreserveTopology(g.geom, 0.000005), 6),
                                  g.funktion, g.anzahlgs
                           FROM gebaeude g JOIN stadtteil s ON s.nr = %s
                                AND ST_Contains(s.geom, ST_PointOnSurface(g.geom))""", (t["nr"],))
            js_datei(DATEN / "gebaeude" / f"{t['nr']}.js", "KIEZ_GEB_" + t["nr"], {"type": "FeatureCollection",
                     "features": [{"type": "Feature", "geometry": json.loads(gj),
                                   "properties": {"f": f or "", "gs": gs, "h": round((gs or 1) * 3.0, 1)}}
                                  for gj, f, gs in cur.fetchall()]})

        # Grenzfall: Zuordnung nach Mittelpunkt (Methode der Seite) gegen flächenanteilig.
        # Gerechnet in EPSG:3035, dem Bezugssystem des Gitters, damit die Zellen echte 100-m-Quadrate sind.
        cur.execute("""WITH z AS (SELECT ew, ST_Expand(ST_Transform(geom, 3035), 50) AS q,
                                         ST_Transform(geom, 3035) AS m FROM zensus_zelle WHERE ew > 0),
                            t AS (SELECT nr, ST_Transform(geom, 3035) AS g FROM stadtteil)
                       SELECT t.nr, coalesce(sum(z.ew) FILTER (WHERE ST_Contains(t.g, z.m)), 0),
                              sum(z.ew * ST_Area(ST_Intersection(z.q, t.g)) / 10000.0),
                              count(*) FILTER (WHERE NOT ST_Within(z.q, t.g))
                       FROM t JOIN z ON ST_Intersects(z.q, t.g) GROUP BY t.nr""")
        grenzfall = {r[0]: {"mittelpunkt": int(r[1]), "flaechenanteilig": round(float(r[2])),
                            "grenzzellen": int(r[3])} for r in cur.fetchall()}
        cur.execute("""WITH stadt AS (SELECT ST_Transform(ST_Union(geom), 3035) AS g FROM stadtteil),
                            z AS (SELECT ew, ST_Expand(ST_Transform(geom, 3035), 50) AS q,
                                         ST_Transform(geom, 3035) AS m FROM zensus_zelle WHERE ew > 0)
                       SELECT sum(ew) FILTER (WHERE ST_Contains(s.g, m)),
                              round(sum(ew * ST_Area(ST_Intersection(q, s.g)) / 10000.0)),
                              count(*) FILTER (WHERE NOT ST_Within(q, s.g)),
                              sum(ew) FILTER (WHERE NOT ST_Within(q, s.g)),
                              count(*) FILTER (WHERE NOT ST_Contains(s.g, m)),
                              sum(ew) FILTER (WHERE NOT ST_Contains(s.g, m))
                       FROM z, stadt s WHERE ST_Intersects(q, s.g)""")
        r = cur.fetchone()
        grenzfall_stadt = {"mittelpunkt": int(r[0]), "flaechenanteilig": int(r[1]), "grenzzellen": int(r[2]),
                           "ew_in_grenzzellen": int(r[3]), "mittelpunkt_aussen_zellen": int(r[4]),
                           "mittelpunkt_aussen_ew": int(r[5])}

        cur.execute("SELECT max(letzter_erfolg) FROM pipeline_meta.quellenstand")
        stand_import = cur.fetchone()[0]

    geb_stadt = {"anzahl": sum(g["anzahl"] for g in geb.values()),
                 "wohngebaeude": sum(g["wohngebaeude"] for g in geb.values())}
    ausgabe = {
        "stand_auswertung": date.today().isoformat(),
        "stand_import": stand_import.isoformat(timespec="minutes") if stand_import else None,
        "methode_zellen": "Zensus-Gitterzellen, deren Mittelpunkt im Stadtteil liegt (ST_Contains in PostGIS)",
        "stadt": {"name": "Potsdam", "flaeche_km2": round(sum(t["flaeche_km2"] for t in teile), 1),
                  **kennzahlen(stadt, geb_stadt)},
        "stadtteile": {t["nr"]: {"name": t["name"], "flaeche_km2": t["flaeche_km2"],
                                 **kennzahlen(je_teil.get(t["nr"], {}), geb.get(t["nr"], {}))} for t in teile},
        "gegenprobe": GEGENPROBE,
        "grenzfall": {"stadt": grenzfall_stadt, "stadtteile": grenzfall,
                      "methode": "Mittelpunkt im Stadtteil (verwendet) gegen Einwohner nach Flächenanteil der Zelle; "
                                 "gerechnet in PostGIS in EPSG:3035"},
        "kontrolle": {"zellen_im_rechteck": None, "gebaeude_im_rechteck": geb_gesamt_rechteck,
                      "gebaeude_in_potsdam": geb_stadt["anzahl"]},
    }
    (DATEN / "kennzahlen.json").write_text(json.dumps(ausgabe, ensure_ascii=False, indent=1), encoding="utf-8")
    js_datei(DATEN / "kennzahlen.js", "KIEZ_KENNZAHLEN", ausgabe)
    k = ausgabe["stadt"]
    print(f"Potsdam: {k['kacheln'][0]['wert']} Einwohner in {k['zellen']} Zellen, "
          f"{geb_stadt['anzahl']} Gebäude ({geb_gesamt_rechteck} im Rechteck)", file=sys.stderr)
    for nr, t in ausgabe["stadtteile"].items():
        print(f"  {nr} {t['name']}: {t['kacheln'][0]['wert']} EW, {t['zellen']} Zellen, "
              f"{t['gebaeude'].get('anzahl', 0)} Gebäude", file=sys.stderr)


if __name__ == "__main__":
    main()
