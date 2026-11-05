"""B0: Gebäudeform aus ALKIS-NAS (alkis_p.zip) und Zuordnung zum Gebäude-Snapshot.

Liest den Bestandsdatenauszug ohne Eigentümer (LGB, Stichtag 01.10.2026) direkt aus dem Zip, ohne ihn
zu entpacken, und schreibt mit der Rolle kiezatlas_rechnen:

  auswertung.alkis_nas_gebaeude  je NAS-Bauwerk mit Fläche: Funktion, Dachform, Bauweise, Geschosse,
                                 Objekthöhe, Baujahr (falls vorhanden), Wohnungen (falls vorhanden),
                                 zugeordnetes oid_bezug aus auswertung.gebaeude_stand_20261105
  auswertung.gebaeude_adresse    Straße und Hausnummer je zugeordnetem Gebäude, NUR INTERN
                                 (Korrektur 6: nie in daten/, nie in Exporte, nie in Ausgaben/Berichte)

Zuordnung (Bauplan B0): größte Überlappung in EPSG:25833, nur innerhalb derselben Objektart
(AX_Gebaeude ↔ „Gebäude“, AX_Bauteil ↔ „Bauteil“ usw.), sonst hinge ein Bauteil am umgebenden Gebäude.
Gültig ist ein Paar, wenn die Schnittfläche mindestens die Hälfte der kleineren der beiden Flächen
ausmacht. ueberlappung = Schnitt / Vereinigung (IoU) des gewählten Paars. Als Gegenprobe zählt das
Skript, wie oft die Überlappung dasselbe Gebäude trifft wie der Kennungsvergleich oid = gml_id || 'BL'.

Bezug ist nur der Snapshot auswertung.gebaeude_stand_20261105 (Korrektur 16), nie public.gebaeude.
Gelesen werden nur die unten aufgeführten Objektarten und Lagebezeichnungen; Buchungs- und
Personendaten (AX_Buchungsblatt, AX_Buchungsstelle, AX_Person, AX_Namensnummer, AX_Anschrift) werden
nicht angefasst. lebenszeitintervall/beginnt ist ein Fortführungsdatum und wird nie als Baujahr benutzt.

Aufruf aus dem Repo (Passwort nur aus der .env, chmod 600):
    set -a; . ../kiezatlas-potsdam/.env; set +a
    PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=kiezatlas_rechnen \\
    PGPASSWORD="$RECHNEN_PASSWORD" KIEZ_DATEN=../kiezatlas-daten \\
    uv run -q --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \\
        python -I skripte/20_alkis_nas.py
Läuft beliebig oft (TRUNCATE und Neuschreiben in einer Transaktion). Schreibt den Bericht
berichte/B0_alkis_nas.md (nur Zählungen, keine Adressen).
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import math
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import psycopg

WURZEL = Path(__file__).resolve().parent.parent
KIEZ_DATEN = Path(os.environ.get("KIEZ_DATEN", WURZEL.parent / "kiezatlas-daten"))
ZIP = KIEZ_DATEN / "alkis_nas" / "2026-10-01" / "alkis_p.zip"
ZIP_SHA256 = "4b92f837fb298333492c6a85f45fc5149986a95df838ee5325a02ada50f094ce"
BERICHT = WURZEL / "berichte" / "B0_alkis_nas.md"
SNAPSHOT = "auswertung.gebaeude_stand_20261105"
GEBAEUDE_IN_POTSDAM = 52309   # Snapshot, PointOnSurface in einem der 32 Stadtteile (pruefen/INVENTAR.md D2)

NS_ADV = "{http://www.adv-online.de/namespaces/adv/gid/7.1}"
NS_GML = "{http://www.opengis.net/gml/3.2}"
NS_WFS = "{http://www.opengis.net/wfs/2.0}"
NS_XLINK = "{http://www.w3.org/1999/xlink}"

# NAS-Objektart -> Wert von gebnutzbez im Snapshot (WFS-Gebäudelayer der LGB)
KLASSEN = {
    "AX_Gebaeude": "Gebäude",
    "AX_Bauteil": "Bauteil",
    "AX_Turm": "Turm",
    "AX_VorratsbehaelterSpeicherbauwerk": "Vorratsbehälter, Speicherbauwerk",
    "AX_BauwerkOderAnlageFuerIndustrieUndGewerbe": "Bauwerk oder Anlage für Industrie und Gewerbe",
    "AX_BauwerkOderAnlageFuerSportFreizeitUndErholung": "Bauwerk oder Anlage für Sport, Freizeit und Erholung",
    "AX_SonstigesBauwerkOderSonstigeEinrichtung": "Sonstiges Bauwerk oder sonstige Einrichtung",
}
# Funktionsattribut je Objektart (Wert wird als „<Art>:<Kennung>“ gespeichert, z. B. „Gebaeude:1010“)
FUNKTIONSFELD = ("gebaeudefunktion", "bauart", "bauwerksfunktion")

# GeoInfoDok 7.1, Werteartenlisten AX_Dachform und AX_Bauweise_Gebaeude
DACHFORM = {
    "1000": "Flachdach", "2100": "Pultdach", "2200": "Versetztes Pultdach", "3100": "Satteldach",
    "3200": "Walmdach", "3300": "Krüppelwalmdach", "3400": "Mansardendach", "3500": "Zeltdach",
    "3600": "Kegeldach", "3700": "Kuppeldach", "3800": "Sheddach", "3900": "Bogendach",
    "4000": "Turmdach", "5000": "Mischform", "9999": "Sonstiges",
}
BAUWEISE = {
    "1100": "Freistehendes Einzelgebäude", "1200": "Freistehender Gebäudeblock", "1300": "Einzelgarage",
    "1400": "Doppelgarage", "1500": "Sammelgarage", "2100": "Doppelhaushälfte", "2200": "Reihenhaus",
    "2300": "Haus in Reihe", "2400": "Gruppenhaus", "2500": "Gebäudeblock in geschlossener Bauweise",
    "4000": "Offen", "9999": "Sonstiges",
}
LAGE_TEILE = ("land", "regierungsbezirk", "kreis", "gemeinde", "lage")


def kurz(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def kind_text(el: ET.Element, name: str) -> str | None:
    k = el.find(NS_ADV + name)
    if k is None or k.text is None:
        return None
    t = k.text.strip()
    return t or None


# ----------------------------------------------------------------------------------- Geometrie
def zahlen(posliste: ET.Element) -> list[tuple[float, float]]:
    werte = [float(v) for v in (posliste.text or "").split()]
    dim = int(posliste.get("srsDimension", "2"))
    return [(werte[i], werte[i + 1]) for i in range(0, len(werte) - dim + 1, dim)]


def segment_punkte(seg: ET.Element) -> list[tuple[float, float]]:
    pl = seg.find(NS_GML + "posList")
    if pl is not None:
        p = zahlen(pl)
    else:
        p = [tuple(float(v) for v in (pos.text or "").split()[:2]) for pos in seg.findall(NS_GML + "pos")]
    if kurz(seg.tag) in ("Arc", "ArcString") and len(p) >= 3:
        aus = [p[0]]
        for i in range(0, len(p) - 2, 2):
            aus.extend(bogen(p[i], p[i + 1], p[i + 2])[1:])
        return aus
    return p


def bogen(a, b, c, schritt=math.radians(5)):
    """Kreisbogen durch a, b, c (b liegt auf dem Bogen) als Punktfolge von a nach c."""
    (ax, ay), (bx, by), (cx, cy) = a, b, c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return [a, b, c]
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    wa, wb, wc = (math.atan2(p[1] - uy, p[0] - ux) for p in (a, b, c))

    def ccw(w0, w1):   # Winkel von w0 nach w1 gegen den Uhrzeigersinn, 0..2π
        return (w1 - w0) % (2 * math.pi)

    if ccw(wa, wb) <= ccw(wa, wc):      # b liegt zwischen a und c gegen den Uhrzeigersinn
        weite = ccw(wa, wc)
    else:
        weite = -ccw(wc, wa)
    n = max(2, int(abs(weite) / schritt) + 1)
    return [a] + [(ux + r * math.cos(wa + weite * i / n), uy + r * math.sin(wa + weite * i / n))
                  for i in range(1, n)] + [c]


def ring(el: ET.Element) -> list[tuple[float, float]]:
    """exterior/interior -> geschlossene Punktfolge (LinearRing oder Ring aus curveMembers)."""
    punkte: list[tuple[float, float]] = []
    for kind in el:
        if kurz(kind.tag) == "LinearRing":
            pl = kind.find(NS_GML + "posList")
            punkte = zahlen(pl) if pl is not None else [
                tuple(float(v) for v in (pos.text or "").split()[:2]) for pos in kind.findall(NS_GML + "pos")]
        elif kurz(kind.tag) == "Ring":
            for seg in kind.iter():
                if kurz(seg.tag) in ("LineStringSegment", "Arc", "ArcString", "LineString"):
                    for p in segment_punkte(seg):
                        if not punkte or (abs(p[0] - punkte[-1][0]) > 1e-6 or abs(p[1] - punkte[-1][1]) > 1e-6):
                            punkte.append(p)
    if punkte and punkte[0] != punkte[-1]:
        punkte.append(punkte[0])
    return punkte


def flaeche_wkt(position: ET.Element) -> str | None:
    polygone = []
    for patch in position.iter():
        if kurz(patch.tag) not in ("PolygonPatch", "Polygon"):
            continue
        ringe = []
        for teil in patch:
            if kurz(teil.tag) in ("exterior", "interior"):
                r = ring(teil)
                if len(r) >= 4:
                    ringe.append(r)
        if ringe:
            polygone.append("(" + ",".join("(" + ",".join(f"{x:.3f} {y:.3f}" for x, y in r) + ")"
                                          for r in ringe) + ")")
    if not polygone:
        return None
    return "MULTIPOLYGON(" + ",".join(polygone) + ")"


# ----------------------------------------------------------------------------------- Einlesen
def objekthoehe(el: ET.Element) -> float | None:
    oh = el.find(NS_ADV + "objekthoehe")
    if oh is None:
        return None
    if oh.text and oh.text.strip():
        return float(oh.text)
    for h in oh.iter(NS_ADV + "hoehe"):
        if h.text and h.text.strip():
            return float(h.text)
    return None


def ganzzahl(t: str | None) -> int | None:
    try:
        return int(t) if t is not None else None
    except ValueError:
        return None


def einlesen(zip_pfad: Path):
    objekte: dict[str, dict] = {}
    lagen: dict[str, tuple[tuple, str]] = {}         # gml_id -> (Lageschlüssel, Hausnummer)
    katalog: dict[tuple, str] = {}                   # Lageschlüssel -> Straßenname
    zaehl = collections.Counter()
    with zipfile.ZipFile(zip_pfad) as z:
        for name in sorted(z.namelist()):
            if not name.endswith(".xml.gz"):
                continue
            zaehl["kacheln"] += 1
            with z.open(name) as roh, gzip.open(roh) as f:
                stapel: list[str] = []
                for ereignis, el in ET.iterparse(f, events=("start", "end")):
                    if ereignis == "start":
                        stapel.append(el.tag)
                        continue
                    stapel.pop()
                    eltern = stapel[-1] if stapel else None
                    if eltern is None or kurz(eltern) not in ("Insert", "Replace", "Update", "Delete"):
                        continue
                    art = kurz(el.tag)
                    if kurz(eltern) != "Insert":
                        zaehl["nicht_insert"] += 1
                    elif art in KLASSEN:
                        objekt(el, art, objekte, zaehl)
                    elif art == "AX_LagebezeichnungMitHausnummer":
                        gid = el.get(NS_GML + "id")
                        vs = el.find(f".//{NS_ADV}AX_VerschluesselteLagebezeichnung")
                        hnr = kind_text(el, "hausnummer")
                        if vs is not None and hnr:
                            lagen[gid] = (tuple(kind_text(vs, t) for t in LAGE_TEILE), hnr)
                    elif art == "AX_LagebezeichnungKatalogeintrag":
                        vs = el.find(f"{NS_ADV}schluessel/{NS_ADV}AX_VerschluesselteLagebezeichnung")
                        bez = kind_text(el, "bezeichnung")
                        if vs is not None and bez:
                            katalog[tuple(kind_text(vs, t) for t in LAGE_TEILE)] = bez
                    el.clear()
    return objekte, lagen, katalog, zaehl


def objekt(el: ET.Element, art: str, objekte: dict, zaehl: collections.Counter) -> None:
    gid = el.get(NS_GML + "id")
    zaehl[f"gelesen:{art}"] += 1
    pos = el.find(NS_ADV + "position")
    wkt = flaeche_wkt(pos) if pos is not None else None
    if wkt is None:
        zaehl[f"ohne_flaeche:{art}"] += 1
        return
    if gid in objekte:
        zaehl["doppelt"] += 1
        return
    code = next((kind_text(el, f) for f in FUNKTIONSFELD if kind_text(el, f)), None)
    df, bw = kind_text(el, "dachform"), kind_text(el, "bauweise")
    objekte[gid] = {
        "art": art,
        "funktion": f"{art[3:]}:{code}" if code else art[3:],
        "dachform": DACHFORM.get(df, df) if df else None,
        "bauweise": BAUWEISE.get(bw, bw) if bw else None,
        "geschosse": ganzzahl(kind_text(el, "anzahlDerOberirdischenGeschosse")),
        "objekthoehe": objekthoehe(el),
        "baujahr": ganzzahl(kind_text(el, "baujahr")),
        "wohnungen": ganzzahl(kind_text(el, "anzahlDerWohnungen")),
        "zeigt_auf": [z.get(NS_XLINK + "href", "").removeprefix("urn:adv:oid:")
                      for z in el.findall(NS_ADV + "zeigtAuf")],
        "wkt": wkt,
    }


# ----------------------------------------------------------------------------------- Zuordnen
def zuordnen(cur, objekte: dict) -> dict:
    cur.execute("""CREATE TEMP TABLE nas (gml_id text PRIMARY KEY, art text, geom geometry) ON COMMIT DROP""")
    with cur.copy("COPY nas (gml_id, art, geom) FROM STDIN") as cp:
        for gid, o in objekte.items():
            cp.write_row((gid, o["art"], "SRID=25833;" + o["wkt"]))
    cur.execute("UPDATE nas SET geom = ST_CollectionExtract(ST_MakeValid(geom), 3)")
    cur.execute("CREATE INDEX ON nas USING gist (geom)")
    faelle = " ".join(f"WHEN '{v}' THEN '{k}'" for k, v in KLASSEN.items())
    cur.execute(f"""
        CREATE TEMP TABLE snap ON COMMIT DROP AS
        SELECT s.oid, CASE s.gebnutzbez {faelle} END AS art,
               ST_CollectionExtract(ST_MakeValid(ST_Transform(s.geom, 25833)), 3) AS geom,
               EXISTS (SELECT 1 FROM public.stadtteil t
                       WHERE ST_Contains(t.geom, ST_PointOnSurface(s.geom))) AS in_potsdam
        FROM {SNAPSHOT} s""")
    cur.execute("CREATE INDEX ON snap USING gist (geom)")
    cur.execute("ANALYZE nas; ANALYZE snap")
    cur.execute("""
        CREATE TEMP TABLE paar ON COMMIT DROP AS
        SELECT DISTINCT ON (n.gml_id) n.gml_id, s.oid, k.schnitt, ST_Area(n.geom) AS a_n, ST_Area(s.geom) AS a_s
        FROM nas n
        JOIN snap s ON s.art = n.art AND n.geom && s.geom
        CROSS JOIN LATERAL (SELECT ST_Area(ST_Intersection(n.geom, s.geom)) AS schnitt) k
        WHERE k.schnitt > 0
        ORDER BY n.gml_id, k.schnitt DESC""")
    cur.execute("""
        SELECT gml_id, oid, round((schnitt / NULLIF(a_n + a_s - schnitt, 0))::numeric, 3)
        FROM paar WHERE schnitt >= 0.5 * least(a_n, a_s)""")
    return {gid: (oid, iou) for gid, oid, iou in cur.fetchall()}


def schreiben(cur, objekte: dict, zuordnung: dict, lagen: dict, katalog: dict) -> collections.Counter:
    z = collections.Counter()
    cur.execute("TRUNCATE auswertung.alkis_nas_gebaeude, auswertung.gebaeude_adresse")
    with cur.copy("COPY auswertung.alkis_nas_gebaeude (gml_id, oid_bezug, funktion, dachform, bauweise, "
                  "geschosse, objekthoehe, baujahr, wohnungen, ueberlappung) FROM STDIN") as cp:
        for gid, o in objekte.items():
            oid, iou = zuordnung.get(gid, (None, None))
            cp.write_row((gid, oid, o["funktion"], o["dachform"], o["bauweise"], o["geschosse"],
                          o["objekthoehe"], o["baujahr"], o["wohnungen"], iou))
    adressen = set()
    for gid, o in objekte.items():
        oid = zuordnung.get(gid, (None, None))[0]
        for ziel in o["zeigt_auf"]:
            z["verweise"] += 1
            if ziel not in lagen:
                z["verweis_ohne_lage"] += 1
                continue
            schluessel, hnr = lagen[ziel]
            strasse = katalog.get(schluessel)
            if strasse is None:
                z["lage_ohne_katalog"] += 1
                continue
            if oid is None:
                z["adresse_ohne_zuordnung"] += 1
                continue
            adressen.add((oid, strasse, hnr))
    with cur.copy("COPY auswertung.gebaeude_adresse (oid_bezug, strasse, hausnr) FROM STDIN") as cp:
        for zeile in adressen:
            cp.write_row(zeile)
    z["adressen"] = len(adressen)
    return z


# ----------------------------------------------------------------------------------- Bericht
def prozent(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}".replace(".", ",") + " %" if b else "–"


def zahl(n) -> str:
    return f"{n:,}".replace(",", ".")


def main() -> int:
    h = hashlib.sha256()
    with open(ZIP, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    if h.hexdigest() != ZIP_SHA256:
        raise SystemExit(f"{ZIP}: SHA256 weicht von HERKUNFT.md ab")
    objekte, lagen, katalog, zaehl = einlesen(ZIP)
    print(f"gelesen: {len(objekte)} Bauwerke mit Fläche, {len(lagen)} Hausnummern, "
          f"{len(katalog)} Katalogeinträge", file=sys.stderr)

    with psycopg.connect("") as conn, conn.cursor() as cur:
        with conn.transaction():
            zuordnung = zuordnen(cur, objekte)
            za = schreiben(cur, objekte, zuordnung, lagen, katalog)
            # Kennzahlen für den Bericht, solange die TEMP-Tabellen leben
            cur.execute("""
                SELECT count(*) FILTER (WHERE in_potsdam),
                       count(*) FILTER (WHERE in_potsdam AND EXISTS (
                           SELECT 1 FROM auswertung.alkis_nas_gebaeude a WHERE a.oid_bezug = snap.oid)),
                       count(*),
                       count(*) FILTER (WHERE EXISTS (
                           SELECT 1 FROM auswertung.alkis_nas_gebaeude a WHERE a.oid_bezug = snap.oid))
                FROM snap""")
            st_pdm, st_pdm_zu, st_alle, st_alle_zu = cur.fetchone()
            cur.execute("""
                SELECT s.art, count(*), count(*) FILTER (WHERE EXISTS (
                           SELECT 1 FROM auswertung.alkis_nas_gebaeude a WHERE a.oid_bezug = s.oid))
                FROM snap s WHERE s.in_potsdam GROUP BY 1 ORDER BY 2 DESC""")
            je_art = cur.fetchall()
            cur.execute("""
                SELECT count(*) FILTER (WHERE oid_bezug IS NOT NULL),
                       count(*) FILTER (WHERE oid_bezug = gml_id || 'BL'),
                       count(*) FILTER (WHERE oid_bezug IS NULL AND EXISTS (
                           SELECT 1 FROM snap s WHERE s.oid = gml_id || 'BL')),
                       count(*) FILTER (WHERE oid_bezug IS NULL)
                FROM auswertung.alkis_nas_gebaeude""")
            zu, gleich_id, verpasst_id, ohne = cur.fetchone()
            cur.execute("""SELECT count(*) FROM (SELECT oid_bezug FROM auswertung.alkis_nas_gebaeude
                           WHERE oid_bezug IS NOT NULL GROUP BY 1 HAVING count(*) > 1) d""")
            mehrfach = cur.fetchone()[0]
            cur.execute("""SELECT width_bucket(ueberlappung, 0, 1.0001, 10), count(*)
                           FROM auswertung.alkis_nas_gebaeude WHERE ueberlappung IS NOT NULL GROUP BY 1 ORDER BY 1""")
            iou_vert = cur.fetchall()
            cur.execute("""SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY ueberlappung)
                           FROM auswertung.alkis_nas_gebaeude""")
            iou_median = cur.fetchone()[0]
            cur.execute("""SELECT count(*), count(DISTINCT oid_bezug) FROM auswertung.gebaeude_adresse""")
            adr_n, adr_geb = cur.fetchone()

    geb = [o for o in objekte.values() if o["art"] == "AX_Gebaeude"]
    n_geb = len(geb)
    fuell = {f: sum(1 for o in geb if o[f] is not None) for f in
             ("dachform", "bauweise", "geschosse", "objekthoehe", "baujahr", "wohnungen")}
    arten = collections.Counter(o["art"] for o in objekte.values())
    dach = collections.Counter(o["dachform"] for o in geb if o["dachform"])
    bauw = collections.Counter(o["bauweise"] for o in geb if o["bauweise"])

    z = []
    z.append("# B0 ALKIS-NAS: Gebäudeform und Zuordnung\n")
    z.append(f"Erzeugt von `skripte/20_alkis_nas.py` am {dt.date.today():%d.%m.%Y}. Quelle: `alkis_p.zip` "
             "(LGB, Bestandsdatenauszug ohne Eigentümer, Stichtag 01.10.2026, SHA256 geprüft). "
             "Bezug: `auswertung.gebaeude_stand_20261105` (Snapshot 05.11.2026), nie `public.gebaeude`.\n")
    z.append("Vermerk: © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), "
             "Daten verändert (eigene Berechnung).\n")
    z.append("## Abnahme\n")
    z.append("| Kriterium | Ergebnis |\n|---|---|")
    z.append(f"| ≥ 98 % der {zahl(GEBAEUDE_IN_POTSDAM)} Gebäude in Potsdam zugeordnet | "
             f"{zahl(st_pdm_zu)} von {zahl(st_pdm)} = **{prozent(st_pdm_zu, st_pdm)}** |")
    z.append(f"| Füllgrad `baujahr` stadtweit | **{zahl(fuell['baujahr'])} von {zahl(n_geb)} AX_Gebaeude "
             f"({prozent(fuell['baujahr'], n_geb)})**; das Element `baujahr` kommt im Auszug nicht vor "
             "(Stichprobe der Erkundung: 0 von 600) |")
    z.append("| Kein Eigentümerfeld importiert | siehe `pruefen/B0_nas.py` (Schemaprüfung, Objektarten) |\n")
    z.append("## Eingelesen\n")
    z.append(f"- Kacheln: {zaehl['kacheln']}; Objekte außerhalb von `wfs:Insert`: {zaehl['nicht_insert']}; "
             f"doppelte gml:id über Kacheln: {zaehl['doppelt']}")
    z.append("- Bauwerke mit Fläche je Objektart (gelesen / ohne Fläche verworfen):")
    for art in KLASSEN:
        z.append(f"  - `{art}`: {zahl(arten[art])} (gelesen {zahl(zaehl['gelesen:' + art])}, "
                 f"ohne Fläche {zahl(zaehl['ohne_flaeche:' + art])})")
    z.append("\n## Zuordnung zum Snapshot\n")
    z.append("Regel: größte Schnittfläche in EPSG:25833 innerhalb derselben Objektart; gültig ab "
             "Schnitt ≥ 50 % der kleineren Fläche. `ueberlappung` = Schnitt / Vereinigung (IoU).\n")
    z.append(f"- Snapshot gesamt (Rechteck): {zahl(st_alle_zu)} von {zahl(st_alle)} zugeordnet "
             f"({prozent(st_alle_zu, st_alle)}); außerhalb der Stadt liefert der Potsdam-Auszug nichts.")
    z.append(f"- In Potsdam: {zahl(st_pdm_zu)} von {zahl(st_pdm)} ({prozent(st_pdm_zu, st_pdm)})")
    z.append("\n| Objektart (Snapshot in Potsdam) | Gebäude | zugeordnet | Anteil |\n|---|---:|---:|---:|")
    for art, n, n_zu in je_art:
        z.append(f"| {art or '(unbekannt)'} | {zahl(n)} | {zahl(n_zu)} | {prozent(n_zu, n)} |")
    z.append("")
    z.append(f"- NAS-Bauwerke mit Zuordnung: {zahl(zu)} von {zahl(len(objekte))}; ohne: {zahl(ohne)}")
    z.append(f"- Gegenprobe Kennung (`oid = gml_id || 'BL'`): {zahl(gleich_id)} der {zahl(zu)} Zuordnungen "
             f"treffen dasselbe Gebäude, {zahl(zu - gleich_id)} weichen ab; ohne Zuordnung, obwohl die Kennung im "
             f"Snapshot steht: {zahl(verpasst_id)}")
    z.append(f"- Snapshot-Gebäude mit mehr als einem NAS-Bauwerk: {zahl(mehrfach)}")
    z.append(f"- IoU Median: {iou_median:.3f}".replace(".", ",") if iou_median is not None else "- IoU Median: –")
    z.append("- IoU-Verteilung (Zehntel): " + ", ".join(
        f"{(b - 1) / 10:.1f}–{b / 10:.1f}: {zahl(n)}".replace(".", ",") for b, n in iou_vert))
    z.append("\n## Füllgrad der Merkmale (AX_Gebaeude)\n")
    z.append("| Merkmal | gefüllt | Anteil |\n|---|---:|---:|")
    for f, n in fuell.items():
        z.append(f"| `{f}` | {zahl(n)} | {prozent(n, n_geb)} |")
    z.append("\n`wohnungen`: Der NAS-Auszug führt kein Attribut zur Zahl der Wohnungen. Die Regel „unter 3 "
             "Wohneinheiten nur Klasse, kein Jahr“ (Prüfbericht, Korrektur 6) lässt sich daher nicht aus B0 "
             "ableiten; B4 braucht eine andere Grundlage (z. B. Gebäudefunktion und Bauweise oder Zensus-"
             "Gebäudetyp).\n")
    z.append("Dachform: " + ", ".join(f"{k} {zahl(v)}" for k, v in dach.most_common()) + ".\n")
    z.append("Bauweise: " + ", ".join(f"{k} {zahl(v)}" for k, v in bauw.most_common()) + ".\n")
    z.append("## Adressen (nur intern)\n")
    z.append(f"`auswertung.gebaeude_adresse`: {zahl(adr_n)} Zeilen an {zahl(adr_geb)} Gebäuden. "
             f"Verweise `zeigtAuf`: {zahl(za['verweise'])}, davon ohne Hausnummernobjekt "
             f"{zahl(za['verweis_ohne_lage'])}, ohne Straßenkatalog {zahl(za['lage_ohne_katalog'])}, "
             f"am nicht zugeordneten Bauwerk {zahl(za['adresse_ohne_zuordnung'])}. "
             "Pseudonummern (Nebengebäude) werden nicht übernommen. Die Tabelle ist für `mosidi_lesen` "
             "gesperrt und darf nie in `daten/` oder einen Export; dieser Bericht enthält nur Zählungen.\n")
    z.append("## Nicht übernommen\n")
    z.append("Buchungs- und Flurstücksangaben (`AX_Buchungsblatt`, `AX_Buchungsstelle`, `AX_Flurstueck`), "
             "Namen an Bauwerken, `lebenszeitintervall` (Fortführungsdatum, kein Baujahr) und alle "
             "übrigen Objektarten. Personen- und Anschriftenobjekte enthält der Auszug nicht.\n")
    BERICHT.parent.mkdir(exist_ok=True)
    BERICHT.write_text("\n".join(z), encoding="utf-8")
    print(f"zugeordnet in Potsdam: {st_pdm_zu}/{st_pdm} ({prozent(st_pdm_zu, st_pdm)}); "
          f"baujahr {fuell['baujahr']}/{n_geb}; Bericht {BERICHT.relative_to(WURZEL)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
