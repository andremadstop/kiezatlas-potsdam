"""Paket A5a: Erreichbarkeit je Zensus-Zelle in Luftlinie (Kiezatlas Potsdam, Ausbau Planer-Ebene).

Kein Netzabruf. Rechnet nur in der Datenbank (EPSG:25833) und schreibt nur eigene Zeilen.

Liest:
  public.zensus_zelle, public.stadtteil      Zellmittelpunkte, Einwohner, Stadtgrenze
  auswertung.einrichtung                     A2: Kitas, Horte, Schulen (MBJS), Gemeinbedarf ohne Kapazität (ALKIS)
  auswertung.gruenflaeche                    A2: Grünflächen aus der ALKIS-Nutzung
  auswertung.gebaeude_stand_20261105         nur für den Berlin-Ersatz (siehe Randeffekt)
  config/richtwerte.yaml                     gruen (Radius), gruen_definition (welche Arten zählen, Mindestfläche)
  config/potsdam.yaml                        Abrufrechtecke der Quellen (Randeffekt), Zensus-Lizenz
Schreibt (Rolle kiezatlas_rechnen, eine Transaktion; gelöscht werden nur Zeilen mit methode = 'luftlinie',
Fußweg-Zeilen aus A5b bleiben stehen):
  auswertung.zelle_erreichbar  je Zelle und Art die nächste Einrichtung: meter, ziel_id, quelle_lizenz;
                               minuten bleibt leer (Luftlinie ist keine Gehzeit). Art „gruen“ = nächste
                               zählende Grünfläche (Abstand zum Flächenrand, 0 = Zellmittelpunkt in der Fläche).
  auswertung.zelle_gruen       Grünfläche im Kreis um den Zellmittelpunkt (Korrektur 22) und je Einwohner
                               im selben Kreis
  belege/A5a_erreichbarkeit_<datum>.md     Kennzahlen je Art, Randeffekt, Hinweise für A6
  belege/A5a_rand_unsicher_<datum>.csv     Zellen, deren Wert wegen fehlender Daten jenseits des Rands
                                           nur eine Obergrenze ist (die Tabelle hat dafür keine Spalte)

Zellen: alle Gitterzellen mit Mittelpunkt in Potsdam und Einwohnerwert (3.443, dieselbe Menge wie
daten/zellen.js), darunter die 3.411 bewohnten. Gerechnet wird vom Zellmittelpunkt aus.

Randeffekt (E7: Brandenburg ja, Berlin nein): Einrichtungen außerhalb der Stadt zählen mit, aber nur so weit,
wie die Quelle abgerufen wurde (Rechtecke in config/potsdam.yaml: MBJS rund 3 km um die Stadt, ALKIS fast
genau die Stadt). Berlin liefert weder MBJS noch LGB. Als Ersatz für die Landesgrenze dienen bewohnte
Zensus-Zellen außerhalb Potsdams ohne ein einziges LGB-Gebäude (dort endet Brandenburg); einzelne solche
Zellen ohne Nachbarn bleiben unberücksichtigt. Ein Wert gilt als „Rand unsicher“, wenn die nächste
Einrichtung weiter weg liegt als der Rand des Abrufrechtecks bzw. das Berliner Gebiet.

Aufruf (aus dem Worktree; Passwort nur aus der .env, nie auf der Kommandozeile ausgeschrieben):
    set -a; . ../kiezatlas-potsdam/.env; set +a
    PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=kiezatlas_rechnen PGPASSWORD="$RECHNEN_PASSWORD" \\
    uv run -q --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \\
        python -I skripte/14_erreichbarkeit.py
"""
from __future__ import annotations

import csv
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import yaml

WURZEL = Path(__file__).resolve().parent.parent
BELEGE = WURZEL / "belege"
SNAPSHOT = "auswertung.gebaeude_stand_20261105"

DLDE_LINK = "https://www.govdata.de/dl-de/by-2-0"
VERAENDERT = "Daten verändert (eigene Berechnung)"

# Quellen in config/potsdam.yaml, deren Abrufrechteck für die Einrichtungen gilt
RECHTECK_MBJS = ("mbjs_kita", "mbjs_schule")
RECHTECK_LGB = ("gebaeude_alkis", "alkis_nutzung")
# Berlin-Ersatz: eine gebäudelose bewohnte Zelle zählt nur mit mindestens so vielen solchen Nachbarn in 150 m
BERLIN_MIN_NACHBARN = 3
# Halbe Zelldiagonale: Abstand vom Mittelpunkt einer Berlin-Ersatzzelle bis zu ihrer fernsten Ecke
HALBE_DIAGONALE = 50 * math.sqrt(2)


def konfiguration() -> dict:
    rw = yaml.safe_load((WURZEL / "config" / "richtwerte.yaml").read_text(encoding="utf-8"))
    pq = yaml.safe_load((WURZEL / "config" / "potsdam.yaml").read_text(encoding="utf-8"))["quellen"]
    arten = (rw.get("gruen_definition") or {}).get("arten")
    if not arten:
        raise SystemExit("config/richtwerte.yaml: gruen_definition.arten fehlt (Paket A2 trägt die Zuordnung ein)")
    zaehlt = sorted(a for a, d in arten.items() if d.get("zaehlt_vorschlag") is True)
    offen = sorted(a for a, d in arten.items() if d.get("zaehlt_vorschlag") not in (True, False))
    if not zaehlt:
        raise SystemExit("config/richtwerte.yaml: keine Grünart mit zaehlt_vorschlag: true")
    radius = rw["gruen"]["radius_m"]["wert"]
    radien = radius if isinstance(radius, list) else [radius]

    def rechteck(namen: tuple[str, ...]) -> tuple[float, float, float, float]:
        boxen = [pq[n]["bbox"] for n in namen]
        # Schnitt der Rechtecke: nur dort liegen sicher Daten aller beteiligten Quellen
        return (max(b[0] for b in boxen), max(b[1] for b in boxen), min(b[2] for b in boxen), min(b[3] for b in boxen))

    return {
        "gruen_zaehlt": zaehlt,
        "gruen_offen": offen,
        "gruen_status": (rw.get("gruen_definition") or {}).get("status"),
        "mindestflaeche": (rw.get("gruen_definition") or {}).get("mindestflaeche_m2"),
        "radien": [int(r) for r in radien],
        "rechteck_mbjs": rechteck(RECHTECK_MBJS),
        "rechteck_lgb": rechteck(RECHTECK_LGB),
        "lizenz_zensus": f"Zellmittelpunkt und Einwohner: © Statistische Ämter des Bundes und der Länder, Zensus 2022, "
                         f"dl-de/by-2-0 ({DLDE_LINK}), {VERAENDERT}",
        "lizenz_lgb": f"© GeoBasis-DE/LGB, dl-de/by-2-0 ({DLDE_LINK})",
    }


def vorbereiten(cur, k: dict) -> None:
    """TEMP-Tabellen (kein CREATE in auswertung): Zellen, Ziele, Berlin-Ersatz, Grün."""
    cur.execute("""
        CREATE TEMP TABLE t_stadt ON COMMIT DROP AS
            SELECT ST_Union(ST_Transform(geom, 25833)) AS g FROM public.stadtteil;
        CREATE TEMP TABLE t_zelle ON COMMIT DROP AS
            SELECT z.gitter_id, z.ew, s.nr AS stadtteil, ST_Transform(z.geom, 25833) AS g
            FROM public.zensus_zelle z
            JOIN public.stadtteil s ON ST_Contains(s.geom, z.geom)
            WHERE z.ew IS NOT NULL;
        CREATE INDEX ON t_zelle USING gist (g);
        CREATE TEMP TABLE t_ew ON COMMIT DROP AS
            SELECT gitter_id, ew, ST_Transform(geom, 25833) AS g FROM public.zensus_zelle WHERE ew > 0;
        CREATE INDEX ON t_ew USING gist (g);
    """)
    xmin_m, ymin_m, xmax_m, ymax_m = k["rechteck_mbjs"]
    xmin_l, ymin_l, xmax_l, ymax_l = k["rechteck_lgb"]
    cur.execute("""
        CREATE TEMP TABLE t_ziel ON COMMIT DROP AS
            SELECT id, art, lizenz, in_potsdam, geom AS g,
                   CASE WHEN id LIKE 'alkis:%' THEN 'lgb' ELSE 'mbjs' END AS herkunft
            FROM auswertung.einrichtung;
        CREATE INDEX ON t_ziel USING gist (g);
    """)
    # psycopg: mit Parametern nur eine Anweisung je execute
    cur.execute("""
        CREATE TEMP TABLE t_rechteck ON COMMIT DROP AS
            SELECT * FROM (VALUES ('mbjs', %s::float8, %s::float8, %s::float8, %s::float8),
                                  ('lgb',  %s::float8, %s::float8, %s::float8, %s::float8)) v(herkunft, x0, y0, x1, y1);
    """, (xmin_m, ymin_m, xmax_m, ymax_m, xmin_l, ymin_l, xmax_l, ymax_l))
    # Berlin-Ersatz: bewohnte Zellen außerhalb Potsdams im LGB-Rechteck ohne LGB-Gebäude in der Zelle
    cur.execute(f"""
        CREATE TEMP TABLE t_geb ON COMMIT DROP AS SELECT ST_Transform(geom, 25833) AS g FROM {SNAPSHOT};
        CREATE INDEX ON t_geb USING gist (g);
        ANALYZE t_geb;
        CREATE TEMP TABLE t_leer0 ON COMMIT DROP AS
            SELECT e.gitter_id, e.ew, e.g FROM t_ew e, t_stadt s, t_rechteck r
            WHERE r.herkunft = 'lgb' AND NOT ST_Contains(s.g, e.g)
              AND ST_X(e.g) BETWEEN r.x0 + 50 AND r.x1 - 50 AND ST_Y(e.g) BETWEEN r.y0 + 50 AND r.y1 - 50
              AND NOT EXISTS (SELECT 1 FROM t_geb b WHERE ST_Intersects(b.g, ST_Expand(e.g, 50)));
        CREATE INDEX ON t_leer0 USING gist (g);
        CREATE TEMP TABLE t_berlin ON COMMIT DROP AS
            SELECT a.* FROM t_leer0 a
            WHERE (SELECT count(*) FROM t_leer0 b WHERE b.gitter_id <> a.gitter_id AND ST_DWithin(a.g, b.g, 150))
                  >= {BERLIN_MIN_NACHBARN};
        CREATE INDEX ON t_berlin USING gist (g);
        ANALYZE t_zelle; ANALYZE t_ziel; ANALYZE t_ew; ANALYZE t_berlin;
    """)
    # Grün: zählende Arten vereinigen (keine Fläche doppelt), dann in kleine Stücke teilen (schneller verschneiden)
    mind = k["mindestflaeche"]
    cur.execute("""
        CREATE TEMP TABLE t_gruen_obj ON COMMIT DROP AS
            SELECT id, art, geom AS g FROM auswertung.gruenflaeche
            WHERE art = ANY(%s) AND (%s::numeric IS NULL OR flaeche_m2 >= %s::numeric)
    """, (k["gruen_zaehlt"], mind, mind))
    cur.execute("""
        CREATE INDEX ON t_gruen_obj USING gist (g);
        CREATE TEMP TABLE t_gruen ON COMMIT DROP AS
            SELECT ST_Subdivide(ST_Union(g), 64) AS g FROM t_gruen_obj;
        CREATE INDEX ON t_gruen USING gist (g);
        ANALYZE t_gruen_obj; ANALYZE t_gruen;
    """)


def erreichbar(cur, k: dict) -> None:
    cur.execute("DELETE FROM auswertung.zelle_erreichbar WHERE methode = 'luftlinie'")
    cur.execute("""
        INSERT INTO auswertung.zelle_erreichbar (gitter_id, art, methode, meter, minuten, ziel_id, quelle_lizenz)
        SELECT z.gitter_id, a.art, 'luftlinie', round(ST_Distance(z.g, n.g)::numeric, 1), NULL, n.id,
               n.lizenz || '; ' || %s
        FROM t_zelle z
        CROSS JOIN (SELECT DISTINCT art FROM t_ziel) a
        CROSS JOIN LATERAL (SELECT e.id, e.g, e.lizenz FROM t_ziel e WHERE e.art = a.art
                            ORDER BY e.g <-> z.g, e.id LIMIT 1) n
    """, (k["lizenz_zensus"],))
    lizenz_gruen = (f"{k['lizenz_lgb']} (ALKIS-Nutzung: {', '.join(k['gruen_zaehlt'])}), {VERAENDERT}; "
                    f"{k['lizenz_zensus']}")
    cur.execute("""
        INSERT INTO auswertung.zelle_erreichbar (gitter_id, art, methode, meter, minuten, ziel_id, quelle_lizenz)
        SELECT z.gitter_id, 'gruen', 'luftlinie', round(ST_Distance(z.g, n.g)::numeric, 1), NULL, n.id, %s
        FROM t_zelle z
        CROSS JOIN LATERAL (SELECT o.id, o.g FROM t_gruen_obj o ORDER BY o.g <-> z.g, o.id LIMIT 1) n
    """, (lizenz_gruen,))


def gruen(cur, k: dict) -> None:
    cur.execute("DELETE FROM auswertung.zelle_gruen WHERE methode = 'luftlinie'")
    lizenz = (f"{k['lizenz_lgb']} (ALKIS-Nutzung: {', '.join(k['gruen_zaehlt'])}), {VERAENDERT}; "
              f"{k['lizenz_zensus']}")
    for r in k["radien"]:
        cur.execute("""
            INSERT INTO auswertung.zelle_gruen (gitter_id, methode, radius_m, m2_gruen, m2_je_ew, quelle_lizenz)
            SELECT z.gitter_id, 'luftlinie', %(r)s, round(f.m2::numeric, 1),
                   CASE WHEN w.ew > 0 THEN round((f.m2 / w.ew)::numeric, 2) END, %(liz)s
            FROM t_zelle z
            CROSS JOIN LATERAL (
                SELECT coalesce(sum(ST_Area(ST_Intersection(g, ST_Buffer(z.g, %(r)s, 'quad_segs=64')))), 0) AS m2
                FROM t_gruen WHERE ST_DWithin(g, z.g, %(r)s)) f
            CROSS JOIN LATERAL (
                SELECT coalesce(sum(ew), 0) AS ew FROM t_ew e WHERE ST_DWithin(e.g, z.g, %(r)s)) w
        """, {"r": r, "liz": lizenz})


def rand(cur, k: dict) -> list[tuple]:
    """Zellen, deren nächstes Ziel weiter weg liegt als der Rand des Datengebiets (Obergrenze statt Messwert)."""
    cur.execute("""
        WITH e AS (
            SELECT ze.gitter_id, ze.art, ze.meter::float8 AS meter, z.ew, z.stadtteil, z.g,
                   CASE WHEN ze.art = 'gruen' THEN 'lgb'
                        ELSE (SELECT t.herkunft FROM t_ziel t WHERE t.id = ze.ziel_id) END AS herkunft
            FROM auswertung.zelle_erreichbar ze JOIN t_zelle z USING (gitter_id)
            WHERE ze.methode = 'luftlinie'),
        d AS (
            SELECT e.*, least(ST_X(e.g) - r.x0, r.x1 - ST_X(e.g), ST_Y(e.g) - r.y0, r.y1 - ST_Y(e.g)) AS d_rechteck,
                   (SELECT ST_Distance(b.g, e.g) FROM t_berlin b ORDER BY b.g <-> e.g LIMIT 1) - %s AS d_berlin
            FROM e JOIN t_rechteck r USING (herkunft))
        SELECT gitter_id, art, meter, ew, stadtteil, round(d_rechteck::numeric, 0), round(d_berlin::numeric, 0),
               concat_ws('+', CASE WHEN meter > d_rechteck THEN 'rechteck' END,
                              CASE WHEN meter > d_berlin THEN 'berlin' END)
        FROM d WHERE meter > d_rechteck OR meter > d_berlin
        ORDER BY art, gitter_id
    """, (HALBE_DIAGONALE,))
    return cur.fetchall()


def rand_gruen(cur, k: dict) -> list[tuple]:
    """Zellen, deren Kreis über das LGB-Rechteck oder ins Berliner Gebiet reicht (Grün dort nicht erfasst)."""
    cur.execute("""
        SELECT zg.gitter_id, zg.radius_m, z.ew, z.stadtteil,
               round(least(ST_X(z.g) - r.x0, r.x1 - ST_X(z.g), ST_Y(z.g) - r.y0, r.y1 - ST_Y(z.g))::numeric, 0) AS d_r,
               round(((SELECT ST_Distance(b.g, z.g) FROM t_berlin b ORDER BY b.g <-> z.g LIMIT 1) - %s)::numeric, 0)
                   AS d_b
        FROM auswertung.zelle_gruen zg JOIN t_zelle z USING (gitter_id), t_rechteck r
        WHERE zg.methode = 'luftlinie' AND r.herkunft = 'lgb'
        ORDER BY zg.radius_m, zg.gitter_id
    """, (HALBE_DIAGONALE,))
    aus = []
    for gid, rad, ew, st, d_r, d_b in cur.fetchall():
        gruende = [g for g, ja in (("rechteck", d_r < rad), ("berlin", d_b is not None and d_b < rad)) if ja]
        if gruende:
            aus.append((gid, f"gruen_{rad}m", None, ew, st, d_r, d_b, "+".join(gruende)))
    return aus


def q(cur, sql: str, args=()) -> list:
    cur.execute(sql, args)
    return cur.fetchall()


def z(n) -> str:
    if n is None:
        return "–"
    if isinstance(n, float) and not n.is_integer():
        return f"{n:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(n):,}".replace(",", ".")


def tabelle(kopf: list[str], zeilen: list) -> str:
    t = ["| " + " | ".join(kopf) + " |", "|" + "|".join("---" for _ in kopf) + "|"]
    t += ["| " + " | ".join(str(x) for x in r) + " |" for r in zeilen]
    return "\n".join(t)


def bericht(cur, k: dict, randliste: list[tuple], fuss_vorher: tuple, fuss_nachher: tuple, heute: str,
            lauf: str) -> str:
    t = [f"# A5a Erreichbarkeit in Luftlinie: Lauf {lauf}", "",
         "Erzeugt von `skripte/14_erreichbarkeit.py` (Rolle `kiezatlas_rechnen`, kein Netzabruf). "
         "Gerechnet in EPSG:25833 vom Mittelpunkt der Zensus-Zelle aus. Der Mittelpunkt kann bis zu 71 m vom "
         "tatsächlichen Wohnort abweichen; Meterwerte sind auf 0,1 m gespeichert, aussagekräftig sind sie auf "
         "rund 50 m.", ""]
    n_zellen, n_bew, ew = q(cur, "SELECT count(*), count(*) FILTER (WHERE ew > 0), sum(ew) FROM t_zelle")[0]
    t += [f"**Zellen:** {z(n_zellen)} mit Mittelpunkt in Potsdam (Menge von `daten/zellen.js`), davon {z(n_bew)} "
          f"bewohnt mit {z(ew)} Einwohnern (Zensus 2022).", ""]

    t += ["## Nächste Einrichtung je Art", "",
          "Mediane und P90 nach Einwohnern gewichtet (bewohnte Zellen). „außerhalb“ = die nächste Einrichtung liegt "
          "außerhalb der Stadtgrenze (E7: Brandenburg wird mitgerechnet). „Rand unsicher“ siehe unten.", ""]
    zeilen = q(cur, """
        WITH r AS (SELECT ze.art, ze.meter, z.ew, coalesce(t.in_potsdam, true) AS drin
                   FROM auswertung.zelle_erreichbar ze JOIN t_zelle z USING (gitter_id)
                   LEFT JOIN t_ziel t ON t.id = ze.ziel_id
                   WHERE ze.methode = 'luftlinie' AND z.ew > 0),
             w AS (SELECT art, meter, ew, drin,
                          sum(ew) OVER (PARTITION BY art ORDER BY meter ROWS UNBOUNDED PRECEDING)::float8
                          / sum(ew) OVER (PARTITION BY art) AS kum FROM r)
        SELECT art, count(*),
               CASE WHEN art = 'gruen' THEN (SELECT count(*) FROM t_gruen_obj)
                    ELSE (SELECT count(*) FROM t_ziel t WHERE t.art = w.art) END,
               min(meter) FILTER (WHERE kum >= 0.5), min(meter) FILTER (WHERE kum >= 0.9), max(meter),
               count(*) FILTER (WHERE NOT drin), sum(ew) FILTER (WHERE NOT drin)
        FROM w GROUP BY art ORDER BY art""")
    t.append(tabelle(["art", "bewohnte Zellen", "Standorte (gesamt)", "Median m", "P90 m", "max m",
                      "Zellen mit Ziel außerhalb", "EW dort"],
                     [(a, z(n), z(s), z(round(m5)), z(round(m9)), z(round(mx)), z(na), z(ea or 0))
                      for a, n, s, m5, m9, mx, na, ea in zeilen]))
    t.append("")
    t.append(f"Art `gruen`: nächste Grünfläche der Arten {', '.join(k['gruen_zaehlt'])} (Abstand zum Flächenrand; "
             "0 m = Zellmittelpunkt liegt in der Fläche). Standorte = ALKIS-Objekte.")
    t.append("")

    t += ["## Randeffekt (E7)", "",
          "Abrufrechtecke laut `config/potsdam.yaml` (EPSG:25833): "
          f"MBJS {list(k['rechteck_mbjs'])}, ALKIS/LGB {list(k['rechteck_lgb'])}. Das ALKIS-Rechteck endet "
          "fast an der Stadtgrenze; Bibliotheken, Feuerwehren, Sport und sonstiger Gemeinbedarf jenseits davon "
          "fehlen. Berlin liefert weder MBJS noch LGB (E7: Berlin nein).", ""]
    nb, ewb = q(cur, "SELECT count(*), coalesce(sum(ew), 0) FROM t_berlin")[0]
    n0 = q(cur, "SELECT count(*) FROM t_leer0")[0][0]
    xb = q(cur, "SELECT round(min(ST_X(g))), round(max(ST_X(g))), round(min(ST_Y(g))), round(max(ST_Y(g))) "
                "FROM t_berlin")[0]
    t += [f"Berlin-Ersatz: {z(n0)} bewohnte Zellen außerhalb Potsdams ohne LGB-Gebäude im LGB-Rechteck, davon "
          f"{z(nb)} mit mindestens {BERLIN_MIN_NACHBARN} solchen Nachbarn in 150 m ({z(ewb)} EW; "
          f"x {z(xb[0])}–{z(xb[1])}, y {z(xb[2])}–{z(xb[3])}). Das ist das Berliner Gebiet östlich der Stadt.", ""]
    zaehl: dict[str, list[int]] = {}
    for gid, art, meter, ew_, st, d_r, d_b, grund in randliste:
        e = zaehl.setdefault(art, [0, 0, 0, 0])
        e[0] += 1
        e[1] += ew_ or 0
        e[2] += "rechteck" in grund
        e[3] += "berlin" in grund
    t.append("„berlin“: nach E7 vorerst nicht gerechnet; eine Berliner Einrichtung könnte näher liegen. "
             "„rechteck“: der Abruf der Quelle endete dort.")
    t.append("")
    t.append("Zellen, deren Wert nur eine Obergrenze ist (die nächste Einrichtung liegt weiter weg als der Rand "
             "des Datengebiets; jenseits davon könnte eine nähere liegen). Liste: "
             f"`belege/A5a_rand_unsicher_{heute}.csv`.")
    t.append("")
    t.append(tabelle(["art", "Zellen", "EW", "davon Rechteckrand", "davon Berlin"],
                     [(a, z(v[0]), z(v[1]), z(v[2]), z(v[3])) for a, v in sorted(zaehl.items())]))
    t.append("")

    t += ["## Grün im Umkreis (`auswertung.zelle_gruen`, Korrektur 22)", ""]
    for r in k["radien"]:
        g = q(cur, """SELECT count(*), count(*) FILTER (WHERE zg.m2_gruen = 0),
                             percentile_cont(0.5) WITHIN GROUP (ORDER BY zg.m2_gruen),
                             percentile_cont(0.5) WITHIN GROUP (ORDER BY zg.m2_je_ew),
                             count(*) FILTER (WHERE zg.m2_je_ew < 6), max(zg.m2_gruen)
                      FROM auswertung.zelle_gruen zg JOIN t_zelle z USING (gitter_id)
                      WHERE zg.methode = 'luftlinie' AND zg.radius_m = %s AND z.ew > 0""", (r,))[0]
        t.append(f"- Radius {r} m, bewohnte Zellen {z(g[0])}: Median Grünfläche {z(round(g[2]))} m², "
                 f"Median {z(float(round(g[3], 1)))} m² je EW im Kreis; {z(g[1])} Zellen ohne Grün im Kreis; "
                 f"{z(g[4])} Zellen unter 6 m² je EW; größter Wert {z(round(g[5]))} m² "
                 f"(Kreisfläche {z(round(math.pi * r * r))} m²).")
    t += ["",
          f"Definition: ALKIS-Nutzung der Arten {', '.join(k['gruen_zaehlt'])} (`gruen_definition.arten`, "
          f"`zaehlt_vorschlag: true`), vereinigt, Mindestfläche "
          f"{k['mindestflaeche'] if k['mindestflaeche'] is not None else 'keine (mindestflaeche_m2: null)'}. "
          f"Nicht gezählt: Arten mit offenem Vorschlag ({', '.join(k['gruen_offen']) or 'keine'}) und mit "
          f"`false`. `gruen_definition.status` ist `{k['gruen_status']}`: entscheidet A6 anders, muss "
          "dieses Skript neu laufen.",
          "",
          "`m2_je_ew` = Grünfläche im Kreis geteilt durch die Einwohner aller Zensus-Zellen, deren Mittelpunkt im "
          "selben Kreis liegt (auch außerhalb der Stadt). Das ist eine vereinfachte Annäherung an die Berliner "
          "Methode (Umweltatlas 2020), nicht deren Nachbildung: dort zählen Grünanlagen ab einer Mindestgröße und "
          "die Fläche wird auf alle Einwohner im Einzugsbereich verteilt. Der Kreis ist ein Polygon mit 256 "
          "Ecken (Flächenfehler unter 0,01 %). Kreise, die über das LGB-Rechteck oder nach Berlin reichen, "
          "unterschätzen das Grün (Berliner Einwohner zählen im Nenner, Berliner Parks fehlen im Zähler); "
          "sie stehen mit `gruen_<radius>m` in der CSV.",
          ""]

    t += ["## Fußweg-Zeilen (A5b) unberührt", "",
          f"Vor dem Lauf: zelle_erreichbar {fuss_vorher[0]}, zelle_gruen {fuss_vorher[1]} Zeilen mit methode "
          f"„fussweg“. Nach dem Lauf: {fuss_nachher[0]} bzw. {fuss_nachher[1]}. Gelöscht und neu geschrieben "
          "wurden nur Zeilen mit methode „luftlinie“.", ""]

    t += ["## Hinweise für A6", "",
          "- `minuten` ist bei Luftlinie leer. Luftlinie ist für ÖPNV (NVP 2019) und Nahversorgung (EHK 2014) die "
          "Potsdamer Messart; als Gehzeit taugt sie nicht.",
          "- Grundschule: Art `grundschule` = Schulform G. Grundschulteile in kombinierten Schulformen "
          "(sek1 `G/S`, `G/O/OG`) zählen nicht dazu; die nächste Grundschule kann deshalb näher liegen als "
          "angegeben. Ohne Schulbezirke (H2) bleibt der Wert vorläufig.",
          "- Kita und Hort: Entfernung zum nächsten Haus (auch weitere Häuser `#haus<n>` ohne Plätze). Kitas "
          "haben in Brandenburg keine Einzugsbereiche (Wunsch- und Wahlrecht); Entfernung ist Lage, keine "
          "Versorgung.",
          "- Gemeinbedarf aus ALKIS (Bibliothek, Feuerwehr, Sport, sonstiger Gemeinbedarf): nur Lage, ohne "
          "Kapazität; am Stadtrand Obergrenze (siehe Randeffekt).",
          "- Jugend, Senioren, Bürgerhaus: A2 erzeugt diese Arten erst, wenn B0 `auswertung.alkis_nas_gebaeude` "
          "gefüllt hat. Danach A2 und dieses Skript neu laufen lassen; das Skript liest die Arten aus der Tabelle.",
          ""]
    return "\n".join(t)


def main() -> int:
    k = konfiguration()
    jetzt = datetime.now(timezone.utc)
    heute = jetzt.strftime("%Y%m%d")
    lauf = jetzt.strftime("%Y%m%dT%H%M%SZ")
    with psycopg.connect("") as conn, conn.cursor() as cur:
        cur.execute("SELECT current_user")
        if cur.fetchone()[0] != "kiezatlas_rechnen":
            raise SystemExit("Bitte als kiezatlas_rechnen ausführen (PGUSER)")
        fuss = """SELECT (SELECT count(*) FROM auswertung.zelle_erreichbar WHERE methode = 'fussweg'),
                         (SELECT count(*) FROM auswertung.zelle_gruen WHERE methode = 'fussweg')"""
        fuss_vorher = q(cur, fuss)[0]
        vorbereiten(cur, k)
        erreichbar(cur, k)
        gruen(cur, k)
        randliste = rand(cur, k) + rand_gruen(cur, k)
        fuss_nachher = q(cur, fuss)[0]
        if fuss_vorher != fuss_nachher:
            raise SystemExit(f"Fußweg-Zeilen verändert: {fuss_vorher} -> {fuss_nachher}")
        text = bericht(cur, k, randliste, fuss_vorher, fuss_nachher, heute, lauf)
        n_e = q(cur, "SELECT count(*) FROM auswertung.zelle_erreichbar WHERE methode = 'luftlinie'")[0][0]
        n_g = q(cur, "SELECT count(*) FROM auswertung.zelle_gruen WHERE methode = 'luftlinie'")[0][0]
        conn.commit()
    BELEGE.mkdir(exist_ok=True)
    (BELEGE / f"A5a_erreichbarkeit_{heute}.md").write_text(text + "\n", encoding="utf-8")
    with (BELEGE / f"A5a_rand_unsicher_{heute}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["gitter_id", "art", "meter", "ew", "stadtteil", "abstand_rechteckrand_m", "abstand_berlin_m",
                    "grund"])
        w.writerows(randliste)
    print(f"zelle_erreichbar (luftlinie): {n_e} Zeilen; zelle_gruen (luftlinie): {n_g} Zeilen; "
          f"Rand unsicher: {len(randliste)}; Bericht belege/A5a_erreichbarkeit_{heute}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
