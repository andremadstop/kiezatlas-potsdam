"""Zensus 2022: Gebäude mit Wohnraum nach Baujahr je Gitterzelle (Paket B1, Bauplan 05.11.2026).

Liest die beiden Destatis-Zips selbst (Korrektur 17: kein Pipeline-Ziel, kein Eintrag in
config/potsdam.yaml; Korrektur 21: skripte/01_vorbereiten.py bleibt unberührt) und schreibt:

  auswertung.zensus_gebaeude_jahr   100-m- und 1-km-Zellen, die Potsdam berühren, beide Merkmale
                                    (Jahrzehnte, Mikrozensus-Klassen), je Zelle die Klassen und
                                    'insgesamt'; geaendert = true, wo der Rohwert „–“ ist
                                    („genau Null oder auf Null geändert“, Cell-Key-Methode)
  daten/jahre_zellen.js             KIEZ_JAHRE_ZELLEN in der Reihenfolge von daten/zellen.js
                                    (Mikrozensus-Klassen, Anteile in %, vorherrschende Klasse)
  belege/B1_zensus_jahre.md         Bericht: Zellen, Summen, Klassensumme gegen Gesamtwert

Welche Zelle zu Potsdam gehört, rechnet PostGIS wie in 02_auswerten.py: 100-m-Zelle, deren
Mittelpunkt in einem Stadtteil liegt; 1-km-Zelle, deren Quadrat die Stadt schneidet (auch anteilig,
für die Verteilung in B4). Nur Gebäude mit Wohnraum, keine einzelnen Gebäude und keine Färbung
einzelner Gebäude aus Zellklassen.

Kein Netzabruf. Rohdaten: $KIEZ_DATEN/zensus/2022/ (HERKUNFT.md dort).
Rolle: kiezatlas_rechnen (schreibt nur auswertung.zensus_gebaeude_jahr, Zwischenstand in TEMP).

Aufruf (aus dem Repo-Wurzelverzeichnis, Passwort nur per Umgebung):
  set -a; . ../kiezatlas-potsdam/.env; set +a
  PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=kiezatlas_rechnen PGPASSWORD="$RECHNEN_PASSWORD" \\
    uv run -q --offline --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \\
    python -I skripte/21_jahre_zensus.py
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import os
import re
import sys
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

import psycopg

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "daten"
KIEZ_DATEN = Path(os.environ.get("KIEZ_DATEN") or (WURZEL.parent / "kiezatlas-daten"))
ZENSUS = KIEZ_DATEN / "zensus" / "2022"
BERICHT = WURZEL / "belege" / "B1_zensus_jahre.md"

# merkmal: (Zip, Ordner im Zip, Spalten der Klassen in Reihenfolge -> Klassenschlüssel)
MERKMALE = {
    "mz_klassen": ("Gebaeude_nach_Baujahr_in_Mikrozensus_Klassen.zip",
                   {"Vor1919": "vor_1919", "a1919bis1948": "1919_1948", "a1949bis1978": "1949_1978",
                    "a1979bis1990": "1979_1990", "a1991bis2000": "1991_2000", "a2001bis2010": "2001_2010",
                    "a2011bis2019": "2011_2019", "a2020undspaeter": "ab_2020"}),
    "jahrzehnte": ("Gebaeude_nach_Baujahr_Jahrzehnte.zip",
                   {"Vor1919": "vor_1919", "a1919bis1949": "1919_1949", "a1950bis1959": "1950_1959",
                    "a1960bis1969": "1960_1969", "a1970bis1979": "1970_1979", "a1980bis1989": "1980_1989",
                    "a1990bis1999": "1990_1999", "a2000bis2009": "2000_2009", "a2010bis2015": "2010_2015",
                    "a2016undspaeter": "ab_2016"}),
}
# Beschriftung der Mikrozensus-Klassen für die Seite (wie die Fixture, gegen die B5 baut)
MZ_BESCHRIFTUNG = ["vor 1919", "1919–1948", "1949–1978", "1979–1990", "1991–2000", "2001–2010",
                   "2011–2019", "ab 2020"]
LEER = "–"   # „Genau Null oder auf Null geändert“ (Datensatzbeschreibung)
RASTER = {"100m": 100, "1km": 1000}
VERMERK = ("© Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 "
           "(https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)")
ID_MUSTER = {"100m": re.compile(r"^CRS3035RES100mN\d{7}E\d{7}$"),
             "1km": re.compile(r"^CRS3035RES1000mN\d{7}E\d{7}$")}


def zahl(roh: str) -> tuple[int, bool]:
    """Zählwert und Merker 'auf Null geändert'. Alles andere als Ganzzahl oder „–“ bricht ab."""
    s = roh.strip()
    if s == LEER:
        return 0, True
    if not s.isdigit():
        raise ValueError(f"unerwarteter Zählwert {roh!r}")
    return int(s), False


def csv_lesen(merkmal: str, raster: str, rahmen: tuple[float, float, float, float]):
    """Zeilen (gitter_id, x, y, insgesamt, [klassen]) im Rahmen; prüft Kopf und Werte streng."""
    zipname, spalten = MERKMALE[merkmal]
    zpfad = ZENSUS / zipname
    with zipfile.ZipFile(zpfad) as zf:
        namen = [n for n in zf.namelist() if n.endswith(f"_{raster}-Gitter.csv")]
        if len(namen) != 1:
            raise SystemExit(f"{zipname}: {raster}-CSV nicht eindeutig: {namen}")
        with zf.open(namen[0]) as f:
            r = csv.reader(io.TextIOWrapper(f, encoding="utf-8-sig", newline=""), delimiter=";")
            kopf = next(r)
            erwartet = ["Insgesamt_Gebaeude", *spalten]
            if kopf[0].lower() != f"gitter_id_{raster}".lower() or kopf[3:] != erwartet:
                raise SystemExit(f"{namen[0]}: Kopf unerwartet: {kopf}")
            xmin, ymin, xmax, ymax = rahmen
            gesamt = 0
            for z in r:
                gesamt += 1
                x, y = float(z[1]), float(z[2])
                if not (xmin <= x <= xmax and ymin <= y <= ymax):
                    continue
                if not ID_MUSTER[raster].match(z[0]):
                    raise SystemExit(f"{namen[0]}: Gitter-ID unerwartet: {z[0]!r}")
                yield z[0], x, y, zahl(z[3]), [zahl(v) for v in z[4:]]
    print(f"  {namen[0].split('/')[-1]}: {gesamt} Zeilen gelesen", file=sys.stderr)


def js_lesen(pfad: Path):
    t = pfad.read_text(encoding="utf-8")
    return json.loads(t[t.index("=") + 1:].strip().rstrip(";"))


def main() -> int:
    for zipname, _ in MERKMALE.values():
        if not (ZENSUS / zipname).is_file():
            print(f"fehlt: {ZENSUS / zipname} (HERKUNFT.md in {ZENSUS})", file=sys.stderr)
            return 1
    zellen = js_lesen(DATEN / "zellen.js")["features"]
    ids = [f["properties"]["id"] for f in zellen]
    st_von = {f["properties"]["id"]: f["properties"]["st"] for f in zellen}
    if ids != sorted(ids):
        raise SystemExit("daten/zellen.js nicht nach gitter_id sortiert")

    with psycopg.connect("") as conn:
        cur = conn.cursor()
        # Rahmen um die Stadt in EPSG:3035, 1 km Rand (für die 1-km-Zellen am Rand)
        cur.execute("""SELECT ST_XMin(e) - 1000, ST_YMin(e) - 1000, ST_XMax(e) + 1000, ST_YMax(e) + 1000
                       FROM (SELECT ST_Extent(ST_Transform(geom, 3035))::box2d AS e FROM stadtteil) t""")
        rahmen = tuple(float(v) for v in cur.fetchone())
        cur.execute("""CREATE TEMP TABLE b1_roh (gitter_id varchar(40), raster text, merkmal text, x float8,
                         y float8, klasse text, anzahl int, geaendert bool) ON COMMIT PRESERVE ROWS""")
        roh_zeilen = Counter()
        with cur.copy("COPY b1_roh FROM STDIN") as cp:
            for merkmal, (_, spalten) in MERKMALE.items():
                klassen = list(spalten.values())
                for raster in RASTER:
                    for gid, x, y, (ges, ges_g), werte in csv_lesen(merkmal, raster, rahmen):
                        roh_zeilen[(merkmal, raster)] += 1
                        cp.write_row((gid, raster, merkmal, x, y, "insgesamt", ges, ges_g))
                        for k, (w, g) in zip(klassen, werte):
                            cp.write_row((gid, raster, merkmal, x, y, k, w, g))
        # Zugehörigkeit zu Potsdam: 100 m Mittelpunkt im Stadtteil (wie 02_auswerten.py),
        # 1 km Quadrat schneidet die Stadt (Anteil der Fläche für B4 mitgeführt im Bericht)
        cur.execute("""CREATE TEMP TABLE b1_zelle AS
                       WITH z AS (SELECT DISTINCT gitter_id, raster, x, y FROM b1_roh),
                            s AS (SELECT nr, ST_Transform(geom, 3035) AS g FROM stadtteil),
                            stadt AS (SELECT ST_Union(g) AS g FROM s)
                       SELECT z.gitter_id, z.raster,
                              (SELECT s.nr FROM s WHERE z.raster = '100m'
                                 AND ST_Contains(s.g, ST_SetSRID(ST_MakePoint(z.x, z.y), 3035)) LIMIT 1) AS st,
                              CASE WHEN z.raster = '1km' THEN
                                ST_Area(ST_Intersection(stadt.g, ST_Expand(ST_SetSRID(ST_MakePoint(z.x, z.y), 3035), 500))) / 1e6
                              END AS anteil_stadt
                       FROM z, stadt""")
        cur.execute("""SELECT gitter_id FROM b1_zelle
                       WHERE (raster = '100m' AND st IS NOT NULL) OR (raster = '1km' AND anteil_stadt > 0)""")
        in_potsdam = {r[0] for r in cur.fetchall()}
        with conn.transaction():
            cur.execute("DELETE FROM auswertung.zensus_gebaeude_jahr")
            cur.execute("""INSERT INTO auswertung.zensus_gebaeude_jahr (gitter_id, raster, merkmal, klasse, anzahl, geaendert)
                           SELECT r.gitter_id, r.raster, r.merkmal, r.klasse, r.anzahl, r.geaendert
                           FROM b1_roh r JOIN b1_zelle z USING (gitter_id, raster)
                           WHERE (z.raster = '100m' AND z.st IS NOT NULL) OR (z.raster = '1km' AND z.anteil_stadt > 0)""")
            eingefuegt = cur.rowcount
        bericht = berichten(cur, ids, st_von, roh_zeilen, eingefuegt)
        bericht += jahre_zellen_schreiben(cur, ids)
    BERICHT.write_text(bericht, encoding="utf-8")
    print(f"auswertung.zensus_gebaeude_jahr: {eingefuegt} Zeilen ({len(in_potsdam)} Zellen); "
          f"{DATEN / 'jahre_zellen.js'}; {BERICHT}", file=sys.stderr)
    return 0


def jahre_zellen_schreiben(cur, ids: list[str]) -> str:
    cur.execute("""SELECT gitter_id, klasse, anzahl, geaendert FROM auswertung.zensus_gebaeude_jahr
                   WHERE raster = '100m' AND merkmal = 'mz_klassen'""")
    werte: dict[str, dict[str, tuple[int, bool]]] = {}
    for gid, k, n, g in cur.fetchall():
        werte.setdefault(gid, {})[k] = (n, g)
    klassen = list(MERKMALE["mz_klassen"][1].values())
    gebaeude, anteile, vorherrschend = [], [], []
    for gid in ids:
        w = werte.get(gid)
        if w is None:                       # Zelle ohne Gebäude mit Wohnraum im Zensus
            gebaeude.append(None); anteile.append(None); vorherrschend.append(None)
            continue
        gebaeude.append(w["insgesamt"][0])
        n = [w[k][0] for k in klassen]
        summe = sum(n)
        if summe == 0:                      # alle Klassen „–“: keine Verteilung ablesbar
            anteile.append(None); vorherrschend.append(None)
            continue
        anteile.append([round(100 * v / summe, 1) for v in n])
        top = max(n)
        vorherrschend.append(n.index(top) if n.count(top) == 1 else None)
    inhalt = {
        "stand": date.today().isoformat(),
        "hinweis": ("Zensus 2022 (Stichtag 15.05.2022), Gebäude mit Wohnraum je 100-m-Zelle. gebaeude = Gesamtwert "
                    "der Zelle (null: keine Gebäude mit Wohnraum gemeldet). anteile = Anteil jeder Baujahresklasse an "
                    "der Summe der Klassen in Prozent, auf 0,1 gerundet; die Klassen ergeben wegen der Geheimhaltung "
                    "(Cell-Key-Methode, kleine Werte verändert oder auf Null gesetzt) nicht immer den Gesamtwert. "
                    "null bei anteile und vorherrschend: alle Klassen auf Null geändert; vorherrschend null auch bei "
                    "Gleichstand. Bei wenigen Gebäuden je Zelle sind Anteile unsicher, Summen über viele Zellen "
                    "weichen von amtlichen Gemeindewerten ab. Keine Aussage über einzelne Gebäude."),
        "merkmal": "mz_klassen",
        "beschriftung": "Gebäude mit Wohnraum je Zelle, nicht einzelne Gebäude",
        "klassen": MZ_BESCHRIFTUNG,
        "quellen": {"zensus": {"quelle": "Zensus 2022, Gebäude nach Baujahr in Mikrozensus-Klassen, 100-m-Gitter",
                               "lizenz": "dl-de/by-2-0", "vermerk": VERMERK,
                               "url": "https://www.destatis.de/static/DE/zensus/gitterdaten/"
                                      "Gebaeude_nach_Baujahr_in_Mikrozensus_Klassen.zip",
                               "stand": "2022-05-15"}},
        "anzahl": len(ids), "erste_id": ids[0], "letzte_id": ids[-1], "schluessel": "zellen.js-Reihenfolge",
        "gebaeude": gebaeude, "anteile": anteile, "vorherrschend": vorherrschend,
    }
    kopf = ("/* Kiezatlas Potsdam: Gebäude mit Wohnraum nach Baujahr je 100-m-Zelle (Paket B1, "
            "skripte/21_jahre_zensus.py). " + VERMERK + ". */\n")
    (DATEN / "jahre_zellen.js").write_text(
        kopf + "window.KIEZ_JAHRE_ZELLEN=" + json.dumps(inhalt, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    roh = (DATEN / "jahre_zellen.js").read_bytes()
    gz = len(gzip.compress(roh, 9))
    mit = sum(1 for g in gebaeude if g is not None)
    ohne_vert = sum(1 for g, an in zip(gebaeude, anteile) if g is not None and an is None)
    gleich = sum(1 for an, v in zip(anteile, vorherrschend) if an is not None and v is None)
    return ("## daten/jahre_zellen.js\n\n"
            f"{len(ids)} Zellen in `zellen.js`-Reihenfolge, davon {mit} mit Gebäuden (Σ {sum(g for g in gebaeude if g)}). "
            f"Ohne ablesbare Verteilung (alle Klassen „–“, `anteile` und `vorherrschend` null): {ohne_vert}. "
            f"Gleichstand zweier Klassen (`vorherrschend` null): {gleich}. Größe {len(roh)} Byte, "
            f"gzip -9 {gz} Byte (Grenze 120 KB). Nur Zellwerte, keine Gebäude-IDs, keine Färbung einzelner Gebäude.\n")


def berichten(cur, ids, st_von, roh_zeilen, eingefuegt) -> str:
    z = []
    a = z.append
    a("# B1: Zensus-Baujahr im Gitter (Bericht)\n")
    a(f"Erzeugt von `skripte/21_jahre_zensus.py` am {date.today().isoformat()}. Quelle: Zensus 2022 (Stichtag "
      "15.05.2022), Gebäude mit Wohnraum, Destatis-Gitterdaten (`$KIEZ_DATEN/zensus/2022/`, HERKUNFT.md dort). "
      f"{VERMERK}.\n")
    a("„–“ heißt laut Datensatzbeschreibung „genau Null oder auf Null geändert“ (Cell-Key-Methode). In "
      "`auswertung.zensus_gebaeude_jahr` steht dafür `anzahl = 0, geaendert = true`.\n")
    a("## Gelesen und geschrieben\n")
    a("| Merkmal | Raster | Zeilen im Rahmen um Potsdam (1 km Rand) |\n|---|---|---:|")
    for (m, r), n in sorted(roh_zeilen.items()):
        a(f"| {m} | {r} | {n} |")
    a(f"\n`auswertung.zensus_gebaeude_jahr`: {eingefuegt} Zeilen. 100-m-Zellen mit Mittelpunkt in einem der 32 "
      "Stadtteile (wie `02_auswerten.py`), 1-km-Zellen, deren Quadrat die Stadt schneidet.\n")

    a("## Potsdam, 100-m-Zellen (Mittelpunkt im Stadtteil)\n")
    idset = set(ids)
    cur.execute("""SELECT r.merkmal, r.gitter_id, z.st, sum(r.anzahl) FILTER (WHERE r.klasse = 'insgesamt'),
                          sum(r.anzahl) FILTER (WHERE r.klasse <> 'insgesamt'),
                          bool_or(r.geaendert) FILTER (WHERE r.klasse = 'insgesamt'),
                          count(*) FILTER (WHERE r.klasse <> 'insgesamt' AND NOT r.geaendert)
                   FROM b1_roh r JOIN b1_zelle z USING (gitter_id, raster)
                   WHERE r.raster = '100m' AND z.st IS NOT NULL GROUP BY 1, 2, 3""")
    zeilen = cur.fetchall()
    a("| Merkmal | Zellen mit Gebäuden | Σ Gesamtwert | Σ Klassen | Lücke | Zellen, in denen alle Klassen „–“ sind | "
      "davon in zellen.js | Σ Gesamtwert in zellen.js-Zellen | Zellen ohne Einwohner (nicht in zellen.js) | Gebäude dort |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    je_merkmal = {}
    for m in ("mz_klassen", "jahrzehnte"):
        zm = [r for r in zeilen if r[0] == m]
        ges = sum(r[3] for r in zm)
        kl = sum(r[4] for r in zm)
        mit_strich = sum(1 for r in zm if r[6] == 0)
        drin = [r for r in zm if r[1] in idset]
        draussen = [r for r in zm if r[1] not in idset]
        je_merkmal[m] = {r[1]: r[3] for r in zm}
        luecke = f"{100 * (ges - kl) / ges:.1f}".replace(".", ",")
        a(f"| {m} | {len(zm)} | {ges} | {kl} | {ges - kl} ({luecke} %) | {mit_strich} | "
          f"{len(drin)} | {sum(r[3] for r in drin)} | {len(draussen)} | {sum(r[3] for r in draussen)} |")
    gleich = sum(1 for g, v in je_merkmal["mz_klassen"].items() if je_merkmal["jahrzehnte"].get(g) == v)
    nur_eins = set(je_merkmal["mz_klassen"]) ^ set(je_merkmal["jahrzehnte"])
    a(f"\nGesamtwert je Zelle in beiden Dateien gleich: {gleich} von {len(je_merkmal['mz_klassen'])} Zellen; "
      f"Zellen nur in einer der beiden Dateien: {len(nur_eins)}.\n")
    a("**Erwartung aus der Erkundung:** 2.869 Zellen mit Gebäuden, 23.155 Gebäude, gerechnet über die 3.443 "
      "bewohnten Zellen von `zellen.js` (Mikrozensus-Klassen). Spalten „davon in zellen.js“ und „Σ Gesamtwert in "
      "zellen.js-Zellen“ sind der Vergleichswert; Zellen mit Gebäuden, aber ohne gemeldete Einwohner, fehlen in "
      "`zellen.js` und damit in `jahre_zellen.js`.\n")

    a("### Klassen, Stadt (Σ über die 100-m-Zellen)\n")
    for m in ("mz_klassen", "jahrzehnte"):
        cur.execute("""SELECT r.klasse, sum(r.anzahl), count(*) FILTER (WHERE r.geaendert)
                       FROM b1_roh r JOIN b1_zelle z USING (gitter_id, raster)
                       WHERE r.raster = '100m' AND z.st IS NOT NULL AND r.merkmal = %s GROUP BY 1""", (m,))
        d = {k: (n, g) for k, n, g in cur.fetchall()}
        reihe = ["insgesamt", *MERKMALE[m][1].values()]
        a(f"**{m}**\n")
        a("| Klasse | Gebäude | Zellen mit „–“ |\n|---|---:|---:|")
        for k in reihe:
            a(f"| {k} | {d[k][0]} | {d[k][1]} |")
        a("")

    a("## 1-km-Zellen gegen Σ der 100-m-Zellen\n")
    a("Die 1-km-Werte sind eigenständig geheim gehalten. Für 1-km-Zellen, die ganz in der Stadt liegen, zeigt der "
      "Vergleich, wie stark sich die Veränderung kleiner Werte bei der Summe von 100 Zellen auswirkt. B4 verteilt "
      "die 1-km-Summen.\n")
    a("| Merkmal | 1-km-Zellen, die Potsdam schneiden | davon ganz in der Stadt | Σ Gesamtwert 1 km (ganz) | "
      "Σ Gesamtwert 100 m darin | Σ Klassen 1 km (ganz) | Σ Klassen 100 m darin |")
    a("|---|---:|---:|---:|---:|---:|---:|")
    for m in ("mz_klassen", "jahrzehnte"):
        cur.execute("""WITH k AS (SELECT gitter_id, anteil_stadt FROM b1_zelle WHERE raster = '1km' AND anteil_stadt > 0),
                            kw AS (SELECT r.gitter_id, sum(r.anzahl) FILTER (WHERE r.klasse = 'insgesamt') AS ges,
                                          sum(r.anzahl) FILTER (WHERE r.klasse <> 'insgesamt') AS kl
                                   FROM b1_roh r JOIN k USING (gitter_id) WHERE r.merkmal = %s GROUP BY 1),
                            hw AS (SELECT 'CRS3035RES1000mN' || substr(r.gitter_id, 16, 4) || '000E'
                                            || substr(r.gitter_id, 24, 4) || '000' AS km,
                                          sum(r.anzahl) FILTER (WHERE r.klasse = 'insgesamt') AS ges,
                                          sum(r.anzahl) FILTER (WHERE r.klasse <> 'insgesamt') AS kl
                                   FROM b1_roh r WHERE r.raster = '100m' AND r.merkmal = %s GROUP BY 1)
                       SELECT count(*), count(*) FILTER (WHERE k.anteil_stadt > 0.999),
                              sum(kw.ges) FILTER (WHERE k.anteil_stadt > 0.999),
                              sum(coalesce(hw.ges, 0)) FILTER (WHERE k.anteil_stadt > 0.999),
                              sum(kw.kl) FILTER (WHERE k.anteil_stadt > 0.999),
                              sum(coalesce(hw.kl, 0)) FILTER (WHERE k.anteil_stadt > 0.999)
                       FROM k JOIN kw USING (gitter_id) LEFT JOIN hw ON hw.km = k.gitter_id""", (m, m))
        a("| " + m + " | " + " | ".join(str(v) for v in cur.fetchone()) + " |")
    a("")

    a("## Gegenprobe: Wohnungen nach Baujahr (Bestand `zensus_zelle.w_*`)\n")
    cur.execute("""SELECT count(*) FILTER (WHERE coalesce(z.w_ges, 0) > 0), sum(z.w_ges)
                   FROM zensus_zelle z JOIN stadtteil s ON ST_Contains(s.geom, z.geom)""")
    zw, sw = cur.fetchone()
    geb_zellen = set(je_merkmal["mz_klassen"])
    cur.execute("""SELECT z.gitter_id FROM zensus_zelle z JOIN stadtteil s ON ST_Contains(s.geom, z.geom)
                   WHERE coalesce(z.w_ges, 0) > 0""")
    w_zellen = {r[0] for r in cur.fetchall()}
    a(f"Zellen in Potsdam mit Wohnungen (`w_ges > 0`): {zw}, zusammen {sw} Wohnungen. Zellen mit Wohnungen, aber "
      f"ohne Gebäude im Baujahr-Gitter: {len(w_zellen - geb_zellen)}; Zellen mit Gebäuden, aber ohne Wohnungen: "
      f"{len(geb_zellen - w_zellen)}. (Wohnungen und Gebäude sind getrennt geheim gehalten, kleine Abweichungen "
      "sind zu erwarten.)\n")

    a("## Je Stadtteil (Mikrozensus-Klassen, 100 m, Zellen in zellen.js)\n")
    name = {f["properties"]["nr"]: f["properties"]["name"] for f in js_lesen(DATEN / "stadtteile.js")["features"]}
    cur.execute("""SELECT gitter_id, klasse, anzahl FROM b1_roh WHERE raster = '100m' AND merkmal = 'mz_klassen'""")
    st_ges, st_kl, st_n = Counter(), Counter(), Counter()
    for gid, k, n in cur.fetchall():
        st = st_von.get(gid)
        if st is None:
            continue
        if k == "insgesamt":
            st_ges[st] += n
            st_n[st] += 1
        else:
            st_kl[st] += n
    a("| Stadtteil | Zellen mit Gebäuden | Σ Gesamtwert | Σ Klassen | Lücke |\n|---|---:|---:|---:|---:|")
    for st in sorted(st_ges, key=int):
        a(f"| {st} {name.get(st, '')} | {st_n[st]} | {st_ges[st]} | {st_kl[st]} | {st_ges[st] - st_kl[st]} |")
    a(f"| **Σ** | {sum(st_n.values())} | {sum(st_ges.values())} | {sum(st_kl.values())} | "
      f"{sum(st_ges.values()) - sum(st_kl.values())} |")
    a("\nDie Summen je Stadtteil sind Summen veränderter Zellwerte; bei kleinen Stadtteilen ist die Lücke "
      "zwischen Gesamtwert und Klassen anteilig groß. Für Aussagen je Stadtteil auf 10 Gebäude runden und den "
      "Gesamtwert, nicht die Klassensumme, als Bezug nennen.\n")
    return "\n".join(z) + "\n"


if __name__ == "__main__":
    sys.exit(main())
