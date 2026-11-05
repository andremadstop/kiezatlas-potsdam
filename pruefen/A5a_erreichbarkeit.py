"""Prüfung Paket A5a: auswertung.zelle_erreichbar und auswertung.zelle_gruen (Luftlinie) gegen die Abnahme.

Nur lesen (Rolle kiezatlas_rechnen, TEMP für eine Hilfstabelle). Prüft die Abnahme aus dem Bauplan (A5)
mit den Korrekturen des Prüfberichts (22, 26) und rechnet die Werte unabhängig nach:
  1. Abdeckung: jede bewohnte Potsdamer Zelle (3.411) und jede Art aus auswertung.einrichtung plus „gruen“
     hat eine Luftlinie-Zeile mit Meterwert; dazu die 3.443 Zellen von daten/zellen.js
  2. Gegenrechnung Einrichtungen: Minimum über alle Standorte in Python (ohne Datenbank-Index, ohne KNN),
     jede Zeile, Toleranz 0,1 m; die Zeile verweist auf einen Standort genau in diesem Abstand
  3. Gegenrechnung Grünabstand: Minimum von ST_Distance über alle zählenden Flächen, ohne KNN, 60 Zellen
  4. E7: Einrichtungen außerhalb der Stadt zählen; eine Randzelle in Golm hat eine nähere Einrichtung
     außerhalb als innerhalb
  5. methode in jeder Zeile gesetzt; minuten bei Luftlinie leer; Fußweg-Zeilen (A5b) gezählt
  6. Lizenz: dl-de/by-2-0 mit Link und „Daten verändert (eigene Berechnung)“, Zensus-Vermerk; kein OSM, kein ODbL
  7. Grün: 0 ≤ m2_gruen ≤ Kreisfläche; Fläche per 10-m-Punktraster nachgezählt (40 Zellen);
     m2_je_ew = m2_gruen / Einwohner im Kreis, Einwohner in Python nachgerechnet (alle Zellen)
  8. Randliste (belege/A5a_rand_unsicher_<datum>.csv): Zellen und Arten existieren
  9. Skripte: schreiben nur in zelle_erreichbar und zelle_gruen, kein Netzmodul

Aufruf wie skripte/14_erreichbarkeit.py, mit python -I pruefen/A5a_erreichbarkeit.py. Rückgabe 0 = alles ok.
Protokoll: belege/A5a_pruefung_<datum>.txt
"""
from __future__ import annotations

import csv
import math
import random
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import yaml

WURZEL = Path(__file__).resolve().parent.parent
BELEGE = WURZEL / "belege"
SKRIPT = WURZEL / "skripte" / "14_erreichbarkeit.py"
DLDE_LINK = "https://www.govdata.de/dl-de/by-2-0"

aus: list[str] = []
befunde: list[str] = []


def log(text: str) -> None:
    aus.append(text)
    print(text)


def pruefe(ok: bool, was: str, beleg: str) -> None:
    log(f"[{'ok' if ok else 'FEHLER'}] {was}: {beleg}")
    if not ok:
        befunde.append(was)


def main() -> int:
    rw = yaml.safe_load((WURZEL / "config" / "richtwerte.yaml").read_text(encoding="utf-8"))
    zaehlt = sorted(a for a, d in rw["gruen_definition"]["arten"].items() if d.get("zaehlt_vorschlag") is True)
    r_cfg = rw["gruen"]["radius_m"]["wert"]
    radien = [int(r) for r in (r_cfg if isinstance(r_cfg, list) else [r_cfg])]
    jetzt = datetime.now(timezone.utc)
    log(f"Prüfung A5a, {jetzt.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    rnd = random.Random(20261105)

    with psycopg.connect("") as conn, conn.cursor() as cur:
        def q(sql: str, args=()) -> list:
            cur.execute(sql, args)
            return cur.fetchall()

        # Zellen und Standorte (EPSG:25833)
        zellen = {g: (x, y, ew, st) for g, x, y, ew, st in q("""
            SELECT z.gitter_id, ST_X(t.g), ST_Y(t.g), z.ew, s.nr
            FROM public.zensus_zelle z JOIN public.stadtteil s ON ST_Contains(s.geom, z.geom),
                 LATERAL (SELECT ST_Transform(z.geom, 25833) AS g) t
            WHERE z.ew IS NOT NULL""")}
        bewohnt = {g for g, v in zellen.items() if v[2] > 0}
        ziele = q("SELECT id, art, ST_X(geom), ST_Y(geom), in_potsdam FROM auswertung.einrichtung")
        arten = sorted({a for _, a, *_ in ziele})
        zeilen = q("""SELECT gitter_id, art, methode, meter::float8, minuten, ziel_id, quelle_lizenz
                      FROM auswertung.zelle_erreichbar WHERE methode = 'luftlinie'""")
        wert = {(g, a): (m, zid) for g, a, _, m, _, zid, _ in zeilen}

        # 1. Abdeckung
        log(f"Zellen mit Mittelpunkt in Potsdam: {len(zellen)}, davon bewohnt: {len(bewohnt)}; Arten: {arten} + gruen")
        alle_arten = arten + ["gruen"]
        fehlt_bew = [(g, a) for g in bewohnt for a in alle_arten if wert.get((g, a), (None,))[0] is None]
        fehlt_alle = [(g, a) for g in zellen for a in alle_arten if wert.get((g, a), (None,))[0] is None]
        pruefe(len(bewohnt) == 3411 and not fehlt_bew, "1a Abdeckung bewohnte Zellen × Arten",
               f"{len(bewohnt)} Zellen × {len(alle_arten)} Arten = {len(bewohnt) * len(alle_arten)} erwartet, "
               f"fehlend {len(fehlt_bew)}")
        pruefe(len(zellen) == 3443 and not fehlt_alle, "1b Abdeckung Zellen von zellen.js",
               f"{len(zellen)} Zellen, fehlend {len(fehlt_alle)}, Luftlinie-Zeilen {len(zeilen)}")
        fremd = [r for r in zeilen if r[0] not in zellen]
        pruefe(not fremd, "1c keine Zeile für Zellen außerhalb", f"{len(fremd)} Zeilen")

        # 2. Gegenrechnung Einrichtungen, alle Zeilen, ohne KNN
        je_art = defaultdict(list)
        for zid, a, x, y, _ in ziele:
            je_art[a].append((zid, x, y))
        pos = {zid: (x, y) for zid, _, x, y, _ in ziele}
        abw, ziel_falsch = [], []
        for g, (x, y, _, _) in zellen.items():
            for a in arten:
                d = min(math.hypot(x - ex, y - ey) for _, ex, ey in je_art[a])
                m, zid = wert[(g, a)]
                if abs(m - d) > 0.1:
                    abw.append((g, a, m, round(d, 1)))
                zx, zy = pos[zid]
                if abs(math.hypot(x - zx, y - zy) - m) > 0.1:
                    ziel_falsch.append((g, a, zid))
        pruefe(not abw, "2a Gegenrechnung Meter (Python, alle Standorte, ohne KNN)",
               f"{len(zellen) * len(arten)} Werte, Abweichung > 0,1 m: {len(abw)} {abw[:3]}")
        pruefe(not ziel_falsch, "2b ziel_id liegt im angegebenen Abstand", f"{len(ziel_falsch)} Abweichungen")

        # 3. Gegenrechnung Grünabstand (ohne KNN, ohne Index-Operator)
        stich = rnd.sample(sorted(zellen), 60)
        abw_g = []
        for g in stich:
            (d,) = q("""SELECT min(ST_Distance(f.geom, ST_Transform(z.geom, 25833)))::float8
                        FROM auswertung.gruenflaeche f, public.zensus_zelle z
                        WHERE z.gitter_id = %s AND f.art = ANY(%s)""", (g, zaehlt))[0]
            if abs(wert[(g, "gruen")][0] - d) > 0.1:
                abw_g.append((g, wert[(g, "gruen")][0], round(d, 1)))
        pruefe(not abw_g, "3 Gegenrechnung Grünabstand (60 Zellen, ST_Distance über alle Flächen)",
               f"Abweichungen > 0,1 m: {len(abw_g)} {abw_g[:3]}")

        # 4. E7
        aussen = sum(1 for *_, drin in ziele if not drin)
        in_stadt = {zid: drin for zid, _, _, _, drin in ziele}
        golm = []
        for g, (x, y, ew, st) in zellen.items():
            if st != "17" or ew <= 0:
                continue
            for a in arten:
                m, zid = wert[(g, a)]
                drin = [math.hypot(x - ex, y - ey) for i, ex, ey in je_art[a] if in_stadt[i]]
                if not in_stadt[zid] and drin and m < min(drin):
                    golm.append((g, a, round(m), round(min(drin)), zid))
        n_aussen_ziel = sum(1 for (g, a), (m, zid) in wert.items() if a != "gruen" and not in_stadt[zid])
        pruefe(aussen > 0 and n_aussen_ziel > 0, "4a Einrichtungen außerhalb der Stadt gerechnet",
               f"{aussen} Standorte außerhalb in auswertung.einrichtung; {n_aussen_ziel} Zeilen mit Ziel außerhalb")
        bsp = sorted(golm, key=lambda t: (t[1] != "kita", t[2] - t[3]))[:3]
        pruefe(bool(golm), "4b Golm: Randzelle mit näherer Einrichtung außerhalb als innerhalb",
               f"{len(golm)} Fälle (Zelle × Art), {len({t[0] for t in golm})} Zellen; Beispiele "
               + "; ".join(f"{g} {a}: außerhalb {m} m ({zid}), nächste in Potsdam {d} m" for g, a, m, d, zid in bsp))

        # 5. methode, minuten, Fußweg
        (ohne_methode, mit_minuten, fuss_e, fuss_g) = q("""
            SELECT (SELECT count(*) FROM auswertung.zelle_erreichbar WHERE methode IS NULL OR methode = ''),
                   (SELECT count(*) FROM auswertung.zelle_erreichbar
                    WHERE methode = 'luftlinie' AND minuten IS NOT NULL),
                   (SELECT count(*) FROM auswertung.zelle_erreichbar WHERE methode = 'fussweg'),
                   (SELECT count(*) FROM auswertung.zelle_gruen WHERE methode = 'fussweg')""")[0]
        pruefe(ohne_methode == 0, "5a methode in jeder Zeile gesetzt", f"{ohne_methode} Zeilen ohne methode")
        pruefe(mit_minuten == 0, "5b minuten bei Luftlinie leer", f"{mit_minuten} Zeilen mit minuten")
        log(f"     Fußweg-Zeilen (A5b, nicht von A5a): zelle_erreichbar {fuss_e}, zelle_gruen {fuss_g}")

        # 6. Lizenz
        gr = q("SELECT gitter_id, radius_m, m2_gruen::float8, m2_je_ew::float8, quelle_lizenz "
               "FROM auswertung.zelle_gruen WHERE methode = 'luftlinie'")
        lizenzen = [r[6] for r in zeilen] + [r[4] for r in gr]
        # jeder Teilvermerk (getrennt durch „; “) braucht Link und Bearbeitungshinweis (Korrektur 26)
        schlecht = [t for t in set(lizenzen)
                    if "Zensus 2022" not in t or re.search(r"openstreetmap|odbl|\bosm\b", t, re.I)
                    or not all("dl-de/by-2-0" in teil and DLDE_LINK in teil
                               and "Daten verändert (eigene Berechnung)" in teil for teil in t.split("; "))]
        pruefe(not schlecht, "6 Lizenzvermerk je Zeile und Teil (dl-de mit Link, verändert, Zensus; kein OSM/ODbL)",
               f"{len(set(lizenzen))} verschiedene Vermerke, davon fehlerhaft {len(schlecht)}")
        gruen_ids = {i for (i,) in q("SELECT id FROM auswertung.gruenflaeche")}
        ohne_ziel = [(g, a, zid) for g, a, _, _, _, zid, _ in zeilen
                     if zid not in (gruen_ids if a == "gruen" else pos)]
        pruefe(not ohne_ziel, "6b jede ziel_id existiert", f"{len(ohne_ziel)} ohne Ziel")

        # 7. Grün
        ew_pkt = q("SELECT ST_X(g), ST_Y(g), ew FROM (SELECT ST_Transform(geom, 25833) g, ew FROM public.zensus_zelle "
                   "WHERE ew > 0) s")
        for r in radien:
            gz = {g: (m2, je) for g, rad, m2, je, _ in gr if rad == r}
            kreis = math.pi * r * r
            pruefe(set(gz) == set(zellen), f"7a zelle_gruen r={r}: eine Zeile je Zelle", f"{len(gz)} Zeilen")
            ausser = [g for g, (m2, _) in gz.items() if m2 is None or m2 < 0 or m2 > kreis * 1.0001]
            pruefe(not ausser, f"7b 0 ≤ m2_gruen ≤ Kreisfläche (r={r})", f"{len(ausser)} außerhalb")
            # m2_je_ew: Einwohner im Kreis in Python
            abw_je = []
            for g, (m2, je) in gz.items():
                x, y = zellen[g][:2]
                ew_k = sum(e for ex, ey, e in ew_pkt if abs(ex - x) <= r and abs(ey - y) <= r
                           and math.hypot(ex - x, ey - y) <= r)
                soll = round(m2 / ew_k, 2) if ew_k > 0 else None
                if (soll is None) != (je is None) or (soll is not None and abs(soll - je) > 0.011):
                    abw_je.append((g, je, soll))
            pruefe(not abw_je, f"7c m2_je_ew = m2_gruen / Einwohner im Kreis (r={r}, Python, alle Zellen)",
                   f"{len(abw_je)} Abweichungen {abw_je[:3]}")
            # Fläche per Punktraster (10 m), 40 Zellen
            cur.execute("CREATE TEMP TABLE IF NOT EXISTS p_gruen AS SELECT geom AS g FROM auswertung.gruenflaeche "
                        "WHERE art = ANY(%s)", (zaehlt,))
            cur.execute("CREATE INDEX IF NOT EXISTS p_gruen_g ON p_gruen USING gist (g)")
            abw_f = []
            for g in rnd.sample(sorted(zellen), 40):
                x, y = zellen[g][:2]
                schritte = range(-r // 10, r // 10)
                pkte = [(x + i * 10 + 5, y + j * 10 + 5) for i in schritte for j in schritte
                        if math.hypot(i * 10 + 5, j * 10 + 5) <= r]
                wkt = "MULTIPOINT(" + ",".join(f"({a:.2f} {b:.2f})" for a, b in pkte) + ")"
                (n,) = q("""SELECT count(*) FROM (SELECT (ST_Dump(ST_GeomFromText(%s, 25833))).geom AS p) d
                            WHERE EXISTS (SELECT 1 FROM p_gruen f WHERE ST_Intersects(f.g, d.p))""", (wkt,))[0]
                m2 = gz[g][0]
                if abs(n * 100 - m2) > max(0.01 * kreis, 0.03 * m2):
                    abw_f.append((g, m2, n * 100))
            pruefe(not abw_f, f"7d Grünfläche per 10-m-Punktraster nachgezählt (r={r}, 40 Zellen, Toleranz 1 % "
                   "der Kreisfläche oder 3 %)", f"{len(abw_f)} Abweichungen {abw_f[:3]}")
        conn.rollback()

    # 8. Randliste
    listen = sorted(BELEGE.glob("A5a_rand_unsicher_*.csv"))
    if listen:
        with listen[-1].open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f, delimiter=";"))
        gueltig = set(alle_arten) | {f"gruen_{r}m" for r in radien}
        falsch = [r for r in rows if r["gitter_id"] not in zellen or r["art"] not in gueltig
                  or not set(r["grund"].split("+")) <= {"rechteck", "berlin"}]
        pruefe(not falsch, "8 Randliste: Zellen, Arten, Gründe gültig", f"{listen[-1].name}: {len(rows)} Zeilen, "
               f"{len(falsch)} ungültig")
    else:
        pruefe(False, "8 Randliste vorhanden", "keine belege/A5a_rand_unsicher_*.csv")

    # 9. Skripte statisch
    quelltext = SKRIPT.read_text(encoding="utf-8")
    ziele_schreiben = set(re.findall(r"(?:INSERT INTO|DELETE FROM|UPDATE|TRUNCATE)\s+([a-z_.]+)", quelltext, re.I))
    pruefe(ziele_schreiben <= {"auswertung.zelle_erreichbar", "auswertung.zelle_gruen"},
           "9a 14_erreichbarkeit.py schreibt nur eigene Tabellen", f"Schreibziele {sorted(ziele_schreiben)}")
    netz = [m for p in (SKRIPT, Path(__file__))
            for m in re.findall(r"^\s*(?:import|from)\s+(requests|urllib|http|socket|aiohttp)\b",
                                p.read_text(encoding="utf-8"), re.M)]
    pruefe(not netz, "9b kein Netzmodul in Skript und Prüfung", f"{netz or 'keins'}")

    log(f"Ergebnis: {len(befunde)} Befunde" + (f": {befunde}" if befunde else ""))
    BELEGE.mkdir(exist_ok=True)
    (BELEGE / f"A5a_pruefung_{jetzt.strftime('%Y%m%d')}.txt").write_text("\n".join(aus) + "\n", encoding="utf-8")
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
