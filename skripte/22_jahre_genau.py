"""B2: Genaue Jahre (Kaskadenstufe 1) als Belege je Gebäude in auswertung.jahr_beleg.

Jede Quelle ist ein eigener Leser. Ein Leser schreibt nur, wenn seine Rohdatei vorliegt; fehlt sie, meldet
er, welche Datei fehlt, und der Lauf geht weiter. Jede Quelle wird für sich ersetzt (DELETE der eigenen
Zeilen und INSERT in einer Transaktion), damit Läufe wiederholbar sind.

  bldam      Denkmalliste BLDAM, Stand 01.01.2026 (PDF), Teil D. Nur Schlüssel MIDAS-ID → Adresse → Gebäude.
             Schreibt je Denkmal und Adresse eine Kennzeile ohne Jahr: art 'unklar', genau false,
             nur_pruefung true. Vertrag für B4: Ein Gebäude ist Denkmal, wenn es eine Zeile mit
             quelle LIKE 'BLDAM%' hat. Lizenz ungeklärt (E8), deshalb nie veröffentlichen.
  wikipedia  „Liste der Baudenkmale in Potsdam“ (27 Teillisten, nur /wiki/-HTML). Jahre aus dem Feld
             „Baujahr:“ und aus Sätzen mit Bauverb. Nur Prüfspalte (nur_pruefung true, Korrektur 5).
  wikidata   Handexport aus dem WDQS-Browser (H9), eingang/wikidata_potsdam_baujahr.csv (oder KIEZ_WD_CSV),
             CC0. Abfrage: kiezatlas-daten/entwuerfe/2026-11-05-wikidata-abfrage-b2.rq.
             Darf in die Kaskade (nur_pruefung false).
  ddb        DDB-API mit Key (H8), eingang/ddb-key. Leser noch nicht gebaut: API-Bedingungen und
             Antwortformat erst nach H8 prüfbar. Meldet „blockiert“.
  osm        start_date/building:year aus OSM-Extrakt (H5). Nur Prüfspalte (E1). Meldet „blockiert“,
             solange kein Extrakt in eingang/osm/ liegt.

Zuordnung zum Gebäude (nur Snapshot auswertung.gebaeude_stand_20261105, Korrektur 16):
  - über die Adresse aus B0 (auswertung.gebaeude_adresse, nur intern). Gibt es zu einer Adresse mehrere
    Gebäude, gilt das Hauptgebäude: kein Nebengebäude (Garage, Schuppen, Laube …), dann größte Fläche.
    Liegen die Gebäude einer Adresse mehr als 300 m auseinander (gleicher Straßenname in zwei
    Ortsteilen), entscheidet der Ort aus der BLDAM-Liste; bleibt es mehrdeutig, wird nicht zugeordnet.
  - Wikipedia-Zeilen hängen zuerst an den Gebäuden, die BLDAM für dieselbe ID gefunden hat; sonst an der
    Koordinate der Zeile (Gebäude, das den Punkt enthält, sonst das nächste Hauptgebäude bis 10 m).
  - Ensembles: Hat ein Denkmal mehr als 4 zugeordnete Gebäude, bekommt keines davon ein Jahr aus der
    Denkmalzeile (ein Park hat kein Baujahr).

Adressen und Beschreibungstexte verlassen die Datenbank nicht: Ausgaben und Berichte nennen nur Zählungen,
MIDAS-IDs und oids.

Aufruf aus dem Worktree (Passwort nur aus der .env, chmod 600):
    set -a; . ../kiezatlas-potsdam/.env; set +a
    PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=kiezatlas_rechnen \\
    PGPASSWORD="$RECHNEN_PASSWORD" KIEZ_DATEN=../kiezatlas-daten \\
    uv run -q --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \\
    python -I skripte/22_jahre_genau.py [--quelle bldam,wikipedia,...] [--trocken]
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
KIEZ_DATEN = Path(os.environ.get("KIEZ_DATEN", WURZEL.parent / "kiezatlas-daten"))
SNAPSHOT = "auswertung.gebaeude_stand_20261105"

BLDAM_PDF = KIEZ_DATEN / "bldam/2026-01-01/04_P_Internet-25.pdf"
BLDAM_SHA = "45ede0d4c89a0ffeffd4c4a2c61128df02b804d5d619eb3ee8490c55accd7ae3"
BLDAM_URL = "https://bldam-brandenburg.de/wp-content/uploads/2026/03/04_P_Internet-25.pdf"
BLDAM_QUELLE = "BLDAM Denkmalliste Potsdam, Stand 01.01.2026"
BLDAM_ENSEMBLE = " (Ensemble, mehr als 4 Gebäude)"
BLDAM_LIZENZ = "ungeklärt (Anfrage E8 offen), nur interne Prüfung"

WP_ORDNER = KIEZ_DATEN / "wikipedia_denkmale/2026-11-05"
WP_BASIS = "https://de.wikipedia.org/wiki/Liste_der_Baudenkmale_in_Potsdam"
WP_QUELLE = "Wikipedia: Liste der Baudenkmale in Potsdam"
WP_LIZENZ = "CC BY-SA 4.0"

WD_DATEI = Path(os.environ.get("KIEZ_WD_CSV", KIEZ_DATEN / "eingang/wikidata_potsdam_baujahr.csv"))
WD_QUELLE = "Wikidata"
WD_LIZENZ = "CC0 1.0"
DDB_KEY = KIEZ_DATEN / "eingang/ddb-key"
OSM_ORDNER = KIEZ_DATEN / "eingang/osm"
WD_ENSEMBLE = re.compile(r"(park|garten|gärten|friedhof|kirchhof|siedlung|allee|platz|ensemble|anlage)\b",
                         re.IGNORECASE)

# Funktionen aus dem Snapshot, die nie als Hauptgebäude eines Denkmals gelten.
NEBEN = ("Garage", "Gebäude zum Parken", "Tiefgarage", "Schuppen", "Gartenhaus", "Überdachung",
         "Durchfahrt im Gebäude", "Umformer", "Gebäude zur Freizeitgestaltung", "Wochenendhaus",
         "Treibhaus, Gewächshaus")
ENSEMBLE_GRENZE = 4
ENSEMBLE_BEZ = re.compile(r"^\W*(Schloss- und Parkanlage|Park|Garten|Gärten|Siedlung|Wohnsiedlung|Wohnanlage|"
                          r"Gesamtanlage|Friedhof|Kirchhof|Straßenzug|Platzanlage|Allee|Denkmalbereich)")
STREUUNG_M = 300

# Stadtteile, die in der BLDAM-Liste als eigener Ort stehen (Ortsteile seit 2003 und Sacrow/Grube/Golm).
ORTSTEIL_NR = {11, 12, 13, 14, 15, 16, 17, 81, 82, 83, 84, 85, 86}
ORT_ZU_STADTTEIL = {"Kartzow": "Fahrland", "Krampnitz": "Fahrland", "Nattwerder": "Golm"}


# ------------------------------------------------------------------------------------------ Hilfen
def sha256(pfad: Path) -> str:
    h = hashlib.sha256()
    with pfad.open("rb") as f:
        while stueck := f.read(1 << 20):
            h.update(stueck)
    return h.hexdigest()


def strasse_norm(s: str) -> str:
    s = s.strip().lower().replace("str.", "straße").replace("strasse", "straße")
    return re.sub(r"\s+", " ", s)


def hausnr_norm(s: str) -> str:
    return re.sub(r"\s+", "", s).upper()


def hausnummern(spez: str) -> list[str]:
    """'49-52' → 49..52, '28 a' → 28A, '3 a-c' → 3A..3C, '1/2' → 1, 2. Leere Liste bei Unklarem."""
    aus: list[str] = []
    for teil in re.split(r"\s*[,/]\s*|\s+und\s+", spez.strip()):
        teil = teil.strip()
        if not teil:
            continue
        seite = re.search(r"\((un)?gerade\)\s*$", teil)
        teil = re.sub(r"\s*\((?:un)?gerade\)\s*$", "", teil)
        m = re.fullmatch(r"(\d+)\s*([a-zA-Z])?\s*[-–]\s*(\d+)\s*([a-zA-Z])?", teil)
        if m and not m.group(2) and not m.group(4):
            a, b = int(m.group(1)), int(m.group(3))
            if a < b <= a + 40:
                schritt = 2 if seite else 1
                aus += [str(n) for n in range(a, b + 1, schritt)]
            continue
        m = re.fullmatch(r"(\d+)\s*([a-zA-Z])\s*[-–]\s*([a-zA-Z])", teil)
        if m:
            von, bis = m.group(2).upper(), m.group(3).upper()
            if von <= bis:
                aus += [f"{m.group(1)}{chr(c)}" for c in range(ord(von), ord(bis) + 1)]
            continue
        m = re.fullmatch(r"(\d+)\s*([a-zA-Z])?", teil)
        if m:
            aus.append(m.group(1) + (m.group(2) or "").upper())
            continue
        m = re.fullmatch(r"[a-zA-Z]", teil)
        if m and aus:  # „12 a, b“: Buchstabe zur letzten Nummer
            aus.append(re.sub(r"[A-Z]$", "", aus[-1]) + teil.upper())
    return aus


def adressen_zerlegen(adresse: str) -> list[tuple[str, str]]:
    """'Am Fährgut 1, 11-20' → [(Am Fährgut, 1), (Am Fährgut, 11) …]. Ohne Hausnummer: leer."""
    paare: list[tuple[str, str]] = []
    strasse = None
    for stueck in re.split(r";\s*|,\s*(?=[A-ZÄÖÜ][a-zäöüß])|(?<=[\d)])\s+(?=[A-ZÄÖÜ][a-zäöüß])", adresse):
        stueck = stueck.strip()
        m = re.match(r"^(.*?[^\d\s])\s+(\d.*)$", stueck)
        if m:
            strasse, spez = m.group(1).strip(), m.group(2)
        elif strasse and re.match(r"^\d", stueck):
            spez = stueck
        else:
            strasse = stueck or strasse
            continue
        paare += [(strasse, n) for n in hausnummern(spez)]
    return paare


# ------------------------------------------------------------------------------------------ BLDAM
def bldam_lesen() -> list[dict]:
    if sha256(BLDAM_PDF) != BLDAM_SHA:
        raise SystemExit(f"SHA256 von {BLDAM_PDF} weicht ab")
    text = subprocess.run(["pdftotext", "-layout", str(BLDAM_PDF), "-"], check=True, capture_output=True,
                          text=True).stdout
    zeilen = text.splitlines()
    start = next(i for i, z in enumerate(zeilen) if z.startswith("D) Denkmale übriger Gattungen"))
    eintraege: list[dict] = []
    spalten = None
    akt = None
    for z in zeilen[start + 1:]:
        if re.search(r"\bOrt\s+Gemeinde\s+Adresse\s+Bezeichnung\s+ID-Nummer", z):
            spalten = (z.index("Adresse"), z.index("Bezeichnung"), z.index("ID-Nummer"))
            continue
        if (not z.strip() or z.startswith(("Denkmalliste des Landes", "Stadt Potsdam", "Stand:", "Stiftung "))
                or "(MIDAS-Obj.Nr.)" in z or re.fullmatch(r"\s*Seite \d+ von \d+\s*", z)):
            continue
        if spalten is None:
            continue
        a, b, _c = spalten
        m = re.search(r"\b(09\d{6})\s*$", z)
        stuecke = [(s.start(), s.group()) for s in re.finditer(r"\S+(?: \S+)*", z[:m.start()] if m else z)]
        if m:
            ort = next((t for s, t in stuecke if s < a - 2), "")
            mitte = [(s, t) for s, t in stuecke if s >= a - 2]
            adr, bez = "", ""
            if mitte and mitte[0][0] < b - 4:
                adr, bez = mitte[0][1], " ".join(t for _, t in mitte[1:])
                # Adresse und Bezeichnung nur durch ein Leerzeichen getrennt: an der letzten Hausnummer teilen
                h = re.match(r"^([^\d]*?-) ([A-ZÄÖÜ„\"].*)$", adr)
                if not bez and h:  # „Henning-von-Tresckow- Kaserne …“: Straßenname bricht in die nächste Zeile um
                    adr, bez = h.group(1), h.group(2)
                if not bez:
                    t = re.match(r"^(.*?\d+(?: ?[a-zA-Z](?![a-zäöüß]))?(?:\s*[-–,]\s*\d+(?: ?[a-zA-Z]"
                                 r"(?![a-zäöüß]))?)*(?: \((?:un)?gerade\))?,?)\s+([A-ZÄÖÜ„\"].*)$", adr)
                    if t:
                        adr, bez = t.group(1), t.group(2)
                    elif len(adr) > b - a + 2:  # keine Hausnummer: an der Spaltengrenze teilen
                        adr, bez = z[a:b].strip(), z[b:m.start()].strip()
            else:
                bez = " ".join(t for _, t in mitte)
            akt = {"midas": m.group(1), "ort": ort, "adresse": adr, "bez": bez}
            eintraege.append(akt)
        elif akt is not None:
            for s, t in stuecke:
                if a - 2 <= s < b - 4:
                    if akt["adresse"].endswith("-") and t[:1].islower():  # „Weinmeister-“ + „straße“
                        akt["adresse"] = akt["adresse"][:-1] + t
                    else:
                        trenn = "" if akt["adresse"].endswith("-") else " "
                        akt["adresse"] = (akt["adresse"] + trenn + t).strip()
                elif s >= b - 4:
                    akt["bez"] += " " + t
    for e in eintraege:
        e["paare"] = adressen_zerlegen(e["adresse"]) if e["adresse"] else []
    return eintraege


# ------------------------------------------------------------------------------------------ Wikipedia
def wiki_klartext(wt: str) -> str:
    wt = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", wt, flags=re.DOTALL)
    wt = re.sub(r"<br\s*/?>", "\n", wt)
    wt = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", wt)
    wt = re.sub(r"<[^>]+>|'{2,}|\{\{[^}]*\}\}", "", wt)
    return html.unescape(wt)


def wikipedia_lesen() -> list[dict]:
    zeilen = []
    for datei in sorted(WP_ORDNER.glob("teil_*.html")):
        teil = datei.stem.removeprefix("teil_")
        url = WP_BASIS + ("_(Außenbereiche)" if teil == "Aussenbereiche" else f"/{teil}")
        t = datei.read_text(encoding="utf-8")
        for roh in re.findall(r"data-mw='([^']*)'", t):
            d = json.loads(html.unescape(roh))
            for p in d.get("parts", []):
                if not (isinstance(p, dict) and "template" in p
                        and "Tabellenzeile" in p["template"]["target"].get("wt", "")):
                    continue
                pr = {k: v.get("wt", "") for k, v in p["template"]["params"].items()}
                try:
                    ns, ew = float(pr.get("NS") or "x"), float(pr.get("EW") or "x")
                except ValueError:
                    ns = ew = None
                zeilen.append({"midas": (pr.get("Id") or "").strip(), "url": url, "ns": ns, "ew": ew,
                               "bez": wiki_klartext(pr.get("Bezeichnung", "")),
                               "text": wiki_klartext(pr.get("Beschreibung", ""))})
    return zeilen


JAHR = r"(1[2-9]\d\d|20[0-2]\d)"
BAUVERB = re.compile(r"\b(errichtet|erbaut|entstand|entstanden|gebaut|erbauen|erbaute|errichten|"
                     r"errichtete|Bauzeit|Bau des|Bau der)\b", re.IGNORECASE)
UMBAU = re.compile(r"(umgebaut|Umbau|aufgestockt|Aufstockung|erweitert|Erweiterung|Anbau|angebaut|"
                   r"umgestaltet|Umgestaltung|wiederaufgebaut|Wiederaufbau|rekonstruiert|Rekonstruktion|"
                   r"saniert|Sanierung|restauriert|Restaurierung|überformt|verändert|ersetzt|Neubau|"
                   r"modernisiert|ausgebaut|Ausbau|erneuert|Erneuerung)", re.IGNORECASE)
BAUTEIL = re.compile(r"\b(Säulengang|Turm|Glockenturm|Campanile|Kuppel|Portal|Vorhalle|Flügel|Seitenflügel|"
                     r"Anbau|Hinterhaus|Fassade|Treppe|Einfriedung|Gitter|Terrasse|Terrassen|Saal|Apsis|Chor|"
                     r"Dachreiter|Erker|Loggia|Veranda|Remise|Stall|Nebengebäude)\b")
UNGENAU = re.compile(r"\b(um|ca\.|circa|vor|nach|ab|seit|bis|etwa|vermutlich|wohl|angeblich|frühestens|"
                     r"spätestens)\s*$",
                     re.IGNORECASE)


def jahre_aus(ausdruck: str) -> tuple[int, int, bool] | None:
    """'1848/49' → (1848, 1849); '1874–1876', 'zwischen 1745 und 1747', '1776'. genau = Spanne ≤ 3 J."""
    jahre: list[int] = []
    for m in re.finditer(JAHR + r"(?:\s*/\s*(\d{1,2})(?!\d))?", ausdruck):
        j = int(m.group(1))
        jahre.append(j)
        if m.group(2):  # „1848/49“, „1956/7“
            k = int(m.group(1)[:4 - len(m.group(2))] + m.group(2))
            jahre.append(k if k >= j else k + 10 ** len(m.group(2)))
    if not jahre:
        return None
    von, bis = min(jahre), max(jahre)
    vorne = ausdruck[:re.search(JAHR, ausdruck).start()]
    genau = bis - von <= 3 and not UNGENAU.search(vorne) and "Jh" not in ausdruck
    return von, bis, genau


REKON = re.compile(r"(rekonstruiert|Rekonstruktion|wiederaufgebaut|Wiederaufbau|Nachbau|nachgebaut)", re.IGNORECASE)
FELD_KOPF = re.compile(r"^\(?\s*(um|ca\.|circa|vor|nach|ab|etwa)?\s*(" + JAHR + r"(?:\s*[/–-]\s*\d{2,4}(?!\d))?)",
                       re.IGNORECASE)


def belege_aus_feld(wert: str) -> list[tuple[int | None, int | None, str, bool, str]]:
    """Feld „Baujahr: …“. Kopf = erstes Jahr am Anfang, Rest = Zusätze.

    '1739, Umbau 1851/1890' → Bau 1739 + Umbau 1851–1890; '1785 (rekonstruiert)' → 1785 unklar (das
    heutige Gebäude ist jünger); '1847–1849 Um- und Erweiterungsbau' → Umbau; 'vor 1874' → bis 1874,
    'nach 1873' → ab 1873, jeweils ungenau.
    """
    m = FELD_KOPF.match(wert.strip())
    if not m:
        return []
    j = jahre_aus(m.group(2))
    if not j:
        return []
    von, bis, genau = j
    zusatz = (m.group(1) or "").lower()
    if zusatz == "vor":
        von, genau = None, False
    elif zusatz in ("nach", "ab"):
        bis, genau = None, False
    elif zusatz:
        genau = False
    rest = wert.strip()[m.end():]
    rest_jahre = re.search(JAHR, rest)
    aus = []
    if rest_jahre:
        # „1781 (rekonstruiert 1956/7)“: das heutige Gebäude ist die Rekonstruktion, der Kopf kein Baujahr
        kopf_art = "unklar" if REKON.search(rest) else "bau"
        jr = jahre_aus(rest)
        aus.append((jr[0], jr[1], "umbau" if UMBAU.search(rest) else "unklar", False, "feld_zusatz"))
    elif UMBAU.search(rest):
        # „(rekonstruiert)“: Jahr des Vorgängers; „1847–1849 Umbau“: das Jahr selbst ist ein Umbau
        kopf_art = "unklar" if rest.lstrip().startswith("(") else "umbau"
    else:
        kopf_art = "bau"
    aus.insert(0, (von, bis, kopf_art, genau and kopf_art == "bau", "feld"))
    return aus


def belege_aus_text(bez: str, text: str) -> list[tuple[int | None, int | None, str, bool, str]]:
    """Liefert (von, bis, art, genau, regel). Streng: Umbau nie als Bau."""
    aus = []
    m = re.search(r"Baujahr(?:e)?\s*:\s*([^\n]*)", text)
    if m:
        aus += belege_aus_feld(m.group(1))
    nur_jahr = re.fullmatch(r"\s*(?:um\s+)?" + JAHR + r"(?:\s*[/–-]\s*\d{2,4})?\s*", text)
    if not aus and nur_jahr:
        j = jahre_aus(text)
        if j:
            aus.append((j[0], j[1], "unklar", False, "nur_jahr"))
    if not aus:
        # Nur die ersten drei Sätze: lange Beschreibungen (Parks, Ensembles) erzählen später andere Bauten.
        for satz in re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9])|\n", text)[:3]:
            satz = re.sub(r"\([^)]*\)", "", satz)  # Klammern nennen oft Namens- oder Lebensdaten
            if not re.search(JAHR, satz):
                continue
            if UMBAU.search(satz):
                j = jahre_aus(satz)
                if j:
                    aus.append((j[0], j[1], "umbau", False, "satz_umbau"))
                continue
            if BAUVERB.search(satz):
                j = jahre_aus(satz)
                if j:
                    # „Der vorgelagerte Säulengang entstand 1842/43“: Jahr eines Bauteils, nicht des Gebäudes
                    breit = j[1] - j[0] > 10 or bool(BAUTEIL.search(" ".join(satz.split()[:4])))
                    aus.append((j[0], j[1], "unklar" if breit else "bau", j[2] and not breit, "satz_bau"))
                    break  # nur der erste Bau-Satz zählt; spätere Sätze erzählen meist Umbauten
    return aus


# ------------------------------------------------------------------------------------------ Wikidata
def wikidata_lesen() -> list[dict]:
    """CSV aus der Abfrage in kiezatlas-daten/entwuerfe/2026-11-05-wikidata-abfrage-b2.rq.

    Spalten: item, itemLabel (nur zum Aussortieren von Ensembles, wird nicht gespeichert), inception
    (ISO-Datum), precision (9 = Jahr, 8 = Jahrzehnt, 7 = Jahrhundert), coord ('Point(lon lat)'),
    denkmal_id (optional, MIDAS). Hat ein Objekt mehrere inception-Werte, ist keiner davon genau.
    """
    zeilen = []
    with WD_DATEI.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            m = re.match(r"^\+?(-?\d{1,4})-", (r.get("inception") or "").strip())
            if not m:
                continue
            j = int(m.group(1))
            prec = int(r.get("precision") or 9)
            if prec >= 9:
                von, bis, genau = j, j, True
            elif prec == 8:
                von, bis, genau = j - j % 10, j - j % 10 + 9, False
            else:
                continue
            pm = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", r.get("coord") or "")
            zeilen.append({"item": r["item"].strip(), "von": von, "bis": bis, "genau": genau,
                           "midas": (r.get("denkmal_id") or "").strip(),
                           "ensemble": bool(WD_ENSEMBLE.search(r.get("itemLabel") or "")),
                           "ew": float(pm.group(1)) if pm else None, "ns": float(pm.group(2)) if pm else None})
    werte = collections.Counter(z["item"] for z in zeilen)
    for z in zeilen:
        if werte[z["item"]] > 1:
            z["genau"] = False
    return zeilen


# ------------------------------------------------------------------------------------------ Datenbank
def adressen_zuordnen(cur, paare: list[tuple[str, str, str, str]]) -> dict[tuple[str, str, str], str]:
    """paare: (midas, ort, strasse, hausnr) → {(midas, strasse, hausnr): oid Hauptgebäude}."""
    cur.execute("CREATE TEMP TABLE b2_adr (midas text, ort text, strasse text, hausnr text) ON COMMIT DROP")
    with cur.copy("COPY b2_adr FROM STDIN") as cp:
        for p in paare:
            cp.write_row(p)
    cur.execute(f"""
        WITH kand AS (
          SELECT a.midas, a.ort, a.strasse, a.hausnr, g.oid, g.funktion,
                 ST_Area(g.geom::geography) AS flaeche, ST_PointOnSurface(g.geom) AS pkt, s.nr AS st_nr,
                 s.name AS st_name
          FROM b2_adr a
          JOIN auswertung.gebaeude_adresse ga
            ON lower(ga.strasse) = lower(a.strasse)
           AND upper(replace(ga.hausnr, ' ', '')) = a.hausnr
          JOIN {SNAPSHOT} g ON g.oid = ga.oid_bezug
          LEFT JOIN public.stadtteil s ON ST_Intersects(s.geom, ST_PointOnSurface(g.geom)))
        SELECT midas, ort, strasse, hausnr, oid, coalesce(funktion, ''), flaeche, st_nr, st_name,
               ST_X(pkt), ST_Y(pkt)
        FROM kand""")
    nach_adresse: dict[tuple[str, str, str], list] = collections.defaultdict(list)
    for midas, ort, strasse, hausnr, oid, funk, fl, st_nr, st_name, x, y in cur.fetchall():
        nach_adresse[(midas, strasse, hausnr)].append((oid, funk, fl, st_nr, st_name, x, y, ort))
    return nach_adresse


def streuung_m(kand) -> float:
    from math import cos, hypot, radians
    if len(kand) < 2:
        return 0.0
    ys = [k[6] for k in kand]
    f = 111_320 * cos(radians(sum(ys) / len(ys)))
    return max(hypot((a[5] - b[5]) * f, (a[6] - b[6]) * 111_320) for a in kand for b in kand)


def ort_filter(kand, ort: str):
    if ort in ("Potsdam", ""):
        return [k for k in kand if k[3] not in ORTSTEIL_NR - {11, 12, 13, 15}]
    name = ORT_ZU_STADTTEIL.get(ort, ort)
    genau = [k for k in kand if k[4] == name]
    return genau or [k for k in kand if k[3] in ORTSTEIL_NR]


def hauptgebaeude(kand, zaehler: collections.Counter):
    """Hauptgebäude einer Adresse oder None (nur Nebengebäude bzw. mehrdeutig)."""
    if streuung_m(kand) > STREUUNG_M:
        kand = ort_filter(kand, kand[0][7])
        if not kand or streuung_m(kand) > STREUUNG_M:
            zaehler["adresse_mehrdeutig"] += 1
            return None
        zaehler["adresse_ueber_ort_entschieden"] += 1
    haupt = [k for k in kand if k[1] not in NEBEN]
    if not haupt:
        zaehler["adresse_nur_nebengebaeude"] += 1
        return None
    if len(kand) > 1:
        zaehler["adresse_mehrere_gebaeude"] += 1
    return max(haupt, key=lambda k: k[2])[0]


def punkt_zuordnen(cur, punkte: list[tuple[str, float, float]]) -> dict[str, str]:
    """(schluessel, lon, lat) → oid: Gebäude, das den Punkt enthält, sonst nächstes Hauptgebäude ≤ 10 m."""
    cur.execute("CREATE TEMP TABLE b2_pkt (k text, lon float8, lat float8) ON COMMIT DROP")
    with cur.copy("COPY b2_pkt FROM STDIN") as cp:
        for p in punkte:
            cp.write_row(p)
    cur.execute(f"""
        SELECT p.k, g.oid FROM b2_pkt p
        CROSS JOIN LATERAL (
          SELECT g.oid FROM {SNAPSHOT} g
          WHERE ST_DWithin(g.geom::geography, ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326)::geography, 10)
            AND (ST_Intersects(g.geom, ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326))
                 OR coalesce(g.funktion, '') <> ALL(%s))
          ORDER BY ST_Intersects(g.geom, ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326)) DESC,
                   g.geom::geography <-> ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326)::geography
          LIMIT 1) g""", (list(NEBEN),))
    return dict(cur.fetchall())


def ersetzen(conn, quelle_muster: str, zeilen: list[tuple], trocken: bool) -> None:
    """Löscht alle Zeilen mit quelle LIKE quelle_muster und schreibt zeilen, in einer Transaktion."""
    if trocken:
        print(f"  (trocken) {len(zeilen)} Zeilen für {quelle_muster}")
        return
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("DELETE FROM auswertung.jahr_beleg WHERE quelle LIKE %s", (quelle_muster,))
        geloescht = cur.rowcount
        with cur.copy("COPY auswertung.jahr_beleg (oid_bezug, jahr_von, jahr_bis, art, genau, nur_pruefung, "
                      "quelle, lizenz, beleg_url) FROM STDIN") as cp:
            for z in zeilen:
                cp.write_row(z)
    print(f"  {quelle_muster}: {geloescht} alte Zeilen ersetzt durch {len(zeilen)}")


# ------------------------------------------------------------------------------------------ Läufe
def lauf_bldam(conn, trocken: bool, stand: dict) -> None:
    eintraege = bldam_lesen()
    z = collections.Counter(eintraege=len(eintraege), ids=len({e["midas"] for e in eintraege}),
                            ohne_adresse=sum(1 for e in eintraege if not e["paare"]),
                            adressen=sum(len(e["paare"]) for e in eintraege))
    paare = [(e["midas"], e["ort"], strasse, nr) for e in eintraege for strasse, nr in e["paare"]]
    with conn.transaction(), conn.cursor() as cur:
        nach_adresse = adressen_zuordnen(cur, paare)
    zeilen, je_midas = [], collections.defaultdict(set)
    gesehen = set()
    for midas, _ort, strasse, nr in paare:
        kand = nach_adresse.get((midas, strasse, nr))
        if not kand:
            z["adresse_nicht_gefunden"] += 1
            continue
        oid = hauptgebaeude(kand, z)
        if oid is None or (midas, oid) in gesehen:
            continue
        gesehen.add((midas, oid))
        je_midas[midas].add(oid)
        zeilen.append((oid, None, None, "unklar", False, True, BLDAM_QUELLE, BLDAM_LIZENZ,
                       f"{BLDAM_URL}#{midas}"))
    # Ensemble-Mitglieder (mehr als ENSEMBLE_GRENZE Gebäude je ID) im Quelltext kennzeichnen: B4 trennt so
    # Einzeldenkmal und Siedlungsmitglied, der Vertrag quelle LIKE 'BLDAM%' bleibt gültig.
    gross = {m for m, v in je_midas.items() if len(v) > ENSEMBLE_GRENZE}
    zeilen = [z_[:6] + (BLDAM_QUELLE + BLDAM_ENSEMBLE if z_[8].rsplit("#", 1)[1] in gross else z_[6],) + z_[7:]
              for z_ in zeilen]
    z["ids_zugeordnet"] = len(je_midas)
    z["gebaeude_markiert"] = len({r[0] for r in zeilen})
    z["ids_ensemble_gt4"] = sum(1 for v in je_midas.values() if len(v) > ENSEMBLE_GRENZE)
    stand["bldam"] = dict(z)
    stand["bldam_je_midas"] = {k: sorted(v) for k, v in je_midas.items()}
    ersetzen(conn, "BLDAM%", zeilen, trocken)


def lauf_wikipedia(conn, trocken: bool, stand: dict) -> None:
    if not any(WP_ORDNER.glob("teil_*.html")):
        print(f"  wikipedia: keine Teillisten unter {WP_ORDNER}")
        return
    wp = wikipedia_lesen()
    je_midas = stand.get("bldam_je_midas")
    if je_midas is None:  # BLDAM-Zuordnung aus der Datenbank, wenn bldam in diesem Lauf nicht lief
        with conn.cursor() as cur:
            cur.execute("SELECT split_part(beleg_url, '#', 2), oid_bezug FROM auswertung.jahr_beleg "
                        "WHERE quelle LIKE 'BLDAM%'")
            je_midas = collections.defaultdict(list)
            for m, o in cur.fetchall():
                je_midas[m].append(o)
    z = collections.Counter(zeilen=len(wp))
    belege = []
    for i, r in enumerate(wp):
        b = belege_aus_text(r["bez"], r["text"])
        if b:
            z["zeilen_mit_jahr"] += 1
            belege.append((i, b))
    # Mehrere Zeilen mit derselben ID (Kapelle und Wohnhaus eines Denkmals): jede Zeile nur über ihre
    # eigene Koordinate, sonst trügen alle Gebäude der ID die Jahre aller Zeilen.
    mehrfach = {k for k, n in collections.Counter(r["midas"] for r in wp if r["midas"]).items() if n > 1}
    punkte = [(str(i), wp[i]["ew"], wp[i]["ns"]) for i, _ in belege
              if wp[i]["ns"] is not None
              and (wp[i]["midas"] in mehrfach or len(je_midas.get(wp[i]["midas"], [])) == 0)]
    with conn.transaction(), conn.cursor() as cur:
        per_punkt = punkt_zuordnen(cur, punkte) if punkte else {}
    zeilen = []
    for i, b in belege:
        r = wp[i]
        oids = je_midas.get(r["midas"], []) if r["midas"] and r["midas"] not in mehrfach else []
        weg = "ID"
        if ENSEMBLE_BEZ.match(r["bez"]):
            z["ensemble_ohne_jahr"] += 1  # Park, Siedlung, Friedhof: Jahr der Anlage ist kein Gebäude-Baujahr
            continue
        if not oids:
            o = per_punkt.get(str(i))
            oids, weg = ([o] if o else []), "Koordinate"
        if not oids:
            z["ohne_gebaeude"] += 1
            continue
        if len(oids) > ENSEMBLE_GRENZE:
            z["ensemble_ohne_jahr"] += 1
            continue
        z[f"zugeordnet_{weg}"] += 1
        url = f"{r['url']}#{r['midas'] or 'ohne-id'}"
        for von, bis, art, genau, regel in b:
            z[f"art_{art}"] += 1
            z[f"regel_{regel}"] += 1
            for oid in oids:
                zeilen.append((oid, von, bis, art, genau, True, f"{WP_QUELLE} (Zuordnung über {weg})",
                               WP_LIZENZ, url))
    stand["wikipedia"] = dict(z)
    ersetzen(conn, WP_QUELLE + "%", zeilen, trocken)


def lauf_wikidata(conn, trocken: bool, stand: dict) -> None:
    if not WD_DATEI.exists():
        print(f"  wikidata: blockiert (H9), Datei fehlt: {WD_DATEI}")
        stand["wikidata"] = {"blockiert": f"H9, fehlt {WD_DATEI}"}
        return
    wd = wikidata_lesen()
    with conn.cursor() as cur:
        cur.execute("SELECT split_part(beleg_url, '#', 2), oid_bezug FROM auswertung.jahr_beleg "
                    "WHERE quelle LIKE 'BLDAM%'")
        je_midas = collections.defaultdict(list)
        for m, o in cur.fetchall():
            je_midas[m].append(o)
    punkte = [(str(i), r["ew"], r["ns"]) for i, r in enumerate(wd) if r["ns"] is not None]
    with conn.transaction(), conn.cursor() as cur:
        per_punkt = punkt_zuordnen(cur, punkte) if punkte else {}
    # Mehrere Objekte mit derselben Denkmal-ID: nur über die eigene Koordinate (wie bei Wikipedia)
    paare = {(r["midas"], r["item"]) for r in wd if r["midas"]}
    mehrfach = {m for m, n in collections.Counter(m for m, _ in paare).items() if n > 1}
    z = collections.Counter(zeilen=len(wd))
    zeilen = []
    for i, r in enumerate(wd):
        if r["ensemble"]:
            z["ensemble_ohne_jahr"] += 1  # Park, Friedhof, Siedlung: Jahr der Anlage, kein Gebäude-Baujahr
            continue
        oids = je_midas.get(r["midas"], []) if r["midas"] and r["midas"] not in mehrfach else []
        if not oids and per_punkt.get(str(i)):
            oids = [per_punkt[str(i)]]
        if not oids or len(oids) > ENSEMBLE_GRENZE:
            z["ohne_gebaeude_oder_ensemble"] += 1
            continue
        z["zugeordnet"] += 1
        for oid in oids:
            zeilen.append((oid, r["von"], r["bis"], "bau", r["genau"], False, WD_QUELLE, WD_LIZENZ, r["item"]))
    stand["wikidata"] = dict(z)
    ersetzen(conn, WD_QUELLE, zeilen, trocken)


def lauf_ddb(conn, trocken: bool, stand: dict) -> None:
    if not DDB_KEY.exists():
        print(f"  ddb: blockiert (H8), Datei fehlt: {DDB_KEY}")
        stand["ddb"] = {"blockiert": f"H8, fehlt {DDB_KEY}"}
        return
    print("  ddb: Key liegt vor, Leser noch nicht gebaut (API-Bedingungen und Antwortformat erst prüfen)")
    stand["ddb"] = {"blockiert": "Leser fehlt, nach H8 bauen"}


def lauf_osm(conn, trocken: bool, stand: dict) -> None:
    if not (OSM_ORDNER.exists() and any(OSM_ORDNER.glob("*.pbf"))):
        print(f"  osm: blockiert (H5), kein Extrakt unter {OSM_ORDNER}")
        stand["osm"] = {"blockiert": f"H5, kein *.pbf unter {OSM_ORDNER}"}
        return
    print("  osm: Extrakt liegt vor, Leser noch nicht gebaut (nur Prüfspalte, E1)")
    stand["osm"] = {"blockiert": "Leser fehlt, nach H5 bauen"}


LAEUFE = {"bldam": lauf_bldam, "wikipedia": lauf_wikipedia, "wikidata": lauf_wikidata, "ddb": lauf_ddb,
          "osm": lauf_osm}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quelle", default=",".join(LAEUFE), help="Komma-Liste aus " + ", ".join(LAEUFE))
    ap.add_argument("--trocken", action="store_true", help="nichts schreiben, nur zählen")
    ap.add_argument("--stand", type=Path, help="Zählungen als JSON hierhin schreiben (ohne Adressen)")
    a = ap.parse_args()
    import psycopg

    stand: dict = {}
    with psycopg.connect(autocommit=True) as conn:
        for q in a.quelle.split(","):
            print(f"Quelle {q}")
            LAEUFE[q](conn, a.trocken, stand)
    stand.pop("bldam_je_midas", None)
    print(json.dumps(stand, ensure_ascii=False, indent=1))
    if a.stand:
        a.stand.write_text(json.dumps(stand, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
