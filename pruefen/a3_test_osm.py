"""Tests für Paket A3 (skripte/osm_pbf.py, skripte/12_osm.py) mit einer selbst erzeugten Mini-PBF.

Aufruf: skripte/12_osm.sh test            (ohne Datenbank)
        A3_DB_TEST=1 skripte/12_osm.sh test   (dazu Trockenlauf gegen die Datenbank, am Ende ROLLBACK)
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "skripte"))
sys.path.insert(0, str(WURZEL / "pruefen"))
import a3_pbf_schreiben as mini
import osm_pbf

osm = importlib.import_module("12_osm")
RECHTECK = (12.9, 52.3, 13.2, 52.5)


@pytest.fixture(scope="module")
def pbf(tmp_path_factory) -> Path:
    return mini.schreiben(tmp_path_factory.mktemp("a3") / "mini.osm.pbf")


@pytest.fixture(scope="module")
def erg(pbf):
    return osm.lies_osm(pbf, RECHTECK)


# ------------------------------------------------------------------------------- Leser

def test_varints_wie_reines_python():
    rng = np.random.default_rng(5)
    werte = list(rng.integers(0, 2**62, 500)) + [0, 1, 127, 128, 300, 2**63 + 5]
    neg = [-1, -300, -(2**31)]   # int32 negativ: 10 Byte Zweierkomplement
    roh = b"".join(mini._varint(int(v)) for v in werte + neg)
    a = osm_pbf.varints(roh)
    assert a.tolist()[: len(werte)] == [int(v) for v in werte]
    assert osm_pbf.als_int64(a)[len(werte):].tolist() == neg
    zz = [0, -1, 1, -2, 2**40, -(2**40)]
    assert osm_pbf.zigzag(osm_pbf.varints(b"".join(mini._varint(mini._zz(v)) for v in zz))).tolist() == zz


def test_kopf_und_zaehler(erg):
    assert erg.kopf.zeitstempel == 1_793_836_800
    assert "DenseNodes" in erg.kopf.pflicht
    assert erg.knoten_gesamt == len(mini.KNOTEN)
    assert erg.wege_gesamt == len(mini.WEGE)
    assert erg.relationen_gesamt == len(mini.RELATIONEN)


def test_koordinaten_exakt(erg):
    ids = np.array(sorted(i for i in mini.KNOTEN if i not in (31, 99)), dtype=np.int64)
    lon, lat, ok = erg.koordinaten(ids)
    assert ok.all()
    soll = np.array([mini.KNOTEN[i][:2] for i in ids])
    assert np.abs(lon - soll[:, 0]).max() < 1e-7 and np.abs(lat - soll[:, 1]).max() < 1e-7
    _lo, _la, ok_aus = erg.koordinaten(np.array([31, 99, 123456]))
    assert not ok_aus.any()                          # außerhalb des Rechtecks bzw. unbekannt


def test_kompression_unbekannt(tmp_path):
    b = mini.feld_bytes(7, b"abc")                   # zstd
    h = mini.feld_bytes(1, b"OSMData") + mini.feld_varint(3, len(b))
    p = tmp_path / "zstd.pbf"
    p.write_bytes(len(h).to_bytes(4, "big") + h + b)
    with pytest.raises(ValueError, match="zstd"):
        list(osm_pbf.bloecke(p))


# ------------------------------------------------------------------------------- Regeln

@pytest.mark.parametrize("tags, soll", [
    ({"highway": "residential"}, True),
    ({"highway": "footway"}, True),
    ({"highway": "steps"}, True),
    ({"highway": "cycleway"}, False),
    ({"highway": "cycleway", "foot": "designated"}, True),
    ({"highway": "motorway"}, False),
    ({"highway": "trunk", "motorroad": "yes"}, False),
    ({"highway": "service", "access": "private"}, False),
    ({"highway": "service", "access": "private", "foot": "yes"}, True),
    ({"highway": "primary", "foot": "use_sidepath"}, False),
    ({"highway": "construction"}, False),
    ({"building": "yes"}, False),
])
def test_fussweg(tags, soll):
    assert osm.ist_fussweg(tags) is soll


def test_poi_art_ohne_namen():
    assert osm.poi_art({"amenity": "doctors", "name": "Dr. X", "healthcare:speciality": "paediatrics"}) == \
        ("arzt", "paediatrics")
    assert osm.poi_art({"healthcare": "doctor"}) == ("arzt", None)
    assert osm.poi_art({"amenity": "social_facility", "social_facility": "food_bank"}) is None
    assert osm.poi_art({"leisure": "playground", "access": "private"}) is None
    assert osm.poi_art({"shop": "convenience"}) == ("supermarkt", "convenience")
    assert osm.poi_art({"disused:shop": "supermarket"}) is None


# ------------------------------------------------------------------------------- Netz und Objekte

def test_netz(erg):
    fuss = [w for w in erg.wege if "_nur_relation" not in w[1] and osm.ist_fussweg(w[1])]
    assert {w[0] for w in fuss} == mini.ERWARTET["netz_wege"]
    von, nach, knoten, koords = osm.netz_bauen(fuss, erg)
    assert len(von) == mini.ERWARTET["kanten"]
    assert len(knoten) == mini.ERWARTET["knoten"]
    assert (von < nach).all()
    assert len({(a, b) for a, b in zip(von.tolist(), nach.tolist())}) == len(von)
    assert 31 not in knoten.tolist() and 20 not in knoten.tolist()
    assert koords.shape == (len(knoten), 2)


def test_objekte(erg):
    pois, bildung = osm.objekte_sammeln(erg)
    assert {p[0]: p[1] for p in pois} == mini.ERWARTET["pois"]
    assert {b[0]: b[1] for b in bildung} == mini.ERWARTET["bildung"]
    for p in pois:
        assert len(p) == 4 and "Beispiel" not in " ".join(str(x) for x in p)   # kein Name
    rel = next(p for p in pois if p[0] == "r200")
    assert rel[3].startswith("MULTIPOINT(") and rel[3].count("(") == 1 + 4   # 4 verschiedene Ecken aus 2 Mitgliedswegen


def test_relation_zweiter_durchgang(erg):
    ids = {w[0] for w in erg.wege if "_nur_relation" in w[1]}
    assert ids == {121, 122}


# ------------------------------------------------------------------------------- Datenbank

@pytest.mark.skipif(os.environ.get("A3_DB_TEST") != "1" or os.environ.get("PGUSER") != "kiezatlas_rechnen",
                    reason="nur mit A3_DB_TEST=1 über skripte/12_osm.sh")
def test_trockenlauf_datenbank(pbf, tmp_path):
    import psycopg
    with psycopg.connect("") as c, c.cursor() as cur:
        cur.execute("SELECT (SELECT count(*) FROM auswertung.osm_poi), (SELECT count(*) FROM auswertung.netz_knoten),"
                    " (SELECT count(*) FROM auswertung.netz_kante)")
        vorher = cur.fetchone()
    bericht = tmp_path / "bericht.md"
    lauf = subprocess.run([sys.executable, "-I", str(WURZEL / "skripte" / "12_osm.py"), "--pbf", str(pbf),
                           "--trockenlauf", "--bericht", str(bericht)], capture_output=True, text=True, check=False)
    assert lauf.returncode == 0, lauf.stderr
    assert "ROLLBACK" in lauf.stdout
    # Einrichtungen nach Dublette: 6, Netz 10 Knoten / 13 Kanten (Knoten 30 liegt im Puffer)
    assert "'arzt': 1" in lauf.stdout and "'spielplatz': 1" in lauf.stdout and "'supermarkt': 1" in lauf.stdout
    assert "'pflege': 2" in lauf.stdout and "'apotheke': 1" in lauf.stdout
    assert "Netz 10 Knoten, 13 Kanten" in lauf.stdout
    text = bericht.read_text(encoding="utf-8")
    assert "Trefferquote" in text and "TROCKENLAUF" in text
    with psycopg.connect("") as c, c.cursor() as cur:
        cur.execute("SELECT (SELECT count(*) FROM auswertung.osm_poi), (SELECT count(*) FROM auswertung.netz_knoten),"
                    " (SELECT count(*) FROM auswertung.netz_kante)")
        assert cur.fetchone() == vorher                 # nichts gespeichert
