"""Prüfgerüst Daten (Paket P0): Summen, Kontrollfelder, Datenverträge, Lizenz- und Datenschutzgrenzen.

Liest nur Dateien unter daten/ (kein Netz, keine Datenbank). Prüft:
  1. Summen gegen daten/kennzahlen.json: Einwohner und Zellen je Stadtteil und Stadt aus zellen.js,
     Gebäude je Stadtteil aus daten/gebaeude/<nr>.js, kontrolle-Felder, Anteile der Kacheln.
  2. Jede daten/**/*.js gegen ihr Schema aus daten/schema/*.json (x-datei, x-global). Eine Datei ohne
     Schema ist ein Befund. Werte in Zellreihenfolge (x-laenge) müssen so lang sein wie zellen.js.
  3. Jede Fixture unter daten/fixtures/ gegen dasselbe Schema, mit fixture: true; echte Dateien ohne.
  4. ODbL als Dateigrenze: *_odbl-Dateien tragen den ODbL-Vermerk im Kopf; alle anderen enthalten
     weder OpenStreetMap/ODbL noch methode "fussweg" noch osm_id.
  5. Keine Adress- oder Kontaktfelder (strasse, hausnr, adresse, telefon, fax, email) in daten/.
  6. Keine feinen Zensusklassen als Feldnamen (i_u3 … st_sonst aus public.zensus_struktur) in daten/.

Aufruf: python -I pruefen/daten.py [--nur-fixtures]   Rückgabe 0 = 0 Abweichungen, 1 = Befund.
"""
from __future__ import annotations

import fnmatch
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "daten"
SCHEMA = DATEN / "schema"
FIXTURES = DATEN / "fixtures"

ADRESSFELDER = {"strasse", "straße", "hausnr", "hausnummer", "adresse", "street", "telefon", "telefonnummer",
                "fax", "faxnummer", "email", "e_mail", "dienst_email", "homepage"}
FEINE_KLASSEN = {f"i_{s}" for s in ("u3", "3_5", "6_9", "10_15", "16_18", "19_24", "25_39", "40_59", "60_66",
                                    "67_74", "75p")} | {
    "hh_1", "hh_2", "hh_3", "hh_4", "hh_5", "hh_6p", "ht_single", "ht_paar_ohne", "ht_paar_mit", "ht_alleinerz",
    "ht_mehrpers", "kf_ehe_ohne", "kf_ehe_u18", "kf_ehe_ab18", "kf_lp_ohne", "kf_lp_u18", "kf_lp_ab18",
    "kf_nel_ohne", "kf_nel_u18", "kf_nel_ab18", "kf_vater_u18", "kf_vater_ab18", "kf_mutter_u18",
    "kf_mutter_ab18", "sen_nur", "sen_mit", "sen_ohne", "st_de", "st_ausland", "st_eu27", "st_europa",
    "st_welt", "st_sonst"}
OSM_SPUR = re.compile(r"OpenStreetMap|ODbL|\"methode\":\"fussweg\"|\"osm_id\"", re.I)

befunde: list[str] = []


def pruef(ok: bool, text: str) -> bool:
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        befunde.append(text)
    return ok


# ---------------------------------------------------------------- JS-Datei lesen
def js_lesen(pfad: Path) -> tuple[str, str, object]:
    """window.NAME=<JSON>; mit optionalem Kommentar davor. Rückgabe: Kopf, Name, Inhalt."""
    text = pfad.read_text(encoding="utf-8")
    m = re.search(r"window\.([A-Za-z0-9_]+)\s*=\s*", text)
    if not m:
        raise ValueError("keine Zuweisung window.NAME=")
    rumpf = text[m.end():].rstrip().rstrip(";")
    return text[:m.start()], m.group(1), json.loads(rumpf)


# ---------------------------------------------------------------- kleines JSON-Schema (Teilmenge)
TYPEN = {"string": str, "boolean": bool, "object": dict, "array": list}


def typ_passt(wert, typ: str) -> bool:
    if typ == "null":
        return wert is None
    if typ == "integer":
        return isinstance(wert, int) and not isinstance(wert, bool)
    if typ == "number":
        return isinstance(wert, (int, float)) and not isinstance(wert, bool)
    return isinstance(wert, TYPEN[typ])


def validieren(wert, s: dict, wurzel: dict, ort: str, fehler: list, kontext: dict) -> None:
    if len(fehler) > 20:
        return
    if "$ref" in s:
        teil = s["$ref"].removeprefix("#/").split("/")
        ziel = wurzel
        for t in teil:
            ziel = ziel[t]
        return validieren(wert, ziel, wurzel, ort, fehler, kontext)
    if "anyOf" in s:
        if not any(not _probe(wert, x, wurzel, kontext) for x in s["anyOf"]):
            fehler.append(f"{ort}: passt zu keiner Variante")
        return
    if "const" in s and wert != s["const"]:
        fehler.append(f"{ort}: erwartet {s['const']!r}, ist {wert!r}"[:200])
        return
    if "enum" in s and wert not in s["enum"]:
        fehler.append(f"{ort}: {wert!r} nicht in {s['enum']}"[:200])
        return
    if "type" in s:
        typen = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(typ_passt(wert, t) for t in typen):
            fehler.append(f"{ort}: Typ {type(wert).__name__}, erwartet {typen}")
            return
    if isinstance(wert, str):
        if "pattern" in s and not re.search(s["pattern"], wert):
            fehler.append(f"{ort}: {wert!r} passt nicht zu {s['pattern']}"[:200])
        if len(wert) < s.get("minLength", 0):
            fehler.append(f"{ort}: zu kurz")
    if isinstance(wert, (int, float)) and not isinstance(wert, bool):
        if "minimum" in s and wert < s["minimum"]:
            fehler.append(f"{ort}: {wert} < {s['minimum']}")
        if "maximum" in s and wert > s["maximum"]:
            fehler.append(f"{ort}: {wert} > {s['maximum']}")
    if isinstance(wert, list):
        if len(wert) < s.get("minItems", 0) or len(wert) > s.get("maxItems", 1 << 62):
            fehler.append(f"{ort}: Länge {len(wert)} außerhalb der Grenzen")
        if "x-laenge" in s and kontext.get(s["x-laenge"]) is not None and len(wert) != kontext[s["x-laenge"]]:
            fehler.append(f"{ort}: Länge {len(wert)}, erwartet {s['x-laenge']} = {kontext[s['x-laenge']]}")
        if "items" in s:
            for i, x in enumerate(wert):
                validieren(x, s["items"], wurzel, f"{ort}[{i}]", fehler, kontext)
    if isinstance(wert, dict):
        for r in s.get("required", []):
            if r not in wert:
                fehler.append(f"{ort}: Pflichtfeld {r} fehlt")
        if len(wert) < s.get("minProperties", 0):
            fehler.append(f"{ort}: zu wenige Einträge")
        props, muster = s.get("properties", {}), s.get("patternProperties", {})
        for k, v in wert.items():
            if k in props:
                validieren(v, props[k], wurzel, f"{ort}.{k}", fehler, kontext)
                continue
            treffer = [ps for p, ps in muster.items() if re.search(p, k)]
            for ps in treffer:
                validieren(v, ps, wurzel, f"{ort}.{k}", fehler, kontext)
            if treffer:
                continue
            zusatz = s.get("additionalProperties", True)
            if zusatz is False:
                fehler.append(f"{ort}: Feld {k} nicht im Vertrag")
            elif isinstance(zusatz, dict):
                validieren(v, zusatz, wurzel, f"{ort}.{k}", fehler, kontext)


def _probe(wert, s, wurzel, kontext) -> list:
    f: list = []
    validieren(wert, s, wurzel, "", f, kontext)
    return f


def schluessel(obj, aus: set) -> set:
    if isinstance(obj, dict):
        for k, v in obj.items():
            aus.add(k)
            schluessel(v, aus)
    elif isinstance(obj, list):
        for v in obj:
            schluessel(v, aus)
    return aus


# ---------------------------------------------------------------- Prüfungen
def schemas() -> list[tuple[Path, dict]]:
    return [(p, json.loads(p.read_text(encoding="utf-8"))) for p in sorted(SCHEMA.glob("*.json"))]


def datei_pruefen(pfad: Path, rel: str, liste, kontext: dict, fixture: bool) -> None:
    passend = [(p, s) for p, s in liste if fnmatch.fnmatch(rel, s["x-datei"])]
    if len(passend) != 1:
        grund = "kein Schema in daten/schema/" if not passend else "mehrere Schemas"
        pruef(False, f"{'Fixture ' if fixture else ''}{rel}: {grund}")
        return
    sp, s = passend[0]
    try:
        kopf, name, inhalt = js_lesen(pfad)
    except (ValueError, json.JSONDecodeError) as e:
        pruef(False, f"{rel}: nicht lesbar ({e})"[:200])
        return
    fehler: list[str] = []
    if not re.search(s["x-global"], name):
        fehler.append(f"globaler Name {name} passt nicht zu {s['x-global']}")
    validieren(inhalt, s, s, "$", fehler, kontext)
    if isinstance(inhalt, dict) and inhalt.get("schluessel") == "zellen.js-Reihenfolge":
        for k in ("anzahl", "erste_id", "letzte_id"):
            if inhalt.get(k) != kontext.get(k):
                fehler.append(f"{k} = {inhalt.get(k)!r}, zellen.js hat {kontext.get(k)!r}")
    if fixture and not (isinstance(inhalt, dict) and inhalt.get("fixture") is True):
        fehler.append("Fixture ohne fixture: true")
    if not fixture and isinstance(inhalt, dict) and "fixture" in inhalt:
        fehler.append("echte Datei mit Feld fixture")
    text = pfad.read_text(encoding="utf-8")
    if "_odbl" in pfad.name:
        if not (s.get("x-odbl") and "ODbL" in kopf and "OpenStreetMap" in kopf):
            fehler.append("_odbl-Datei ohne ODbL-Vermerk im Kopf oder Schema ohne x-odbl")
    elif OSM_SPUR.search(text):
        fehler.append("OSM/ODbL-Spur in einer Datei ohne _odbl im Namen")
    if s.get("x-odbl") and "_odbl" not in pfad.name:
        fehler.append("ODbL-Vertrag, aber Dateiname ohne _odbl")
    k = schluessel(inhalt, set())
    if k & ADRESSFELDER:
        fehler.append(f"Adress- oder Kontaktfeld: {sorted(k & ADRESSFELDER)}")
    if k & FEINE_KLASSEN:
        fehler.append(f"feine Zensusklasse als Feld: {sorted(k & FEINE_KLASSEN)[:5]}")
    zusatz = (": " + "; ".join(fehler[:4])) if fehler else ""
    pruef(not fehler, f"{'Fixture ' if fixture else ''}{rel}: Vertrag {sp.name}{zusatz}")


def summen(kontext: dict) -> None:
    K = json.loads((DATEN / "kennzahlen.json").read_text(encoding="utf-8"))
    _, _, K_js = js_lesen(DATEN / "kennzahlen.js")
    pruef(K_js == K, "kennzahlen.js und kennzahlen.json gleich")
    _, _, Z = js_lesen(DATEN / "zellen.js")
    _, _, ST = js_lesen(DATEN / "stadtteile.js")
    feats = Z["features"]
    kontext["anzahl"] = len(feats)
    ids = [f["properties"]["id"] for f in feats]
    pruef(ids == sorted(ids), "zellen.js nach gitter_id sortiert (Grundlage der Zellreihenfolge)")
    pruef(len(set(ids)) == len(ids), f"zellen.js ohne doppelte gitter_id ({len(ids)})")
    ew = defaultdict(int)
    n = defaultdict(int)
    for f in feats:
        p = f["properties"]
        ew[p["st"]] += p["ew"] or 0
        n[p["st"]] += 1

    def kachel(G, i):
        return next(k for k in G["kacheln"] if k["id"] == i)
    stadt_ew = kachel(K["stadt"], "einwohner")["wert"]
    pruef(sum(ew.values()) == stadt_ew, f"Σ ew über zellen.js = Kachel Einwohner Stadt ({sum(ew.values())} = {stadt_ew})")
    pruef(len(feats) == K["stadt"]["zellen"], f"Zahl der Zellen = stadt.zellen ({len(feats)} = {K['stadt']['zellen']})")
    abw = [nr for nr, G in K["stadtteile"].items()
           if kachel(G, "einwohner")["wert"] != ew.get(nr, 0) or G["zellen"] != n.get(nr, 0)]
    pruef(not abw, f"Einwohner und Zellen je Stadtteil aus zellen.js = kennzahlen "
                   f"({len(K['stadtteile'])} Stadtteile, Abweichungen: {abw})")
    nrs = {f["properties"]["nr"] for f in ST["features"]}
    pruef(nrs == set(K["stadtteile"]), f"Stadtteile in stadtteile.js = kennzahlen ({len(nrs)})")
    # Anteile der Kacheln = zaehler/nenner
    falsch = []
    for nr, G in [("stadt", K["stadt"]), *K["stadtteile"].items()]:
        for k in G["kacheln"]:
            if k.get("anzeige") == "anteil" and k.get("nenner"):
                if abs(round(100 * k["zaehler"] / k["nenner"], 1) - k["wert"]) > 0.05:
                    falsch.append(f"{nr}/{k['id']}")
    pruef(not falsch, f"Anteile der Kacheln = zaehler/nenner (Abweichungen: {falsch[:5]})")
    # Summe der Stadtteile = Stadt
    for key in ("einwohner",):
        s = sum(kachel(G, key)["wert"] for G in K["stadtteile"].values())
        pruef(s == kachel(K["stadt"], key)["wert"], f"Σ Stadtteile {key} = Stadt ({s})")
    # Gebäude je Stadtteil und kontrolle
    geb = {}
    for p in sorted((DATEN / "gebaeude").glob("*.js")):
        _, name, G = js_lesen(p)
        geb[p.stem] = len(G["features"])
    abw = [nr for nr, G in K["stadtteile"].items() if G["gebaeude"].get("anzahl", 0) != geb.get(nr, 0)]
    pruef(not abw, f"Gebäude je Stadtteil in gebaeude/<nr>.js = kennzahlen (Abweichungen: {abw})")
    kontrolle = K["kontrolle"]
    pruef(sum(geb.values()) == kontrolle["gebaeude_in_potsdam"] == K["stadt"]["gebaeude"]["anzahl"],
          f"Σ Gebäude = kontrolle.gebaeude_in_potsdam = stadt.gebaeude.anzahl ({sum(geb.values())})")
    pruef(kontrolle["gebaeude_im_rechteck"] >= kontrolle["gebaeude_in_potsdam"],
          f"kontrolle: Gebäude im Rechteck ({kontrolle['gebaeude_im_rechteck']}) ≥ in Potsdam")
    gf = K.get("grenzfall", {}).get("stadt")
    if gf:
        pruef(gf["mittelpunkt"] == stadt_ew, f"grenzfall.stadt.mittelpunkt = Einwohner Stadt ({gf['mittelpunkt']})")
    kontext["erste_id"], kontext["letzte_id"] = ids[0], ids[-1]


def main() -> int:
    nur_fix = "--nur-fixtures" in sys.argv
    kontext: dict = {}
    print("Summen und Kontrollen gegen kennzahlen.json")
    summen(kontext)
    liste = schemas()
    print(f"Datenverträge ({len(liste)} Schemas)")
    if not nur_fix:
        for p in sorted(DATEN.rglob("*.js")):
            rel = p.relative_to(DATEN).as_posix()
            if rel.startswith("fixtures/"):
                continue
            datei_pruefen(p, rel, liste, kontext, fixture=False)
    print("Fixtures")
    for p in sorted(FIXTURES.rglob("*.js")) if FIXTURES.exists() else []:
        datei_pruefen(p, p.relative_to(FIXTURES).as_posix(), liste, kontext, fixture=True)
    print(f"\n{len(befunde)} Abweichung(en)" if befunde else "\n0 Abweichungen")
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
