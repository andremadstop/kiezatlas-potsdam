"""Paket A6: Versorgungsaussagen und Datendateien der Planer-Ebene (Kiezatlas Potsdam, Ausbau).

Kein Netzabruf, kein Schreiben in die Datenbank. Liest mit der Leserolle (mosidi_lesen, nur SELECT) und schreibt
Dateien unter daten/ (Verträge in daten/schema/):

  daten/planer.js            KIEZ_PLANER         Kennzahlen je Raumeinheit, Luftlinie (dl-de/by-2-0, CC BY 4.0)
  daten/erreichbar.js        KIEZ_ERREICHBAR     Entfernung je Zelle und Art, Luftlinie (dl-de/by-2-0)
  daten/einrichtungen.js     KIEZ_EINRICHTUNGEN  Einrichtungen aus MBJS und ALKIS (dl-de/by-2-0)
  daten/planer_fuss_odbl.js       Kennzahlen je Raumeinheit, Fußweg      } nur wenn A5b Fußweg-Zeilen bzw. A3
  daten/erreichbar_fuss_odbl.js   Entfernung je Zelle, Fußweg            } OSM-Punkte geschrieben hat; sonst
  daten/einrichtungen_odbl.js     OSM-Einrichtungen ohne Namen           } wird die Datei nicht angelegt
  belege/A6_planer_<datum>.md     Lauf: Raumebene, Zahlen, Geheimhaltung, was fehlt

Liest:
  public.zensus_zelle, public.stadtteil, public.planungsraum   Einwohner, Raumeinheiten (Planungsraum, sobald H1 da)
  public.zensus_struktur (A1)                                  Kinder je Altersgruppe (Summe der Klassen)
  auswertung.einrichtung (A2), auswertung.zelle_erreichbar, auswertung.zelle_gruen (A5a/A5b)
  auswertung.haltestelle (A4), auswertung.osm_poi (A3)
  config/richtwerte.yaml (Richtwerte, Quoten, Rundung, Geheimhaltung), config/potsdam.yaml nicht
  belege/A5a_rand_unsicher_*.csv (Zellen, deren Wert nur eine Obergrenze ist)
  $KIEZ_DATEN/eingang/prognose_planungsraum.csv (H11, falls vorhanden)

Regeln (Bauplan A6 und Prüfbericht 4, 8, 9, 13, 15):
  - Raumeinheit = Planungsraum, wenn public.planungsraum Zeilen hat, sonst Stadtteil (Feld raumebene).
    Zuordnung über den Zellmittelpunkt wie in skripte/02_auswerten.py.
  - Feine Zensusklassen nur je Raumeinheit mit mindestens geheimhaltung.min_ew_raumeinheit Einwohnern; je Zelle
    nur Entfernungen. Einwohner auf rundung_ew gerundet, Anteile ganzzahlig, jeder Wert mit Unsicherheitshinweis.
  - Fußweg-Kennzahlen nie in planer.js (Korrektur 4), sondern in planer_fuss_odbl.js.
  - Ärzte, Apotheken, Pflege: nur Entfernung, keine Versorgungsaussage (Korrektur 13).
  - Status: amtlich nur bei Richtwerten mit gelesener Fundstelle (geprueft gesetzt); Berliner Methode und Werte
    ohne Primärbeleg oder ohne gelesene Fundstelle: orientierung.

Aufruf (aus dem Worktree; Passwort nur aus der .env):
    set -a; . ../kiezatlas-potsdam/.env; set +a
    PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=mosidi_lesen PGPASSWORD="$LESE_PASSWORD" \\
    KIEZ_DATEN=../kiezatlas-daten \\
    uv run -q --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \\
        python -I skripte/15_planer.py
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "daten"
BELEGE = WURZEL / "belege"

DLDE = "https://www.govdata.de/dl-de/by-2-0"
ODBL = "https://opendatacommons.org/licenses/odbl/1-0/"
CCBY = "https://creativecommons.org/licenses/by/4.0/"
VERAENDERT = "Daten verändert (eigene Berechnung)"
ODBL_KOPF = (
    "/* Abgeleitet aus OpenStreetMap. © OpenStreetMap-Mitwirkende, Open Database License 1.0 (ODbL), "
    f"{ODBL}. Inhalte unter der Database Contents License 1.0. {VERAENDERT}. */\n"
)

# Datenquellen (Schlüssel q in den Dateien)
QUELLEN = {
    "zensus": {
        "quelle": "Zensus 2022, 100-m-Gitter, Stichtag 15.05.2022 (Bevölkerung, infrastrukturelle Altersgruppen)",
        "lizenz": "dl-de/by-2-0",
        "vermerk": f"© Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 ({DLDE}), {VERAENDERT}",
        "url": "https://www.destatis.de/static/DE/zensus/gitterdaten/",
        "stand": "2022-05-15",
    },
    "mbjs": {
        "quelle": "Ministerium für Bildung, Jugend und Sport Brandenburg, WFS Kita- und Schulstandorte",
        "lizenz": "dl-de/by-2-0",
        "vermerk": f"© Ministerium für Bildung, Jugend und Sport, dl-de/by-2-0 ({DLDE}), {VERAENDERT}",
        "stand": "2026-11-05",
    },
    "lgb": {
        "quelle": (
            "ALKIS vereinfacht (Gebäude, tatsächliche Nutzung), Landesvermessung und Geobasisinformation Brandenburg"
        ),
        "lizenz": "dl-de/by-2-0",
        "vermerk": f"© GeoBasis-DE/LGB, dl-de/by-2-0 ({DLDE}), {VERAENDERT}",
        "url": "https://isk.geobasis-bb.de/ows/alkis_vereinf_wfs",
        "stand": "2026-11-05",
    },
    "vbb": {
        "quelle": "VBB-Fahrplandaten (GTFS), Fahrplan ab 03.11.2026, Stichtag 10.11.2026",
        "lizenz": "CC BY 4.0",
        "vermerk": f"VBB Verkehrsverbund Berlin-Brandenburg GmbH, CC BY 4.0 ({CCBY}), {VERAENDERT}",
        "url": "https://www.vbb.de/gtfs",
        "stand": "2026-11-05",
    },
    "osm": {
        "quelle": "OpenStreetMap",
        "lizenz": "ODbL 1.0",
        "vermerk": f"© OpenStreetMap-Mitwirkende, Open Database License 1.0 ({ODBL}), {VERAENDERT}",
        "url": "https://www.openstreetmap.org/copyright",
    },
}
# Dokumente mit Richtwerten (Schlüssel richtwert.q). Übernommen sind nur Zahlen mit Fundstelle.
DOKUMENTE = {
    "nvp": {
        "quelle": (
            "Nahverkehrsplan 2019 der Landeshauptstadt Potsdam, Kap. 4.1 (Geltung 2019–2023, Nachfolger ungeprüft)"
        ),
        "lizenz": "keine Angabe; übernommen sind nur Richtwerte mit Fundstelle",
        "vermerk": "Richtwerte: Nahverkehrsplan 2019 der Landeshauptstadt Potsdam, gelesen am 05.11.2026",
        "url": "https://www.potsdam.de/system/files/documents/2020-09-29_nvp_potsdam_mit_anlagen.pdf",
    },
    "baulandmodell": {
        "quelle": "Potsdamer Baulandmodell 2019, Anlage C (Versorgungsquoten)",
        "lizenz": "keine Angabe; übernommen sind nur Quoten mit Fundstelle",
        "vermerk": (
            "Quoten: Richtlinie zur sozialgerechten Baulandentwicklung der Landeshauptstadt Potsdam, "
            "Stand 20.11.2019, Anlage C, gelesen am 05.11.2026"
        ),
        "url": "https://www.potsdam.de/system/files/documents/anlage1potsdamerbaulandmodell-fortschreibung2019.pdf",
    },
    "umweltatlas": {
        "quelle": "Umweltatlas Berlin, Öffentliche Grünanlagen 2020, Methode (Berliner Methode, nicht Potsdamer Norm)",
        "lizenz": "keine Angabe; übernommen sind nur Richtwerte",
        "vermerk": (
            "Richtwert: Senatsverwaltung Berlin, Umweltatlas, Versorgung mit öffentlichen, wohnungsnahen "
            "Grünanlagen 2020"
        ),
        "url": "https://www.berlin.de/umweltatlas/nutzung/oeffentliche-gruenanlagen/2020/methode/",
    },
    "satzung": {
        "quelle": (
            "Schülerfahrtkostensatzung der Landeshauptstadt Potsdam 2016 (Anspruchsschwelle, Fundstelle nicht gelesen)"
        ),
        "lizenz": "keine Angabe; übernommen ist nur die Schwelle",
        "vermerk": (
            "Schwelle: Schülerfahrtkostensatzung der Landeshauptstadt Potsdam 2016, Wert aus der "
            "Erkundung, an der Quelle nicht bestätigt"
        ),
    },
    "ehk": {
        "quelle": "Einzelhandelskonzept der Landeshauptstadt Potsdam 2014 (Fundstelle nicht gelesen)",
        "lizenz": "keine Angabe; übernommen ist nur der Radius",
        "vermerk": (
            "Radius: Einzelhandelskonzept der Landeshauptstadt Potsdam 2014, Wert aus der Erkundung, an "
            "der Quelle nicht bestätigt"
        ),
    },
    "orientierung": {
        "quelle": "ohne Primärbeleg (Entscheidung E6: Orientierung, kein Richtwert)",
        "lizenz": "eigene Festlegung",
        "vermerk": "Orientierungswert ohne Primärbeleg, kein amtlicher Richtwert",
    },
}
# Abschnitt in richtwerte.yaml → Dokument
ABSCHNITT_DOKUMENT = {
    "oepnv": "nvp",
    "baulandmodell": "baulandmodell",
    "gruen": "umweltatlas",
    "schulweg": "satzung",
    "nahversorgung": "ehk",
    "kita": "orientierung",
    "grundschule": "orientierung",
    "spielplatz": "orientierung",
}
NEUBAU_RAEUME = {"stadtteil": {"13": "Bornstedter Feld", "17": "Golm", "84": "Krampnitz"}}
KLASSEN_RANG = {"I": 3, "II": 2, "III": 1, "unter III": 0}
ZELL_ID = re.compile(r'"id":"(CRS3035RES100m[^"]+)"')


# ---------------------------------------------------------------------------------------------- Hilfen
def rund(x: float | None, auf: int) -> int | None:
    return None if x is None else int(auf * math.floor(x / auf + 0.5))


def rund2(x: float | None) -> float | None:
    return None if x is None else float(f"{x:.2f}")


def prozent(z: float, n: float) -> int | None:
    return None if not n else int(math.floor(100.0 * z / n + 0.5))


def gew_median(paare: list[tuple[float, float]]) -> float | None:
    """Nach Gewicht w gewichteter Median der Werte v (Paare v, w)."""
    paare = sorted((v, w) for v, w in paare if v is not None and w and w > 0)
    ges = sum(w for _, w in paare)
    if not ges:
        return None
    lauf = 0.0
    for v, w in paare:
        lauf += w
        if lauf >= ges / 2:
            return v
    return paare[-1][0]


def yaml_weg(rw: dict, pfad: str):
    """'kita.radius_orientierung_m' → (Abschnitt, Knoten)."""
    teile = pfad.split(".")
    k = rw
    for t in teile:
        k = k[t]
    return teile[0], k


def richtwert(rw: dict, pfad: str) -> tuple[dict, str, str]:
    """Richtwert-Objekt für planer.js, Status (amtlich|orientierung) und Begründung des Status."""
    abschnitt, knoten = yaml_weg(rw, pfad)
    wert = knoten.get("wert")
    einheit = "m"
    if pfad.endswith("_km"):
        wert, einheit = wert * 1000, "m"
    q = ABSCHNITT_DOKUMENT[abschnitt]
    obj = {"wert": wert, "einheit": einheit, "q": q}
    seite = knoten.get("seite") or rw[abschnitt].get("seite")
    if seite:
        obj["seite"] = seite
    st = knoten.get("status")
    geprueft = rw[abschnitt].get("geprueft")
    if st == "amtlich" and geprueft:
        return obj, "amtlich", ""
    if st == "amtlich":
        return (
            obj,
            "orientierung",
            "Schwelle aus der Quelle laut Erkundung, Fundstelle nicht selbst gelesen; deshalb Orientierung.",
        )
    if st == "berliner_methode":
        return obj, "orientierung", "Berliner Methode, keine Potsdamer Norm."
    return obj, "orientierung", "Orientierung ohne Primärbeleg, kein Richtwert."


def js_schreiben(pfad: Path, variable: str, inhalt: dict, kopf: str = "") -> None:
    text = json.dumps(inhalt, ensure_ascii=False, separators=(",", ":"))
    pfad.write_text(f"{kopf}window.{variable}={text};\n", encoding="utf-8")


# ---------------------------------------------------------------------------------------------- Lesen
def lesen(cur) -> dict:
    d: dict = {}
    cur.execute("SELECT count(*) FROM public.planungsraum")
    d["raumebene"] = "planungsraum" if cur.fetchone()[0] > 0 else "stadtteil"
    tab = "public.planungsraum" if d["raumebene"] == "planungsraum" else "public.stadtteil"
    cur.execute(f"SELECT nr, name FROM {tab} ORDER BY nr")
    d["raeume"] = {str(nr): name for nr, name in cur.fetchall()}
    # Zellen: Mittelpunkt in der Raumeinheit (Menge wie daten/zellen.js bei Stadtteilen)
    cur.execute(f"""SELECT z.gitter_id, r.nr, z.ew, ST_X(ST_Transform(z.geom, 25833)), ST_Y(ST_Transform(z.geom, 25833))
                    FROM public.zensus_zelle z JOIN {tab} r ON ST_Contains(r.geom, z.geom)
                    WHERE z.ew IS NOT NULL""")
    d["zellen"] = {g: {"raum": str(nr), "ew": ew, "x": x, "y": y} for g, nr, ew, x, y in cur.fetchall()}
    # Struktur über die eigene Geometrie zuordnen (kein INNER JOIN an zensus_zelle, Hinweis A1)
    cur.execute(f"""SELECT s.gitter_id, r.nr, s.i_u3, s.i_3_5, s.i_6_9, s.i_10_15
                    FROM public.zensus_struktur s JOIN {tab} r ON ST_Contains(r.geom, s.geom)""")
    d["struktur"] = {
        g: {"raum": str(nr), "i_u3": a or 0, "i_3_5": b or 0, "i_6_9": c or 0, "i_10_15": e or 0}
        for g, nr, a, b, c, e in cur.fetchall()
    }
    cur.execute("""SELECT gitter_id, art, methode, meter FROM auswertung.zelle_erreichbar""")
    d["erreichbar"] = {"luftlinie": defaultdict(dict), "fussweg": defaultdict(dict)}
    for g, art, methode, meter in cur.fetchall():
        d["erreichbar"][methode][art][g] = None if meter is None else float(meter)
    cur.execute("SELECT gitter_id, methode, radius_m, m2_je_ew FROM auswertung.zelle_gruen")
    d["gruen"] = {"luftlinie": {}, "fussweg": {}}
    for g, methode, radius, m2 in cur.fetchall():
        d["gruen"][methode][(g, radius)] = None if m2 is None else float(m2)
    cur.execute(f"""SELECT e.id, e.art, e.unterart, e.name, e.plaetze, e.schueler, e.schueler_stand, e.status,
                           e.in_potsdam, e.quelle, ST_X(ST_Transform(e.geom, 4326)), ST_Y(ST_Transform(e.geom, 4326)),
                           r.nr
                    FROM auswertung.einrichtung e
                    LEFT JOIN {tab} r ON ST_Contains(r.geom, ST_Transform(e.geom, 4326))
                    ORDER BY e.id""")
    spalten = (
        "id",
        "art",
        "unterart",
        "name",
        "plaetze",
        "schueler",
        "schueler_stand",
        "status",
        "in_potsdam",
        "quelle",
        "lon",
        "lat",
        "raum",
    )
    d["einrichtungen"] = [dict(zip(spalten, r)) for r in cur.fetchall()]
    for e in d["einrichtungen"]:
        e["raum"] = None if e["raum"] is None else str(e["raum"])
    cur.execute("""SELECT stop_id, verkehrsmittel, klasse, ST_X(geom), ST_Y(geom) FROM auswertung.haltestelle""")
    d["haltestellen"] = [
        {"id": s, "vm": set((vm or "").split("+")), "klasse": k, "x": x, "y": y} for s, vm, k, x, y in cur.fetchall()
    ]
    cur.execute("""SELECT osm_id, art, unterart, ST_X(ST_Transform(geom, 4326)), ST_Y(ST_Transform(geom, 4326))
                   FROM auswertung.osm_poi ORDER BY osm_id""")
    d["osm_poi"] = [{"id": i, "art": a, "unterart": u, "lon": x, "lat": y} for i, a, u, x, y in cur.fetchall()]
    return d


def rand_unsicher() -> dict:
    """(gitter_id, art) → Grund aus der neuesten A5a-Randliste."""
    dateien = sorted(BELEGE.glob("A5a_rand_unsicher_*.csv"))
    if not dateien:
        return {}
    with dateien[-1].open(encoding="utf-8") as f:
        return {(r["gitter_id"], r["art"]): r["grund"] for r in csv.DictReader(f, delimiter=";")}


def prognose_lesen(rw: dict, raumebene: str, meldungen: list) -> dict:
    """H11: {raum: {altersgruppe: {jahr: personen}}} und Quelle, oder leer."""
    basis = Path(os.environ.get("KIEZ_DATEN", WURZEL.parent / "kiezatlas-daten"))
    pfad = basis / rw["prognose"]["datei"]
    if not pfad.exists():
        meldungen.append(f"Prognose (H11): {pfad} fehlt, Spalte prognose nicht ausgegeben")
        return {}
    gruppen = {"u3", "3_5", "6_9", "6_11", "ges"}
    jahre = {int(j) for j in rw["prognose"]["jahre"]}
    aus: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    quellen = set()
    andere_ebene = 0
    with pfad.open(encoding="utf-8") as f:
        for n, z in enumerate(csv.DictReader(f, delimiter=";"), start=2):
            if (z.get("raumebene") or "").strip() != raumebene:
                andere_ebene += 1  # Prognose auf Stadtteilen passt nicht auf Planungsräume und umgekehrt
                continue
            if z.get("altersgruppe") not in gruppen:
                meldungen.append(f"Prognose Zeile {n}: Altersgruppe {z.get('altersgruppe')!r} ignoriert")
                continue
            if int(z["jahr"]) not in jahre:
                continue
            roh = (z.get("personen") or "").strip().replace(".", "").replace(" ", "")
            if not roh.isdigit():
                raise SystemExit(f"{pfad} Zeile {n}: personen {z.get('personen')!r} ist keine ganze Zahl")
            # mehrere Zeilen je Raum, Gruppe und Jahr (z. B. Teilgebiete) werden addiert
            aus[str(z["raum"]).strip()][z["altersgruppe"]][int(z["jahr"])] += int(roh)
            quellen.add((z.get("quelle") or "").strip())
    if andere_ebene:
        meldungen.append(f"Prognose: {andere_ebene} Zeilen mit anderer raumebene als {raumebene} ignoriert")
    meldungen.append(
        f"Prognose (H11): {len(aus)} Raumeinheiten ({raumebene}) aus {pfad.name}, Quelle {sorted(quellen)}"
    )
    return {"werte": aus, "quelle": "; ".join(sorted(q for q in quellen if q)), "raumebene": raumebene}


# ---------------------------------------------------------------------------------------------- Rechnen
def zielgruppe_je_zelle(d: dict, rw: dict, zg: str) -> dict:
    """gitter_id → Zahl der Zielgruppe (Einwohner aus zensus_zelle, Kinder aus der Struktur)."""
    felder = rw["planer"]["zielgruppen"][zg]["felder"]
    if felder is None:
        return {g: z["ew"] or 0 for g, z in d["zellen"].items()}
    return {g: sum(s[f] for f in felder) for g, s in d["struktur"].items()}


def raum_von(d: dict, g: str) -> str | None:
    if g in d["zellen"]:
        return d["zellen"][g]["raum"]
    s = d["struktur"].get(g)
    return s["raum"] if s else None


class Rechner:
    def __init__(self, d: dict, rw: dict, methode: str, rand: dict):
        self.d, self.rw, self.methode = d, rw, methode
        # Die Randliste stammt aus der Luftlinie (A5a) und gilt nicht für Netzentfernungen
        self.rand = rand if methode == "luftlinie" else {}
        g = rw["geheimhaltung"]
        self.min_ew, self.rd_ew = g["min_ew_raumeinheit"], g["rundung_ew"]
        self.min_zg = rw["planer"]["min_zielgruppe"]
        self.ew_roh = defaultdict(int)
        for z in d["zellen"].values():
            self.ew_roh[z["raum"]] += z["ew"] or 0
        self.basis_u = g["unsicherheit"]
        self.stand_zensus = "Zensus 15.05.2022"
        self.zg_cache: dict = {}
        self.geheim_null = 0

    def zg(self, name):
        if name not in self.zg_cache:
            self.zg_cache[name] = zielgruppe_je_zelle(self.d, self.rw, name)
        return self.zg_cache[name]

    def q_art(self, art: str) -> str:
        """Quelle der Standorte: OSM beim Fußweg, ALKIS bei Grün und Gemeinbedarf, sonst MBJS."""
        if self.methode == "fussweg":
            return "osm"
        if art == "gruen" or any(e["id"].startswith("alkis:") for e in self.d["einrichtungen"] if e["art"] == art):
            return "lgb"
        return "mbjs"

    def geheim(self, raum) -> bool:
        return self.ew_roh[raum] < self.min_ew

    def neubau(self, raum, ebene) -> str:
        n = NEUBAU_RAEUME.get(ebene, {}).get(raum)
        return f" Neubau nach dem Zensus-Stichtag ({n}) fehlt in den Einwohnern." if n else ""

    # --- Anteil der Zielgruppe mit Einrichtung im Radius
    def anteil_in_radius(self, raum, art, zg, rpfad, ebene) -> dict | None:
        dist = self.d["erreichbar"][self.methode].get(art)
        if not dist:
            return None
        rwobj, status, grund = richtwert(self.rw, rpfad)
        radius = rwobj["wert"]
        zgz = self.zg(zg)
        nenner = zaehler = rand_ueber = 0.0
        for g, v in zgz.items():
            if raum_von(self.d, g) != raum or not v:
                continue
            m = dist.get(g)
            if m is None:
                continue
            nenner += v
            if m <= radius:
                zaehler += v
            elif (g, art) in self.rand:
                rand_ueber += v
        w = {
            "kennzahl": "anteil_in_radius",
            "art": art,
            "zielgruppe": self.rw["planer"]["zielgruppen"][zg]["text"],
            "einheit": "%",
            "methode": self.methode,
            "status": status,
            "richtwert": rwobj,
            "q": self.q_art(art),
            "stand": f"{self.stand_zensus}, Standorte 05.11.2026",
        }
        teile = []
        fein = self.rw["planer"]["zielgruppen"][zg]["felder"] is not None
        if fein and self.geheim(raum):
            w["wert"] = None
            self.geheim_null += 1
            teile.append(
                f"Raumeinheit unter {self.min_ew} Einwohnern: Wert aus Geheimhaltungsgründen nicht ausgewiesen."
            )
        elif nenner < self.min_zg:
            w["wert"] = None
            teile.append(f"Weniger als {self.min_zg} Personen der Zielgruppe: kein belastbarer Anteil.")
        else:
            w["wert"] = prozent(zaehler, nenner)
        teile.append(
            f"{self.basis_u} Anteil gegen die Summe der Altersklassen, ganzzahlig gerundet."
            if fein
            else f"{self.basis_u} Anteil ganzzahlig gerundet."
        )
        teile.append("Entfernung vom Zellmittelpunkt (bis 71 m vom Wohnort), aussagekräftig auf rund 50 m.")
        if rand_ueber and w["wert"] is not None:
            teile.append(
                f"Für {prozent(rand_ueber, nenner)} % der Zielgruppe ist die Entfernung nur eine Obergrenze "
                "(Einrichtungen in Berlin oder jenseits des Datengebiets nicht gerechnet)."
            )
        if grund:
            teile.append(grund)
        if art == "grundschule":
            w["vorlaeufig"] = True
            teile.append(
                "Vorläufig, ohne Schulbezirk: Grundschulen werden über Schulbezirke geplant; "
                "Grundschulteile kombinierter Schulformen zählen nicht mit."
            )
        if art in ("kita", "hort"):
            teile.append(
                "Kitas haben in Brandenburg keine Einzugsbereiche (Wunsch- und Wahlrecht): Entfernung ist Lage, "
                "keine Versorgung."
            )
        teile.append(self.neubau(raum, ebene).strip())
        w["unsicherheit"] = " ".join(t for t in teile if t)
        return w

    # --- nur Lage (Ärzte, Apotheken, Pflege, Märkte, Spielplätze aus OSM; Korrektur 13)
    def entfernung_median(self, raum, art, ebene) -> dict | None:
        dist = self.d["erreichbar"][self.methode].get(art)
        if not dist:
            return None
        paare = [(dist.get(g), z["ew"]) for g, z in self.d["zellen"].items() if z["raum"] == raum]
        med = gew_median(paare)
        return {
            "kennzahl": "entfernung_median",
            "art": art,
            "zielgruppe": "Einwohner",
            "wert": rund(med, self.rw["planer"]["rundung_meter"]),
            "einheit": "m",
            "methode": self.methode,
            "status": "orientierung",
            "q": "osm",
            "stand": f"{self.stand_zensus}, Standorte laut Datenstand",
            "unsicherheit": "Median nach Einwohnern. Nur Lage, keine Versorgungsaussage: ohne Kapazität, "
            "Bedarfsplanung auf größeren Bereichen." + self.neubau(raum, ebene),
        }


def anteile(r: Rechner, raum: str, ebene: str) -> list[dict]:
    """Anteile der Zielgruppe im Radius laut richtwerte.yaml (planer.anteil_in_radius), je Methode."""
    werte = []
    for e in r.rw["planer"]["anteil_in_radius"]:
        w = r.anteil_in_radius(raum, e["art"], e["zielgruppe"], e["richtwert"], ebene)
        if w:
            werte.append(w)
    return werte


def kennzahlen_luftlinie(r: Rechner, raum: str, ebene: str) -> list[dict]:
    d = r.d
    werte = anteile(r, raum, ebene)
    ein = [e for e in d["einrichtungen"] if e["raum"] == raum]
    werte += plaetze(r, raum, ein, ebene)
    werte += ew_je(r, raum, ein, ebene)
    w = oepnv(r, raum, ebene)
    if w:
        werte += w
    w = gruen(r, raum, ebene)
    if w:
        werte.append(w)
    return werte


def plaetze(r: Rechner, raum: str, ein: list[dict], ebene: str) -> list[dict]:
    """Prüfbericht 9: Kombinierte Einrichtungen nicht still mischen. Drei Kennzahlen (siehe richtwerte.yaml)."""
    rw = r.rw
    bl = rw["baulandmodell"]
    q = {k: v["quote_prozent"] / 100 for k, v in bl["quoten"].items()}
    f612 = bl["zensus_6_bis_unter_12"]
    kap = [e for e in ein if e["status"] == "kapazitaet" and e["plaetze"]]
    kita_rein = sum(e["plaetze"] for e in kap if e["art"] == "kita" and "hort" not in (e["unterart"] or ""))
    kita_komb = [e for e in kap if e["art"] == "kita" and "hort" in (e["unterart"] or "")]
    hort_rein = sum(e["plaetze"] for e in kap if e["art"] == "hort")
    alle = sum(e["plaetze"] for e in kap if e["art"] in ("kita", "hort"))
    s = defaultdict(float)
    for g, st in r.d["struktur"].items():
        if st["raum"] == raum:
            for k in ("i_u3", "i_3_5", "i_6_9", "i_10_15"):
                s[k] += st[k]
    k6_12 = s["i_6_9"] * f612["i_6_9"] + s["i_10_15"] * f612["i_10_15"]
    bedarf = q["krippe"] * s["i_u3"] + q["kindergarten"] * s["i_3_5"] + q["hort"] * k6_12
    geheim = r.geheim(raum)
    stand = f"Kinder: {r.stand_zensus}; Plätze: MBJS 05.11.2026"
    gemein = (
        f"{r.basis_u} Plätze = Kapazität laut Betriebserlaubnis (MBJS), nicht belegte Plätze; Kindertagespflege fehlt. "
        "Wunsch- und Wahlrecht: Kinder besuchen auch Einrichtungen in anderen Raumeinheiten."
    )
    neubau = r.neubau(raum, ebene)

    def zeile(
        art, zielgruppe, zaehler, nenner, einheit, extra, kennzahl="plaetze_je_kind", rwobj=None, q="mbjs"
    ) -> dict:
        w = {
            "kennzahl": kennzahl,
            "art": art,
            "zielgruppe": zielgruppe,
            "einheit": einheit,
            "methode": "luftlinie",
            "status": "amtlich",
            "q": q,
            "stand": stand,
        }
        if rwobj:
            w["richtwert"] = rwobj
        if geheim:
            w["wert"] = None
            r.geheim_null += 1
            extra = (
                f"Raumeinheit unter {r.min_ew} Einwohnern: Wert aus Geheimhaltungsgründen nicht ausgewiesen. " + extra
            )
        elif nenner < r.min_zg:
            w["wert"] = None
            extra = f"Weniger als {r.min_zg} Kinder der Zielgruppe: keine belastbare Relation. " + extra
        else:
            w["wert"] = rund2(zaehler / nenner)
        w["unsicherheit"] = (extra + " " + gemein + neubau).strip()
        return w

    aus = []
    komb_txt = (
        f" Ohne {sum(e['plaetze'] for e in kita_komb)} Plätze in {len(kita_komb)} "
        f"{'Einrichtung' if len(kita_komb) == 1 else 'Einrichtungen'} mit Krippe "
        "oder Kindergarten und Hort (Kapazität nicht nach Altersbereich aufteilbar): Untergrenze."
        if kita_komb
        else " Keine kombinierte Einrichtung mit Hort in der Raumeinheit."
    )
    aus.append(
        zeile(
            "kita",
            "Kinder unter 6, Kitas ohne Hortanteil",
            kita_rein,
            s["i_u3"] + s["i_3_5"],
            "Plätze je Kind",
            "Plätze reiner Krippen und Kindergärten." + komb_txt,
        )
    )
    w = zeile(
        "hort",
        "Kinder 6 bis 9, reine Horte",
        hort_rein,
        s["i_6_9"],
        "Plätze je Kind",
        "Plätze reiner Horte gegen Kinder 6 bis 9 Jahre (Hortalter reicht bis unter 12)."
        + (" Hortplätze kombinierter Kitas fehlen hier." if kita_komb else ""),
    )
    if not hort_rein and kita_komb and w["wert"] is not None:
        w["wert"] = None
        w["unsicherheit"] = (
            "Kein reiner Hort in der Raumeinheit; Hortplätze gibt es hier nur in kombinierten Kitas, "
            "deren Kapazität sich nicht aufteilen lässt. " + w["unsicherheit"]
        )
    aus.append(w)
    rwobj = {"wert": 1.0, "einheit": "Platz je Bedarfsplatz", "q": "baulandmodell", "seite": bl["seite"]}
    aus.append(
        zeile(
            "kita",
            "rechnerischer Bedarf Krippe, Kindergarten und Hort",
            alle,
            bedarf,
            "Plätze je Bedarfsplatz",
            f"Alle Plätze in Krippe, Kindergarten und Hort gegen den Bedarf nach Baulandmodell, Anlage C: "
            f"{bl['quoten']['krippe']['quote_prozent']} % der Kinder unter 3, "
            f"{bl['quoten']['kindergarten']['quote_prozent']} % der 3- bis 5-Jährigen, "
            f"{bl['quoten']['hort']['quote_prozent']} % der 6- bis unter 12-Jährigen. Die Quoten sind um "
            "Kapazitätsreserven vermindert (rechnerischer Mindestbedarf). 6 bis unter 12 geschätzt: "
            "Zensus 6 bis 9 plus ein Drittel von 10 bis 15 (gleich verteilt angenommen).",
            kennzahl="plaetze_je_bedarf",
            rwobj=rwobj,
        )
    )
    # Grundschule: Schülerzahl laut MBJS gegen Kinder 6 bis unter 12 (Quote 100 %)
    gs = [e for e in ein if e["art"] == "grundschule" and e["schueler"]]
    stand_s = sorted({e["schueler_stand"] for e in gs if e["schueler_stand"]})
    w = zeile(
        "grundschule",
        "Kinder 6 bis unter 12 (geschätzt)",
        sum(e["schueler"] for e in gs),
        k6_12,
        "Schüler je Kind",
        "Schülerzahl der Grundschulen (Schulform G) in der Raumeinheit, nicht Kapazität; Grundschulteile "
        "kombinierter Schulformen fehlen. Vorläufig, ohne Schulbezirk. 6 bis unter 12 geschätzt wie oben.",
        kennzahl="schueler_je_kind",
        rwobj={
            "wert": bl["quoten"]["grundschule"]["quote_prozent"] / 100,
            "einheit": "Schüler je Kind",
            "q": "baulandmodell",
            "seite": bl["seite"],
        },
    )
    w["vorlaeufig"] = True
    w["stand"] = f"Kinder: {r.stand_zensus}; Schüler: MBJS, Stand {', '.join(stand_s) or 'k. A.'}"
    aus.append(w)
    return aus


def ew_je(r: Rechner, raum: str, ein: list[dict], ebene: str) -> list[dict]:
    aus = []
    ew = r.ew_roh[raum]
    vorhanden = {e["art"] for e in r.d["einrichtungen"]}
    for art in r.rw["planer"]["ew_je_einrichtung"]:
        if art not in vorhanden:
            continue
        # eine Kita zählt je id_kita einmal (weitere Häuser „#haus<n>“ nicht)
        n = len([e for e in ein if e["art"] == art and "#haus" not in e["id"]])
        lgb = any(e["id"].startswith("alkis:") for e in r.d["einrichtungen"] if e["art"] == art)
        w = {
            "kennzahl": "ew_je_einrichtung",
            "art": art,
            "zielgruppe": "Einwohner",
            "wert": rund(ew / n, r.rd_ew) if n and ew else None,
            "einheit": "Einwohner je Standort",
            "methode": "luftlinie",
            "status": "amtlich",
            "q": "lgb" if lgb else "mbjs",
            "stand": f"Einwohner: {r.stand_zensus}; Standorte 05.11.2026",
        }
        txt = [
            (f"{n} Standort in der Raumeinheit." if n == 1 else f"{n} Standorte in der Raumeinheit.")
            if n
            else "Kein Standort in der Raumeinheit.",
            f"Einwohner auf {r.rd_ew} gerundet.",
        ]
        if lgb:
            txt.append(
                "Nur Lage aus ALKIS-Gebäudefunktionen, ohne Kapazität; benachbarte Gebäude derselben Art bis 50 m "
                "als ein Standort."
            )
        if art == "grundschule":
            w["vorlaeufig"] = True
            txt.append("Vorläufig, ohne Schulbezirk.")
        txt.append("Raumgrenzen schneiden Einzugsbereiche: Standorte nahe der Grenze versorgen auch Nachbarräume.")
        w["unsicherheit"] = " ".join(txt) + r.neubau(raum, ebene)
        aus.append(w)
    return aus


def oepnv(r: Rechner, raum: str, ebene: str) -> list[dict] | None:
    rw, o = r.rw, r.rw["oepnv"]
    if not r.d["haltestellen"]:
        return None
    vm_rad = rw["planer"]["oepnv_verkehrsmittel_mit_radius"]
    zellen = [(g, z) for g, z in r.d["zellen"].items() if z["raum"] == raum and z["ew"]]
    hs = r.d["haltestellen"]

    def anteil(klasse: str, mit_takt: bool) -> float | None:
        radien = {vm: o["einzugsradius_m"][vm].get(klasse) for vm in vm_rad}
        nenner = zaehler = 0
        for _, z in zellen:
            nenner += z["ew"]
            for h in hs:
                if mit_takt and KLASSEN_RANG.get(h["klasse"], 0) < KLASSEN_RANG[klasse]:
                    continue
                d2 = (h["x"] - z["x"]) ** 2 + (h["y"] - z["y"]) ** 2
                if any(radien[vm] and vm in h["vm"] and d2 <= radien[vm] ** 2 for vm in vm_rad):
                    zaehler += z["ew"]
                    break
        return None if not nenner else 100.0 * zaehler / nenner

    gk = (o["gebietsklassen"]["stadtteile"].get(raum) if ebene == "stadtteil" else None) or {}
    klasse = gk.get("klasse")
    # Klassen der Bestandteile; Freitext wie „II laut Tab. 4.1, I laut Text und Anlage 4“ (Waldstadt I) liefert beide
    teile_kl = sorted(
        {k for v in (gk.get("teile") or {}).values() if v for k in re.findall(r"\b(I{1,3})\b", str(v))},
        key=lambda k: -KLASSEN_RANG[k],
    )
    rwobj = {
        "wert": o["erschliessung"]["anteil_ew_prozent"],
        "einheit": "%",
        "q": "nvp",
        "seite": o["erschliessung"]["seite"],
    }
    basis = (
        f"Erschlossen = Zellmittelpunkt im Einzugsradius einer Haltestelle nach NVP Tab. 4.2 (Bus "
        f"{'/'.join(str(o['einzugsradius_m']['bus'][k]) for k in ('I', 'II', 'III'))} m, Tram "
        f"{'/'.join(str(o['einzugsradius_m']['tram'][k]) for k in ('I', 'II'))} m je Gebietsklasse). "
        "Eigene Festlegung: Haltestellen mit Bus und Tram zählen mit beiden Radien; S-Bahn, Regionalbahn und "
        "Fähre haben im NVP keinen Radius und zählen nicht. Der NVP bewertet Teilflächen über "
        f"{o['erschliessung']['teilflaeche_min_ew']} EW, hier die ganze Raumeinheit. Brandenburger Haltestellen "
        "bis 1 km außerhalb zählen mit, Berliner nicht. Anteil der Einwohner, ganzzahlig."
    )
    if r.ew_roh[raum] <= o["erschliessung"]["teilflaeche_min_ew"]:
        basis += (
            f" Raumeinheit mit höchstens {o['erschliessung']['teilflaeche_min_ew']} EW: "
            "der NVP fordert hier keine Erschließung."
        )
    aus = []
    for kennzahl, mit_takt, zusatz in (
        ("oepnv_erschliessung", False, ""),
        (
            "oepnv_takt",
            True,
            " Zusätzlich muss die Haltestelle den Soll-Takt der Gebietsklasse in der Hauptverkehrszeit "
            "erreichen (NVP Tab. 4.3, Taktklasse je Haltestelle aus A4, Stichtag 10.11.2026).",
        ),
    ):
        w = {
            "kennzahl": kennzahl,
            "art": "oepnv",
            "zielgruppe": "Einwohner",
            "einheit": "%",
            "methode": "luftlinie",
            "status": "amtlich",
            "richtwert": rwobj,
            "q": "vbb",
            "stand": f"Einwohner: {r.stand_zensus}; Fahrplan Stichtag 10.11.2026",
        }
        if klasse in KLASSEN_RANG:
            w["wert"] = rund(anteil(klasse, mit_takt), 1)
            txt = f"Gebietsklasse {klasse} laut NVP Tab. 4.1 ({gk.get('zuordnung')}). "
        elif teile_kl:
            spanne = [x for x in (rund(anteil(k, mit_takt), 1) for k in teile_kl) if x is not None] or ["k. A."]
            w["wert"] = None
            txt = (
                f"Gebietsklasse gemischt ({', '.join(f'{n}: {k}' for n, k in gk['teile'].items())}); ohne Grenzen der "
                f"NVP-Ortsteile keine eindeutige Klasse. Spanne: {min(spanne)} bis {max(spanne)} % je nach Klasse "
                f"({', '.join(teile_kl)}). "
            )
        else:
            w["wert"] = None
            txt = (
                "Keine Gebietsklasse zugeordnet ("
                + (gk.get("hinweis") or ("Planungsraum" if ebene != "stadtteil" else "offen"))
                + "). "
            )
        w["unsicherheit"] = (
            txt + basis + zusatz + " NVP-Geltung 2019 bis 2023, Nachfolger ungeprüft." + r.neubau(raum, ebene)
        ).strip()
        aus.append(w)
    return aus


def gruen(r: Rechner, raum: str, ebene: str) -> dict | None:
    rw = r.rw
    radius = int(rw["gruen"]["radius_m"]["wert"])
    g_m = r.d["gruen"][r.methode]
    if not g_m:
        return None
    rwobj, status, grund = richtwert(rw, "gruen.m2_je_ew")
    rwobj["einheit"] = "m² je EW"
    paare, unter, ges = [], 0, 0
    for g, z in r.d["zellen"].items():
        if z["raum"] != raum or not z["ew"]:
            continue
        v = g_m.get((g, radius))
        if v is None:
            continue
        paare.append((v, z["ew"]))
        ges += z["ew"]
        if v < rwobj["wert"]:
            unter += z["ew"]
    med = gew_median(paare)
    return {
        "kennzahl": "gruen_m2_je_ew",
        "art": "gruen",
        "zielgruppe": "Einwohner",
        "wert": None if med is None else rund(med, 1),
        "einheit": "m² je EW",
        "methode": r.methode,
        "status": status,
        "richtwert": rwobj,
        "q": "lgb",
        "stand": f"Einwohner: {r.stand_zensus}; ALKIS-Nutzung 05.11.2026",
        "unsicherheit": (
            f"Median über die Zellen der Raumeinheit, nach Einwohnern gewichtet: Grünanlagen und Parks "
            f"(ALKIS) im {radius}-m-Kreis je Einwohner im selben Kreis. "
            + (
                f"{prozent(unter, ges)} % der Einwohner wohnen in Zellen unter {rwobj['wert']} m² je EW. "
                if ges
                else ""
            )
            + f"{grund} Vereinfachte Annäherung: ohne Mindestgröße, Schlossparks zählen mit, "
            "Berliner Grün fehlt am Stadtrand. " + r.basis_u + r.neubau(raum, ebene)
        ).strip(),
    }


def kennzahlen_fussweg(r: Rechner, raum: str, ebene: str) -> list[dict]:
    rw = r.rw
    werte = anteile(r, raum, ebene)
    for art in sorted(r.d["erreichbar"]["fussweg"]):
        if art in rw["gesundheit"]["arten_nur_lage"] or art in ("supermarkt", "spielplatz"):
            w = r.entfernung_median(raum, art, ebene)
            if w:
                werte.append(w)
    w = gruen(r, raum, ebene)
    if w:
        w["q"] = "osm"
        werte.append(w)
    return werte


def prognose_anhaengen(werte: list[dict], raum: str, prog: dict) -> None:
    if not prog:
        return
    p = prog["werte"].get(raum)
    if not p:
        return
    zuordnung = {
        "Kinder unter 6": ("u3", "3_5"),
        "Kinder 6 bis 9": ("6_9",),
        "Kinder 6 bis unter 12": ("6_11",),
        "Einwohner": ("ges",),
    }
    for w in werte:
        for text, gruppen in zuordnung.items():
            if (w.get("zielgruppe") or "").startswith(text) and all(g in p for g in gruppen):
                jahre = sorted(set.intersection(*(set(p[g]) for g in gruppen)))
                w["prognose"] = {
                    "quelle": prog["quelle"],
                    "personen": {str(j): sum(p[g][j] for g in gruppen) for j in jahre},
                }


# ---------------------------------------------------------------------------------------------- Dateien
def zellen_reihenfolge() -> list[str]:
    text = (DATEN / "zellen.js").read_text(encoding="utf-8")
    return ZELL_ID.findall(text)


def erreichbar_datei(d: dict, rw: dict, methode: str, ids: list[str]) -> dict | None:
    werte = d["erreichbar"][methode]
    if not werte:
        return None
    rd = rw["planer"]["rundung_meter"]
    arten = sorted(werte)
    ew = {g: z["ew"] for g, z in d["zellen"].items()}
    aus = {a: [rund(werte[a].get(g), rd) if ew.get(g) else None for g in ids] for a in arten}
    if methode == "luftlinie":
        q = {k: QUELLEN[k] for k in ("zensus", "mbjs", "lgb")}
        hinweis = (
            "Luftlinie vom Mittelpunkt der 100-m-Zelle zum nächsten Standort je Art, auf "
            f"{rd} m gerundet, aussagekräftig auf rund 50 m. null = Zelle ohne Einwohner. Standorte in "
            "Brandenburg außerhalb der Stadt zählen mit, Berlin nicht: am Stadtrand teils nur Obergrenze. "
            "gruen = Abstand zum Rand der nächsten Grünanlage bzw. des nächsten Parks (ALKIS)."
        )
    else:
        q = {k: QUELLEN[k] for k in ("zensus", "mbjs", "lgb", "osm")}
        hinweis = (
            f"Fußweg über das Wegenetz vom Mittelpunkt der 100-m-Zelle, auf {rd} m gerundet. null = Zelle ohne "
            "Einwohner oder ohne Netzanschluss."
        )
    return {
        "stand": date.today().isoformat(),
        "hinweis": hinweis,
        "methode": methode,
        "einheit": "m",
        "quellen": q,
        "arten": arten,
        "anzahl": len(ids),
        "erste_id": ids[0],
        "letzte_id": ids[-1],
        "schluessel": "zellen.js-Reihenfolge",
        "werte": aus,
    }


def einrichtungen_datei(d: dict) -> dict:
    feats = []
    for e in d["einrichtungen"]:
        q = "lgb" if e["id"].startswith("alkis:") else "mbjs"
        feats.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(e["lon"], 5), round(e["lat"], 5)]},
                "properties": {
                    "id": e["id"],
                    "art": e["art"],
                    "unterart": e["unterart"],
                    "q": q,
                    "name": e["name"] if q == "mbjs" else None,
                    "plaetze": e["plaetze"],
                    "schueler": e["schueler"],
                    "schueler_stand": e["schueler_stand"],
                    "status": e["status"],
                    "in_potsdam": bool(e["in_potsdam"]),
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "stand": date.today().isoformat(),
        "hinweis": (
            "Kitas, Horte und Schulen laut MBJS (Plätze je Kita einmal am Hauptstandort, weitere Häuser "
            "ohne Plätze), Gemeinbedarf aus ALKIS nur als Lage ohne Kapazität. Ohne Adresse und Kontakt."
        ),
        "quellen": {k: QUELLEN[k] for k in ("mbjs", "lgb")},
        "features": feats,
    }


def einrichtungen_odbl_datei(d: dict) -> dict | None:
    if not d["osm_poi"]:
        return None
    feats = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(p["lon"], 5), round(p["lat"], 5)]},
            "properties": {"id": p["id"], "art": p["art"], "unterart": p["unterart"], "q": "osm"},
        }
        for p in d["osm_poi"]
    ]
    return {
        "type": "FeatureCollection",
        "stand": date.today().isoformat(),
        "hinweis": "Nur Lage, ohne Namen, Adresse und Kontakt. Keine Versorgungsaussage.",
        "quellen": {"osm": QUELLEN["osm"]},
        "features": feats,
    }


def planer_datei(d: dict, rw: dict, methode: str, rand: dict, prog: dict, meldungen: list) -> dict | None:
    if methode == "fussweg" and not d["erreichbar"]["fussweg"]:
        return None
    r = Rechner(d, rw, methode, rand)
    ebene = d["raumebene"]
    raeume = {}
    for nr, name in d["raeume"].items():
        werte = kennzahlen_luftlinie(r, nr, ebene) if methode == "luftlinie" else kennzahlen_fussweg(r, nr, ebene)
        prognose_anhaengen(werte, nr, prog)
        raeume[nr] = {"name": name, "ew": rund(r.ew_roh[nr], r.rd_ew), "werte": werte}
    meldungen.append(
        f"{methode}: {len(raeume)} Raumeinheiten, {sum(len(x['werte']) for x in raeume.values())} Werte, "
        f"{r.geheim_null} Werte wegen Geheimhaltung null"
    )
    benutzt = {w["q"] for x in raeume.values() for w in x["werte"]} | {"zensus"}
    benutzt_rw = {w["richtwert"]["q"] for x in raeume.values() for w in x["werte"] if "richtwert" in w}
    quellen = {k: QUELLEN[k] for k in sorted(benutzt)}
    quellen.update({k: DOKUMENTE[k] for k in sorted(benutzt_rw)})
    hinweis = (
        f"Je {'Planungsraum' if ebene == 'planungsraum' else 'Stadtteil (Planungsräume fehlen noch)'}. "
        "Kinder und Einwohner: Zensus 2022, Stichtag 15.05.2022; Neubaugebiete danach (u. a. Krampnitz, "
        "Bornstedter Feld, Golm) fehlen. Einwohner auf "
        f"{rw['geheimhaltung']['rundung_ew']} gerundet; Werte aus feinen Altersklassen nur bei Raumeinheiten ab "
        f"{rw['geheimhaltung']['min_ew_raumeinheit']} Einwohnern. Status amtlich: Maßstab aus einem Potsdamer "
        "Dokument mit gelesener Fundstelle bzw. bei Werten ohne Maßstab nur amtliche Daten; orientierung: "
        "Maßstab ohne Primärbeleg, ungelesene Fundstelle oder Berliner Methode."
    )
    if methode == "luftlinie":
        hinweis += " Fußweg-Werte stehen in einer eigenen Datei unter eigener Lizenz."
    return {
        "stand": date.today().isoformat(),
        "raumebene": ebene,
        "rundung": {"ew": rw["geheimhaltung"]["rundung_ew"]},
        "hinweis": hinweis,
        "quellen": quellen,
        "raeume": raeume,
    }


def main() -> int:
    import psycopg
    import yaml

    rw = yaml.safe_load((WURZEL / "config" / "richtwerte.yaml").read_text(encoding="utf-8"))
    if rw["gruen_definition"].get("status") != "festgelegt":
        raise SystemExit("config/richtwerte.yaml: gruen_definition.status ist nicht festgelegt")
    with psycopg.connect() as con, con.cursor() as cur:
        con.read_only = True
        cur.execute("SELECT current_user")
        rolle = cur.fetchone()[0]
        if rolle != "mosidi_lesen":
            raise SystemExit(f"Erwartet die Leserolle mosidi_lesen, verbunden als {rolle}")
        d = lesen(cur)
    ids = zellen_reihenfolge()
    meldungen: list[str] = [f"Raumebene: {d['raumebene']} ({len(d['raeume'])} Raumeinheiten)"]
    rand = rand_unsicher()  # gilt nur für Luftlinie (A5a); der Fußweg hat keine Randliste
    prog = prognose_lesen(rw, d["raumebene"], meldungen)
    geschrieben, fehlt = [], []
    for name, var, inhalt, kopf in (
        ("planer.js", "KIEZ_PLANER", planer_datei(d, rw, "luftlinie", rand, prog, meldungen), ""),
        ("erreichbar.js", "KIEZ_ERREICHBAR", erreichbar_datei(d, rw, "luftlinie", ids), ""),
        ("einrichtungen.js", "KIEZ_EINRICHTUNGEN", einrichtungen_datei(d), ""),
        ("planer_fuss_odbl.js", "KIEZ_PLANER_FUSS", planer_datei(d, rw, "fussweg", {}, prog, meldungen), ODBL_KOPF),
        ("erreichbar_fuss_odbl.js", "KIEZ_ERREICHBAR_FUSS", erreichbar_datei(d, rw, "fussweg", ids), ODBL_KOPF),
        ("einrichtungen_odbl.js", "KIEZ_EINRICHTUNGEN_ODBL", einrichtungen_odbl_datei(d), ODBL_KOPF),
    ):
        pfad = DATEN / name
        if inhalt is None:
            fehlt.append(name)
            if pfad.exists():
                pfad.unlink()  # alte Datei nicht stehen lassen, wenn die Quelle leer ist
            continue
        js_schreiben(pfad, var, inhalt, kopf)
        geschrieben.append(name)
    meldungen.append("geschrieben: " + ", ".join(geschrieben))
    if fehlt:
        meldungen.append(
            "nicht geschrieben (Quelle leer: auswertung.zelle_erreichbar/zelle_gruen methode fussweg "
            "bzw. auswertung.osm_poi, wartet auf A3/A5b): " + ", ".join(fehlt)
        )
    print("\n".join(meldungen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
