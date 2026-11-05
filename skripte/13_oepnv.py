"""ÖPNV-Haltestellen mit Verkehrsmittel und Taktklasse nach dem Potsdamer Nahverkehrsplan 2019 (Paket A4).

Kein Netzabruf. Eingang: VBB-GTFS ($KIEZ_DATEN/vbb_gtfs/<stand>/GTFS.zip, CC BY 4.0 VBB) wird direkt aus dem Zip
gestreamt. Alle Grenzwerte, das Messfenster und der Stichtag stehen in config/richtwerte.yaml (Abschnitt oepnv),
nicht hier.

Ausgang: auswertung.haltestelle (stop_id, name, verkehrsmittel, fahrten_hvz_je_richtung, klasse, in_potsdam, geom).

Was die Spalten bedeuten:
- stop_id: Haltestelle im Sinne des Fahrgasts, also der Haltepunkt ohne Steig. Bei VBB-Kennungen der DHID-Stamm
  vor „::“ (z. B. de:12054:900230014), sonst parent_station bzw. die eigene stop_id.
- verkehrsmittel: alle Verkehrsmittel mit Abfahrten am Stichtag, sortiert und mit „+“ verbunden
  (bus, faehre, spnv, tram, sonstige), z. B. „bus+tram“.
- fahrten_hvz_je_richtung: Abfahrten im HVZ-Fenster je Stunde, alle Linien zusammen, gezählt je direction_id;
  es zählt die stärkere Richtung (sonst fiele eine Endhaltestelle durch). Ohne Endhalt einer Fahrt und ohne
  Halte, an denen niemand einsteigen darf (pickup_type 1).
- klasse: TAKTKLASSE der Haltestelle, d. h. der erreichte Takt gemessen an den Untergrenzen der Tab. 4.3
  (I, II, III oder „unter III“). Das ist NICHT die Klasse des NVP: Dort ist die Klasse eine Eigenschaft des
  Ortsteils (Tab. 4.1), und aus ihr folgen Einzugsradius (Tab. 4.2) und Soll-Takt. A5 nimmt den Radius deshalb
  aus richtwerte.yaml (oepnv.einzugsradius_m nach Verkehrsmittel und oepnv.gebietsklassen), nie aus `klasse`.
- in_potsdam: Lage in einem der 32 Stadtteile (ST_Within). Haltestellen bis randpuffer_m außerhalb bleiben drin,
  soweit sie in Brandenburg liegen (E7), Berliner Haltestellen (DHID de:11000) nicht.

Nur Haltestellen mit mindestens einer Abfahrt am Stichtag; Ersatzhalte ohne Fahrten fallen weg.

Aufruf (Rolle kiezatlas_rechnen, psycopg und PyYAML aus der Pipeline-Umgebung):
    set -a; . ../kiezatlas-potsdam/.env; set +a
    PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=kiezatlas_rechnen PGPASSWORD="$RECHNEN_PASSWORD" \
    uv run -q --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \
        python -I skripte/13_oepnv.py [--gtfs PFAD] [--trocken]
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import zipfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import psycopg
import yaml

WURZEL = Path(__file__).resolve().parent.parent
BERLIN = "de:11000:"


def verkehrsmittel_von(route_type: int) -> str:
    """GTFS route_type (Basis und erweiterte Typen) → Verkehrsmittel des NVP."""
    if route_type in (0, 900) or 900 <= route_type < 1000:
        return "tram"
    if route_type in (3, 11) or 700 <= route_type < 800 or 200 <= route_type < 300:
        return "bus"
    if route_type in (1, 2) or 100 <= route_type < 200 or 400 <= route_type < 500:
        return "spnv"   # Regional-, S- und U-Bahn
    if route_type == 4 or 1000 <= route_type < 1100 or route_type == 1200:
        return "faehre"
    return "sonstige"


def sekunden(hhmmss: str) -> int:
    h, m, s = hhmmss.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def lies(z: zipfile.ZipFile, name: str):
    with z.open(name) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", newline=""))


def dienste_am(z: zipfile.ZipFile, tag: date) -> set[str]:
    """service_id, die am Tag fahren: calendar (Wochentag, Zeitraum) plus/minus calendar_dates."""
    wt = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")[tag.weekday()]
    t = tag.strftime("%Y%m%d")
    aktiv = {r["service_id"] for r in lies(z, "calendar.txt")
             if r[wt] == "1" and r["start_date"] <= t <= r["end_date"]}
    for r in lies(z, "calendar_dates.txt"):
        if r["date"] == t:
            (aktiv.add if r["exception_type"] == "1" else aktiv.discard)(r["service_id"])
    return aktiv


def haltestelle_von(stop: dict) -> str:
    sid = stop["stop_id"]
    if sid.startswith("de:") and "::" in sid:
        return sid.split("::")[0]
    return stop.get("parent_station") or sid


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    daten = Path(os.environ.get("KIEZ_DATEN") or WURZEL.parent / "kiezatlas-daten")
    ap.add_argument("--gtfs", type=Path, default=daten / "vbb_gtfs" / "2026-11-05" / "GTFS.zip")
    ap.add_argument("--richtwerte", type=Path, default=WURZEL / "config" / "richtwerte.yaml")
    ap.add_argument("--trocken", action="store_true", help="nur rechnen und berichten, nicht schreiben")
    a = ap.parse_args()

    oe = yaml.safe_load(a.richtwerte.read_text(encoding="utf-8"))["oepnv"]
    m = oe["messung"]
    tag = m["stichtag"] if isinstance(m["stichtag"], date) else date.fromisoformat(str(m["stichtag"]))
    von, bis = (sekunden(x + ":00") for x in m["hvz_fenster"])
    stunden = (bis - von) / 3600
    puffer = float(m["randpuffer_m"])
    grenzen = sorted(((k, float(v["fahrten_hvz_je_richtung_min"])) for k, v in oe["taktklassen"].items()
                      if isinstance(v, dict) and "fahrten_hvz_je_richtung_min" in v), key=lambda kv: -kv[1])

    with psycopg.connect() as db:
        # Rechteck um Potsdam plus Puffer in WGS84, als grober Vorfilter für stops.txt
        x0, y0, x1, y1 = db.execute(
            "SELECT ST_XMin(b), ST_YMin(b), ST_XMax(b), ST_YMax(b) FROM (SELECT ST_Transform(ST_SetSRID(ST_Expand("
            "ST_Extent(ST_Transform(geom, 25833))::geometry, %s), 25833), 4326) AS b FROM public.stadtteil) q",
            (puffer + 500,)).fetchone()

        z = zipfile.ZipFile(a.gtfs)
        stopname: dict[str, str] = {}
        lage: dict[str, list[tuple[float, float]]] = defaultdict(list)
        steig_zu: dict[str, str] = {}
        stationslage: dict[str, tuple[float, float]] = {}
        for s in lies(z, "stops.txt"):
            lt = s.get("location_type") or "0"
            if lt not in ("0", "1"):
                continue                      # Zugänge, Knoten, Einstiegsbereiche
            lon, lat = float(s["stop_lon"]), float(s["stop_lat"])
            if not (x0 <= lon <= x1 and y0 <= lat <= y1):
                continue
            h = s["stop_id"] if lt == "1" else haltestelle_von(s)
            if h.startswith(BERLIN):
                continue                      # E7: Berlin vorerst nicht
            if lt == "1":
                stationslage[h] = (lon, lat)
                stopname[h] = s["stop_name"]
            else:
                steig_zu[s["stop_id"]] = h
                lage[h].append((lon, lat))
                stopname.setdefault(h, s["stop_name"])

        art = {r["route_id"]: verkehrsmittel_von(int(r["route_type"])) for r in lies(z, "routes.txt")}
        heute, gestern = dienste_am(z, tag), dienste_am(z, tag - timedelta(days=1))
        fahrt: dict[str, tuple[str, str, bool]] = {}   # trip_id → (route_id, direction_id, heute?)
        for r in lies(z, "trips.txt"):
            if r["service_id"] in heute:
                fahrt[r["trip_id"]] = (r["route_id"], r.get("direction_id") or "0", True)
            elif r["service_id"] in gestern:
                fahrt[r["trip_id"]] = (r["route_id"], r.get("direction_id") or "0", False)

        letzte: dict[str, int] = {}
        halte = []   # (trip, haltestelle, seq, pickup, abfahrt_s)
        for r in lies(z, "stop_times.txt"):
            t = r["trip_id"]
            if t not in fahrt:
                continue
            seq = int(r["stop_sequence"])
            if seq > letzte.get(t, -1):
                letzte[t] = seq
            h = steig_zu.get(r["stop_id"])
            if h is not None:
                halte.append((t, h, seq, r.get("pickup_type") or "0", sekunden(r["departure_time"] or r["arrival_time"])))

        abfahrt_tag: dict[str, set[str]] = defaultdict(set)              # Haltestelle → Verkehrsmittel
        im_fenster: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        for t, h, seq, pickup, sek in halte:
            if pickup == "1" or seq == letzte[t]:
                continue
            route, richtung, ist_heute = fahrt[t]
            s = sek if ist_heute else sek - 86400       # Fahrten des Vortags nach Mitternacht (Zeiten ≥ 24:00)
            if ist_heute:
                abfahrt_tag[h].add(art.get(route, "sonstige"))
            if von <= s < bis:
                im_fenster[h][richtung].add(t)

        zeilen = []
        for h, mittel in abfahrt_tag.items():
            je_richtung = max((len(v) for v in im_fenster[h].values()), default=0) / stunden
            klasse = next((k for k, g in grenzen if je_richtung >= g), "unter III")
            lon, lat = stationslage.get(h) or (sum(p[0] for p in lage[h]) / len(lage[h]),
                                               sum(p[1] for p in lage[h]) / len(lage[h]))
            zeilen.append((h, stopname.get(h), "+".join(sorted(mittel)), round(je_richtung, 1), klasse, lon, lat))

        with db.transaction():
            db.execute("CREATE TEMP TABLE hs (stop_id text, name text, verkehrsmittel text, f numeric, "
                       "klasse text, lon float8, lat float8) ON COMMIT DROP")
            with db.cursor().copy("COPY hs FROM STDIN") as c:
                for z_ in zeilen:
                    c.write_row(z_)
            db.execute("CREATE TEMP TABLE stadt ON COMMIT DROP AS "
                       "SELECT ST_Union(ST_Transform(geom, 25833)) AS g FROM public.stadtteil")
            db.execute("CREATE TEMP TABLE hs2 ON COMMIT DROP AS SELECT h.*, "
                       "ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 25833) AS geom FROM hs h")
            db.execute("DELETE FROM hs2 USING stadt WHERE NOT ST_DWithin(hs2.geom, stadt.g, %s)", (puffer,))
            if not a.trocken:
                db.execute("DELETE FROM auswertung.haltestelle")
                db.execute("INSERT INTO auswertung.haltestelle (stop_id, name, verkehrsmittel, "
                           "fahrten_hvz_je_richtung, klasse, in_potsdam, geom) "
                           "SELECT h.stop_id, h.name, h.verkehrsmittel, h.f, h.klasse, ST_Within(h.geom, s.g), h.geom "
                           "FROM hs2 h, stadt s")
            bericht = db.execute(
                "SELECT ST_Within(h.geom, s.g) AS in_potsdam, h.klasse, count(*) FROM hs2 h, stadt s "
                "GROUP BY 1, 2 ORDER BY 1 DESC, 2").fetchall()
            if a.trocken:
                raise psycopg.Rollback()

    print(f"Stichtag {tag:%a %d.%m.%Y}, Fenster {m['hvz_fenster'][0]}–{m['hvz_fenster'][1]}, "
          f"{len(heute)} Dienste, {sum(1 for v in fahrt.values() if v[2])} Fahrten, "
          f"{len(zeilen)} Haltestellen mit Abfahrten im Rechteck")
    for in_p, klasse, n in bericht:
        print(f"  {'Potsdam ' if in_p else 'Umland  '} Klasse {klasse:<9} {n:>4}")
    print("trocken: nichts geschrieben" if a.trocken else "geschrieben: auswertung.haltestelle")
    return 0


if __name__ == "__main__":
    sys.exit(main())
