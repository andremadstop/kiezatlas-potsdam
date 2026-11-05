"""Paket A2: amtliche Einrichtungen, Gemeinbedarf aus ALKIS und Grünflächen nach `auswertung`.

Kein Netzabruf. Liest:
  public.mbjs_kita, public.mbjs_schule        (P0 lädt per --nur, © MBJS, dl-de/by-2-0)
  $KIEZ_DATEN/mbjs/2026-11-05/kitas_standorte.geojson   (alle Häuser je Kita, ohne Adresse und Kontakt)
  auswertung.gebaeude_stand_20261105           (Snapshot der ALKIS-Gebäude, © GeoBasis-DE/LGB)
  public.alkis_nutzung                         (ALKIS vereinfacht, tatsächliche Nutzung)
  public.stadtteil                             (Stadtgrenze für in_potsdam)
  config/richtwerte.yaml, Abschnitt gruen_definition (welche Nutzung welche Grünart ist)
Schreibt (Rolle kiezatlas_rechnen, eine Transaktion, vorher geleert):
  auswertung.einrichtung   Kitas und Horte getrennt, Schulen nach Schulform, Gemeinbedarf aus ALKIS
                           nur als Lage (status lage_ohne_kapazitaet, Prüfbericht 12)
  auswertung.gruenflaeche  Grünarten laut gruen_definition, Fläche in m² (EPSG:25833)
  berichte/A2_gegenprobe.md  Gegenprobe ALKIS-Gebäude gegen MBJS-Punkte

Datenschutz: Aus MBJS werden nur Name, Art, Altersstruktur, Kapazität bzw. Schülerzahl übernommen.
Telefon, Fax, E-Mail, Straße und Hausnummer gibt es weder in den Quelltabellen noch hier.

Aufruf (aus dem Worktree; Passwort nur aus der .env, nie auf der Kommandozeile ausgeschrieben):
    set -a; . ../kiezatlas-potsdam/.env; set +a
    PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=kiezatlas_rechnen PGPASSWORD="$RECHNEN_PASSWORD" \\
    uv run -q --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \\
        python -I skripte/11_einrichtungen.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import psycopg
import yaml

WURZEL = Path(__file__).resolve().parent.parent
DATEN = Path(os.environ.get("KIEZ_DATEN") or WURZEL.parent / "kiezatlas-daten")
STANDORTE = DATEN / "mbjs" / "2026-11-05" / "kitas_standorte.geojson"
BERICHT = WURZEL / "berichte" / "A2_gegenprobe.md"

DLDE = "dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)"
LIZENZ_MBJS = f"© Ministerium für Bildung, Jugend und Sport, {DLDE}"
LIZENZ_LGB = f"© GeoBasis-DE/LGB, {DLDE}"
STAND_MBJS = date(2026, 11, 5)      # Abruf der Pipeline (belege/20261105T093628Z, …093707Z)
STAND_ALKIS_GEB = date(2026, 11, 4)  # Pipeline-Lauf 20261104T132333Z, Snapshot vom 05.11.
STAND_ALKIS_NUTZ = date(2026, 11, 5)

# ------------------------------------------------------------------ Kitas: Altersstruktur lesen
# Freitext des MBJS, z. B. „1 1/2 Jahre bis Schuleintritt“, „2 Jahre bis einschließlich Grundschullalter“
# (Tippfehler in der Quelle), „Kinder im Grundschulalter“, „Krippenkinder 0 bis 3 Jahre“.
# Ergebnis: (von_monate | None, bis) mit bis in schuleintritt | grundschulalter | <n>m | None.
def alter_lesen(text: str | None) -> tuple[int | None, str | None]:
    t = re.sub(r"\s+", " ", (text or "").strip().lower())
    if not t or t == "sonstiges":
        return None, None
    if t.startswith("kinder im grundschulalter"):
        return 72, "grundschulalter"   # ab Einschulung (rund 6 Jahre)
    if "grundschul" in t and "einschließlich" in t:
        bis = "grundschulalter"
    elif "schuleintritt" in t or "einschulung" in t:
        bis = "schuleintritt"
    else:
        m = re.search(r"bis (\d+) jahre?", t)
        bis = f"{int(m.group(1)) * 12}m" if m else None
    kopf = t.split(" bis ")[0].strip()
    m = re.match(r"^(?:krippenkinder |kindergartenkinder )?(\d+)?\s*(?:(\d)/(\d))?\s*(jahre?|monate?)?$", kopf)
    if not m or (m.group(1) is None and m.group(2) is None):
        return None, bis
    ganz = int(m.group(1) or 0)
    bruch = int(m.group(2)) / int(m.group(3)) if m.group(2) else 0.0
    einheit = m.group(4) or "jahr"
    von = round((ganz + bruch) * 12) if einheit.startswith("jahr") else ganz
    return von, bis


def kita_art(einrichtungsart: str | None, alters: str | None) -> tuple[str, str, str | None]:
    """Rückgabe (art, unterart, altersstruktur normiert). Kita und Hort getrennt (Prüfbericht 9)."""
    von, bis = alter_lesen(alters)
    norm = None if von is None and bis is None else f"{'' if von is None else str(von) + 'm'}-{bis or ''}"
    ea = (einrichtungsart or "").lower()
    if bis == "grundschulalter" and von is not None and von >= 72:
        return "hort", "hort", norm
    if "hort" in ea or "grundschulalter" in ea:   # „Kinderhort …“, „Ganztagsangebote für Kinder im Grundschulalter“
        return "hort", "hort", norm
    if von is None and bis is None:
        return "kita", "sonstige", norm
    krippe = von is not None and von < 36
    if bis == "grundschulalter":
        return "kita", ("krippe_kindergarten_hort" if krippe else "kindergarten_hort"), norm
    if bis == "schuleintritt":
        return "kita", ("krippe_kindergarten" if krippe else "kindergarten"), norm
    if bis and bis.endswith("m") and int(bis[:-1]) <= 36:
        return "kita", "krippe", norm
    return "kita", "krippe_kindergarten" if krippe else "sonstige", norm


# ------------------------------------------------------------------ Schulen: Schulform
# schulform_kurzbez des MBJS → art. Grundschulteile kombinierter Schulen (G/S, G/O/OG) bleiben an der
# weiterführenden Schulform und sind über unterart erkennbar (beginnt mit „G/“).
SCHULART = {
    "G": "grundschule",
    "G/S": "sek1", "S": "sek1", "O/OG": "sek1", "G/O/OG": "sek1",
    "OG": "gymnasium",
    "FL": "foerderschule", "FE": "foerderschule", "FK": "foerderschule", "FSH": "foerderschule",
    "FG": "foerderschule", "FS": "foerderschule", "FH": "foerderschule", "FSE": "foerderschule",
    "OSZ": "osz", "OSZ/OG": "osz", "BS": "osz", "F": "osz",
    "WS": "sonstige_schule", "ZBW": "sonstige_schule",
}
_SCHUELER = re.compile(r"^\s*(\d+)\s*(?:\(\s*Stand:\s*([^)]*)\))?\s*$")


def schueler_lesen(text: str | None) -> tuple[int | None, str | None]:
    m = _SCHUELER.match(text or "")
    if not m:
        return None, None
    return int(m.group(1)), (m.group(2) or "").strip() or None


# ------------------------------------------------------------------ Gemeinbedarf aus ALKIS (nur Lage)
# Prüfbericht 12. ALKIS vereinfacht kennt keine eigene Funktion für Jugendfreizeit, Seniorenbegegnung
# oder Bürgerhaus; diese stecken in „Gebäude für soziale Zwecke“ bzw. „… kulturelle Zwecke“.
GEMEINBEDARF_GEBAEUDE = {
    "Feuerwehr": ("feuerwehr", "feuerwehr"),
    "Bibliothek, Bücherei": ("bibliothek", "bibliothek"),
    "Sport-, Turnhalle": ("sport", "sporthalle"),
    "Gebäude für Sportzwecke": ("sport", "sportgebaeude"),
    "Hallenbad": ("sport", "hallenbad"),
    "Gebäude für soziale Zwecke": ("sonstiger_gemeinbedarf", "soziale_zwecke"),
    "Gebäude für kulturelle Zwecke": ("sonstiger_gemeinbedarf", "kultur"),
    "Veranstaltungsgebäude": ("sonstiger_gemeinbedarf", "veranstaltung"),
    "Gebäude für öffentliche Zwecke": ("sonstiger_gemeinbedarf", "oeffentliche_zwecke"),
}
GEMEINBEDARF_NUTZUNG = {   # bez in public.alkis_nutzung (Sport-, Freizeit- und Erholungsfläche)
    "Sportanlage": ("sport", "sportanlage"),
    "Schwimmen": ("sport", "schwimmen"),
}
CLUSTER_M = 50   # Gebäude und Flächen derselben Art in höchstens 50 m Abstand = ein Standort


def gruen_arten(richtwerte: dict) -> list[tuple[str, str, str]]:
    """(art, nutzart, bez) aus gruen_definition.arten; bez leer = alle bez dieser nutzart."""
    gd = richtwerte.get("gruen_definition") or {}
    arten = gd.get("arten")
    if not arten:
        raise SystemExit("config/richtwerte.yaml: gruen_definition.arten fehlt (Paket A2 trägt die Zuordnung ein)")
    aus = []
    for art, d in arten.items():
        bez = d.get("bez")
        for b in (bez if isinstance(bez, list) else [bez]):
            aus.append((art, d["nutzart"], b or ""))
    return aus


def main() -> int:
    richtwerte = yaml.safe_load((WURZEL / "config" / "richtwerte.yaml").read_text(encoding="utf-8"))
    gruen = gruen_arten(richtwerte)
    standorte = json.loads(STANDORTE.read_text(encoding="utf-8"))
    if "25833" not in json.dumps(standorte.get("crs") or {}):
        raise SystemExit(f"{STANDORTE}: Bezugssystem nicht EPSG:25833")

    with psycopg.connect("") as conn, conn.cursor() as cur:
        with conn.transaction():
            cur.execute("CREATE TEMP TABLE stadt AS "
                        "SELECT ST_Union(ST_Transform(geom, 25833)) AS geom FROM public.stadtteil")
            cur.execute("TRUNCATE auswertung.einrichtung, auswertung.gruenflaeche")

            # ---------------------------------------------------------- Kitas und Horte
            cur.execute("SELECT id_kita, name, einrichtungsart, altersstruktur, kapazitaet, "
                        "ST_X(ST_Transform(geom, 25833)), ST_Y(ST_Transform(geom, 25833)) FROM public.mbjs_kita")
            kitas = cur.fetchall()
            haupt = {}
            zeilen = []
            for id_kita, name, ea, alters, kap, x, y in kitas:
                art, unterart, norm = kita_art(ea, alters)
                plaetze = int(kap) if kap and kap.strip().isdigit() else None
                haupt[id_kita] = (x, y)
                zeilen.append((id_kita, art, unterart, name, plaetze, None, None, norm,
                               "kapazitaet" if plaetze is not None else "lage_ohne_kapazitaet",
                               "MBJS WFS ms:KITA_Standorte", LIZENZ_MBJS, STAND_MBJS, x, y))
            # Weitere Häuser derselben Kita (gleiche id_kita, gleiche Kapazität je Eintrag in der Quelle):
            # als eigene Lage ohne Kapazität, damit die Plätze nur einmal zählen.
            haeuser = defaultdict(int)
            for f in standorte["features"]:
                p = f["properties"]
                x, y = f["geometry"]["coordinates"][:2]
                hx, hy = haupt.get(p["id_kita"], (None, None))
                if hx is None:
                    raise SystemExit(f"Standort {p['id_kita']} fehlt in public.mbjs_kita")
                if abs(hx - x) < 1 and abs(hy - y) < 1:
                    continue
                haeuser[p["id_kita"]] += 1
                art, unterart, norm = kita_art(p.get("einrichtungsart"), p.get("altersstruktur"))
                zeilen.append((f"{p['id_kita']}#haus{haeuser[p['id_kita']] + 1}", art, unterart, p.get("name"),
                               None, None, None, norm, "lage_ohne_kapazitaet",
                               "MBJS WFS ms:KITA_Standorte (weiteres Haus derselben Kita, Plätze am Hauptstandort)",
                               LIZENZ_MBJS, STAND_MBJS, x, y))

            # ---------------------------------------------------------- Schulen
            cur.execute("SELECT schul_nr, schulname, schulform_kurzbez, schulform, schueler, "
                        "ST_X(ST_Transform(geom, 25833)), ST_Y(ST_Transform(geom, 25833)) FROM public.mbjs_schule")
            unbekannt = set()
            for nr, name, kurz, form, schueler, x, y in cur.fetchall():
                art = SCHULART.get((kurz or "").strip())
                if art is None:
                    unbekannt.add(f"{kurz} ({form})")
                    art = "sonstige_schule"
                n, stand = schueler_lesen(schueler)
                zeilen.append((nr, art, (kurz or "").strip() or None, name, None, n, stand, None,
                               "kapazitaet" if n is not None else "lage_ohne_kapazitaet",
                               "MBJS WFS ms:Schul_Standorte", LIZENZ_MBJS, STAND_MBJS, x, y))
            if unbekannt:
                print("Hinweis: Schulform ohne Zuordnung, als sonstige_schule geführt: " + ", ".join(sorted(unbekannt)))

            cur.executemany(
                "INSERT INTO auswertung.einrichtung (id, art, unterart, name, plaetze, schueler, schueler_stand, "
                "altersstruktur, status, quelle, lizenz, stand, in_potsdam, geom) "
                "SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_Within(p, stadt.geom), p "
                "FROM stadt, ST_SetSRID(ST_MakePoint(%s, %s), 25833) AS p", zeilen)

            # ---------------------------------------------------------- Gemeinbedarf aus ALKIS (Lage)
            cur.execute("CREATE TEMP TABLE gb (oid text, art text, unterart text, geom geometry) ON COMMIT DROP")
            for funktion, (art, unterart) in GEMEINBEDARF_GEBAEUDE.items():
                cur.execute("INSERT INTO gb SELECT oid, %s, %s, ST_Transform(geom, 25833) "
                            "FROM auswertung.gebaeude_stand_20261105 WHERE funktion = %s AND geom IS NOT NULL",
                            (art, unterart, funktion))
            for bez, (art, unterart) in GEMEINBEDARF_NUTZUNG.items():
                cur.execute("INSERT INTO gb SELECT oid, %s, %s, ST_Transform(geom, 25833) "
                            "FROM public.alkis_nutzung WHERE bez = %s", (art, unterart, bez))
            cur.execute(f"""
                INSERT INTO auswertung.einrichtung (id, art, unterart, name, status, quelle, lizenz, stand,
                                                    in_potsdam, geom)
                SELECT 'alkis:' || art || ':' || min(oid), art, string_agg(DISTINCT unterart, ',' ORDER BY unterart),
                       NULL, 'lage_ohne_kapazitaet',
                       'ALKIS vereinfacht (Gebäudefunktion bzw. tatsächliche Nutzung), '
                         || count(*) || ' Objekte in höchstens {CLUSTER_M} m Abstand',
                       %s, %s, ST_Within(ST_PointOnSurface(ST_Union(geom)), (SELECT geom FROM stadt)),
                       ST_PointOnSurface(ST_Union(geom))
                FROM (SELECT *, ST_ClusterDBSCAN(geom, eps := {CLUSTER_M}, minpoints := 1)
                                OVER (PARTITION BY art) AS k FROM gb) t
                GROUP BY art, k""", (LIZENZ_LGB, STAND_ALKIS_GEB))

            # ---------------------------------------------------------- Grünflächen
            for art, nutzart, bez in gruen:
                cur.execute("""
                    INSERT INTO auswertung.gruenflaeche (id, art, bez, flaeche_m2, quelle, lizenz, geom)
                    SELECT 'alkis:' || oid, %s, NULLIF(bez, ''), round(ST_Area(g)::numeric, 1),
                           'ALKIS vereinfacht ave:Nutzung (' || nutzart || ')', %s, g
                    FROM (SELECT oid, nutzart, bez,
                                 ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Transform(geom, 25833)), 3)) AS g
                          FROM public.alkis_nutzung
                          WHERE nutzart = %s AND (%s = '' OR bez = %s)) s
                    WHERE NOT ST_IsEmpty(g)""", (art, LIZENZ_LGB, nutzart, bez, bez))

        bericht(cur)
    print(f"auswertung.einrichtung und auswertung.gruenflaeche geschrieben, Bericht {BERICHT.relative_to(WURZEL)}")
    return 0


# ------------------------------------------------------------------ Bericht
def tabelle(kopf: list[str], zeilen: list) -> str:
    zahl = [bool(zeilen) and all(isinstance(r[i], int) or r[i] is None for r in zeilen) for i in range(len(kopf))]
    aus = ["| " + " | ".join(kopf) + " |", "|" + "|".join("---:" if zahl[i] else "---" for i in range(len(kopf))) + "|"]
    for r in zeilen:
        aus.append("| " + " | ".join(z(v) if isinstance(v, int) or v is None else str(v) for v in r) + " |")
    return "\n".join(aus)


def q(cur, sql: str, args=()) -> list:
    cur.execute(sql, args)
    return cur.fetchall()


def z(n: int | None) -> str:
    """Ganzzahl mit Tausenderpunkt."""
    return "–" if n is None else f"{n:,}".replace(",", ".")


def anteil(a: int, b: int) -> str:
    return f"{100 * a / b:.0f} %" if b else "–"


def bericht(cur) -> None:
    t = []
    t.append("# A2 Gegenprobe: ALKIS-Gebäude gegen MBJS-Einrichtungen\n")
    t.append(f"Erzeugt von `skripte/11_einrichtungen.py` am {date.today().isoformat()}. Quellen: MBJS-WFS "
             "(Abruf 05.11.2026, © Ministerium für Bildung, Jugend und Sport), ALKIS-Gebäude (Snapshot "
             "`auswertung.gebaeude_stand_20261105`) und ALKIS-Nutzung (© GeoBasis-DE/LGB), jeweils "
             "dl-de/by-2-0, Daten verändert (eigene Berechnung). Abstände in EPSG:25833.\n")

    # 1. Bestand in auswertung.einrichtung
    t.append("## 1. Bestand in `auswertung.einrichtung`\n")
    t.append(tabelle(["art", "status", "in Potsdam", "außerhalb (Rechteck)", "Plätze in Potsdam",
                      "Schüler in Potsdam"],
                     q(cur, """SELECT art, status, count(*) FILTER (WHERE in_potsdam)::int,
                                      count(*) FILTER (WHERE NOT in_potsdam)::int,
                                      sum(plaetze) FILTER (WHERE in_potsdam)::int,
                                      sum(schueler) FILTER (WHERE in_potsdam)::int
                               FROM auswertung.einrichtung GROUP BY 1, 2 ORDER BY 1, 2""")))
    t.append("")

    # 2. Abgleich mit den Zahlen des Bauplans
    kita_e, kita_p = q(cur, """SELECT count(*)::int, sum(plaetze)::int FROM auswertung.einrichtung
                               WHERE art IN ('kita','hort') AND status = 'kapazitaet' AND in_potsdam""")[0]
    kita_h = q(cur, """SELECT count(*)::int FROM auswertung.einrichtung
                       WHERE art IN ('kita','hort') AND in_potsdam""")[0][0]
    hort_e, hort_p = q(cur, """SELECT count(*)::int, sum(plaetze)::int FROM auswertung.einrichtung
                               WHERE art = 'hort' AND status = 'kapazitaet' AND in_potsdam""")[0]
    hort_h = q(cur, "SELECT count(*)::int FROM auswertung.einrichtung WHERE art = 'hort' AND in_potsdam")[0][0]
    kh_e, kh_p = q(cur, """SELECT count(*)::int, sum(plaetze)::int FROM auswertung.einrichtung
                           WHERE art = 'kita' AND unterart LIKE '%%hort' AND in_potsdam""")[0]
    t.append("## 2. Abgleich mit dem Bauplan\n")
    t.append(f"- **Kitas und Horte in Potsdam (MBJS, alle Einrichtungsarten):** {kita_e} Einrichtungen (`id_kita`) "
             f"mit {z(kita_p)} Plätzen laut Betriebserlaubnis; dazu {kita_h - kita_e} weitere Häuser derselben "
             f"Einrichtungen, zusammen {kita_h} Standorte. Der Bauplan nennt 171 Kitas mit 24.581 Plätzen: Das sind "
             "die Einträge des Dienstes (Häuser), deren Kapazität je Haus wiederholt wird. Je Einrichtung gezählt "
             "sind es die Werte hier; die weiteren Häuser stehen als `lage_ohne_kapazitaet` mit der Kennung "
             "`<id_kita>#haus<n>` in der Tabelle.")
    t.append(f"- **Horte:** {hort_e} Einrichtungen mit {z(hort_p)} Plätzen ({hort_h} Standorte mit weiteren "
             "Häusern). Hort heißt: Altersstruktur „Kinder im Grundschulalter“ oder Einrichtungsart „Kinderhort …“. "
             f"Der Bauplan nennt 39 ohne Herleitung; je Einrichtung sind es {hort_e}, je Haus {hort_h}. "
             f"Zusätzlich betreuen {kh_e} Kitas mit {z(kh_p)} Plätzen Kinder bis "
             "einschließlich Grundschulalter (`unterart` endet auf `_hort`); ihre Kapazität lässt sich aus "
             "den Quelldaten nicht auf Kita und Hort aufteilen.")
    gs = q(cur, "SELECT count(*)::int FROM auswertung.einrichtung WHERE art='grundschule' AND in_potsdam")[0][0]
    gsk = q(cur, """SELECT count(*)::int FROM auswertung.einrichtung
                    WHERE art <> 'grundschule' AND unterart LIKE 'G/%%' AND in_potsdam""")[0][0]
    sch = q(cur, """SELECT count(*)::int FROM auswertung.einrichtung WHERE in_potsdam AND art IN
                    ('grundschule','sek1','gymnasium','foerderschule','osz','sonstige_schule')""")[0][0]
    t.append(f"- **Schulen in Potsdam:** {sch}, davon {gs} Grundschulen (Schulform G). Weitere {gsk} Schulen haben "
             "einen Grundschulteil (Schulform G/S bzw. G/O/OG, `unterart` beginnt mit `G/`).")
    t.append("")

    # 3. Altersstruktur
    t.append("## 3. Altersstruktur der Kitas und Horte in Potsdam (Prüfbericht 9)\n")
    t.append("Normiert als `<ab Monate>m-<bis>`, `bis` = `schuleintritt`, `grundschulalter` oder eine Grenze in "
             "Monaten; `72m` steht für „ab Einschulung“. Kapazität je Einrichtung, weitere Häuser ohne Plätze.\n")
    t.append(tabelle(["art", "unterart", "Einrichtungen", "Plätze"],
                     q(cur, """SELECT art, unterart, count(*)::int, sum(plaetze)::int FROM auswertung.einrichtung
                               WHERE art IN ('kita','hort') AND in_potsdam AND status = 'kapazitaet'
                               GROUP BY 1, 2 ORDER BY 1, 4 DESC""")))
    t.append("")

    # 4. Gegenprobe Gebäude
    t.append("## 4. Gegenprobe: liegt ein passendes ALKIS-Gebäude in der Nähe?\n")
    t.append("Je MBJS-Standort in Potsdam: Abstand zum nächsten ALKIS-Gebäude mit der genannten Funktion "
             "(Gebäudeumriss, nicht Mittelpunkt).\n")
    zeilen = []
    for titel, filt, funk in [
        ("Kitas (Einrichtung, Hauptstandort)", "art='kita' AND status='kapazitaet'",
         ["Kinderkrippe, Kindergarten, Kindertagesstätte"]),
        ("Kitas (alle Häuser)", "art='kita'", ["Kinderkrippe, Kindergarten, Kindertagesstätte"]),
        ("Horte (alle Häuser)", "art='hort'", ["Kinderkrippe, Kindergarten, Kindertagesstätte",
                                                "Allgemein bildende Schule"]),
        ("Schulen ohne OSZ", "art IN ('grundschule','sek1','gymnasium','foerderschule','sonstige_schule')",
         ["Allgemein bildende Schule"]),
        ("Oberstufenzentren und berufliche Schulen", "art='osz'",
         ["Allgemein bildende Schule", "Berufsbildende Schule", "Gebäude für Bildung und Forschung"]),
    ]:
        r = q(cur, f"""
            WITH e AS (SELECT id, geom FROM auswertung.einrichtung WHERE in_potsdam AND {filt}),
                 g AS (SELECT ST_Transform(geom, 25833) AS geom FROM auswertung.gebaeude_stand_20261105
                       WHERE funktion = ANY(%s))
            SELECT count(*)::int,
                   count(*) FILTER (WHERE d <= 25)::int, count(*) FILTER (WHERE d <= 75)::int,
                   count(*) FILTER (WHERE d <= 150)::int
            FROM (SELECT e.id, (SELECT min(ST_Distance(e.geom, g.geom)) FROM g
                                WHERE ST_DWithin(e.geom, g.geom, 500)) AS d FROM e) x""", (funk,))[0]
        zeilen.append((titel, " / ".join(funk), r[0], f"{r[1]} ({anteil(r[1], r[0])})",
                       f"{r[2]} ({anteil(r[2], r[0])})", f"{r[3]} ({anteil(r[3], r[0])})"))
    t.append(tabelle(["MBJS", "ALKIS-Funktion", "Standorte", "≤ 25 m", "≤ 75 m", "≤ 150 m"], zeilen))
    t.append("")
    t.append("**Kennzahl der Abnahme:** Anteil der MBJS-Kitas mit ALKIS-Kitagebäude in 75 m = Zeile "
             "„Kitas (Einrichtung, Hauptstandort)“, Spalte „≤ 75 m“.\n")

    # 5. Umgekehrt: ALKIS-Cluster ohne MBJS-Punkt
    t.append("## 5. Umgekehrt: ALKIS-Gebäudegruppen ohne MBJS-Standort\n")
    t.append(f"Gebäude gleicher Funktion in höchstens {CLUSTER_M} m Abstand sind eine Gruppe (DBSCAN, "
             "`ST_ClusterDBSCAN`, minpoints 1). Gezählt in Potsdam; „ohne MBJS“ = kein MBJS-Standort der "
             "passenden Art in 75 m. Gründe können sein: Kindertagespflege oder Betriebskita (nicht im Dienst), "
             "geschlossene oder umgenutzte Häuser, falsche Funktion im Kataster, Standortpunkt am Grundstücksrand.\n")
    zeilen = []
    for funk, filt in [("Kinderkrippe, Kindergarten, Kindertagesstätte", "art IN ('kita','hort')"),
                       ("Allgemein bildende Schule",
                        "art IN ('grundschule','sek1','gymnasium','foerderschule','sonstige_schule','hort')")]:
        r = q(cur, f"""
            WITH g AS (SELECT ST_Transform(geom, 25833) AS geom FROM auswertung.gebaeude_stand_20261105
                       WHERE funktion = %s),
                 k AS (SELECT ST_ClusterDBSCAN(geom, eps := {CLUSTER_M}, minpoints := 1) OVER () AS k, geom FROM g),
                 c AS (SELECT k, ST_Union(geom) AS geom FROM k GROUP BY k),
                 cp AS (SELECT * FROM c WHERE ST_Within(ST_PointOnSurface(c.geom), (SELECT geom FROM stadt)))
            SELECT (SELECT count(*) FROM g WHERE ST_Intersects(g.geom, (SELECT geom FROM stadt)))::int,
                   count(*)::int,
                   count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM auswertung.einrichtung e
                                    WHERE {filt} AND ST_DWithin(e.geom, cp.geom, 75)))::int
            FROM cp""", (funk,))[0]
        zeilen.append((funk, r[0], r[1], f"{r[2]} ({anteil(r[2], r[1])})"))
    t.append(tabelle(["ALKIS-Funktion", "Gebäude in Potsdam", "Gruppen", "Gruppen ohne MBJS in 75 m"], zeilen))
    t.append("")

    # 6. Gemeinbedarf aus ALKIS
    t.append("## 6. Gemeinbedarf aus ALKIS, nur Lage (Prüfbericht 12)\n")
    t.append(f"Standort = Gruppe aus Gebäuden bzw. Nutzungsflächen derselben Art in höchstens {CLUSTER_M} m Abstand, "
             "Punkt auf der Fläche (`ST_PointOnSurface`). Ohne Kapazität, ohne Namen (ALKIS vereinfacht führt "
             "keine).\n")
    t.append(tabelle(["art", "unterarten (Gruppen enthalten)", "Standorte in Potsdam", "außerhalb"],
                     q(cur, """SELECT art, string_agg(DISTINCT u, ', ' ORDER BY u),
                                      count(DISTINCT id) FILTER (WHERE in_potsdam)::int,
                                      count(DISTINCT id) FILTER (WHERE NOT in_potsdam)::int
                               FROM auswertung.einrichtung, unnest(string_to_array(unterart, ',')) u
                               WHERE id LIKE 'alkis:%%' GROUP BY 1 ORDER BY 1""")))
    t.append("")
    t.append("Zuordnung der Funktionen:\n")
    for f, (a, u) in GEMEINBEDARF_GEBAEUDE.items():
        t.append(f"- Gebäudefunktion „{f}“ → `{a}` / `{u}`")
    for b, (a, u) in GEMEINBEDARF_NUTZUNG.items():
        t.append(f"- Nutzung „{b}“ (Sport-, Freizeit- und Erholungsfläche) → `{a}` / `{u}`")
    t.append("")
    t.append("**Lücke:** ALKIS vereinfacht hat keine eigene Funktion für Jugendfreizeiteinrichtungen, "
             "Seniorenbegegnung oder Bürgerhäuser. Im Snapshot gibt es dafür keinen Wert; sie stecken in "
             "„Gebäude für soziale Zwecke“ (`soziale_zwecke`) bzw. „Gebäude für kulturelle Zwecke“ (`kultur`) "
             "zusammen mit Pflegeheimen, Beratungsstellen, Museen und Ähnlichem. Getrennt ausweisen lassen sie sich "
             "nur mit einer weiteren Quelle (z. B. Einrichtungsliste der Stadt, Handdownload). Die Arten `jugend`, "
             "`senioren` und `buergerhaus` aus dem Tabellenkommentar bleiben deshalb leer.\n")

    # 7. Grünflächen
    t.append("## 7. Grünflächen (`auswertung.gruenflaeche`)\n")
    t.append("Zuordnung laut `config/richtwerte.yaml`, Abschnitt `gruen_definition.arten`. Fläche je ALKIS-Objekt, "
             "ganzes Rechteck des Abrufs (auch knapp außerhalb der Stadt, für den Randeffekt).\n")
    t.append(tabelle(["art", "Objekte", "Fläche gesamt (ha)", "davon in Potsdam (ha)", "Objekte ≥ 0,5 ha"],
                     q(cur, """SELECT art, count(*)::int, round(sum(flaeche_m2) / 1e4)::int,
                                      round(sum(ST_Area(ST_Intersection(g.geom, s.geom))) / 1e4)::int,
                                      count(*) FILTER (WHERE flaeche_m2 >= 5000)::int
                               FROM auswertung.gruenflaeche g, stadt s GROUP BY 1 ORDER BY 1""")))
    t.append("")
    t.append("Offen für A6 (Prüfbericht 14): ALKIS vereinfacht führt bei Parks keinen Namen; die SPSG-Parks "
             "(Sanssouci, Neuer Garten, Babelsberg) lassen sich daraus nicht getrennt kennzeichnen. Die größten "
             "Park-Objekte liegen bei 90 und 85 ha. Mindestgröße und die Frage, ob Kleingärten, Friedhöfe und Wald "
             "mitzählen, entscheidet A6 in `gruen_definition`.\n")
    BERICHT.parent.mkdir(exist_ok=True)
    BERICHT.write_text("\n".join(t) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
