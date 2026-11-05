"""B3: Luftbild-Pilot. Grenzen die DOP-Zeitreihe der LGB Baujahre ein? (Pilot Bornstedt)

Teilschritte (einzeln aufrufbar, in dieser Reihenfolge):

  abrufen     DOP-Zeitreihe als WMS-Ausschnitte (4 Quadranten je Befliegung, 0,4 m) und die Flugdaten
              je 1-km-Blatt über GetFeatureInfo auf den *_info-Layern. Höchstens eine Anfrage je 10 s an
              isk.geobasis-bb.de, jede Anfrage steht im gemeinsamen Abrufprotokoll (skripte/abruf.py).
              Vorhandene Dateien werden nicht erneut geholt.
  stichprobe  Stichprobe für die Referenz (Rahmen und Seed siehe pruefen/B3_protokoll.md) und Kontaktbögen
              für die Sichtprüfung. Schreibt nur nach $KIEZ_DATEN/luftbild_lgb/<stand>/referenz/
              (nicht ins öffentliche Repo: oid ist über ALKIS auf die Adresse rückführbar, Korrektur 6).
  auswerten   automatische Klammer je Gebäude im Pilotgebiet, Abgleich mit der Referenz, Gegenprobe gegen
              Zensus 2022, schreibt auswertung.jahr_klammer und berichte/B3_pilot.md (nur Aggregate).

Aufruf (Passwort nur aus der .env, chmod 600):
    set -a; . ../kiezatlas-potsdam/.env; set +a
    PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=kiezatlas_rechnen \\
    PGPASSWORD="$RECHNEN_PASSWORD" KIEZ_DATEN=../kiezatlas-daten \\
    uv run -q --offline --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \\
        --with pillow --with numpy --with shapely python -I skripte/23_luftbild_pilot.py <teilschritt>

Lizenz der Bilder: © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0).
Die Bilder bleiben in $KIEZ_DATEN; ins Repo kommen nur Zählungen.
"""
from __future__ import annotations

import fcntl
import importlib.util
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
KIEZ_DATEN = Path(os.environ.get("KIEZ_DATEN", WURZEL.parent / "kiezatlas-daten"))
STAND = "2026-11-05"
ABLAGE = KIEZ_DATEN / "luftbild_lgb" / STAND
REFERENZ = ABLAGE / "referenz"
BERICHT = WURZEL / "berichte" / "B3_pilot.md"
SNAPSHOT = "auswertung.gebaeude_stand_20261105"
PILOT_NR = "13"            # Stadtteil Bornstedt
DIENST = "https://isk.geobasis-bb.de/mapproxy/{dienst}/service/wms"
ABSTAND_S = 10.0           # Bauplan B3: höchstens 1 Anfrage je 10 s

# Ausschnitt (EPSG:25833) um Bornstedt (Stadtteil 13: 364895–367797 / 5808018–5810656), auf 100 m gerundet
AUSSCHNITT = (364800.0, 5808000.0, 367800.0, 5810700.0)
AUFLOESUNG = 0.4           # m je Pixel für alle Befliegungen (1953 und 1992–97 werden hochgerechnet)
QUADRANTEN = 2             # 2 x 2 Bilder je Befliegung, je 1.500 m x 1.350 m = 3.750 x 3.375 px

# Befliegungen, älteste zuerst: (Schlüssel, Dienst, Bildlayer, Info-Layer)
EPOCHEN = [
    ("1953", "dop100g_1953", "bb_dop100g_1953", "bb_dop100g-53_info"),
    ("1992_1997", "dop50g_1992_1997", "bb_dop50g_1992_1997", "bb_dop50g-92-97_info"),
    ("2001_2009", "dop40g_2001_2009", "bb_dop40g_2001_2009", "bb_dop40g-01-09_info"),
    ("2009_2012", "dop20_2009_2012", "dop20_bebb_2009_2012_farbe", "bb_dop-09-12_info"),
    ("2013_2015", "dop20_2013_2015", "dop20_bebb_2013_2015_farbe", "bb_dop-13-15_info"),
    ("2016_2018", "dop20_2016_2018", "dop20_bebb_2016_2018_farbe", "bb_dop-16-18_info"),
    ("2019_2021", "dop20_2019_2021", "dop20_bebb_2019_2021_farbe", "bb_dop-19-21_info"),
    ("aktuell", "dop20c", "bebb_dop20c", "bb_dop_info"),
]
# Flugdaten: je 1-km-Blatt ab 2009 (dort zählt das Jahr), bei den älteren Befliegungen 4 Punkte
BLATT_X = range(364, 368)
BLATT_Y = range(5808, 5811)


def _abruf_modul():
    spec = importlib.util.spec_from_file_location("abruf", WURZEL / "skripte" / "abruf.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def quadranten():
    x0, y0, x1, y1 = AUSSCHNITT
    dx, dy = (x1 - x0) / QUADRANTEN, (y1 - y0) / QUADRANTEN
    for j in range(QUADRANTEN):          # j = 0 oben (Norden)
        for i in range(QUADRANTEN):
            yield f"q{j}{i}", (x0 + i * dx, y1 - (j + 1) * dy, x0 + (i + 1) * dx, y1 - j * dy)


def info_punkte(schluessel: str):
    if schluessel in ("1953", "1992_1997", "2001_2009"):
        for name, (a, b, c, d) in quadranten():
            yield name, ((a + c) / 2, (b + d) / 2)
    else:
        for bx in BLATT_X:
            for by in BLATT_Y:
                yield f"b{bx}_{by}", (bx * 1000 + 500.0, by * 1000 + 500.0)


def anfragen():
    """Alle Anfragen des Abrufs als (url, ziel)."""
    for schluessel, dienst, layer, info in EPOCHEN:
        basis = DIENST.format(dienst=dienst)
        for name, (a, b, c, d) in quadranten():
            breite = round((c - a) / AUFLOESUNG)
            hoehe = round((d - b) / AUFLOESUNG)
            url = (f"{basis}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS={layer}&STYLES=&CRS=EPSG:25833"
                   f"&BBOX={a:.0f},{b:.0f},{c:.0f},{d:.0f}&WIDTH={breite}&HEIGHT={hoehe}&FORMAT=image/jpeg")
            yield url, ABLAGE / schluessel / f"{name}.jpg"
        for name, (x, y) in info_punkte(schluessel):
            url = (f"{basis}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS={info}&QUERY_LAYERS={info}"
                   f"&STYLES=&CRS=EPSG:25833&BBOX={x - 50:.0f},{y - 50:.0f},{x + 50:.0f},{y + 50:.0f}"
                   f"&WIDTH=101&HEIGHT=101&I=50&J=50&INFO_FORMAT=text/plain&FORMAT=image/png")
            yield url, ABLAGE / schluessel / f"info_{name}.txt"


def abrufen() -> int:
    abruf = _abruf_modul()
    protokoll = KIEZ_DATEN / "abrufprotokoll.tsv"
    sperre_datei = KIEZ_DATEN / "abrufprotokoll.lock"
    offen = [(u, z) for u, z in anfragen() if not z.exists()]
    print(f"{len(offen)} Anfragen offen, Abstand {ABSTAND_S:g} s", file=sys.stderr)
    fehler = 0
    for n, (url, ziel) in enumerate(offen, 1):
        # Erst außerhalb der Sperre warten, damit andere Pakete in der Zwischenzeit abrufen können;
        # holen() prüft den Abstand unter der Sperre noch einmal.
        zuletzt = abruf.letzte_anfrage(protokoll, "isk.geobasis-bb.de")
        if zuletzt is not None and (rest := zuletzt + ABSTAND_S - time.time()) > 0:
            time.sleep(rest)
        with sperre_datei.open("w") as sperre:
            fcntl.flock(sperre, fcntl.LOCK_EX)
            code, _ = abruf.holen(url, ziel, ABSTAND_S, 60, protokoll)
        if code != 0:
            fehler += 1
            print(f"[{n}/{len(offen)}] Fehler {code}: {url}", file=sys.stderr)
            if fehler >= 3:
                print("drei Fehler, Abbruch", file=sys.stderr)
                return 4
        else:
            print(f"[{n}/{len(offen)}] {ziel.relative_to(ABLAGE)}  {datetime.now(UTC):%H:%M:%S}", file=sys.stderr)
    return 0


# ----------------------------------------------------------------------------------------- Rahmen
# Hauptgebäude im Pilotgebiet: Bauwerksart „Gebäude“, Fläche >= 50 m², keine Nebengebäude (E5).
NEBENGEBAEUDE = ("Garage", "Schuppen", "Gartenhaus", "Gebäude zur Freizeitgestaltung", "Treibhaus, Gewächshaus",
                 "Gebäude zum Parken", "Tiefgarage", "Überdachung", "Umformer", "Toilette",
                 "Durchfahrt im Gebäude")
MIN_FLAECHE = 50.0
SEED = "B3-Referenz-2026-11-05"
LOS_GROESSE = 40


def verbindung():
    import psycopg
    return psycopg.connect()   # PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD aus der Umgebung


def rahmen(cur, alle: bool = False):
    """Gebäude im Pilotgebiet als Liste (oid, funktion, flaeche, wkb in EPSG:25833), in Los-Reihenfolge.

    alle=False: nur der Stichprobenrahmen (Hauptgebäude). Reihenfolge = md5(oid || SEED), also fest und
    unabhängig von Bild oder Ergebnis."""
    bedingung = "" if alle else "AND g.gebnutzbez = 'Gebäude' AND NOT (g.funktion = ANY(%(neben)s)) " \
                                "AND ST_Area(ST_Transform(g.geom, 25833)) >= %(min)s"
    cur.execute(f"""
        SELECT g.oid, g.funktion, g.gebnutzbez, ST_Area(ST_Transform(g.geom, 25833)),
               ST_AsBinary(ST_Transform(g.geom, 25833))
        FROM {SNAPSHOT} g JOIN public.stadtteil s ON s.nr = %(nr)s
         AND ST_Within(ST_PointOnSurface(g.geom), s.geom)
        WHERE true {bedingung}
        ORDER BY md5(g.oid || %(seed)s)""",
                {"nr": PILOT_NR, "neben": list(NEBENGEBAEUDE), "min": MIN_FLAECHE, "seed": SEED})
    return cur.fetchall()


# ------------------------------------------------------------------------------------------- Bilder
class Mosaik:
    """Die vier Quadranten einer Befliegung als ein Bild im Raster des AUSSCHNITTS."""

    def __init__(self, schluessel: str, modus: str = "L"):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        x0, y0, x1, y1 = AUSSCHNITT
        self.breite = round((x1 - x0) / AUFLOESUNG)
        self.hoehe = round((y1 - y0) / AUFLOESUNG)
        self.bild = Image.new(modus, (self.breite, self.hoehe))
        for name, (a, b, c, d) in quadranten():
            with Image.open(ABLAGE / schluessel / f"{name}.jpg") as q:
                self.bild.paste(q.convert(modus), self.pixel(a, d))

    @staticmethod
    def pixel(x: float, y: float) -> tuple[int, int]:
        return round((x - AUSSCHNITT[0]) / AUFLOESUNG), round((AUSSCHNITT[3] - y) / AUFLOESUNG)


def ausschnitt_um(geom, rand: float = 15.0, mindestens: float = 50.0):
    a, b, c, d = geom.bounds
    seite = max(c - a, d - b) + 2 * rand
    seite = max(seite, mindestens)
    mx, my = (a + c) / 2, (b + d) / 2
    return mx - seite / 2, my - seite / 2, mx + seite / 2, my + seite / 2


def stichprobe(lose: int) -> int:
    """Kontaktbögen der ersten `lose` Lose (je LOS_GROESSE Gebäude) für die Sichtprüfung."""
    import csv

    from PIL import Image, ImageDraw
    from shapely import wkb

    REFERENZ.mkdir(parents=True, exist_ok=True)
    with verbindung() as con, con.cursor() as cur:
        zeilen = rahmen(cur)
    print(f"Rahmen: {len(zeilen)} Hauptgebäude im Pilotgebiet", file=sys.stderr)
    auswahl = zeilen[: lose * LOS_GROESSE]
    with (REFERENZ / "stichprobe.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nr", "los", "oid", "funktion", "flaeche_m2"])
        for i, (oid, funktion, _art, flaeche, _g) in enumerate(auswahl):
            w.writerow([i + 1, i // LOS_GROESSE + 1, oid, funktion, f"{flaeche:.0f}"])
    chip, kopf, zeilen_je_bogen = 150, 22, 8
    geoms = [wkb.loads(bytes(g)) for *_, g in auswahl]
    bilder = {}
    for schluessel, *_ in EPOCHEN:
        m = Mosaik(schluessel, "RGB")
        for i, g in enumerate(geoms):
            a, b, c, d = ausschnitt_um(g)
            p0, p1 = Mosaik.pixel(a, d), Mosaik.pixel(c, b)
            stueck = m.bild.crop((*p0, *p1)).resize((chip, chip))
            zeichner = ImageDraw.Draw(stueck)
            skala = chip / (c - a)
            for ring in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
                punkte = [((x - a) * skala, (d - y) * skala) for x, y in ring.exterior.coords]
                zeichner.line(punkte, fill=(0, 220, 255), width=1)
            bilder[(i, schluessel)] = stueck
        del m
    for start in range(0, len(geoms), zeilen_je_bogen):
        nummern = range(start, min(start + zeilen_je_bogen, len(geoms)))
        bogen = Image.new("RGB", (60 + chip * len(EPOCHEN), kopf + chip * len(nummern)), "white")
        zeichner = ImageDraw.Draw(bogen)
        for k, (schluessel, *_) in enumerate(EPOCHEN):
            zeichner.text((60 + k * chip + 4, 4), f"{k} {schluessel}", fill="black")
        for z, i in enumerate(nummern):
            zeichner.text((4, kopf + z * chip + chip // 2), f"#{i + 1}", fill="black")
            for k, (schluessel, *_) in enumerate(EPOCHEN):
                bogen.paste(bilder[(i, schluessel)], (60 + k * chip, kopf + z * chip))
        bogen.save(REFERENZ / f"bogen_{start // zeilen_je_bogen + 1:02d}.png")
    print(f"{len(geoms)} Gebäude, Bögen in {REFERENZ}", file=sys.stderr)
    return 0


def main() -> int:
    schritt = sys.argv[1] if len(sys.argv) > 1 else ""
    if schritt == "abrufen":
        return abrufen()
    if schritt == "stichprobe":
        return stichprobe(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
