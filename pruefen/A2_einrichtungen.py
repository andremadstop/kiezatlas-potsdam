"""Prüfung Paket A2: auswertung.einrichtung und auswertung.gruenflaeche gegen Quelle und Abnahme.

Nur lesen, Rolle kiezatlas_rechnen (braucht TEMPORARY; mosidi_lesen darf das nicht). Prüft die Abnahme aus dem Bauplan (A2) mit den
Korrekturen des Prüfberichts (9, 12, 14, 26):
  1. Kitas in Potsdam je id_kita = Quelle, Plätze nur einmal gezählt (weitere Häuser ohne Plätze)
  2. Horte als eigene Art; Altersstruktur normiert; Kita-Hort-Kombinationen erkennbar
  3. Schulen in Potsdam = Quelle, davon Grundschulen (Schulform G)
  4. Einrichtungen außerhalb der Stadt mit in_potsdam = false erhalten
  5. Keine Spalte mit Telefon, Fax, E-Mail, Straße oder Hausnummer; kein OSM-Anteil
  6. Lizenzvermerk dl-de mit Link und „Daten verändert (eigene Berechnung)“ in jeder Zeile
  7. Gemeinbedarf aus ALKIS nur als Lage ohne Kapazität
  8. Grünarten = gruen_definition.arten in config/richtwerte.yaml, Flächen > 0
  9. Gegenprobebericht mit dem Anteil der Kitas mit ALKIS-Kitagebäude in 75 m
 10. Altersstruktur-Parser an allen Freitexten der Quelle

Aufruf wie skripte/11_einrichtungen.py, mit python -I pruefen/A2_einrichtungen.py. Rückgabe 0 = alles ok.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import psycopg
import yaml

WURZEL = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True   # kein skripte/__pycache__ beim Einlesen des Parsers
_spec = importlib.util.spec_from_file_location("einr", WURZEL / "skripte" / "11_einrichtungen.py")
einr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(einr)

befunde: list[str] = []


def pruef(ok: bool, text: str) -> None:
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        befunde.append(text)


def eins(cur, sql: str, args=()):
    cur.execute(sql, args)
    return cur.fetchone()


def main() -> int:
    with psycopg.connect("") as conn, conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE stadt AS SELECT ST_Union(ST_Transform(geom, 25833)) geom FROM public.stadtteil")
        HORT = "(altersstruktur = 'Kinder im Grundschulalter' OR einrichtungsart ILIKE '%%hort%%')"

        print("1. Kitas je Einrichtung")
        q_n, q_p = eins(cur, """SELECT count(*), sum(kapazitaet::int) FROM public.mbjs_kita k, stadt s
                                WHERE ST_Within(ST_Transform(k.geom, 25833), s.geom)""")
        a_n, a_p = eins(cur, """SELECT count(*), sum(plaetze) FROM auswertung.einrichtung
                                WHERE art IN ('kita','hort') AND status = 'kapazitaet' AND in_potsdam""")
        pruef(a_n == q_n, f"Kitas und Horte in Potsdam je id_kita: {a_n} (Quelle {q_n}; Bauplan 171 = Häuser, s. Bericht)")
        pruef(a_p == q_p, f"Plätze in Potsdam: {a_p} (Quelle je id_kita {q_p}; Bauplan 24.581 = je Haus summiert)")
        h_n, h_p = eins(cur, """SELECT count(*), coalesce(sum(plaetze), 0) FROM auswertung.einrichtung
                                WHERE id LIKE '%%#haus%%'""")
        pruef(h_n > 0 and h_p == 0, f"weitere Häuser: {h_n}, ohne Plätze (Summe {h_p})")
        g_n = eins(cur, """SELECT count(*) FROM auswertung.einrichtung
                           WHERE art IN ('kita','hort') AND in_potsdam""")[0]
        pruef(g_n == 171, f"Standorte (Häuser) in Potsdam: {g_n} (Bauplan 171)")

        print("2. Horte und Altersstruktur")
        q_h = eins(cur, f"""SELECT count(*) FROM public.mbjs_kita k, stadt s
                            WHERE ST_Within(ST_Transform(k.geom, 25833), s.geom) AND {HORT}""")[0]
        a_h = eins(cur, """SELECT count(*) FROM auswertung.einrichtung
                           WHERE art = 'hort' AND status = 'kapazitaet' AND in_potsdam""")[0]
        pruef(a_h == q_h and a_h > 0, f"Horte als eigene Art: {a_h} (Quelle {q_h}; Bauplan 39, s. Bericht)")
        leer = eins(cur, """SELECT count(*) FROM auswertung.einrichtung
                            WHERE art IN ('kita','hort') AND id NOT LIKE '%%#haus%%' AND altersstruktur IS NULL
                              AND in_potsdam""")[0]
        pruef(leer == 0, f"Kitas und Horte in Potsdam ohne lesbare Altersstruktur: {leer}")
        komb = eins(cur, """SELECT count(*) FROM auswertung.einrichtung
                            WHERE art = 'kita' AND unterart LIKE '%%hort' AND altersstruktur LIKE '%%-grundschulalter'""")[0]
        pruef(komb > 0, f"Kitas mit Hortteil (unterart *_hort, bis Grundschulalter): {komb}")

        print("3. Schulen")
        q_s = eins(cur, """SELECT count(*), count(*) FILTER (WHERE schulform_kurzbez = 'G')
                           FROM public.mbjs_schule k, stadt s WHERE ST_Within(ST_Transform(k.geom, 25833), s.geom)""")
        a_s = eins(cur, """SELECT count(*), count(*) FILTER (WHERE art = 'grundschule') FROM auswertung.einrichtung
                           WHERE in_potsdam AND quelle LIKE 'MBJS WFS ms:Schul%%'""")
        pruef(a_s == q_s and a_s == (78, 34), f"Schulen in Potsdam {a_s[0]}, davon Grundschulen {a_s[1]} (Bauplan 78/34)")
        ohne = eins(cur, "SELECT count(*) FROM auswertung.einrichtung WHERE art = 'sonstige_schule' AND unterart "
                         "NOT IN ('WS','ZBW')")[0]
        pruef(ohne == 0, f"Schulformen ohne Zuordnung: {ohne}")

        print("4. Randeffekt")
        aus = eins(cur, """SELECT count(*) FILTER (WHERE quelle LIKE 'MBJS%%'),
                                  count(*) FILTER (WHERE quelle LIKE 'MBJS%%' AND NOT in_potsdam)
                           FROM auswertung.einrichtung""")
        q_aus = eins(cur, """SELECT (SELECT count(*) FROM public.mbjs_kita) + (SELECT count(*) FROM public.mbjs_schule)""")[0]
        pruef(aus[1] > 0, f"MBJS-Einrichtungen außerhalb der Stadt mit in_potsdam = false: {aus[1]}")
        pruef(aus[0] - h_n == q_aus, f"alle MBJS-Einrichtungen des Rechtecks erhalten: {aus[0] - h_n} (Quelle {q_aus})")

        print("5. Datenschutz und Lizenzgrenze")
        cur.execute("""SELECT table_name, column_name FROM information_schema.columns
                       WHERE table_schema = 'auswertung' AND table_name IN ('einrichtung', 'gruenflaeche')""")
        spalten = cur.fetchall()
        verboten = [f"{t}.{c}" for t, c in spalten
                    if re.search(r"tel|fax|mail|strasse|straße|hausn|adress|homepage", c, re.I)]
        pruef(not verboten, f"keine Kontakt- oder Adressspalte ({len(spalten)} Spalten geprüft) {verboten or ''}")
        osm = eins(cur, """SELECT (SELECT count(*) FROM auswertung.einrichtung WHERE quelle || lizenz ~* 'openstreetmap|odbl|osm')
                                + (SELECT count(*) FROM auswertung.gruenflaeche WHERE quelle || lizenz ~* 'openstreetmap|odbl|osm')""")[0]
        pruef(osm == 0, f"kein OSM-Anteil: {osm} Zeilen mit OSM/ODbL")
        mail = eins(cur, r"""SELECT count(*) FROM auswertung.einrichtung
                             WHERE name ~ '@|\+49|\d{4,}[ /-]\d{3,}'""")[0]
        pruef(mail == 0, f"keine Kontaktangabe im Namen: {mail}")

        print("6. Lizenzvermerk")
        for t in ("einrichtung", "gruenflaeche"):
            n = eins(cur, f"""SELECT count(*) FROM auswertung.{t}
                              WHERE lizenz NOT LIKE '%%https://www.govdata.de/dl-de/by-2-0%%'
                                 OR lizenz NOT LIKE '%%Daten verändert (eigene Berechnung)%%'""")[0]
            pruef(n == 0, f"auswertung.{t}: Zeilen ohne vollständigen dl-de-Vermerk: {n}")

        print("7. Gemeinbedarf aus ALKIS")
        r = eins(cur, """SELECT count(*), count(*) FILTER (WHERE status <> 'lage_ohne_kapazitaet' OR plaetze IS NOT NULL
                                                             OR schueler IS NOT NULL OR name IS NOT NULL),
                                count(DISTINCT art)
                         FROM auswertung.einrichtung WHERE id LIKE 'alkis:%%'""")
        pruef(r[0] > 0 and r[1] == 0, f"ALKIS-Gemeinbedarf: {r[0]} Standorte in {r[2]} Arten, alle nur Lage ohne Kapazität")
        for art in ("bibliothek", "feuerwehr", "sport", "sonstiger_gemeinbedarf"):
            n = eins(cur, "SELECT count(*) FROM auswertung.einrichtung WHERE art = %s AND in_potsdam", (art,))[0]
            pruef(n > 0, f"  {art} in Potsdam: {n}")

        print("8. Grünflächen")
        arten = set((yaml.safe_load((WURZEL / "config" / "richtwerte.yaml").read_text(encoding="utf-8"))
                     ["gruen_definition"]["arten"]).keys())
        cur.execute("SELECT art, count(*), min(flaeche_m2) FROM auswertung.gruenflaeche GROUP BY 1")
        da = {a: (n, m) for a, n, m in cur.fetchall()}
        pruef(set(da) == arten, f"Grünarten {sorted(da)} = gruen_definition.arten {sorted(arten)}")
        pruef(all(m > 0 for _, m in da.values()), "alle Grünflächen mit Fläche > 0 m²")
        geo = eins(cur, "SELECT count(*) FROM auswertung.gruenflaeche WHERE NOT ST_IsValid(geom)")[0]
        pruef(geo == 0, f"ungültige Geometrien: {geo}")

    print("9. Gegenprobebericht")
    b = WURZEL / "berichte" / "A2_gegenprobe.md"
    text = b.read_text(encoding="utf-8") if b.exists() else ""
    m = re.search(r"\| Kitas \(Einrichtung, Hauptstandort\) \|[^|]*\| \d+ \|[^|]*\| (\d+) \((\d+) %\)", text)
    pruef(bool(m), f"Anteil Kitas mit ALKIS-Kitagebäude in 75 m ausgewiesen: "
                   f"{m.group(1) + ' (' + m.group(2) + ' %)' if m else 'fehlt'}")

    print("10. Altersstruktur-Parser")
    faelle = {
        ("Kombinierte Einrichtung", "1 1/2 Jahre bis Schuleintritt"): ("kita", "krippe_kindergarten", "18m-schuleintritt"),
        ("Kombinierte Einrichtung", "2 Jahre bis einschließlich Grundschullalter"):
            ("kita", "krippe_kindergarten_hort", "24m-grundschulalter"),
        ("Kinderhort", "Kinder im Grundschulalter"): ("hort", "hort", "72m-grundschulalter"),
        ("Kindergarten", "Kindergartenkinder 3 Jahre bis Einschulung"): ("kita", "kindergarten", "36m-schuleintritt"),
        ("Andere Angebote in der Kindertagesbetreuung", "Krippenkinder 0 bis 3 Jahre"): ("kita", "krippe", "0m-36m"),
        ("Kombinierte Einrichtung", "9 Monate bis einschließlich Grundschulalter"):
            ("kita", "krippe_kindergarten_hort", "9m-grundschulalter"),
        ("Kombinierte Einrichtung", "5 Jahre bis einschließlich Grundschulalter"):
            ("kita", "kindergarten_hort", "60m-grundschulalter"),
        ("Eltern-Kind-Gruppe", "Sonstiges"): ("kita", "sonstige", None),
    }
    falsch = [f"{k} → {einr.kita_art(*k)}" for k, v in faelle.items() if einr.kita_art(*k) != v]
    pruef(not falsch, f"{len(faelle)} Freitexte richtig gelesen {falsch or ''}")
    pruef(einr.schueler_lesen("478 (Stand: 2022)") == (478, "2022") and einr.schueler_lesen("") == (None, None),
          "Schülerzahl mit Stand gelesen")

    print(f"\n{len(befunde)} Befund(e)")
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
