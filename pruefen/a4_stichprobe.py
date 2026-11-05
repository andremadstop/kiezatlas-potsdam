"""Stichprobe A4: Abfahrten einzelner Haltestellen roh aus dem GTFS listen, zum Nachzählen von Hand.

Bewusst unabhängig von skripte/13_oepnv.py geschrieben (eigene Dienst- und Fahrtauswahl, keine gemeinsame Funktion),
damit die Liste den Tabellenwert prüft und nicht dieselbe Rechnung wiederholt. Ausgabe je Haltestelle: jede Abfahrt
im Fenster mit Uhrzeit, Linie, Ziel und direction_id. Gezählt wird danach von Hand (Protokoll pruefen/a4_nvp_lesung.md).

Aufruf: python -I pruefen/a4_stichprobe.py GTFS.zip 2026-11-10 06:00 09:00 de:12054:900230037 [...]
"""
import csv
import io
import sys
import zipfile
from datetime import date


def zeilen(z, name):
    return csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig"))


def main():
    pfad, tag, von, bis, *stems = sys.argv[1:]
    d = date.fromisoformat(tag)
    ds = d.strftime("%Y%m%d")
    spalte = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][d.weekday()]
    z = zipfile.ZipFile(pfad)
    dienst = set()
    for r in zeilen(z, "calendar.txt"):
        if r[spalte] == "1" and r["start_date"] <= ds <= r["end_date"]:
            dienst.add(r["service_id"])
    for r in zeilen(z, "calendar_dates.txt"):
        if r["date"] == ds:
            if r["exception_type"] == "1":
                dienst.add(r["service_id"])
            else:
                dienst.discard(r["service_id"])
    linie = {r["route_id"]: r["route_short_name"] for r in zeilen(z, "routes.txt")}
    fahrt = {r["trip_id"]: r for r in zeilen(z, "trips.txt") if r["service_id"] in dienst}
    name = {}
    for r in zeilen(z, "stops.txt"):
        for s in stems:
            if r["stop_id"] == s or r["stop_id"].startswith(s + "::"):
                name[s] = r["stop_name"]
    treffer = {s: [] for s in stems}
    laenge = {}
    for r in zeilen(z, "stop_times.txt"):
        t = r["trip_id"]
        if t not in fahrt:
            continue
        laenge[t] = max(laenge.get(t, 0), int(r["stop_sequence"]))
        for s in stems:
            if r["stop_id"].startswith(s + "::") or r["stop_id"] == s:
                treffer[s].append(r)
    for s in stems:
        print(f"\n== {s} {name.get(s, '?')}  ({tag}, {von}–{bis})")
        liste = []
        for r in treffer[s]:
            h, m, _ = r["departure_time"].split(":")      # GTFS schreibt 6:36:00 ohne führende Null
            zeit = f"{int(h):02d}:{m}"
            if not (von <= zeit < bis):
                continue
            t = fahrt[r["trip_id"]]
            ende = int(r["stop_sequence"]) == laenge[r["trip_id"]]
            liste.append((zeit, linie.get(t["route_id"], "?"), t["direction_id"], t["trip_headsign"],
                          r["stop_id"], "Endhalt" if ende else "", "kein Einstieg" if r["pickup_type"] == "1" else ""))
        for e in sorted(liste):
            print("  " + "  ".join(x for x in e if x is not None))


if __name__ == "__main__":
    main()
