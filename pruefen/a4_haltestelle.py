"""Prüfung A4: auswertung.haltestelle gegen die Abnahme des Bauplans und gegen config/richtwerte.yaml.

Prüft (jede Zeile ein Befund, Rückgabe 1 bei mindestens einem Verstoß):
  1. jede Potsdamer Haltestelle hat genau eine Klasse aus {I, II, III, unter III}, stop_id eindeutig
  2. die Klasse folgt aus fahrten_hvz_je_richtung und den Grenzen in richtwerte.yaml (nicht aus Werten im Code)
  3. die Grenzen tragen eine Seitenangabe des NVP; skripte/13_oepnv.py vergleicht die Fahrten mit keiner Zahl
     und enthält keinen Radius aus Tab. 4.2
  4. keine Berliner Haltestelle (E7), alle Haltestellen höchstens randpuffer_m von der Stadtgrenze
  5. Verkehrsmittel gesetzt und nur aus {bus, faehre, spnv, tram, sonstige}

Aufruf wie skripte/13_oepnv.py (Rolle kiezatlas_rechnen oder mosidi_lesen):
    uv run -q --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt python -I pruefen/a4_haltestelle.py
"""
import re
import sys
from pathlib import Path

import psycopg
import yaml

WURZEL = Path(__file__).resolve().parent.parent


def main() -> int:
    oe = yaml.safe_load((WURZEL / "config" / "richtwerte.yaml").read_text(encoding="utf-8"))["oepnv"]
    tk = oe["taktklassen"]
    grenzen = sorted(((k, float(v["fahrten_hvz_je_richtung_min"])) for k, v in tk.items()
                      if isinstance(v, dict) and "fahrten_hvz_je_richtung_min" in v), key=lambda kv: -kv[1])
    fehler = []
    if not str(tk.get("seite", "")).strip() or not str(oe["einzugsradius_m"].get("seite", "")).strip():
        fehler.append("richtwerte.yaml: Seitenangabe fehlt bei taktklassen oder einzugsradius_m")
    code = (WURZEL / "skripte" / "13_oepnv.py").read_text(encoding="utf-8")
    ohne_doc = code.split('"""', 2)[2]
    # Taktgrenzen: kein Vergleich der gemessenen Fahrten mit einer Zahl im Code (route_type-Bereiche sind erlaubt)
    if re.search(r"(je_richtung|fahrten\w*)\s*[<>]=?\s*\d|\d\s*[<>]=?\s*(je_richtung|fahrten)", ohne_doc):
        fehler.append("13_oepnv.py vergleicht die Fahrten mit einer Zahl im Code")
    # Einzugsradien der Tab. 4.2, die nicht auch route_type-Grenzen sind, dürfen gar nicht vorkommen
    for zahl in ("350", "450"):
        if re.search(rf"\b{zahl}\b", ohne_doc):
            fehler.append(f"13_oepnv.py enthält den Radius {zahl}")
    with psycopg.connect() as db:
        q = db.execute("SELECT count(*), count(*) FILTER (WHERE in_potsdam), "
                       "count(*) FILTER (WHERE in_potsdam AND klasse IS NULL), count(DISTINCT stop_id) "
                       "FROM auswertung.haltestelle").fetchone()
        gesamt, potsdam, ohne, eindeutig = q
        print(f"Haltestellen {gesamt}, davon in Potsdam {potsdam}, ohne Klasse {ohne}, stop_id eindeutig {eindeutig}")
        if potsdam == 0:
            fehler.append("keine Potsdamer Haltestelle")
        if ohne:
            fehler.append(f"{ohne} Potsdamer Haltestellen ohne Klasse")
        if eindeutig != gesamt:
            fehler.append("stop_id nicht eindeutig")
        for sid, name, f, klasse in db.execute(
                "SELECT stop_id, name, fahrten_hvz_je_richtung, klasse FROM auswertung.haltestelle"):
            # Tabellenwert ist auf 0,1 gerundet, 13_oepnv.py ordnet ungerundet ein: an einer Grenze beide Seiten gelten lassen
            moeglich = {next((k for k, g in grenzen if float(f) + d >= g), "unter III") for d in (-0.05, 0, 0.05)}
            soll = next((k for k, g in grenzen if float(f) >= g), "unter III")
            if klasse not in moeglich:
                fehler.append(f"{sid} {name}: {f} Fahrten → {soll}, eingetragen {klasse}")
        n = db.execute("SELECT count(*) FROM auswertung.haltestelle WHERE stop_id LIKE 'de:11000:%'").fetchone()[0]
        if n:
            fehler.append(f"{n} Berliner Haltestellen")
        n = db.execute("SELECT count(*) FROM auswertung.haltestelle h WHERE NOT ST_DWithin(h.geom, "
                       "(SELECT ST_Union(ST_Transform(geom, 25833)) FROM public.stadtteil), %s)",
                       (float(oe["messung"]["randpuffer_m"]) + 0.5,)).fetchone()[0]
        if n:
            fehler.append(f"{n} Haltestellen weiter als randpuffer_m von der Stadt")
        for (vm,) in db.execute("SELECT DISTINCT verkehrsmittel FROM auswertung.haltestelle"):
            if not vm or not set(vm.split("+")) <= {"bus", "faehre", "spnv", "tram", "sonstige"}:
                fehler.append(f"unbekanntes Verkehrsmittel {vm!r}")
        for klasse, anzahl in db.execute("SELECT klasse, count(*) FROM auswertung.haltestelle WHERE in_potsdam "
                                         "GROUP BY 1 ORDER BY 1"):
            print(f"  Potsdam Klasse {klasse:<9} {anzahl}")
    for f in fehler:
        print("VERSTOSS", f)
    print("ok" if not fehler else f"{len(fehler)} Verstöße")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
