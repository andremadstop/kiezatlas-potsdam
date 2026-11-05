"""Prüfung Paket B4 (Kaskade der Gebäudejahre): Abnahmepunkte gegen Datenbank und Dateien.

Prüft:
  A1  jedes der 52.309 Gebäude in Potsdam hat genau eine Zeile in auswertung.gebaeude_jahr, entweder mit
      Klasse und Quelle oder als „nicht datiert“ (Stufe 6, ohne Klasse und Quelle)
  A2  „aktualit“ kommt in keiner B4-Datei vor (Skript, Konfiguration, Daten)
  A3  der Rücktest-Bericht weist je Stufe und je bekannter Bauzeit Treffer, Median und n aus
  A4  Summenprüfung nur für Stufen 1 bis 3, Stufe 4 als tautologisch gekennzeichnet; H4 als blockiert genannt
  A5  kein OSM- und kein Wikipedia-Wert in gebaeude_jahr (Prüfabfrage); keine BLDAM-Herkunft
  A6  größte Datei daten/jahre/<nr>.js ≤ 400 KB gz
  K6  kein Einzeljahr für Gebäude mit Wohnraum (außer freigegebene Denkmale); in daten/jahre nur dann j
  K   keine oid, keine Adressfelder, kein Feld d in daten/jahre; Summe der Gebäude = kennzahlen.json
  K   dl-de-Vermerke mit „Daten verändert (eigene Berechnung)“ und Lizenzlink; Hinweis zur Unsicherheit
  K   Blocktyp-Gebiete mit Beleg (Seite), Bauzeit und Klasse
  K   Skript nutzt nur den Snapshot auswertung.gebaeude_stand_20261105, nicht public.gebaeude

Aufruf wie skripte/24_jahre_kaskade.py (Rolle kiezatlas_rechnen, nur lesend):
  … python -I pruefen/B4_kaskade.py      Rückgabe 0 = keine Abweichung
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

import psycopg

WURZEL = Path(__file__).resolve().parent.parent
SKRIPT = WURZEL / "skripte" / "24_jahre_kaskade.py"
BLOCKTYPEN = WURZEL / "config" / "blocktypen.geojson"
JAHRE = WURZEL / "daten" / "jahre"
BERICHT = WURZEL / "berichte" / "B4_holdout.md"
KLASSEN = ["vor 1919", "1919–1948", "1949–1978", "1979–1990", "1991–2000", "2001–2010", "2011–2019", "ab 2020"]
ADRESSE = re.compile(r'"(strasse|straße|hausnr|hausnummer|adresse|plz|oid|d)"\s*:')
befunde: list[str] = []


def pruef(ok: bool, text: str) -> None:
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        befunde.append(text)


def js(pfad: Path) -> dict:
    text = pfad.read_text(encoding="utf-8")
    m = re.match(r"window\.(KIEZ_JAHR_\d{2})=(.*);\s*$", text, re.DOTALL)
    return {"name": m.group(1), "inhalt": json.loads(m.group(2)), "text": text}


def main() -> int:
    with psycopg.connect("", application_name="kiezatlas-B4-pruefen") as conn, conn.cursor() as cur:
        cur.execute("""SELECT s.oid FROM auswertung.gebaeude_stand_20261105 s
                       JOIN public.stadtteil t ON ST_Contains(t.geom, ST_PointOnSurface(s.geom))""")
        potsdam = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT oid, j, j_klasse, genau, quelle, stufe FROM auswertung.gebaeude_jahr")
        zeilen = {r[0]: r[1:] for r in cur.fetchall()}
        cur.execute("""SELECT count(*) FROM auswertung.gebaeude_jahr
                       WHERE quelle ~* '(openstreetmap|wikipedia|\\mosm\\M|bldam|denkmalliste)'""")
        fremd = cur.fetchone()[0]
        cur.execute("""SELECT count(*) FROM auswertung.gebaeude_jahr g JOIN auswertung.gebaeude_stand_20261105 s
                       ON s.oid = g.oid WHERE g.j IS NOT NULL AND (s.funktion ~* 'wohn' OR s.funktion = 'Forsthaus')""")
        jahr_wohn = cur.fetchone()[0]
        # Denkmale aus freigegebener Quelle dürfen ein Jahr tragen (Korrektur 6); dieselbe Regel wie im Skript
        cur.execute("""SELECT count(DISTINCT oid_bezug) FROM auswertung.jahr_beleg
                       WHERE NOT nur_pruefung AND quelle ~* '(denkmal|bldam|ddb)'
                         AND lizenz !~* '(ungeklärt|by-sa|odbl)'""")
        denkmal_frei = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM auswertung.gebaeude_jahr WHERE j IS NOT NULL")
        jahr_db = cur.fetchone()[0]

    print("A1 Abdeckung")
    pruef(len(potsdam) == 52309, f"Gebäude in Potsdam im Snapshot: {len(potsdam)} (erwartet 52.309)")
    pruef(set(zeilen) == potsdam, f"gebaeude_jahr deckt genau diese Gebäude ab ({len(zeilen)} Zeilen)")
    schlecht = [o for o, (j, k, _g, q, s) in zeilen.items()
                if not ((s in (1, 2, 3, 4, 5) and k in KLASSEN and q) or (s == 6 and k is None and q is None and j is None))]
    pruef(not schlecht, f"jede Zeile: Klasse mit Quelle (Stufe 1–5) oder nicht datiert (Stufe 6); Abweichungen {len(schlecht)}")

    print("A2 aktualit")
    dateien = [SKRIPT, BLOCKTYPEN, *sorted(JAHRE.glob("*.js"))]
    treffer = [p.name for p in dateien if "aktualit" in p.read_text(encoding="utf-8")]
    pruef(not treffer, f"„aktualit“ in keiner B4-Datei ({len(dateien)} Dateien geprüft){': ' + ', '.join(treffer) if treffer else ''}")

    print("A3/A4 Bericht")
    b = BERICHT.read_text(encoding="utf-8") if BERICHT.exists() else ""
    pruef("Je Stufe:" in b and "Je bekannter Bauzeit" in b and "Median Abstand" in b,
          "Rücktest je Stufe und je Bauzeit mit Median")
    pruef(b.count("| n |") >= 4, "Tabellen nennen n (mindestens 4 Tabellen)")
    pruef("Geprüft werden die Stufen 1 bis 3" in b and "prüft nichts" in b, "Summenprüfung nur Stufen 1–3, Stufe 4 tautologisch")
    pruef("(H4) ist blockiert" in b, "H4 als blockiert genannt")
    pruef(not re.search(r"DEBBAL[0-9A-Za-z]{8,}", b), "Bericht ohne Gebäudekennungen")

    print("A5 keine OSM-, Wikipedia- oder BLDAM-Werte")
    pruef(fremd == 0, f"Zeilen mit OSM/Wikipedia/BLDAM als Quelle: {fremd}")

    print("K6 Einzeljahre")
    pruef(jahr_wohn <= denkmal_frei,
          f"Gebäude mit Wohnraum mit Einzeljahr: {jahr_wohn}, höchstens freigegebene Denkmale: {denkmal_frei}")

    print("A6 und Daten je Stadtteil")
    teile = sorted(JAHRE.glob("*.js"))
    pruef(len(teile) == 32, f"Dateien daten/jahre/<nr>.js: {len(teile)} (erwartet 32)")
    kennz = json.loads((WURZEL / "daten" / "kennzahlen.json").read_text(encoding="utf-8"))
    summe, groesste, jahr_js = 0, (0, ""), 0
    for p in teile:
        d = js(p)
        inh = d["inhalt"]
        nr = p.stem
        n = len(inh["features"])
        summe += n
        soll = kennz["stadtteile"][nr]["gebaeude"]["anzahl"]
        if n != soll:
            pruef(False, f"{p.name}: {n} Gebäude, kennzahlen.json {soll}")
        gz = len(gzip.compress(p.read_bytes(), 9))
        groesste = max(groesste, (gz, p.name))
        if ADRESSE.search(d["text"]):
            pruef(False, f"{p.name}: verbotenes Feld (oid, d, Adresse)")
        for f in inh["features"]:
            pr = f["properties"]
            if pr["j"] is not None:
                jahr_js += 1
                if pr["g"] != "belegt":
                    pruef(False, f"{p.name}: Jahr ohne Beleg")
            if (pr["s"] == 6) != (pr["g"] == "nicht_datiert") or (pr["s"] == 6) != (pr["k"] is None):
                pruef(False, f"{p.name}: Stufe/Klasse/Kennzeichen passen nicht")
                break
            if pr["q"] is not None and pr["q"] not in inh["quellen"]:
                pruef(False, f"{p.name}: Quelle {pr['q']} fehlt in quellen")
                break
        for k, q in inh["quellen"].items():
            dl_de = "dl-de" in q["lizenz"] or "dl-de" in q["vermerk"]
            vollstaendig = ("Daten verändert (eigene Berechnung)" in q["vermerk"]
                            and "https://www.govdata.de/dl-de/by-2-0" in q["vermerk"])
            if dl_de and not vollstaendig:
                pruef(False, f"{p.name}: Vermerk {k} ohne Bearbeitungshinweis oder Lizenzlink")
        if "nichts Sicheres über ein einzelnes Gebäude oder Grundstück" not in inh["hinweis"] or "Geheimhaltung" not in inh["hinweis"]:
            pruef(False, f"{p.name}: Hinweis zur Unsicherheit fehlt")
        if inh["klassen"] != KLASSEN:
            pruef(False, f"{p.name}: Klassen weichen ab")
    pruef(summe == kennz["kontrolle"]["gebaeude_in_potsdam"] == 52309,
          f"Σ Gebäude in daten/jahre = {summe} = kennzahlen.json (je Stadtteil gleich)")
    pruef(groesste[0] <= 400 * 1024, f"größte Datei {groesste[1]}: {groesste[0] / 1024:.0f} KB gz (≤ 400 KB)")
    pruef(jahr_js == jahr_db, f"Einzeljahre in daten/jahre ({jahr_js}) = Datenbank ({jahr_db})")

    print("K Blocktypen")
    bt = json.loads(BLOCKTYPEN.read_text(encoding="utf-8"))["features"]
    pruef(len(bt) >= 1, f"{len(bt)} Gebiete")
    for f in bt:
        p = f["properties"]
        ok = (re.search(r"S\. \d+", p["beleg"]) and p["klasse"] in KLASSEN and p["von"] <= p["bis"]
              and f["geometry"]["type"] == "MultiPolygon")
        pruef(bool(ok), f"{p['gebiet']}: Beleg „{p['beleg'][:40]}…“, {p['von']}–{p['bis']} → {p['klasse']}")

    print("K Snapshot")
    s = SKRIPT.read_text(encoding="utf-8")
    pruef("gebaeude_stand_20261105" in s and not re.search(r"\b(FROM|JOIN)\s+(public\.)?gebaeude\b", s),
          "Skript liest Gebäude nur aus dem Snapshot")

    print(f"\n{len(befunde)} Abweichungen")
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
