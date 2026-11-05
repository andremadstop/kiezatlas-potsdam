"""Abnahme Paket A6: Versorgungsaussagen und Datendateien (Kiezatlas Potsdam, Ausbau).

Liest daten/*.js, config/richtwerte.yaml und (Leserolle mosidi_lesen, nur SELECT) die Datenbank. Rechnet
Stichproben auf einem zweiten Weg nach: ganz in SQL statt über skripte/15_planer.py. Kein Netz, kein Schreiben.

Aufruf wie skripte/15_planer.py, mit pruefen/A6_planer.py. Rückgabe 0 = alle Kriterien erfüllt.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "daten"
DLDE = "https://www.govdata.de/dl-de/by-2-0"
VERAENDERT = "Daten verändert (eigene Berechnung)"
OSM_SPUR = re.compile(r"OpenStreetMap|\bODbL\b|\"methode\":\s*\"fussweg\"|\"osm_id\"|\"q\":\"osm\"")
NUR_LAGE = {"arzt", "apotheke", "pflege", "supermarkt", "spielplatz"}
FEINE_ZIELGRUPPEN = ("Kinder", "rechnerischer Bedarf")
befunde: list[str] = []
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("daten_pruefen", WURZEL / "pruefen" / "daten.py")
DATEN_PRUEFEN = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(DATEN_PRUEFEN)
_spec = importlib.util.spec_from_file_location("planer15", WURZEL / "skripte" / "15_planer.py")
PLANER = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PLANER)
H1_DATEI = "planungsraume-in-potsdam.geojson"


def im_ring(x: float, y: float, ring: list) -> bool:
    """Strahlverfahren (gerade-ungerade) für einen Ring aus [lon, lat]-Paaren."""
    drin = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            drin = not drin
    return drin


def in_flaeche(x: float, y: float, geom: dict) -> bool:
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    # gerade-ungerade über alle Ringe eines Polygons: Löcher heben sich auf
    return any(sum(im_ring(x, y, [c[:2] for c in ring]) for ring in poly) % 2 == 1 for poly in polys)


def pruef(ok: bool, text: str) -> bool:
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        befunde.append(text)
    return ok


def js(name: str):
    """Datei lesen wie pruefen/daten.py (js_lesen); fehlt sie, (None, "")."""
    p = DATEN / name
    if not p.exists():
        return None, ""
    t = p.read_text(encoding="utf-8")
    return DATEN_PRUEFEN.js_lesen(p, t)[2], t


def werte(P):
    for nr, r in P["raeume"].items():
        for w in r["werte"]:
            yield nr, r, w


def main() -> int:
    import psycopg
    import yaml

    rw = yaml.safe_load((WURZEL / "config" / "richtwerte.yaml").read_text(encoding="utf-8"))
    P, tp = js("planer.js")
    E, te = js("erreichbar.js")
    N, tn = js("einrichtungen.js")
    PF, _ = js("planer_fuss_odbl.js")
    con = psycopg.connect()
    con.read_only = True
    cur = con.cursor()

    print("A6-1 pruefen/daten.py gegen die Verträge (planer.json, erreichbar.json, einrichtungen.json)")
    lauf = subprocess.run([sys.executable, "-I", str(WURZEL / "pruefen" / "daten.py")], capture_output=True, text=True)
    letzte = lauf.stdout.strip().splitlines()[-1] if lauf.stdout.strip() else lauf.stderr[-200:]
    pruef(lauf.returncode == 0 and P is not None and E is not None and N is not None, f"daten.py: {letzte}")

    print("A6-2 keine feine Altersklasse je gitter_id in daten/")
    zell_ids = {
        n: len(re.findall(r"CRS3035RES100m", t))
        for n, t in (("planer.js", tp), ("erreichbar.js", te), ("einrichtungen.js", tn))
    }
    pruef(
        zell_ids == {"planer.js": 0, "erreichbar.js": 2, "einrichtungen.js": 0},
        f"Zellkennungen nur als erste_id/letzte_id in erreichbar.js: {zell_ids}",
    )
    zg_felder = {f for z in rw["planer"]["zielgruppen"].values() for f in (z["felder"] or [])}
    treffer = sorted({f for f in zg_felder for p in DATEN.glob("*.js") if f'"{f}"' in p.read_text(encoding="utf-8")})
    pruef(not treffer, f"keine Zensus-Feldnamen der Zielgruppen in daten/*.js ({treffer or 'keine'})")
    pruef(set(E["werte"]) == set(E["arten"]), "erreichbar.js: Werte nur je Einrichtungsart, keine Strukturfelder")

    print("A6-3 Status orientierung, wo der Maßstab keine gelesene Potsdamer Fundstelle hat")
    amtlich_dok = {"nvp", "baulandmodell"}
    falsch = [
        (nr, w["kennzahl"], w["art"])
        for nr, _, w in werte(P)
        if "richtwert" in w and (w["richtwert"]["q"] in amtlich_dok) != (w["status"] == "amtlich")
    ]
    pruef(not falsch, f"Status passt zum Dokument des Richtwerts ({len(falsch)} Abweichungen {falsch[:3]})")
    orient_werte = {
        (rw["kita"]["radius_orientierung_m"]["wert"], "kita"),
        (rw["grundschule"]["radius_orientierung_m"]["wert"], "grundschule"),
        (rw["gruen"]["radius_m"]["wert"], "gruen"),
        (rw["gruen"]["m2_je_ew"]["wert"], "gruen"),
    }
    ohne = [
        (nr, w["kennzahl"])
        for nr, _, w in werte(P)
        if "richtwert" in w and (w["richtwert"]["wert"], w["art"]) in orient_werte and w["status"] != "orientierung"
    ]
    pruef(not ohne, f"Orientierungswerte aus richtwerte.yaml tragen status orientierung ({len(ohne)} ohne)")
    n_or = sum(1 for _, _, w in werte(P) if w["status"] == "orientierung")
    pruef(n_or > 0, f"{n_or} Werte mit status orientierung in planer.js")

    print("A6-4 ODbL-Grenze: planer.js, erreichbar.js, einrichtungen.js ohne OSM (Korrektur 4)")
    for n, t in (("planer.js", tp), ("erreichbar.js", te), ("einrichtungen.js", tn)):
        pruef(not OSM_SPUR.search(t), f"{n}: keine OSM-Spur, kein methode fussweg")
    pruef(all(w["methode"] == "luftlinie" for _, _, w in werte(P)), "planer.js: jede Zeile methode luftlinie")
    pruef(E["methode"] == "luftlinie", "erreichbar.js: methode luftlinie")
    pruef(not set(N["quellen"]) - {"mbjs", "lgb"}, f"einrichtungen.js: Quellen {sorted(N['quellen'])}")

    print("A6-5 Gewicht")
    gz = {
        n: len(gzip.compress((DATEN / n).read_bytes(), 9)) for n in ("planer.js", "erreichbar.js", "einrichtungen.js")
    }
    pruef(sum(gz.values()) <= 250 * 1024, f"zusammen {sum(gz.values()) / 1024:.1f} KB gz ≤ 250 KB ({gz})")

    print("A6-6 Grundschulwerte vorläufig ohne Schulbezirke (H2)")
    h2 = list(Path(os.environ.get("KIEZ_DATEN", WURZEL.parent / "kiezatlas-daten"), "eingang").glob("*grundschul*"))
    gs = [w for _, _, w in werte(P) if w["art"] == "grundschule"]
    # H2 (grundschuleinzugsgebiete) liegt seit 05.11. 16:08 im Eingang, ist aber nicht verwendbar: nur eine Nummer je
    # Bezirk ohne Schulzuordnung, Stand 2018, Lizenz „Nutzungsbedingungen der LHP“ (nicht dl-de). Solange
    # 15_planer.py keine Schulbezirke rechnet, bleibt jeder Grundschulwert vorläufig.
    pruef(
        bool(gs) and all(w.get("vorlaeufig") is True for w in gs),
        f"{len(gs)} Grundschulwerte, alle vorlaeufig: true (H2 {'im Eingang, nicht verwendet' if h2 else 'fehlt'})",
    )

    print("A6-7 Rundung und Unsicherheit (Korrektur 15)")
    rd = rw["geheimhaltung"]["rundung_ew"]
    pruef(all(r["ew"] % rd == 0 for r in P["raeume"].values()), f"Einwohner je Raumeinheit auf {rd} gerundet")
    pruef(
        all(isinstance(w["wert"], int) for _, _, w in werte(P) if w["einheit"] == "%" and w["wert"] is not None),
        "Anteile ganzzahlig",
    )
    pruef(
        all(w["wert"] % rd == 0 for _, _, w in werte(P) if w["kennzahl"] == "ew_je_einrichtung" and w["wert"]),
        f"Einwohner je Standort auf {rd} gerundet",
    )
    pruef(all(len(w["unsicherheit"]) >= 20 for _, _, w in werte(P)), "jeder Wert mit Unsicherheitshinweis")
    pruef(
        all(
            "Cell-Key" in w["unsicherheit"]
            for _, _, w in werte(P)
            if (w.get("zielgruppe") or "").startswith(FEINE_ZIELGRUPPEN)
        ),
        "Werte aus Altersklassen nennen das Cell-Key-Verfahren",
    )

    print("A6-8 Raumebene und Geheimhaltung")
    soll, tab, par, herkunft = PLANER.raumquelle(cur)
    par = par or None
    h1 = Path(os.environ.get("KIEZ_DATEN", WURZEL.parent / "kiezatlas-daten"), "eingang", H1_DATEI)
    pruef(
        P["raumebene"] == soll and (soll == "planungsraum") == h1.exists(),
        f"raumebene {P['raumebene']} (Raumeinheiten aus {herkunft}; H1 {'da' if h1.exists() else 'fehlt'})",
    )
    cur.execute(
        f"""SELECT r.nr, coalesce(sum(z.ew), 0) FROM {tab} r
            LEFT JOIN public.zensus_zelle z ON ST_Contains(r.geom, z.geom) GROUP BY r.nr""",
        par,
    )
    ew_db = {str(a): int(b) for a, b in cur.fetchall()}
    pruef(set(ew_db) == set(P["raeume"]), f"alle {len(ew_db)} Raumeinheiten in planer.js")
    klein = min(ew_db, key=ew_db.get)
    print(
        f"        kleinste Raumeinheit {klein} mit {ew_db[klein]} EW "
        f"(Grenze {rw['geheimhaltung']['min_ew_raumeinheit']})"
    )
    verstoss = [
        nr
        for nr, _, w in werte(P)
        if ew_db[nr] < rw["geheimhaltung"]["min_ew_raumeinheit"]
        and (w.get("zielgruppe") or "").startswith(FEINE_ZIELGRUPPEN)
        and w["wert"] is not None
    ]
    pruef(not verstoss, f"keine Altersklassen-Werte in Raumeinheiten unter der Mindestgröße ({verstoss or 'keine'})")
    if soll == "stadtteil":
        K = json.loads((DATEN / "kennzahlen.json").read_text(encoding="utf-8"))["stadtteile"]
        abw = [
            nr
            for nr, r in P["raeume"].items()
            if abs(r["ew"] - next(k["wert"] for k in K[nr]["kacheln"] if k["id"] == "einwohner")) > rd / 2
        ]
        pruef(not abw, f"gerundete Einwohner = kennzahlen.json je Stadtteil ({abw or 'alle'})")
    else:
        # Zweiter Weg für die Zuordnung: GeoJSON aus dem Eingang direkt, Strahlverfahren in Python statt
        # 03_planungsraeume.py + PostGIS ST_Contains
        feats = json.loads(h1.read_text(encoding="utf-8"))["features"]
        cur.execute("""SELECT z.gitter_id, z.ew, ST_X(z.geom), ST_Y(z.geom) FROM public.zensus_zelle z
                       JOIN public.stadtteil s ON ST_Contains(s.geom, z.geom) WHERE z.ew IS NOT NULL""")
        ew_py, ohne, mehrfach = {}, [], []
        for g, ew, x, y in cur.fetchall():
            treffer = [str(ft["properties"]["pr"]) for ft in feats if in_flaeche(x, y, ft["geometry"])]
            if not treffer:
                ohne.append((g, ew))
            elif len(treffer) > 1:
                mehrfach.append(g)
            for nr in treffer[:1]:
                ew_py[nr] = ew_py.get(nr, 0) + (ew or 0)
        pruef(not ohne and not mehrfach, f"jede Zelle im Stadtgebiet in genau einem Planungsraum "
              f"(ohne: {len(ohne)} mit {sum(e or 0 for _, e in ohne)} EW, mehrfach: {len(mehrfach)})")
        abw = [(nr, ew_py.get(nr), ew_db[nr]) for nr in ew_db if ew_py.get(nr, 0) != ew_db[nr]]
        pruef(not abw, f"EW je Planungsraum: Strahlverfahren = PostGIS ({abw[:3] or 'alle 19 gleich'})")
        abw = [nr for nr, r in P["raeume"].items() if abs(r["ew"] - ew_py.get(nr, 0)) > rd / 2]
        pruef(not abw, f"gerundete Einwohner in planer.js = Strahlverfahren ({abw or 'alle'})")
        cur.execute("""SELECT coalesce(sum(z.ew), 0) FROM public.zensus_zelle z
                       JOIN public.stadtteil s ON ST_Contains(s.geom, z.geom)""")
        st_sum = int(cur.fetchone()[0])
        pruef(
            sum(ew_db.values()) == st_sum,
            f"EW-Summe {len(ew_db)} Planungsräume {sum(ew_db.values())} = 32 Stadtteile {st_sum}",
        )

    print("A6-9 Lizenzvermerke (Korrektur 26)")
    for datei, Q in (("planer.js", P["quellen"]), ("erreichbar.js", E["quellen"]), ("einrichtungen.js", N["quellen"])):
        for k, q in Q.items():
            if q["lizenz"].startswith("dl-de"):
                pruef(
                    DLDE in q["vermerk"] and VERAENDERT in q["vermerk"],
                    f"{datei} {k}: Link zum Lizenztext und „{VERAENDERT}“",
                )
            elif q["lizenz"].startswith("CC BY"):
                pruef(
                    "creativecommons.org" in q["vermerk"] and VERAENDERT in q["vermerk"],
                    f"{datei} {k}: CC BY mit Link und Bearbeitungshinweis",
                )
        fehlend = (
            {w["q"] for _, _, w in werte(P)} | {w["richtwert"]["q"] for _, _, w in werte(P) if "richtwert" in w}
            if datei == "planer.js"
            else set()
        )
        pruef(fehlend <= set(Q), f"{datei}: jede Quelle q steht in quellen")

    print("A6-10 Ärzte, Pflege, Apotheken ohne Versorgungsaussage (Korrektur 13)")
    for name, D in (("planer.js", P), ("planer_fuss_odbl.js", PF)):
        if D is None:
            print(f"        {name} nicht vorhanden (Quelle leer)")
            continue
        schlecht = [
            w["kennzahl"] for _, _, w in werte(D) if w["art"] in NUR_LAGE and w["kennzahl"] != "entfernung_median"
        ]
        pruef(not schlecht and "versorgt" not in json.dumps(D), f"{name}: nur Entfernung bei {sorted(NUR_LAGE)}")

    print("A6-11 Nachrechnung auf zweitem Weg (SQL)")
    radius = rw["kita"]["radius_orientierung_m"]["wert"]
    cur.execute(
        f"""SELECT r.nr, 100.0 * coalesce(sum(s.i_u3 + s.i_3_5) FILTER (WHERE e.meter <= %(radius)s), 0)
                           / nullif(sum(s.i_u3 + s.i_3_5), 0)
                    FROM public.zensus_struktur s JOIN {tab} r ON ST_Contains(r.geom, s.geom)
                    JOIN auswertung.zelle_erreichbar e
                      ON e.gitter_id = s.gitter_id AND e.art = 'kita' AND e.methode = 'luftlinie'
                    GROUP BY r.nr""",
        {**(par or {}), "radius": radius},
    )
    sql = {str(a): (None if b is None else float(b)) for a, b in cur.fetchall()}
    datei = {nr: w["wert"] for nr, _, w in werte(P) if w["kennzahl"] == "anteil_in_radius" and w["art"] == "kita"}
    abw = [
        (nr, datei[nr], round(sql[nr], 1)) for nr in datei if datei[nr] is not None and abs(datei[nr] - sql[nr]) > 0.51
    ]
    pruef(
        not abw and len(datei) == len(P["raeume"]),
        f"Kita-Anteil in {radius} m, {len(datei)} Raumeinheiten: SQL = Datei ({abw[:3] or 'alle'})",
    )
    q = rw["baulandmodell"]["quoten"]
    f = rw["baulandmodell"]["zensus_6_bis_unter_12"]
    cur.execute(
        f"""WITH k AS (SELECT r.nr, sum(s.i_u3) u3, sum(s.i_3_5) k35, sum(s.i_6_9) k69, sum(s.i_10_15) k1015
                               FROM public.zensus_struktur s JOIN {tab} r ON ST_Contains(r.geom, s.geom) GROUP BY r.nr),
                         p AS (SELECT r.nr, sum(e.plaetze) pl FROM auswertung.einrichtung e
                               JOIN {tab} r ON ST_Contains(r.geom, ST_Transform(e.geom, 4326))
                               WHERE e.art IN ('kita', 'hort') AND e.status = 'kapazitaet' GROUP BY r.nr)
                    SELECT k.nr, coalesce(p.pl, 0) / nullif(%(q1)s * u3 + %(q2)s * k35
                                                          + %(q3)s * (k69 * %(f1)s + k1015 * %(f2)s), 0)
                    FROM k LEFT JOIN p USING (nr)""",
        {
            **(par or {}),
            "q1": q["krippe"]["quote_prozent"] / 100,
            "q2": q["kindergarten"]["quote_prozent"] / 100,
            "q3": q["hort"]["quote_prozent"] / 100,
            "f1": f["i_6_9"],
            "f2": f["i_10_15"],
        },
    )
    sql = {str(a): (None if b is None else float(b)) for a, b in cur.fetchall()}
    datei = {nr: w["wert"] for nr, _, w in werte(P) if w["kennzahl"] == "plaetze_je_bedarf"}
    abw = [(nr, datei[nr], sql.get(nr)) for nr in datei if datei[nr] is not None and abs(datei[nr] - sql[nr]) > 0.006]
    pruef(not abw and datei, f"Plätze je Bedarfsplatz, {len(datei)} Raumeinheiten: SQL = Datei ({abw[:3] or 'alle'})")
    if soll == "planungsraum":
        # ÖPNV je Planungsraum: Gebietsklasse je Zelle aus dem Stadtteil, Radius je Klasse, ganz in SQL (ST_DWithin)
        o = rw["oepnv"]
        st = {nr: v["klasse"] for nr, v in o["gebietsklassen"]["stadtteile"].items() if v.get("klasse")}
        rad = [(k, vm, m) for vm in rw["planer"]["oepnv_verkehrsmittel_mit_radius"]
               for k, m in o["einzugsradius_m"][vm].items() if k in ("I", "II", "III") and m]
        rang = "CASE {} WHEN 'I' THEN 3 WHEN 'II' THEN 2 WHEN 'III' THEN 1 ELSE 0 END"
        cur.execute(
            f"""WITH k AS (SELECT * FROM unnest(%(st)s::text[], %(kl)s::text[]) AS t(st, klasse)),
                     rad AS (SELECT * FROM unnest(%(rk)s::text[], %(rv)s::text[], %(rm)s::int[]) AS t(klasse, vm, m)),
                     z AS (SELECT r.nr raum, z.ew, ST_Transform(z.geom, 25833) g, k.klasse
                           FROM public.zensus_zelle z JOIN {tab} r ON ST_Contains(r.geom, z.geom)
                           JOIN public.stadtteil s ON ST_Contains(s.geom, z.geom)
                           LEFT JOIN k ON k.st = s.nr::text WHERE z.ew > 0),
                     e AS (SELECT z.*,
                             EXISTS (SELECT 1 FROM auswertung.haltestelle h JOIN rad ON rad.klasse = z.klasse
                                     WHERE rad.vm = ANY (string_to_array(h.verkehrsmittel, '+'))
                                       AND ST_DWithin(h.geom, z.g, rad.m)) AS ersch,
                             EXISTS (SELECT 1 FROM auswertung.haltestelle h JOIN rad ON rad.klasse = z.klasse
                                     WHERE rad.vm = ANY (string_to_array(h.verkehrsmittel, '+'))
                                       AND ST_DWithin(h.geom, z.g, rad.m)
                                       AND {rang.format("h.klasse")} >= {rang.format("z.klasse")}) AS takt
                           FROM z)
                SELECT raum,
                       100.0 * coalesce(sum(ew) FILTER (WHERE klasse IS NOT NULL AND ersch), 0)
                             / nullif(sum(ew) FILTER (WHERE klasse IS NOT NULL), 0),
                       100.0 * coalesce(sum(ew) FILTER (WHERE klasse IS NOT NULL AND takt), 0)
                             / nullif(sum(ew) FILTER (WHERE klasse IS NOT NULL), 0),
                       100.0 * coalesce(sum(ew) FILTER (WHERE klasse IS NULL), 0) / sum(ew)
                FROM e GROUP BY raum""",
            {**(par or {}), "st": list(st), "kl": list(st.values()),
             "rk": [a for a, _, _ in rad], "rv": [b for _, b, _ in rad], "rm": [c for _, _, c in rad]},
        )
        sql = {str(a): (b, c, float(d)) for a, b, c, d in cur.fetchall()}
        grenze = rw["planer"]["oepnv_max_ohne_klasse_prozent"]
        for kz, i in (("oepnv_erschliessung", 0), ("oepnv_takt", 1)):
            datei = {nr: w["wert"] for nr, _, w in werte(P) if w["kennzahl"] == kz}
            soll = {
                nr: (None if v[i] is None or round(v[2]) > grenze else round(float(v[i])))
                for nr, v in sql.items()
            }
            abw = [
                (nr, datei.get(nr), soll[nr])
                for nr in soll
                if (datei.get(nr) is None) != (soll[nr] is None)
                or (soll[nr] is not None and abs(datei[nr] - float(sql[nr][i])) > 0.51)
            ]
            pruef(
                not abw and len(datei) == len(soll) == len(P["raeume"]),
                f"{kz}: SQL = Datei in allen {len(soll)} Planungsräumen, "
                f"{sum(v is None for v in soll.values())} ohne Wert (über {grenze} % ohne Klasse) "
                f"({abw[:3] or 'alle gleich'})",
            )
    cur.execute("""SELECT gitter_id, art, meter FROM auswertung.zelle_erreichbar WHERE methode = 'luftlinie'""")
    db = {(g, a): float(m) for g, a, m in cur.fetchall() if m is not None}
    ids = re.findall(r'"id":"(CRS3035RES100m[^"]+)"', (DATEN / "zellen.js").read_text(encoding="utf-8"))
    ew = [json.loads(x) for x in re.findall(r'"ew":(\d+|null)', (DATEN / "zellen.js").read_text(encoding="utf-8"))]
    abw = n = 0
    for a, liste in E["werte"].items():
        for i, v in enumerate(liste):
            if v is None:
                if ew[i]:
                    abw += 1
                continue
            n += 1
            if abs(v - db[(ids[i], a)]) > rw["planer"]["rundung_meter"] / 2 + 0.05:
                abw += 1
    pruef(
        abw == 0 and n > 0 and len(ids) == E["anzahl"],
        f"erreichbar.js: {n} Werte gegen die Tabelle, {abw} Abweichungen",
    )
    con.close()
    print(f"\n{len(befunde)} Befund(e)" if befunde else "\n0 Befunde")
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
