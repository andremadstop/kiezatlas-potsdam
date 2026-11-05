"""Tests für Paket A5b (skripte/14b_fussweg.py).

Ohne Datenbank: kleine Netze mit bekannten Wegen und ein Zufallsnetz für „Fußweg ≥ Luftlinie“.
Mit A5B_DB_TEST=1: Probelauf gegen die echte Datenbank (echte Zellen und Ziele aus A2/A4), aber mit einem
Gitternetz (50 m) in TEMP-Tabellen statt des OSM-Netzes. In auswertung.netz_* wird nichts geschrieben.
Alles läuft in einer Transaktion und endet mit ROLLBACK.

Aufruf: skripte/14b_fussweg.sh test
        A5B_DB_TEST=1 skripte/14b_fussweg.sh test
"""
from __future__ import annotations

import importlib
import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "skripte"))
sys.path.insert(0, str(WURZEL / "pruefen"))
fw = importlib.import_module("14b_fussweg")


def gitter(nx: int, ny: int, abstand: float = 100.0, x0: float = 0.0, y0: float = 0.0):
    """Rechteckgitter: Knoten-IDs ab 1000, Kanten waagerecht und senkrecht mit Länge = abstand."""
    ii, jj = np.meshgrid(np.arange(nx), np.arange(ny), indexing="ij")
    ids = 1000 + (ii * ny + jj).ravel()
    xy = np.column_stack([x0 + ii.ravel() * abstand, y0 + jj.ravel() * abstand])
    von, nach = [], []
    for i in range(nx):
        for j in range(ny):
            k = 1000 + i * ny + j
            if i + 1 < nx:
                von.append(k), nach.append(k + ny)
            if j + 1 < ny:
                von.append(k), nach.append(k + 1)
    von, nach = np.array(von), np.array(nach)
    return ids, xy, von, nach, np.full(len(von), abstand)


# ------------------------------------------------------------------------------- Netz

def test_gitter_weg_ist_manhattan():
    netz = fw.netz_bauen(*gitter(5, 5))
    meter, ziel = fw.naechstes_ziel(netz, np.array([[400.0, 400.0]]), np.array([[0.0, 0.0], [200.0, 300.0]]))
    assert meter.tolist() == pytest.approx([800.0, 300.0])
    assert ziel.tolist() == [0, 0]


def test_anbindungsstrecken_zaehlen_mit():
    netz = fw.netz_bauen(*gitter(3, 1))         # Knoten bei x = 0, 100, 200 auf y = 0
    meter, _ = fw.naechstes_ziel(netz, np.array([[200.0, 40.0]]), np.array([[0.0, -30.0]]))
    assert meter[0] == pytest.approx(30.0 + 200.0 + 40.0)


def test_mehrere_ziele_naechstes_nach_netz_nicht_nach_luftlinie():
    # Zwei getrennte Straßen, verbunden nur am linken Ende (x = 0): ein Ziel liegt in Luftlinie nah, aber
    # auf der anderen Straße; das andere weiter weg auf derselben Straße.
    ids = np.array([1, 2, 3, 11, 12, 13])
    xy = np.array([[0, 0], [500, 0], [1000, 0], [0, 60], [500, 60], [1000, 60]], dtype=float)
    von, nach = np.array([1, 2, 11, 12, 1]), np.array([2, 3, 12, 13, 11])
    netz = fw.netz_bauen(ids, xy, von, nach, np.array([500, 500, 500, 500, 60.0]))
    ziele = np.array([[1000.0, 60.0], [0.0, 0.0]])  # 0: gegenüber (Luftlinie 60 m), 1: am Anfang derselben Straße
    meter, ziel = fw.naechstes_ziel(netz, ziele, np.array([[1000.0, 0.0]]))
    assert ziel[0] == 1
    assert meter[0] == pytest.approx(1000.0)


def test_kleine_komponente_wird_nicht_angebunden():
    ids, xy, von, nach, laenge = gitter(4, 4)
    ids = np.append(ids, [1, 2])
    xy = np.vstack([xy, [[2000.0, 0.0], [2010.0, 0.0]]])
    von, nach, laenge = np.append(von, 1), np.append(nach, 2), np.append(laenge, 10.0)
    netz = fw.netz_bauen(ids, xy, von, nach, laenge)
    assert netz.gross.sum() == 16
    # Start direkt an der Insel: angebunden wird an den Hauptteil (> MAX_ANBINDUNG_M) → kein Wert
    meter, ziel = fw.naechstes_ziel(netz, np.array([[0.0, 0.0]]), np.array([[2005.0, 0.0]]))
    assert math.isnan(meter[0]) and ziel[0] == -1


def test_zu_weit_vom_netz_kein_wert_und_ziel_ausgelassen():
    netz = fw.netz_bauen(*gitter(3, 3))
    fern = [[0.0, 1000.0]]
    meter, _ = fw.naechstes_ziel(netz, np.array([[200.0, 200.0]]), np.array(fern))
    assert math.isnan(meter[0])
    # Ziel zu weit vom Netz: gilt als nicht erreichbar, das nähere erreichbare zählt
    meter, ziel = fw.naechstes_ziel(netz, np.array([[0.0, 900.0], [200.0, 200.0]]), np.array([[0.0, 0.0]]))
    assert ziel[0] == 1 and meter[0] == pytest.approx(400.0)


def test_parallele_kanten_und_zu_kurze_laenge():
    ids = np.array([1, 2])
    xy = np.array([[0, 0], [100, 0]], dtype=float)
    # doppelt: 150 und 120; dazu eine Länge unter dem geraden Abstand (90 → 100)
    netz = fw.netz_bauen(ids, xy, np.array([1, 2]), np.array([2, 1]), np.array([150.0, 120.0]))
    m, _ = fw.naechstes_ziel(netz, np.array([[100.0, 0.0]]), np.array([[0.0, 0.0]]))
    assert m[0] == pytest.approx(120.0)
    netz = fw.netz_bauen(ids, xy, np.array([1]), np.array([2]), np.array([90.0]))
    m, _ = fw.naechstes_ziel(netz, np.array([[100.0, 0.0]]), np.array([[0.0, 0.0]]))
    assert m[0] == pytest.approx(100.0)


def test_unbekannter_knoten_bricht_ab():
    with pytest.raises(ValueError):
        fw.netz_bauen(np.array([1, 2]), np.zeros((2, 2)), np.array([1]), np.array([3]), np.array([1.0]))


def test_zufallsnetz_fussweg_nie_unter_luftlinie():
    rng = np.random.default_rng(42)
    n = 600
    xy = rng.uniform(0, 3000, size=(n, 2))
    from scipy.spatial import cKDTree
    _, nb = cKDTree(xy).query(xy, k=5)
    von = np.repeat(np.arange(n), 4)
    nach = nb[:, 1:].ravel()
    laenge = np.hypot(*(xy[von] - xy[nach]).T) * rng.uniform(0.98, 1.3, size=len(von))  # auch etwas zu kurz
    netz = fw.netz_bauen(np.arange(n) + 10, xy, von + 10, nach + 10, laenge)
    ziele = rng.uniform(0, 3000, size=(25, 2))
    start = rng.uniform(0, 3000, size=(400, 2))
    meter, ziel = fw.naechstes_ziel(netz, ziele, start, max_anbindung=1e9)
    luft = cKDTree(ziele).query(start)[0]
    ok = np.isfinite(meter)
    assert ok.sum() > 300
    assert np.all(fw.auf_zehntel(meter[ok]) >= luft[ok])
    # Gewähltes Ziel: Fußweg dorthin ist der kleinste über alle Ziele (gegen Einzelrechnung)
    for i in np.flatnonzero(ok)[:20]:
        einzeln = [fw.naechstes_ziel(netz, ziele[j:j + 1], start[i:i + 1], max_anbindung=1e9)[0][0]
                   for j in range(len(ziele))]
        assert meter[i] == pytest.approx(np.nanmin(einzeln))
        assert einzeln[ziel[i]] == pytest.approx(meter[i])


def test_im_radius_gegen_einzelrechnung():
    netz = fw.netz_bauen(*gitter(10, 10))
    zugang = np.array([[0, 0], [900, 900], [450, 0], [0, 450], [900, 0]], dtype=float)
    gruppe = np.array([0, 1, 2, 2, 3])          # Fläche 2 hat zwei Zugänge
    start = np.array([[100, 100], [500, 500], [800, 50], [0, 5000]], dtype=float)
    erg = fw.im_radius(netz, zugang, gruppe, start, radius=500.0, chunk=2)
    for i in range(len(start)):
        if i == 3:
            assert erg[i] is None
            continue
        erwartet = set()
        for g in set(gruppe.tolist()):
            m, _ = fw.naechstes_ziel(netz, zugang[gruppe == g], start[i:i + 1])
            if m[0] <= 500.0:
                erwartet.add(g)
        assert erg[i] == erwartet


def test_aufrunden_und_minuten_und_median():
    assert fw.auf_zehntel(np.array([10.01, 10.0, 0.0]))[:].tolist() == [10.1, 10.0, 0.0]
    assert fw.minuten(np.array([80.0]), 4.8)[0] == pytest.approx(1.0)
    fuss = np.array([120.0, 50.0, 300.0, np.nan])
    luft = np.array([100.0, 40.0, 200.0, 100.0])
    assert fw.median_verhaeltnis(fuss, luft) == pytest.approx(1.35)   # 1,2 und 1,5; 40 m zählt nicht


def test_richtwerte_aus_dem_repo():
    rw = fw.richtwerte()
    assert rw["kmh"] == pytest.approx(4.8)
    assert rw["gruen_radius"] == 500
    assert set(rw["gruen_arten"]) >= {"gruenanlage", "park"}


def test_keine_verbotenen_abrufe_im_code():
    text = (WURZEL / "skripte" / "14b_fussweg.py").read_text(encoding="utf-8")
    for verboten in ("overpass", "osmnx", "requests", "urllib", "http://", "nominatim", "wikidata"):
        assert verboten not in text.lower().replace("https://opendatacommons.org", "").replace(
            "https://creativecommons.org", ""), verboten


# ------------------------------------------------------------------------------- Landesfilter E7 (ohne Datenbank)

def _gtfs_zip(pfad: Path, zeilen: list[str]) -> Path:
    import zipfile
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pfad, "w") as z:
        z.writestr("stops.txt", "﻿stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
                   + "\n".join(zeilen) + "\n")
        z.writestr("routes.txt", "route_id\n1\n")
    return pfad


def test_halte_land_nur_berlin_und_brandenburg_nur_punkte(tmp_path):
    p = _gtfs_zip(tmp_path / "GTFS.zip", [
        "de:11000:900100001::1,Berlin A,52.52,13.40,0,",
        "de:12054:900230999::2,Potsdam B,52.39,13.06,,",
        "de:12069:900220009,Werder Station,52.37,12.94,1,",      # Station, kein Haltepunkt
        "de:13003:1,Rostock,54.09,12.13,0,",                     # anderes Land
        "900000123,ohne DHID,52.5,13.3,0,",
        "de:11000:9,kaputt,x,13.3,0,",
        'de:12054:5,"Name, mit Komma",52.40,13.10,0,',
    ])
    h = fw.halte_land(p)
    assert h == [(13.40, 52.52, "11"), (13.06, 52.39, "12"), (13.10, 52.40, "12")]


def test_gtfs_pfad_nimmt_den_neuesten_stand(tmp_path):
    _gtfs_zip(tmp_path / "vbb_gtfs" / "2026-11-05" / "GTFS.zip", [])
    _gtfs_zip(tmp_path / "vbb_gtfs" / "2027-01-10" / "GTFS.zip", [])
    (tmp_path / "vbb_gtfs" / "2027-02-01").mkdir()                 # Ordner ohne Zip zählt nicht
    assert fw.gtfs_pfad(str(tmp_path)) == tmp_path / "vbb_gtfs" / "2027-01-10" / "GTFS.zip"
    assert fw.gtfs_pfad(str(tmp_path / "fehlt")) is None


# ------------------------------------------------------------------------------- Datenbank (Probelauf)

DB = os.environ.get("A5B_DB_TEST") == "1"


@pytest.mark.skipif(not DB, reason="nur mit A5B_DB_TEST=1")
def test_landesfilter_bekannte_orte_echtes_gtfs():
    """Land der nächsten VBB-Haltestelle an Orten beiderseits der Grenze (Koordinaten von Hand, WGS84)."""
    pfad = fw.gtfs_pfad()
    assert pfad is not None, "VBB-GTFS fehlt unter $KIEZ_DATEN/vbb_gtfs/"
    orte = {
        "Potsdam Hauptbahnhof": (13.0669, 52.3916, "12"),
        "Potsdam Babelsberg, Griebnitzsee-Ufer": (13.1215, 52.3940, "12"),
        "Kleinmachnow Zentrum": (13.2250, 52.4075, "12"),
        "Groß Glienicke (Potsdam)": (13.1060, 52.4680, "12"),
        "Berlin-Wannsee Bahnhof": (13.1795, 52.4213, "11"),
        "Berlin-Steinstücken (Exklave)": (13.1335, 52.3905, "11"),
        "Berlin-Kladow": (13.1450, 52.4540, "11"),
        "Berlin-Zehlendorf": (13.2590, 52.4310, "11"),
    }
    with fw.verbinden() as conn, conn.cursor() as cur:
        fw.laender_anlegen(cur, fw.halte_land(pfad))
        for name, (lon, lat, land) in orte.items():
            cur.execute("""SELECT l.land FROM a5b_land l
                           ORDER BY l.geom <-> ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 25833)
                           LIMIT 1""", (lon, lat))
            assert cur.fetchone()[0] == land, name
        conn.rollback()


@pytest.mark.skipif(not DB, reason="nur mit A5B_DB_TEST=1")
def test_ziele_anlegen_laesst_berliner_osm_ziele_aus():
    """OSM-Ziele aus einer TEMP-osm_poi (A3s Tabelle bleibt unberührt): Berliner fallen heraus, Brandenburger bleiben."""
    rw = fw.richtwerte()
    with fw.verbinden() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM auswertung.osm_poi")
        vorher = cur.fetchone()[0]
        cur.execute("CREATE TEMP TABLE osm_poi (osm_id text, art text, unterart text, geom geometry(Point, 25833)) "
                    "ON COMMIT DROP")
        punkte = [("n1", "supermarkt", 13.0669, 52.3916), ("n2", "supermarkt", 13.1795, 52.4213),
                  ("n3", "apotheke", 13.1335, 52.3905), ("w4", "apotheke", 13.2250, 52.4075),
                  ("n5", "spielplatz", 13.1450, 52.4540)]
        for oid, art, lon, lat in punkte:
            cur.execute("INSERT INTO pg_temp.osm_poi VALUES (%s, %s, NULL, "
                        "ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 25833))", (oid, art, lon, lat))
        land = fw.ziele_anlegen(cur, rw["gruen_arten"], poi_schema="pg_temp")
        cur.execute("SELECT ziel_id FROM a5b_ziel WHERE herkunft = 'osm' ORDER BY 1")
        assert [r[0] for r in cur.fetchall()] == ["n1", "w4"]
        assert land["berlin_ausgelassen"] == {"apotheke": 1, "spielplatz": 1, "supermarkt": 1}
        assert "nächsten VBB-Haltestelle" in land["land_quelle"]
        cur.execute("SELECT count(*) FROM a5b_ziel WHERE herkunft = 'vbb' AND ziel_id LIKE 'de:11%'")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT count(*) FROM auswertung.osm_poi")
        assert cur.fetchone()[0] == vorher     # A3s Tabelle nicht angefasst
        conn.rollback()


@pytest.mark.skipif(not DB, reason="nur mit A5B_DB_TEST=1")
def test_probelauf_gitternetz_rollback():
    a5b_pruefen = importlib.import_module("a5b_pruefen")
    with fw.verbinden() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM auswertung.zelle_erreichbar")
        vorher_alle = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM auswertung.zelle_erreichbar WHERE methode <> 'fussweg'")
        vorher_fremd = cur.fetchone()[0]
        # Gitternetz 50 m über die Ausdehnung von Zellen und Zielen plus 2,5 km, in TEMP-Tabellen (pg_temp)
        cur.execute("""SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) FROM (
                         SELECT ST_Extent(ST_Transform(z.geom, 25833)) e FROM public.zensus_zelle z
                         JOIN public.stadtteil s ON ST_Contains(s.geom, z.geom)) x""")
        x0, y0, x1, y1 = cur.fetchone()
        a = 50.0
        x0, y0 = math.floor((x0 - 2500) / a) * a, math.floor((y0 - 2500) / a) * a
        nx, ny = int((x1 + 2500 - x0) / a) + 1, int((y1 + 2500 - y0) / a) + 1
        ids, xy, von, nach, laenge = gitter(nx, ny, a, x0, y0)
        cur.execute("CREATE TEMP TABLE netz_knoten (id bigint PRIMARY KEY, geom geometry(Point, 25833)) "
                    "ON COMMIT DROP")
        with cur.copy("COPY netz_knoten (id, geom) FROM STDIN") as cp:
            for i, (x, y) in zip(ids.tolist(), xy.tolist()):
                cp.write_row((i, f"SRID=25833;POINT({x} {y})"))
        cur.execute("CREATE TEMP TABLE netz_kante (id bigint, von bigint, nach bigint, laenge_m numeric(10,2)) "
                    "ON COMMIT DROP")
        with cur.copy("COPY netz_kante (id, von, nach, laenge_m) FROM STDIN") as cp:
            for k, (v, n_, l_) in enumerate(zip(von.tolist(), nach.tolist(), laenge.tolist())):
                cp.write_row((k, v, n_, l_))
        k = fw.rechnen(cur, netz_schema="pg_temp")
        assert k["knoten"] == nx * ny and k["zellen"] == 3443 and k["bewohnt"] == 3411
        assert all(a_.verstoesse == 0 for a_ in k["arten"])
        assert k["zellen_ohne_anbindung"] == 0
        # Manhattan-Gitter: Fußweg/Luftlinie im Mittel 4/π ≈ 1,27
        assert 1.15 < k["median_gesamt"] < 1.4
        text = fw.bericht(k, trockenlauf=True)
        assert "ODbL" in text
        assert "Berliner Ziele nicht (E7)" in text and "Land der Ziele" in text
        (WURZEL / "berichte").mkdir(exist_ok=True)
        (WURZEL / "berichte" / "A5b_probelauf_gitternetz.md").write_text(
            "<!-- Probelauf mit synthetischem 50-m-Gitternetz statt OSM, ROLLBACK -->\n" + text, encoding="utf-8")

        cur.execute("SELECT count(*) FROM auswertung.zelle_erreichbar WHERE methode <> 'fussweg'")
        assert cur.fetchone()[0] == vorher_fremd       # Luftlinie-Zeilen (A5a) unberührt
        erg = a5b_pruefen.pruefen(cur)
        (WURZEL / "berichte" / "A5b_probelauf_pruefung.txt").write_text(
            "\n".join(f"[{'ok' if ok else 'FEHLT'}] {kr}: {b}" for kr, ok, b in erg) + "\n", encoding="utf-8")
        for kr, ok, beleg in erg:
            assert ok, f"{kr}: {beleg}"
        conn.rollback()
        cur.execute("SELECT count(*) FROM auswertung.zelle_erreichbar")
        assert cur.fetchone()[0] == vorher_alle
        conn.rollback()
