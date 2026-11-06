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
H1_DATEI = PLANER.H1_DATEI


def im_ring(x: float, y: float, ring: list) -> bool:
    """Strahlverfahren (gerade-ungerade) für einen Ring aus [lon, lat]-Paaren."""
    drin = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True):
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


def strittige_raeume(aus: list[str], cur, tab: str, par: dict | None) -> set[str]:
    """Raumeinheiten des strittigen Punkts und des genannten Ortsteils (wie ort_abweichung in 15_planer.py)."""
    cur.execute(
        f"""SELECT r.nr FROM auswertung.einrichtung e JOIN {tab} r ON ST_Contains(r.geom, ST_Transform(e.geom, 4326))
            WHERE e.id = ANY(%(aus)s)
            UNION
            SELECT r.nr FROM public.mbjs_schule m JOIN public.stadtteil s
                   ON s.name = substr(m.ort, length('Potsdam/OT ') + 1)
            JOIN {tab} r ON ST_Contains(r.geom, ST_PointOnSurface(s.geom)) WHERE m.schul_nr = ANY(%(aus)s)""",
        {**(par or {}), "aus": aus},
    )
    return {str(r[0]) for r in cur.fetchall()}


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
    amtlich_dok = {"baulandmodell"}  # NVP 2019: Fundstelle gelesen, Geltung bis 2023 abgelaufen → orientierung
    # Audit K4/K7: Kennzahlen, deren Rechenweise vom Dokument abweicht, stehen in baulandmodell.status_je_kennzahl
    st_kz = rw["baulandmodell"].get("status_je_kennzahl") or {}

    def status_soll(w):
        if w["richtwert"]["q"] not in amtlich_dok:
            return "orientierung"
        return (st_kz.get(w["kennzahl"]) or {}).get("status", "amtlich")

    alle_w = [(nr, w) for nr, _, w in werte(P)] + [("gesamt", w) for w in P.get("gesamt", {}).get("werte", [])]
    falsch = [(nr, w["kennzahl"], w["art"]) for nr, w in alle_w if "richtwert" in w and status_soll(w) != w["status"]]
    pruef(not falsch, f"Status passt zum Dokument des Richtwerts und zu baulandmodell.status_je_kennzahl "
                      f"({len(falsch)} Abweichungen {falsch[:3]})")
    ohne_satz = [(nr, w["kennzahl"]) for nr, w in alle_w if w["kennzahl"] in st_kz and w["richtwert"]["q"] == "baulandmodell"
                 and st_kz[w["kennzahl"]].get("grund") and st_kz[w["kennzahl"]]["grund"] not in w["unsicherheit"]]
    pruef(not ohne_satz, f"K4/K7: Grund des Status steht in jeder Unsicherheit ({ohne_satz[:3] or 'alle'})")
    nr344 = [nr for nr, w in alle_w if w["kennzahl"] == "plaetze_je_bedarf"
             and "Abweichend von Nr. 3.4.4 (Kita-Bedarfsplanung) ohne angrenzende Planungsräume" not in w["unsicherheit"]]
    pruef(not nr344, f"K7: Satz zu Nr. 3.4.4 an jedem Wert Plätze je Bedarfsplatz ({nr344 or 'alle'})")
    alt_text = [nr for nr, w in alle_w if re.search(r"nicht belegte Plätze|Kapazität laut Betriebserlaubnis",
                                                         w["unsicherheit"])]
    pruef(not alt_text, f"K8: kein Wortlaut „Kapazität … nicht belegte Plätze“ ({alt_text[:3] or 'keiner'})")
    norm = [(nr, w["kennzahl"]) for nr, _, w in werte(P) if "fordert hier keine" in (w.get("unsicherheit") or "")]
    pruef(not norm, f"keine Normaussage „NVP fordert hier keine Erschließung“ ({norm[:3]})")
    klein = [
        (nr, w["kennzahl"])
        for nr, r, w in werte(P)
        if w["art"] == "oepnv" and w.get("wert") is not None and "höchstens 200 Einwohnern" in w["unsicherheit"]
    ]
    pruef(not klein, f"ÖPNV-Werte in Raumeinheiten bis 200 EW ohne Wert ({klein[:3]})")
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
    h1 = Path(os.environ.get("KIEZ_DATEN", WURZEL.parent / "kiezatlas-daten"), "eingang", H1_DATEI)
    try:
        soll, tab, par, herkunft = PLANER.raumquelle(cur)
    except SystemExit as e:
        pruef(False, f"Raumquelle nicht lesbar: {e}")
        print(f"\n{len(befunde)} Befund(e), Abbruch bei A6-8")
        return 1
    par = par or None
    pruef(
        P["raumebene"] == soll and (soll == "planungsraum" or not h1.exists()),
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
        gj = json.loads(h1.read_text(encoding="utf-8"))
        crs = str(((gj.get("crs") or {}).get("properties") or {}).get("name") or "")
        pruef(not crs or crs.endswith(("4326", "CRS84")), f"H1-GeoJSON in Längen/Breiten ({crs or 'ohne crs'})")
        feats = gj["features"]
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
                           LEFT JOIN public.stadtteil s ON ST_Contains(s.geom, z.geom)
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
            erwartet = {nr: (None if v[i] is None or v[2] > grenze else float(v[i])) for nr, v in sql.items()}
            abw = [
                (nr, datei.get(nr), erwartet[nr])
                for nr in erwartet
                if (datei.get(nr) is None) != (erwartet[nr] is None)
                or (erwartet[nr] is not None and abs(datei[nr] - erwartet[nr]) > 0.51)
            ]
            pruef(
                not abw and len(datei) == len(erwartet) == len(P["raeume"]),
                f"{kz}: SQL = Datei in allen {len(erwartet)} Planungsräumen, "
                f"{sum(v is None for v in erwartet.values())} ohne Wert (über {grenze} % ohne Klasse) "
                f"({abw[:3] or 'alle gleich'})",
            )
    print("A6-12 Entfernungen gegen die Tabelle; strittige Lage (Pestalozza-Fall, N4); Schulen mit Primarstufe (K4)")
    # Schulen mit Primarstufe (Schulform „G/…“) zählen als Grundschulziel mit (Audit K4): zweiter Weg in SQL über
    # die Vereinigung beider Zielmengen, ohne strittige Standorte
    vor = rw["grundschule"]["primarstufe_schulform_praefix"]
    cur.execute("SELECT id FROM auswertung.einrichtung WHERE art = 'sek1' AND unterart LIKE %s ORDER BY id",
                (vor.replace("%", "") + "%",))
    prim = [r_[0] for r_ in cur.fetchall()]
    print(f"        Schulen mit Primarstufe: {len(prim)} ({', '.join(prim)})")
    # Standorte mit strittiger Lage (Feld hinweis in einrichtungen.js) zählen für keine Entfernung. Zweiter Weg:
    # nächstes Ziel je Zelle ganz in SQL ohne diese IDs; wo das Ziel der Tabelle nicht strittig ist, muss es
    # dasselbe sein wie in auswertung.zelle_erreichbar (Methode von A5a nachgebaut).
    strittig: dict[str, list[str]] = {}
    for f in N["features"]:
        if f["properties"].get("hinweis"):
            strittig.setdefault(f["properties"]["art"], []).append(f["properties"]["id"])
    cur.execute("""SELECT gitter_id, art, methode, meter, ziel_id FROM auswertung.zelle_erreichbar""")
    db, ziel = {}, {}
    for g, a, m_, me, z in cur.fetchall():
        ziel[(g, a, m_)] = z
        if me is not None:
            db[(g, a, m_)] = float(me)
    ohne, ohne_ziel = {}, {}
    if "grundschule" not in strittig and prim:
        strittig["grundschule"] = []
    for a, aus in strittig.items():
        mit = prim if a == "grundschule" else []
        cur.execute(
            """SELECT z.gitter_id, round(ST_Distance(ST_Transform(z.geom, 25833), n.geom)::numeric, 1), n.id
               FROM public.zensus_zelle z JOIN public.stadtteil s ON ST_Contains(s.geom, z.geom)
               CROSS JOIN LATERAL (SELECT e.geom, e.id FROM auswertung.einrichtung e
                                   WHERE (e.art = %s OR e.id = ANY(%s::text[])) AND e.id <> ALL(%s::text[])
                                   ORDER BY e.geom <-> ST_Transform(z.geom, 25833), e.id LIMIT 1) n
               WHERE z.ew IS NOT NULL""",
            (a, mit, aus),
        )
        for g, me, zid in cur.fetchall():
            ohne[(g, a)] = float(me)
            ohne_ziel[(g, a)] = zid
        if mit:
            n_prim = sum(1 for k, z in ohne_ziel.items() if k[1] == a and z in mit)
            pruef(n_prim > 0, f"K4: {n_prim} Zellen mit einer Schule mit Primarstufe als nächstem Grundschulziel (SQL)")
        gleich = [k for k in ohne if k[1] == a and ziel.get((k[0], a, "luftlinie")) not in aus
                  and ohne_ziel[k] not in mit]
        abw_n = sum(1 for k in gleich if abs(ohne[k] - db[(k[0], a, "luftlinie")]) > 0.05)
        pruef(
            gleich and abw_n == 0,
            f"{a}: SQL ohne strittige Standorte {aus}{' mit Primarstufe' if mit else ''} = Tabelle in {len(gleich)} "
            f"nicht betroffenen Zellen ({abw_n} Abweichungen)",
        )
        if not aus:
            continue
        raeume_s = strittige_raeume(aus, cur, tab, par)
        offen = [(nr, v["kennzahl"]) for nr, _, v in werte(P)
                 if nr in raeume_s and (v["kennzahl"], v["art"]) in PLANER.GS_KENNZAHLEN and v["art"] == a
                 and v["wert"] is not None]
        pruef(
            bool(raeume_s) and not offen,
            f"Strittige Lage {a}: Werte in den Raumeinheiten {sorted(raeume_s)} gesperrt ({offen[:3] or 'alle'})",
        )
    ids = re.findall(r'"id":"(CRS3035RES100m[^"]+)"', (DATEN / "zellen.js").read_text(encoding="utf-8"))
    ew = [json.loads(x) for x in re.findall(r'"ew":(\d+|null)', (DATEN / "zellen.js").read_text(encoding="utf-8"))]
    toleranz = rw["planer"]["rundung_meter"] / 2 + 0.05
    abw = n = neu_n = 0
    for a, liste in E["werte"].items():
        for i, v in enumerate(liste):
            if v is None:
                if ew[i]:
                    abw += 1
                continue
            n += 1
            soll = ohne.get((ids[i], a), db.get((ids[i], a, "luftlinie")))
            neu_n += (ids[i], a) in ohne and abs(soll - db.get((ids[i], a, "luftlinie"), soll)) > 0.05
            if abs(v - soll) > toleranz:
                abw += 1
    pruef(
        abw == 0 and n > 0 and len(ids) == E["anzahl"],
        f"erreichbar.js: {n} Werte gegen die Tabelle bzw. den zweiten Weg, davon {neu_n} anders als die Tabelle "
        f"(strittige Lage, Primarstufe), {abw} Abweichungen",
    )
    EF, _ = js("erreichbar_fuss_odbl.js")
    if EF is None:
        print("        erreichbar_fuss_odbl.js nicht vorhanden (Quelle leer)")
    else:
        abw = n = neu_n = 0
        for a, liste in EF["werte"].items():
            for i, v in enumerate(liste):
                if v is None or not ew[i]:
                    continue
                n += 1
                if ziel.get((ids[i], a, "fussweg")) in strittig.get(a, []) or (a == "grundschule" and prim):
                    # neu gerechnet (A5b-Verfahren in 15_planer.py): nie unter der Luftlinie des zweiten Wegs und
                    # (Primarstufe) nie über der Tabelle, wenn das Tabellenziel nicht strittig ist
                    tab_wert = db.get((ids[i], a, "fussweg"))
                    if ziel.get((ids[i], a, "fussweg")) in strittig.get(a, []) or tab_wert is None:
                        tab_wert = None
                    neu_n += tab_wert is None or abs(v - tab_wert) > toleranz
                    if v + toleranz < ohne[(ids[i], a)] or (tab_wert is not None and v > tab_wert + toleranz):
                        abw += 1
                elif abs(v - db[(ids[i], a, "fussweg")]) > toleranz:
                    abw += 1
        pruef(
            abw == 0 and n > 0 and EF["anzahl"] == len(ids),
            f"erreichbar_fuss_odbl.js: {n} Werte gegen die Tabelle, {neu_n} neu gerechnet (strittige Lage, "
            f"Primarstufe; ≥ Luftlinie, ≤ Tabelle), {abw} Abweichungen",
        )
        pruef(
            "vbb" in EF["quellen"] or "haltestelle" not in EF["arten"],
            "erreichbar_fuss_odbl.js: Quelle vbb genannt, weil Haltestellen Ziele sind (N1)",
        )
        # Treue des Fußweg-Nachbaus: mit allen Zielen muss fussweg_ohne die A5b-Tabelle genau treffen
        if strittig:
            try:
                import numpy  # noqa: F401
                import scipy  # noqa: F401
            except ImportError:
                print("        Hinweis: Fußweg-Nachbau nicht geprüft, numpy/scipy fehlen "
                      "(Aufruf mit uv --with numpy --with scipy)")
            else:
                if prim:
                    # K4 Fußweg nachgebaut: min(Fußweg ohne strittige Standorte, Fußweg zur nächsten Schule mit
                    # Primarstufe) je Zelle, auf rundung_meter gerundet = erreichbar_fuss_odbl.js
                    a, aus = "grundschule", strittig.get("grundschule", [])
                    o_ = PLANER.fussweg_ohne(cur, a, aus)
                    p_ = PLANER.fussweg_zu(cur, "id = ANY(%s::text[])", (prim,), a)
                    rd_m = rw["planer"]["rundung_meter"]
                    abw_n = 0
                    for i, g in enumerate(ids):
                        if not ew[i]:
                            continue
                        alt = db.get((g, a, "fussweg")) if ziel.get((g, a, "fussweg")) not in aus else o_.get(g)
                        kand = [x for x in (alt, p_.get(g)) if x is not None]
                        # Zellen ohne Zeile in der Tabelle bleiben leer (wie primarstufe_einrechnen in 15_planer.py)
                        soll = PLANER.rund(min(kand), rd_m) if kand and (g, a, "fussweg") in ziel else None
                        abw_n += soll != EF["werte"][a][i]
                    pruef(abw_n == 0, f"K4: Fußweg Grundschule mit Primarstufe nachgebaut = erreichbar_fuss_odbl.js "
                                      f"({abw_n} Abweichungen)")
                for a in strittig:
                    if not strittig[a]:
                        continue
                    alle = PLANER.fussweg_ohne(cur, a, [])
                    abw_n = sum(
                        1 for (g, a2, m_), v in ziel.items() if a2 == a and m_ == "fussweg"
                        and ((alle.get(g) is None) != ((g, a, "fussweg") not in db)
                             or ((g, a, "fussweg") in db and abs(alle[g] - db[(g, a, "fussweg")]) > 0.05))
                    )
                    pruef(abw_n == 0, f"Fußweg-Nachbau {a} mit allen Zielen = auswertung.zelle_erreichbar "
                                      f"({abw_n} Abweichungen)")
    print("A6-13 Audit 06.11.2026: Zähler und Nenner (K14), ganz Potsdam (K24), Primarstufe (K4), Kitas über zwei Räume "
          "(K27), Prüfwerte (K28)")
    # Rundung je Kennzahl wie zn_merken in 15_planer.py: (Zähler gerundet auf rd, Nenner gerundet auf rd)
    gerundet = {"anteil_in_radius": (True, True), "plaetze_je_kind": (False, True), "plaetze_je_bedarf": (False, True),
                "schueler_je_kind": (False, True), "ew_je_einrichtung": (True, False),
                "oepnv_erschliessung": (True, True), "oepnv_takt": (True, True)}
    for name, D in (("planer.js", P), ("planer_fuss_odbl.js", PF)):
        if D is None:
            continue
        alle = [(nr, w) for nr, _, w in werte(D)] + [("gesamt", w) for w in D.get("gesamt", {}).get("werte", [])]
        n_zn, falsch, ohne_zn, leer_falsch = 0, [], [], []
        for nr, w in alle:
            if w["kennzahl"] not in gerundet:
                continue
            if "zaehler" not in w or "nenner" not in w:
                ohne_zn.append((nr, w["kennzahl"]))
                continue
            z, n = w["zaehler"], w["nenner"]
            if w["wert"] is None:
                if (z is not None or n is not None) and not (w["kennzahl"] == "ew_je_einrichtung" and n == 0):
                    leer_falsch.append((nr, w["kennzahl"], w["art"]))
                continue
            n_zn += 1
            # gesamt rechnet aus den gerundeten Summen: dort ohne Rundungsspanne der Teile
            hz, hn = ((rd / 2 if g else 0) for g in gerundet[w["kennzahl"]]) if nr != "gesamt" else (0, 0)
            lo = max(z - hz, 0) / (n + hn) if n + hn else 0
            hi = (z + hz) / (n - hn) if n - hn > 0 else float("inf")
            if w["einheit"] == "%":
                lo, hi, tol = 100 * lo, 100 * hi, 0.5
            elif w["kennzahl"] == "ew_je_einrichtung":
                tol = rd / 2
            else:
                tol = 0.005
            if not (lo - tol - 1e-9 <= w["wert"] <= hi + tol + 1e-9):
                falsch.append((nr, w["kennzahl"], w["art"], z, n, w["wert"]))
            if w["kennzahl"] == "plaetze_je_bedarf" and (w.get("differenz") is None
                                                         or abs(w["differenz"] - (z - n)) > rd + 1e-9):
                falsch.append((nr, "differenz", w.get("differenz"), z - n))
        pruef(not ohne_zn and not falsch and not leer_falsch and n_zn > 0,
              f"{name}: zaehler/nenner = wert in {n_zn} Werten (Toleranz: Zähler und Nenner je ±{rd // 2} bei "
              f"Personen und Bedarf, dazu die Rundung des Werts) ({falsch[:3] or 'alle'}); ohne Zähler/Nenner "
              f"{ohne_zn[:3] or 'keiner'}; ohne Wert mit Zahl {leer_falsch[:3] or 'keiner'}")
        G = D.get("gesamt")
        if pruef(bool(G) and G["name"] == "Potsdam", f"{name}: Eintrag gesamt (ganz Potsdam) vorhanden"):
            abw = []
            for g in G["werte"]:
                k = (g["kennzahl"], g["art"], (g.get("richtwert") or {}).get("wert"))
                teile = [w for _, _, w in werte(D)
                         if (w["kennzahl"], w["art"], (w.get("richtwert") or {}).get("wert")) == k
                         and w.get("zaehler") is not None and w.get("nenner") is not None]
                if g["wert"] is None:
                    if not (g["kennzahl"] == "schueler_je_kind" and "Primarstufe" in g["unsicherheit"]):
                        abw.append(k)
                    continue
                if (g["zaehler"], g["nenner"]) != (sum(w["zaehler"] for w in teile), sum(w["nenner"] for w in teile)):
                    abw.append(k)
                if f"aus {len(teile)} von {len(D['raeume'])} Raumeinheiten" not in g["unsicherheit"]:
                    abw.append(("text",) + k)
            pruef(not abw and G["werte"], f"{name}: gesamt = Summe der veröffentlichten Zähler und Nenner, "
                                          f"{len(G['werte'])} Werte ({abw[:3] or 'alle'})")
    kinder_ok = [nr for nr, r_ in P["raeume"].items()
                 if (r_.get("kinder") is None) != (ew_db[nr] < rw["geheimhaltung"]["min_ew_raumeinheit"])
                 or (r_.get("kinder") and any(v % rd for v in r_["kinder"].values()))]
    pruef(not kinder_ok, f"K14: Kinder je Raumeinheit gerundet auf {rd}, null nur unter der Mindestgröße "
                         f"({kinder_ok or 'alle'})")
    # K4: Räume mit Schule mit Primarstufe: Grundschüler je Kind ohne Wert, Grund im ersten Satz
    cur.execute(
        f"""SELECT r.nr, count(*) FROM auswertung.einrichtung e
            JOIN {tab} r ON ST_Contains(r.geom, ST_Transform(e.geom, 4326))
            WHERE e.id = ANY(%(prim)s) GROUP BY r.nr""",
        {**(par or {}), "prim": prim},
    )
    prim_raum = {str(a): b for a, b in cur.fetchall()}
    satz = "Schule mit Primarstufe im Raum, Schülerzahl nicht nach Stufe teilbar"
    falsch = [nr for nr, _, w in werte(P) if w["kennzahl"] == "schueler_je_kind"
              and (nr in prim_raum) != (w["wert"] is None and w["unsicherheit"].startswith(satz))]
    kita_text = [nr for nr, _, w in werte(P) if w["kennzahl"] == "schueler_je_kind"
                 and re.search(r"Betriebserlaubnis|Kindertagespflege|wie oben", w["unsicherheit"])]
    pruef(prim_raum and not falsch and not kita_text,
          f"K4: Grundschüler je Kind in {sorted(prim_raum)} ohne Wert mit Grund ({falsch or 'alle'}); ohne "
          f"Kita-Bausteine und „wie oben“ ({kita_text or 'alle'})")
    cur.execute(
        f"""SELECT r.nr, count(*) FILTER (WHERE e.art = 'grundschule' AND e.id NOT LIKE '%%#haus%%'),
                   count(*) FILTER (WHERE e.id = ANY(%(prim)s))
            FROM auswertung.einrichtung e JOIN {tab} r ON ST_Contains(r.geom, ST_Transform(e.geom, 4326))
            GROUP BY r.nr""",
        {**(par or {}), "prim": prim},
    )
    n_gs = {str(a): b + c for a, b, c in cur.fetchall()}
    falsch = [(nr, w["nenner"], n_gs.get(nr, 0)) for nr, _, w in werte(P)
              if w["kennzahl"] == "ew_je_einrichtung" and w["art"] == "grundschule" and w["nenner"] is not None
              and w["nenner"] != n_gs.get(nr, 0)]
    pruef(not falsch, f"K4: Einwohner je Grundschulstandort zählt Schulen mit Primarstufe mit ({falsch[:3] or 'alle'})")
    # K27: id_kita mit Häusern in mehreren Raumeinheiten, in jeder betroffenen Raumeinheit genannt
    cur.execute(
        f"""SELECT split_part(e.id, '#', 1), array_agg(DISTINCT r.nr::text ORDER BY r.nr::text)
            FROM auswertung.einrichtung e JOIN {tab} r ON ST_Contains(r.geom, ST_Transform(e.geom, 4326))
            WHERE e.art IN ('kita', 'hort') GROUP BY 1 HAVING count(DISTINCT r.nr) > 1""",
        par,
    )
    ueber = cur.fetchall()
    fehlt = [(k, nr) for k, rr in ueber for nr in rr
             if not any(w["kennzahl"] == "plaetze_je_bedarf" and f"(MBJS {k})" in w["unsicherheit"]
                        for w in P["raeume"][nr]["werte"])]
    pruef(not fehlt, f"K27: {len(ueber)} Kita(s) mit Häusern in mehreren Raumeinheiten "
                     f"({'; '.join(f'{k}: {sorted(rr)}' for k, rr in ueber) or 'keine'}), in jeder genannt "
                     f"({fehlt or 'alle'})")
    # K28: Prüfwerte = Belegdateien (zweiter Weg: eigene Muster)
    pw = P.get("pruefwerte") or {}
    n1 = (WURZEL / "belege" / "N1_osm_fussweg_20261105.md").read_text(encoding="utf-8")
    kp = (WURZEL / "belege" / "A5b_landfilter_kreuzprobe.txt").read_text(encoding="utf-8")
    del n1  # OSM-Prüfwerte stehen nicht in planer.js (ODbL-Grenze A1), nur als belegter Text auf der Methodenseite
    soll = {"landfilter_haltepunkte": int(re.search(r"Rechteck: (\d+)", kp).group(1)),
            "landfilter_falsch": int(re.search(r"zugeordnet: (\d+)", kp).group(1))}
    pruef({k: (v or {}).get("wert") for k, v in pw.items()} == soll
          and all((WURZEL / v["beleg"]).exists() for v in pw.values()),
          f"K28: Prüfwerte in planer.js = Belegdateien ({ {k: v.get('wert') for k, v in pw.items()} })")
    con.close()
    print(f"\n{len(befunde)} Befund(e)" if befunde else "\n0 Befunde")
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
