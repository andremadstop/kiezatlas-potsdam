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


# --------------------------------------------------------------------------------------- Auswertung
# Methode (vor dem ersten Lauf festgelegt, nicht an der Referenz abgestimmt; pruefen/B3_protokoll.md §8):
#   1. Je Gebäude und Befliegung k ein Ausschnitt um den heutigen ALKIS-Umriss, in Graustufen, auf die
#      Bodenauflösung der Befliegung geglättet (Gauß, sigma = halbe Bodenauflösung).
#   2. Kantenbild (Sobel-Betrag). Vorlage = Kantenbild der aktuellen Befliegung (k = 7) am selben Ort.
#   3. Wert(k) = größte Pearson-Korrelation zwischen Vorlage und Kantenbild k innerhalb des um 1,5 m
#      gepufferten Umrisses, gesucht über Verschiebungen bis ±2 m (Lagefehler zwischen den Befliegungen).
#   4. Schwelle je Befliegung = 95-%-Quantil einer Nullverteilung: dieselbe Vorlage gegen den Ausschnitt eines
#      anderen Gebäudes des Rahmens (fester Partner) in derselben Befliegung.
#   5. „sichtbar(k)“ = Wert(k) > Schwelle(k); sichtbar(7) gilt per Definition. k_auto = die Stufe, ab der die
#      Treppenfunktion „ab k sichtbar“ die wenigsten Abweichungen von sichtbar(0..7) hat; bei Gleichstand die
#      spätere Stufe (Sichtbarkeit muss belegt sein).
BODEN_M = [1.0, 0.5, 0.4, 0.2, 0.2, 0.2, 0.2, 0.2]   # Bodenauflösung je Befliegung (Capabilities/Handbuch)
FLUGJAHR = [1953, 1996, 2007, 2012, 2015, 2018, 2021, 2024]   # info_*.txt, „Ersterstellung“
PUFFER_M = 1.5
SUCHE_M = 2.0
QUANTIL = 0.95
QUELLE_JA = "LGB DOP-Zeitreihe, Pilot Bornstedt"
QUELLE_NEIN = "LGB DOP-Zeitreihe, Pilot Bornstedt (nicht ausgerollt)"
REFERENZ_SHA = "6f5a0fb5ceb6ffb737292cca9852e414ea8f7794b5169f84291e1ae8270d4173"
NACH_2009_AB = 4          # k_ref >= 4: erstmals 2015 oder später zu sehen (Flug 2012 noch ohne)
WOHNEN = ("Wohnhaus", "Wohngebäude", "Wohngebäude mit Handel und Dienstleistungen", "Wohnheim",
          "Wohn- und Bürogebäude", "Wohn- und Geschäftsgebäude", "Wohn- und Betriebsgebäude",
          "Wohngebäude mit Gemeinbedarf", "Wohngebäude mit Gewerbe und Industrie")


def _graubilder():
    import numpy as np
    bilder = []
    for schluessel, *_ in EPOCHEN:
        bilder.append(np.asarray(Mosaik(schluessel, "L").bild, dtype=np.uint8))
    return bilder


class Vorlage:
    """Ausschnitt-Raster und Maske um einen Umriss (Pixel im Mosaik, 0,4 m)."""

    def __init__(self, geom):
        import numpy as np
        from PIL import Image, ImageDraw
        rand = PUFFER_M + SUCHE_M + 1.0
        a, b, c, d = geom.bounds
        self.p0 = Mosaik.pixel(a - rand, d + rand)
        p1 = Mosaik.pixel(c + rand, b - rand)
        self.groesse = (p1[0] - self.p0[0], p1[1] - self.p0[1])        # (breite, hoehe)
        maske = Image.new("1", self.groesse, 0)
        zeichner = ImageDraw.Draw(maske)
        gepuffert = geom.buffer(PUFFER_M)
        for poly in (gepuffert.geoms if gepuffert.geom_type == "MultiPolygon" else [gepuffert]):
            punkte = [((x - AUSSCHNITT[0]) / AUFLOESUNG - self.p0[0],
                       (AUSSCHNITT[3] - y) / AUFLOESUNG - self.p0[1]) for x, y in poly.exterior.coords]
            zeichner.polygon(punkte, fill=1)
            for loch in poly.interiors:
                zeichner.polygon([((x - AUSSCHNITT[0]) / AUFLOESUNG - self.p0[0],
                                   (AUSSCHNITT[3] - y) / AUFLOESUNG - self.p0[1]) for x, y in loch.coords], fill=0)
        self.maske = np.asarray(maske, dtype=bool)
        self.mitte = ((a + c) / 2, (b + d) / 2)


def _kanten(bild, p0, groesse, sigma_px, rand_px):
    """Kantenbild (Sobel-Betrag) eines Ausschnitts, mit rand_px Zugabe ringsum; None am Mosaikrand."""
    import numpy as np
    from scipy import ndimage
    x0, y0 = p0[0] - rand_px, p0[1] - rand_px
    x1, y1 = p0[0] + groesse[0] + rand_px, p0[1] + groesse[1] + rand_px
    if x0 < 0 or y0 < 0 or x1 > bild.shape[1] or y1 > bild.shape[0]:
        return None
    stueck = ndimage.gaussian_filter(bild[y0:y1, x0:x1].astype(np.float32), sigma_px)
    return np.hypot(ndimage.sobel(stueck, 1), ndimage.sobel(stueck, 0))


def _wert(vorlage_kanten, maske, kanten_k, such_px):
    """Größte Korrelation über alle Verschiebungen bis ±such_px innerhalb der Maske."""
    import numpy as np
    v = vorlage_kanten[maske]
    v = v - v.mean()
    nv = np.sqrt((v * v).sum())
    if nv == 0:
        return float("nan")
    h, b = maske.shape
    bester = -1.0
    for dy in range(2 * such_px + 1):
        for dx in range(2 * such_px + 1):
            w = kanten_k[dy:dy + h, dx:dx + b][maske]
            w = w - w.mean()
            nw = np.sqrt((w * w).sum())
            if nw > 0:
                bester = max(bester, float((v * w).sum() / (nv * nw)))
    return bester


def k_aus_sichtbar(sichtbar: list[bool]) -> int:
    """Treppe 'ab k sichtbar' mit den wenigsten Abweichungen; Gleichstand -> spätere Stufe."""
    letzte = len(sichtbar) - 1
    beste_k, beste_fehler = letzte, None
    for k in range(letzte + 1):
        fehler = sum(sichtbar[j] for j in range(k)) + sum(not sichtbar[j] for j in range(k, letzte + 1))
        if beste_fehler is None or fehler <= beste_fehler:
            beste_k, beste_fehler = k, fehler
    return beste_k


def _zensus_bornstedt(cur):
    """Zensus 2022, Gebäude mit Wohnraum nach Baujahr, 100-m-Zellen mit Mittelpunkt in Bornstedt (offline)."""
    import csv
    import io
    import zipfile
    zip_pfad = KIEZ_DATEN / "zensus" / "2022" / "Gebaeude_nach_Baujahr_Jahrzehnte.zip"
    cur.execute("SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) FROM "
                "(SELECT ST_Extent(ST_Transform(geom, 3035)) e FROM public.stadtteil WHERE nr = %s) q", (PILOT_NR,))
    x0, y0, x1, y1 = cur.fetchone()
    zeilen = []
    with zipfile.ZipFile(zip_pfad) as z, z.open("Gebaeude_nach_Baujahr/Zensus2022_Baujahr_JZ_100m-Gitter.csv") as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
            x, y = int(r["x_mp_100m"]), int(r["y_mp_100m"])
            if x0 - 100 <= x <= x1 + 100 and y0 - 100 <= y <= y1 + 100:
                zeilen.append(r)

    def zahl(s):
        return int(s) if s.strip().isdigit() else 0          # „–“ (verfälscht/geheim) zählt als 0

    cur.execute("CREATE TEMP TABLE b3_zensus (x int, y int, gesamt int, a2010 int, a2016 int, a2000 int) "
                "ON COMMIT DROP")
    with cur.copy("COPY b3_zensus FROM STDIN") as kopie:
        for r in zeilen:
            kopie.write_row((int(r["x_mp_100m"]), int(r["y_mp_100m"]), zahl(r["Insgesamt_Gebaeude"]),
                             zahl(r["a2010bis2015"]), zahl(r["a2016undspaeter"]), zahl(r["a2000bis2009"])))
    cur.execute("""SELECT count(*), sum(gesamt), sum(a2000), sum(a2010), sum(a2016)
                   FROM b3_zensus z JOIN public.stadtteil s ON s.nr = %s
                    AND ST_Within(ST_Transform(ST_SetSRID(ST_MakePoint(z.x, z.y), 3035), 4326), s.geom)""",
                (PILOT_NR,))
    return cur.fetchone()


def auswerten() -> int:
    import csv
    import hashlib
    import statistics

    import numpy as np
    from shapely import wkb

    ref_datei = REFERENZ / "referenz.csv"
    if hashlib.sha256(ref_datei.read_bytes()).hexdigest() != REFERENZ_SHA:
        print("referenz.csv weicht vom festgelegten SHA256 ab, Abbruch", file=sys.stderr)
        return 3
    with verbindung() as con, con.cursor() as cur:
        zeilen = rahmen(cur)
    oids = [z[0] for z in zeilen]
    funktion = {z[0]: z[1] for z in zeilen}
    geoms = [wkb.loads(bytes(z[4])) for z in zeilen]
    n = len(geoms)
    print(f"Rahmen: {n} Hauptgebäude, lade Mosaike", file=sys.stderr)
    bilder = _graubilder()
    such_px = round(SUCHE_M / AUFLOESUNG)
    vorlagen = [Vorlage(g) for g in geoms]
    partner = [(i + 1) % n for i in range(n)]                 # fester Partner für die Nullverteilung
    werte = np.full((n, len(EPOCHEN)), np.nan)
    null = np.full((n, len(EPOCHEN)), np.nan)
    for k in range(len(EPOCHEN) - 1):
        sigma = BODEN_M[k] / AUFLOESUNG / 2
        for i, v in enumerate(vorlagen):
            vk = _kanten(bilder[-1], v.p0, v.groesse, sigma, 0)
            ek = _kanten(bilder[k], v.p0, v.groesse, sigma, such_px)
            if vk is None or ek is None:
                continue
            werte[i, k] = _wert(vk, v.maske, ek, such_px)
            # Null: dieselbe Vorlage gegen den Ort des Partners (gleiche Ausschnittgröße, um dessen Mitte)
            w = vorlagen[partner[i]]
            mx, my = Mosaik.pixel(*w.mitte)
            p0 = (mx - v.groesse[0] // 2, my - v.groesse[1] // 2)
            ek0 = _kanten(bilder[k], p0, v.groesse, sigma, such_px)
            if ek0 is not None:
                null[i, k] = _wert(vk, v.maske, ek0, such_px)
        print(f"Befliegung {k} ({EPOCHEN[k][0]}) fertig", file=sys.stderr)
    schwelle = [float(np.nanquantile(null[:, k], QUANTIL)) for k in range(len(EPOCHEN) - 1)]
    k_auto = {}
    for i, oid in enumerate(oids):
        if np.isnan(werte[i, :-1]).any():
            continue
        sichtbar = [bool(werte[i, k] > schwelle[k]) for k in range(len(EPOCHEN) - 1)] + [True]
        k_auto[oid] = k_aus_sichtbar(sichtbar)

    # ---- Abgleich mit der Referenz (erst jetzt gelesen)
    with ref_datei.open(encoding="utf-8") as f:
        ref = list(csv.DictReader(f))
    def quote(auswahl, bedingung):
        auswahl = [r for r in auswahl if r["oid"] in k_auto]
        treffer = sum(bedingung(r) for r in auswahl)
        return treffer, len(auswahl)
    klar = [r for r in ref if r["unklar"] == "0"]
    nach = [r for r in klar if int(r["k_ref"]) >= NACH_2009_AB]
    k3 = [r for r in klar if int(r["k_ref"]) == 3]
    alt_genau = [r for r in klar if int(r["k_ref"]) <= 2 and r["frueher_moeglich"] == "0"]
    vor = [r for r in klar if int(r["k_ref"]) < NACH_2009_AB]
    gleich = lambda r: k_auto[r["oid"]] == int(r["k_ref"])
    nah = lambda r: abs(k_auto[r["oid"]] - int(r["k_ref"])) <= 1
    haupt = quote(nach, gleich)
    neben = quote(vor, lambda r: k_auto[r["oid"]] >= NACH_2009_AB)
    haupt_quote = haupt[0] / haupt[1] if haupt[1] else 0.0
    neben_quote = neben[0] / neben[1] if neben[1] else 1.0
    ausrollen = haupt[1] >= 50 and haupt_quote >= 0.80 and neben_quote <= 0.10
    quelle = QUELLE_JA if ausrollen else QUELLE_NEIN

    # Verwechslungstafel (Zeilen k_ref, Spalten k_auto) für die Referenz ohne unklar
    tafel = [[0] * len(EPOCHEN) for _ in EPOCHEN]
    for r in klar:
        if r["oid"] in k_auto:
            tafel[int(r["k_ref"])][k_auto[r["oid"]]] += 1

    # ---- Datenbank: Klammer je Gebäude des Rahmens (nur Pilotgebiet, keine Nebengebäude)
    with verbindung() as con, con.cursor() as cur:
        cur.execute("DELETE FROM auswertung.jahr_klammer WHERE quelle IN (%s, %s)", (QUELLE_JA, QUELLE_NEIN))
        with cur.copy("COPY auswertung.jahr_klammer (oid_bezug, nicht_vor, nicht_nach, quelle) FROM STDIN") as kopie:
            for oid, k in k_auto.items():
                kopie.write_row((oid, FLUGJAHR[k - 1] if k > 0 else None, FLUGJAHR[k], quelle))
        zensus = _zensus_bornstedt(cur)
        con.commit()
    verteilung = [sum(1 for k in k_auto.values() if k == j) for j in range(len(EPOCHEN))]
    wohnen_neu_46 = sum(1 for o, k in k_auto.items() if funktion[o] in WOHNEN and 4 <= k <= 6)
    wohnen_neu_47 = sum(1 for o, k in k_auto.items() if funktion[o] in WOHNEN and 4 <= k <= 7)
    wohnen_neu_ref = [r for r in nach if r["funktion"] in WOHNEN]
    breite = [FLUGJAHR[k] - FLUGJAHR[k - 1] for k in k_auto.values() if k > 0]
    _bericht(n=n, k_auto=k_auto, schwelle=schwelle, null=null, werte=werte, haupt=haupt, neben=neben,
             k3=quote(k3, gleich), alt=quote(alt_genau, gleich), nah=quote(nach, nah),
             klar=klar, ref=ref, tafel=tafel, ausrollen=ausrollen, quelle=quelle, verteilung=verteilung,
             zensus=zensus, wohnen_neu_46=wohnen_neu_46, wohnen_neu_47=wohnen_neu_47,
             wohnhaus=quote(wohnen_neu_ref, gleich),
             rest=quote([r for r in nach if r["funktion"] not in WOHNEN], gleich),
             lose={los: quote([r for r in nach if r["los"] == los], gleich)
                   for los in sorted({r["los"] for r in nach})},
             median_breite=statistics.median(breite) if breite else None)
    print(f"Hauptkriterium {haupt[0]}/{haupt[1]}, Nebenbedingung {neben[0]}/{neben[1]}, "
          f"ausrollen={ausrollen}", file=sys.stderr)
    return 0


def _pz(a: int, b: int) -> str:
    return f"{a} von {b} ({100 * a / b:.1f} %)".replace(".", ",") if b else "–"


def _bericht(**w) -> None:
    import numpy as np
    zz = w["zensus"]
    zeilen = [
        "# B3 Luftbild-Pilot Bornstedt: Ergebnis",
        "",
        f"Stand {datetime.now(UTC):%d.%m.%Y}. Erzeugt von `skripte/23_luftbild_pilot.py auswerten`. Protokoll, Stichprobe und",
        "Trefferregel stehen in `pruefen/B3_protokoll.md` und wurden vor diesem Lauf festgelegt (Commits f482058, 67bffd5).",
        "Dieser Bericht enthält nur Zählungen, keine Gebäudekennungen.",
        "",
        "## Entscheidung",
        "",
        f"- **{'Ausrollen: ja' if w['ausrollen'] else 'Ausrollen: nein'}.** Hauptkriterium (Bauplan B3): Die automatische Klammer trifft",
        f"  bei {_pz(*w['haupt'])} Referenzgebäuden, die erst nach dem Flug vom 20.05.2012 zu sehen sind (Schwelle 80 %,",
        "  mindestens 50 Gebäude).",
        f"- Nebenbedingung: Von den Referenzgebäuden, die 2012 schon zu sehen sind, datiert die Automatik {_pz(*w['neben'])}",
        "  fälschlich auf „nach 2012“ (zulässig höchstens 10 %).",
        f"- Folge: Die {len(w['k_auto'])} Zeilen in `auswertung.jahr_klammer` tragen die Quelle „{w['quelle']}“.",
        "  B4 nimmt nur Zeilen ohne den Zusatz „nicht ausgerollt“ als Kaskadenstufe." if not w["ausrollen"] else
        "  B4 darf sie als Kaskadenstufe 2 nehmen, vorerst nur für Bornstedt.",
        "",
        "## Referenz und Treffer",
        "",
        "| Gruppe | Treffer (k_auto = k_ref) |",
        "|---|---|",
        f"| erstmals ab 2015 zu sehen (k_ref ≥ 4), Hauptkriterium | {_pz(*w['haupt'])} |",
        f"| davon Wohngebäude | {_pz(*w['wohnhaus'])} |",
        f"| davon übrige Hauptgebäude | {_pz(*w['rest'])} |",
        f"| erstmals 2012 zu sehen (k_ref = 3, 2007 bis 2012) | {_pz(*w['k3'])} |",
        f"| bis 2007 zu sehen, Stufe sicher (k_ref ≤ 2) | {_pz(*w['alt'])} |",
        f"| k_ref ≥ 4, höchstens eine Stufe daneben | {_pz(*w['nah'])} |",
        "",
        "Treffer im Hauptkriterium je Los: " + ", ".join(f"Los {los}: {_pz(*q)}" for los, q in w["lose"].items()) + ".",
        "",
        f"Referenz: 200 Gebäude in 5 Losen, davon {sum(r['unklar'] == '1' for r in w['ref'])} unklar (nicht gewertet).",
        "Sichtprüfung durch den Agenten auf denselben Bildern; gemessen ist „Automatik gegen Sichtprüfung“.",
        "",
        "Verwechslungstafel (Zeile = Sichtprüfung k_ref, Spalte = Automatik k_auto, ohne unklar):",
        "",
        "| k_ref \\ k_auto | " + " | ".join(str(j) for j in range(8)) + " |",
        "|---|" + "---:|" * 8,
    ]
    for kr in range(8):
        zeilen.append(f"| {kr} ({FLUGJAHR[kr]}) | " + " | ".join(str(x) for x in w["tafel"][kr]) + " |")
    zeilen += [
        "",
        "## Automatik",
        "",
        f"- Gebäude im Rahmen: {w['n']}, davon mit Klammer: {len(w['k_auto'])}.",
        "- Verteilung k_auto (erste Befliegung mit Gebäude): " + ", ".join(
            f"{FLUGJAHR[j]}: {c}" for j, c in enumerate(w["verteilung"])) + ".",
        f"- Median der Klammerbreite (ohne „schon 1953“): {w['median_breite']} Jahre." if w["median_breite"] else "",
        "- Schwellen (95-%-Quantil der Nullverteilung) je Befliegung: " + ", ".join(
            f"{FLUGJAHR[k]}: {s:.2f}".replace(".", ",") for k, s in enumerate(w["schwelle"])) + ".",
        "- Median des Werts am eigenen Ort je Befliegung: " + ", ".join(
            f"{FLUGJAHR[k]}: {np.nanmedian(w['werte'][:, k]):.2f}".replace(".", ",") for k in range(7)) + ".",
        "",
        "## Gegenprobe Zensus 2022 (beschreibend, kein Abbruchkriterium)",
        "",
        f"- 100-m-Zellen mit Mittelpunkt in Bornstedt: {zz[0]}, Gebäude mit Wohnraum insgesamt {zz[1]},",
        f"  davon 2000 bis 2009: {zz[2]}, 2010 bis 2015: {zz[3]}, 2016 und später: {zz[4]}",
        f"  (zusammen ab 2010: {zz[3] + zz[4]}). Werte mit Cell-Key-Verfahren, „–“ als 0 gezählt; Stichtag 15.05.2022.",
        f"- Automatik, Wohngebäude im Rahmen, erstmals 2015 bis 2021 zu sehen: {w['wohnen_neu_46']};",
        f"  erstmals 2015 bis 2024: {w['wohnen_neu_47']}.",
        "- Vergleich nur in der Größenordnung: ALKIS zählt Gebäudeteile (Reihenhäuser einzeln), der Zensus Gebäude mit",
        "  Wohnraum; Flugjahre und Zensus-Klassen decken sich nicht (Bauten von 2010 bis Mai 2012 sind schon im Flug 2012).",
        "",
        "## Lizenz",
        "",
        "Luftbilder: © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung).",
        "Zensus: © Statistisches Bundesamt (Destatis), Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0),",
        "Daten verändert (eigene Berechnung).",
        "",
    ]
    BERICHT.parent.mkdir(parents=True, exist_ok=True)
    BERICHT.write_text("\n".join(z for z in zeilen if z is not None) + "\n", encoding="utf-8")


def main() -> int:
    schritt = sys.argv[1] if len(sys.argv) > 1 else ""
    if schritt == "abrufen":
        return abrufen()
    if schritt == "stichprobe":
        return stichprobe(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    if schritt == "auswerten":
        return auswerten()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
