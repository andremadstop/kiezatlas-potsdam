"""Erzeugt daten/fixtures/*.js: kleine Beispieldateien nach den Verträgen in daten/schema/.

Die Werte sind ausdrücklich unecht (fixture: true, Namen mit „Beispiel“, glatte Muster), damit
Seiten (A7 planer.html, B5 jahre.html) gebaut werden können, bevor die echten Daten aus A6, B1
und B4 da sind. Werte in Zellreihenfolge haben dieselbe Länge wie daten/zellen.js, damit die
Seiten sie gegen die echten Zellen legen können. Kein Netz, keine Datenbank.

Aufruf: python -I pruefen/fixtures_erzeugen.py   (danach pruefen/daten.py)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "daten"
AUS = DATEN / "fixtures"
STAND = "2026-11-05"
DLDE = "https://www.govdata.de/dl-de/by-2-0"
ODBL_KOPF = ("/* Beispieldaten (Fixture). Echte Dateien dieser Art stehen unter der Open Database License 1.0 "
             "(https://opendatacommons.org/licenses/odbl/1-0/), © OpenStreetMap-Mitwirkende. ODbL */\n")
HINWEIS = "Beispieldaten mit unechten Werten, nur zum Bauen der Seiten."


def lies(name: str):
    """Wie js_lesen in pruefen/daten.py: Kommentar vor window.NAME= ist erlaubt."""
    text = (DATEN / name).read_text(encoding="utf-8")
    m = re.search(r"window\.[A-Za-z0-9_]+\s*=\s*", text)
    return json.loads(text[m.end():].rstrip().rstrip(";"))


def schreib(rel: str, variable: str, inhalt, kopf: str = "") -> None:
    p = AUS / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(kopf + f"window.{variable}=" + json.dumps(inhalt, ensure_ascii=False, separators=(",", ":")) + ";\n",
                 encoding="utf-8")
    print(f"{p.relative_to(WURZEL)}  {p.stat().st_size // 1024} KB")


def q(quelle: str, lizenz: str, vermerk: str) -> dict:
    return {"quelle": quelle, "lizenz": lizenz, "vermerk": vermerk}


Q_BEISPIEL = q("Beispielquelle (unecht)", "dl-de/by-2-0",
               f"© Beispielanbieter, dl-de/by-2-0 ({DLDE}), Daten verändert (eigene Berechnung)")
Q_OSM = q("OpenStreetMap (Beispiel)", "ODbL 1.0", "© OpenStreetMap-Mitwirkende, ODbL 1.0")


def main() -> None:
    zellen = lies("zellen.js")["features"]
    ids = [f["properties"]["id"] for f in zellen]
    n = len(ids)
    reihe = {"anzahl": n, "erste_id": ids[0], "letzte_id": ids[-1], "schluessel": "zellen.js-Reihenfolge"}
    arten = ["kita", "hort", "grundschule", "gruen"]

    def muster(i: int, k: int, s: int) -> int | None:
        ew = zellen[i]["properties"]["ew"]
        return None if not ew else (i * 37 + k * 211) % s + 50

    schreib("erreichbar.js", "KIEZ_ERREICHBAR", {
        "fixture": True, "stand": STAND, "hinweis": HINWEIS, "methode": "luftlinie", "einheit": "m",
        "quellen": {"bsp": Q_BEISPIEL}, "arten": arten, **reihe,
        "werte": {a: [muster(i, k, 1500) for i in range(n)] for k, a in enumerate(arten)}})
    schreib("erreichbar_fuss_odbl.js", "KIEZ_ERREICHBAR_FUSS", {
        "fixture": True, "stand": STAND, "hinweis": HINWEIS, "methode": "fussweg", "einheit": "min",
        "quellen": {"osm": Q_OSM}, "arten": arten, **reihe,
        "werte": {a: [None if muster(i, k, 30) is None else (muster(i, k, 30) - 49) for i in range(n)]
                  for k, a in enumerate(arten)}}, ODBL_KOPF)

    # Einrichtungen: ein Raster aus Beispielpunkten um die Potsdamer Mitte, klar benannt
    punkte = [(13.03 + 0.02 * (i % 6), 52.37 + 0.015 * (i // 6)) for i in range(24)]
    amtlich = ["kita", "hort", "grundschule", "gymnasium"]
    schreib("einrichtungen.js", "KIEZ_EINRICHTUNGEN", {
        "fixture": True, "type": "FeatureCollection", "stand": STAND, "hinweis": HINWEIS, "quellen": {"bsp": Q_BEISPIEL},
        "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(x, 5), round(y, 5)]},
                      "properties": {"id": f"bsp-{i}", "art": amtlich[i % 4], "unterart": None,
                                     "name": f"Beispiel-Einrichtung {i} (unecht)",
                                     "plaetze": 111 if amtlich[i % 4] in ("kita", "hort") else None,
                                     "schueler": 222 if amtlich[i % 4] in ("grundschule", "gymnasium") else None,
                                     "schueler_stand": "Beispiel" if amtlich[i % 4] in ("grundschule", "gymnasium") else None,
                                     "status": "kapazitaet", "in_potsdam": i % 7 != 0, "q": "bsp"}}
                     for i, (x, y) in enumerate(punkte)]})
    osm = ["arzt", "apotheke", "supermarkt", "pflege", "spielplatz"]
    schreib("einrichtungen_odbl.js", "KIEZ_EINRICHTUNGEN_ODBL", {
        "fixture": True, "type": "FeatureCollection", "stand": STAND, "hinweis": HINWEIS, "quellen": {"osm": Q_OSM},
        "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(x + 0.007, 5), round(y + 0.004, 5)]},
                      "properties": {"id": f"bsp-osm-{i}", "art": osm[i % 5], "unterart": None, "q": "osm"}}
                     for i, (x, y) in enumerate(punkte)]}, ODBL_KOPF)

    teile = lies("kennzahlen.js")["stadtteile"]

    def raeume(methode: str) -> dict:
        aus = {}
        for j, (nr, t) in enumerate(sorted(teile.items())[:6]):
            werte = [
                {"kennzahl": "anteil_in_radius", "art": "kita", "zielgruppe": "Kinder unter 6", "wert": 50 + j,
                 "einheit": "%", "methode": methode, "status": "orientierung",
                 "richtwert": {"wert": 500, "einheit": "m", "q": "bsp"}, "q": "bsp", "stand": "Beispiel",
                 "unsicherheit": "Beispielwert"},
                {"kennzahl": "anteil_in_radius", "art": "grundschule", "zielgruppe": "Kinder 6 bis 9", "wert": 60 + j,
                 "einheit": "%", "methode": methode, "status": "amtlich", "vorlaeufig": True,
                 "richtwert": {"wert": 2000, "einheit": "m", "q": "bsp", "seite": "Beispiel"}, "q": "bsp",
                 "stand": "Beispiel", "unsicherheit": "Beispielwert"}]
            # Zähler und Nenner (Audit K14): glatte Beispielzahlen, die zum Wert passen
            werte[0].update({"zaehler": 50 + j, "nenner": 100, "zaehler_text": "Beispielkinder im Radius",
                             "nenner_text": "Beispielkinder"})
            if methode == "luftlinie":
                werte.append({"kennzahl": "plaetze_je_kind", "art": "kita", "zielgruppe": "Kinder unter 6",
                              "wert": 0.5 + j / 100, "einheit": "Plätze je Kind", "methode": methode,
                              "status": "amtlich", "q": "bsp", "stand": "Beispiel", "unsicherheit": "Beispielwert",
                              "zaehler": 50 + j, "nenner": 100, "zaehler_text": "Beispielplätze",
                              "nenner_text": "Beispielkinder"})
            aus[nr] = {"name": f"{t['name']} (Beispiel)", "ew": 1000 * (j + 1), "werte": werte}
        return aus

    def gesamt(raeume_: dict) -> dict:
        """Ganz Potsdam (Audit K24) als Summe der Beispiel-Zähler und -Nenner."""
        werte = []
        for w in next(iter(raeume_.values()))["werte"]:
            g = {k: v for k, v in w.items() if k not in ("wert", "zaehler", "nenner")}
            if "zaehler" in w:
                z = sum(x["zaehler"] for r in raeume_.values() for x in r["werte"] if (x["kennzahl"], x["art"]) == (w["kennzahl"], w["art"]))
                n = sum(x["nenner"] for r in raeume_.values() for x in r["werte"] if (x["kennzahl"], x["art"]) == (w["kennzahl"], w["art"]))
                g.update({"zaehler": z, "nenner": n, "wert": round(z / n, 2) if w["einheit"] != "%" else round(100 * z / n)})
            else:
                g["wert"] = None
            werte.append(g)
        return {"name": "Potsdam", "ew": sum(r["ew"] for r in raeume_.values()), "werte": werte}

    kopf = {"fixture": True, "stand": STAND, "raumebene": "stadtteil", "rundung": {"ew": 10},
            "hinweis": HINWEIS + " Zensus-Stichtag 15.05.2022; Neubaugebiete danach fehlen."}
    rl, rf = raeume("luftlinie"), raeume("fussweg")
    schreib("planer.js", "KIEZ_PLANER", {**kopf, "quellen": {"bsp": Q_BEISPIEL}, "raeume": rl, "gesamt": gesamt(rl)})
    schreib("planer_fuss_odbl.js", "KIEZ_PLANER_FUSS", {**kopf, "quellen": {"bsp": Q_BEISPIEL, "osm": Q_OSM},
                                                        "raeume": rf, "gesamt": gesamt(rf)}, ODBL_KOPF)

    klassen = ["vor 1919", "1919–1948", "1949–1978", "1979–1990", "1991–2000", "2001–2010", "2011–2019", "ab 2020"]
    geb = [None if not zellen[i]["properties"]["ew"] else (i % 9) + 1 for i in range(n)]
    anteile = [None if g is None else [round(100 * ((i + k) % 3) / 3, 1) for k in range(8)] for i, g in enumerate(geb)]
    schreib("jahre_zellen.js", "KIEZ_JAHRE_ZELLEN", {
        "fixture": True, "stand": STAND, "hinweis": HINWEIS, "merkmal": "mz_klassen",
        "beschriftung": "Gebäude mit Wohnraum je Zelle, nicht einzelne Gebäude", "klassen": klassen,
        "quellen": {"bsp": Q_BEISPIEL}, **reihe, "gebaeude": geb, "anteile": anteile,
        "vorherrschend": [None if a is None else a.index(max(a)) for a in anteile]})

    # Synthetische Quadrate (rund 15 m) im Raster um den Beschriftungspunkt von Stadtteil 52, keine
    # echten Gebäudeumrisse: erfundene Jahre an echten Gebäuden wären genau die Fehldeutung, die die
    # Klassenregel für kleine Wohngebäude verhindern soll.
    t52 = next(f for f in lies("stadtteile.js")["features"] if f["properties"]["nr"] == "52")["properties"]
    g52 = []
    for i in range(40):
        x, y = t52["lx"] + 0.0004 * (i % 8), t52["ly"] + 0.0003 * (i // 8)
        ring = [[round(x, 6), round(y, 6)], [round(x + 0.0002, 6), round(y, 6)], [round(x + 0.0002, 6), round(y + 0.00014, 6)],
                [round(x, 6), round(y + 0.00014, 6)], [round(x, 6), round(y, 6)]]
        g52.append({"geometry": {"type": "Polygon", "coordinates": [ring]}})
    arten_g = ["belegt", "geschaetzt", "nicht_datiert"]
    grenzen = [1919, 1949, 1979, 1991, 2001, 2011, 2020]   # Beginn der Klassen 2 bis 8

    def jahr(i: int) -> int:
        return 1880 + (i * 37) % 145                       # 1880 bis 2024, über alle Klassen verteilt

    def klasse_von(j: int) -> int:
        return sum(1 for g in grenzen if j >= g)
    schreib("jahre/52.js", "KIEZ_JAHR_52", {
        "fixture": True, "type": "FeatureCollection", "stand": STAND, "klassen": klassen,
        "hinweis": HINWEIS + " Schätzung, keine Aussage über einzelne Grundstücke.",
        "quellen": {"bsp": Q_BEISPIEL},
        "features": [{"type": "Feature", "geometry": f["geometry"], "properties": {
            "j": jahr(i) if arten_g[i % 3] == "belegt" else None,
            "k": None if arten_g[i % 3] == "nicht_datiert" else klasse_von(jahr(i)), "g": arten_g[i % 3], "d": i % 3 == 0,
            "q": None if arten_g[i % 3] == "nicht_datiert" else "bsp", "s": [1, 4, 6][i % 3], "h": 3 + (i * 7) % 30, "hq": ["kataster", "geschosse", "ersatz"][i % 3]}}
            for i, f in enumerate(g52)]})


if __name__ == "__main__":
    main()
