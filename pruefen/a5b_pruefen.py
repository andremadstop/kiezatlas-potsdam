"""Abnahme A5b (Fußweg je Zelle) gegen die Datenbank. Nur lesen, am Ende ROLLBACK (TEMP-Tabellen).

Kriterien (Bauplan A5, Teil A5b):
  K1  Für jede Potsdamer Zelle (Menge von daten/zellen.js, darin alle bewohnten) und jede gerechnete Art gibt es
      genau eine Fußweg-Zeile; bewohnte Zellen ohne Wert werden gezählt und genannt
  K2  Für jede Zelle gilt Fußweg ≥ Luftlinie (0 Verstöße). Die Luftlinie wird hier unabhängig vom Rechenskript
      ermittelt: Minimum von ST_Distance über alle Ziele der Art, ohne Index und ohne KNN.
      Liegen schon Luftlinie-Zeilen von A5a vor, werden sie zusätzlich verglichen (Hinweis, kein Kriterium,
      weil A5a eine andere Zielmenge gewählt haben kann).
  K3  Median Fußweg/Luftlinie zwischen 1,1 und 1,6 (über Zellen mit Luftlinie ≥ 100 m), sonst Ursache im Bericht
  K4  methode ist bei jeder Zeile gesetzt; jede Fußweg-Zeile (zelle_erreichbar und zelle_gruen) trägt ODbL

Aufruf: skripte/14b_fussweg.sh pruefen      Ausgang 0 = alle Kriterien erfüllt
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "skripte"))
fw = importlib.import_module("14b_fussweg")


def vorbereiten(cur) -> tuple[list[str], set[str], dict]:
    """TEMP-Tabellen a5b_zelle und a5b_ziel wie im Rechenskript (mit Landesfilter E7).

    Gibt Zell-IDs, bewohnte Zell-IDs und den Befund des Landesfilters zurück."""
    rw = fw.richtwerte()
    ids, xy, ew = fw.zellen_laden(cur)
    fw.zellen_temp(cur, ids, xy)
    land = fw.ziele_anlegen(cur, rw["gruen_arten"])
    return ids, {i for i, e in zip(ids, ew.tolist()) if e > 0}, land


def pruefen(cur) -> list[tuple[str, bool, str]]:
    ids, bewohnt, land = vorbereiten(cur)
    n = len(ids)
    erg: list[tuple[str, bool, str]] = []

    # K1
    cur.execute("""SELECT e.art, count(*), count(DISTINCT e.gitter_id), count(*) FILTER (WHERE c.gitter_id IS NULL),
                          count(e.meter)
                   FROM auswertung.zelle_erreichbar e LEFT JOIN a5b_zelle c USING (gitter_id)
                   WHERE e.methode = 'fussweg' GROUP BY e.art ORDER BY e.art""")
    je_art = cur.fetchall()
    fehl = [f"{a}: {z} Zeilen, {d} Zellen, {fremd} fremd" for a, z, d, fremd, _ in je_art
            if z != n or d != n or fremd]
    cur.execute("SELECT art, gitter_id FROM auswertung.zelle_erreichbar WHERE methode = 'fussweg' AND meter IS NULL")
    ohne = {}
    for a, g in cur.fetchall():
        if g in bewohnt:
            ohne[a] = ohne.get(a, 0) + 1
    ok1 = bool(je_art) and not fehl and len(bewohnt) > 0
    erg.append(("K1 je Zelle und Art eine Fußweg-Zeile", ok1,
                f"{len(je_art)} Arten × {n} Zellen (davon {len(bewohnt)} bewohnt); "
                + ("; ".join(fehl) if fehl else "vollständig")
                + "; bewohnte Zellen ohne Wert: " + (", ".join(f"{a} {c}" for a, c in sorted(ohne.items()))
                                                    if ohne else "0")))

    # K2: Luftlinie unabhängig (Minimum ohne Index), Vergleich mit dem gespeicherten Fußweg
    cur.execute("""
      CREATE TEMP TABLE a5b_luft ON COMMIT DROP AS
        SELECT e.gitter_id, e.art, e.meter::float8 AS fuss, min(ST_Distance(c.g, z.geom)) AS luft
        FROM auswertung.zelle_erreichbar e
        JOIN a5b_zelle c USING (gitter_id)
        JOIN a5b_ziel z ON z.art = e.art
        WHERE e.methode = 'fussweg' AND e.meter IS NOT NULL
        GROUP BY e.gitter_id, e.art, e.meter""")
    cur.execute("SELECT count(*), count(*) FILTER (WHERE fuss < luft) FROM a5b_luft")
    verglichen, verstoesse = cur.fetchone()
    cur.execute("SELECT art, gitter_id, fuss, luft FROM a5b_luft WHERE fuss < luft ORDER BY luft - fuss DESC LIMIT 5")
    bsp = cur.fetchall()
    erg.append(("K2 Fußweg ≥ Luftlinie (0 Verstöße)", verglichen > 0 and verstoesse == 0,
                f"{verglichen} Zellwerte verglichen, {verstoesse} Verstöße" + (f", z. B. {bsp}" if bsp else "")))

    cur.execute("""SELECT count(*), count(*) FILTER (WHERE f.meter < l.meter)
                   FROM auswertung.zelle_erreichbar f JOIN auswertung.zelle_erreichbar l
                     ON l.gitter_id = f.gitter_id AND l.art = f.art AND l.methode = 'luftlinie'
                   WHERE f.methode = 'fussweg' AND f.meter IS NOT NULL AND l.meter IS NOT NULL""")
    a5a_n, a5a_v = cur.fetchone()

    # K3
    cur.execute(f"""SELECT art, percentile_cont(0.5) WITHIN GROUP (ORDER BY fuss / luft), count(*)
                    FROM a5b_luft WHERE luft >= {fw.MIN_LUFTLINIE_VERHAELTNIS_M} GROUP BY ROLLUP (art) ORDER BY art""")
    med = cur.fetchall()
    gesamt = next((m for a, m, _ in med if a is None), None)
    ok3 = gesamt is not None and 1.1 <= gesamt <= 1.6
    beleg3 = ("keine Werte" if gesamt is None else
              f"gesamt {gesamt:.3f}; je Art: " + ", ".join(f"{a} {m:.2f} (n={c})" for a, m, c in med if a))
    erg.append(("K3 Median Fußweg/Luftlinie zwischen 1,1 und 1,6", ok3, beleg3))

    # K4
    cur.execute("""SELECT count(*), count(*) FILTER (WHERE methode IS NULL OR methode = ''),
                          count(*) FILTER (WHERE methode = 'fussweg' AND quelle_lizenz NOT ILIKE '%%ODbL%%')
                   FROM auswertung.zelle_erreichbar""")
    z_all, z_ohne, z_odbl = cur.fetchone()
    cur.execute("""SELECT count(*) FILTER (WHERE methode = 'fussweg'),
                          count(*) FILTER (WHERE methode = 'fussweg' AND quelle_lizenz NOT ILIKE '%%ODbL%%')
                   FROM auswertung.zelle_gruen""")
    g_fuss, g_odbl = cur.fetchone()
    cur.execute("SELECT obj_description('auswertung.zelle_erreichbar'::regclass) ILIKE '%ODbL%'")
    kommentar = cur.fetchone()[0]
    erg.append(("K4 methode gesetzt, Fußweg-Zeilen tragen ODbL", z_ohne == 0 and z_odbl == 0 and g_odbl == 0
                and kommentar,
                (f"zelle_erreichbar {z_all} Zeilen, ohne methode {z_ohne}, Fußweg ohne ODbL {z_odbl}; "
                f"zelle_gruen Fußweg {g_fuss} Zeilen, ohne ODbL {g_odbl}; Tabellenkommentar nennt ODbL: {kommentar}")))

    # E7, Berlin nein: jedes Ziel einer Fußweg-Zeile steht im gefilterten Zielbestand, keine Berliner Haltestelle
    cur.execute("""SELECT count(*) FILTER (WHERE z.ziel_id IS NULL),
                          count(*) FILTER (WHERE e.ziel_id LIKE %s)
                   FROM auswertung.zelle_erreichbar e
                   LEFT JOIN a5b_ziel z ON z.art = e.art AND z.ziel_id = e.ziel_id
                   WHERE e.methode = 'fussweg' AND e.ziel_id IS NOT NULL""", (f"de:{fw.LAND_BERLIN}%",))
    ausserhalb, berlin_halt = cur.fetchone()
    erg.append(("E7 keine Berliner Ziele", ausserhalb == 0 and berlin_halt == 0,
                (f"Ziele außerhalb des gefilterten Bestands: {ausserhalb}, Berliner Haltestellen: {berlin_halt}; "
                 f"als Berlin ausgelassen: {land['berlin_ausgelassen'] or 'keine'} ({land['land_quelle']})")))

    # E7: Ziele außerhalb der Stadtgrenze (Brandenburg) werden mitgerechnet
    cur.execute("""SELECT e.art, count(*) FROM auswertung.zelle_erreichbar e
                   JOIN auswertung.einrichtung i ON i.id = e.ziel_id AND i.art = e.art AND NOT i.in_potsdam
                   WHERE e.methode = 'fussweg' GROUP BY e.art ORDER BY e.art""")
    aussen = cur.fetchall()
    erg.append(("Hinweis E7: nächstes Ziel außerhalb der Stadtgrenze", True,
                ", ".join(f"{a} {c} Zellen" for a, c in aussen) if aussen else "keine Zelle"))
    erg.append(("Hinweis: Vergleich mit A5a-Luftlinie", True,
                f"{a5a_n} Paare, davon Fußweg < A5a-Luftlinie: {a5a_v}" if a5a_n else "noch keine Luftlinie-Zeilen"))
    return erg


def main() -> int:
    with fw.verbinden() as conn, conn.cursor() as cur:
        erg = pruefen(cur)
        conn.rollback()
    for k, ok, beleg in erg:
        print(f"[{'ok' if ok else 'FEHLT'}] {k}: {beleg}")
    return 0 if all(ok for _, ok, _ in erg) else 1


if __name__ == "__main__":
    sys.exit(main())
