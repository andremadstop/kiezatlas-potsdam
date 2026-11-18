"""Erzeugt daten/ort.js (window.KIEZ_ORT) aus der Ortskonfiguration: alles, was die Seiten über den Ort wissen.

Name und Stadt je Sprache, Grundkarte und Luftbild samt Bildzeile, Gliederung (Gruppen mit Farbton, Stadtteile
mit Anzeige- und Lokativform je Sprache), Kartenausschnitt, Themen der Zellkarte, Zitierzeile, kanonische
Basis-URL und Seitenliste. Die Seiten lesen nur diese Datei; ortsgebundene Werte stehen nicht im JavaScript.

Quelle: $KIEZ_CONFIG oder die Ortskonfiguration unter config/ (skripte/ort_konfig.py). Ausgabe ist deterministisch (kein Datum,
keine Uhrzeit), damit --pruefen byte-gleich vergleichen kann.

Aufruf:
  python -I skripte/31_ort.py                 daten/ort.js schreiben
  python -I skripte/31_ort.py --aus DATEI     an anderen Ort schreiben (Gegenprobe Potsdam)
  python -I skripte/31_ort.py --pruefen       erzeugen und mit der eingecheckten Datei vergleichen (Rückgabe 1 bei Abweichung)
Kein Netz, keine Datenbank.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "skripte"))   # python -I lässt das Skriptverzeichnis weg
import ort_konfig  # noqa: E402

PFLICHT_SPRACHFELDER = ("name", "stadt", "stadt_lokativ", "ganze_stadt", "stadt_amtlich", "stadt_art", "zitierzeile")
PLATZHALTER = re.compile(r"\{(\w+)\}")


class Fehler(Exception):
    pass


def sprachwert(wert, sprachen: list[str], ort: str) -> dict | str:
    """Sprachabhängiger Wert: Objekt mit genau den konfigurierten Sprachen; reine Zeichenkette gilt für alle."""
    if isinstance(wert, str):
        return wert
    if not isinstance(wert, dict):
        raise Fehler(f"{ort}: erwartet Zeichenkette oder Objekt je Sprache, ist {type(wert).__name__}")
    fehlt = [s for s in sprachen if not isinstance(wert.get(s), str) or not wert[s].strip()]
    zuviel = sorted(set(wert) - set(sprachen))
    if fehlt or zuviel:
        raise Fehler(f"{ort}: Sprachen fehlen {fehlt} oder sind nicht konfiguriert {zuviel}")
    return {s: wert[s] for s in sprachen}


def muster_fuellen(muster: dict, felder: dict, ort: str) -> dict:
    aus = {}
    for s, m in muster.items():
        namen = set(PLATZHALTER.findall(m))
        if namen - set(felder):
            raise Fehler(f"{ort}: unbekannte Platzhalter {sorted(namen - set(felder))}")
        aus[s] = PLATZHALTER.sub(lambda x: str(felder[x.group(1)]), m)
    return aus


def erzeugen(k: dict, quelle: Path) -> dict:
    sprachen = k.get("sprachen")
    if not isinstance(sprachen, list) or not sprachen or len(set(sprachen)) != len(sprachen):
        raise Fehler("sprachen: Liste ohne Doppelte erwartet")
    for s in sprachen:
        if s not in ("pl", "en", "de"):
            raise Fehler(f"sprachen: {s!r} nicht vorgesehen (pl, en, de)")
    basis = k.get("basis_url", "")
    if not re.fullmatch(r"https://[^\s]+/", basis):
        raise Fehler("basis_url: https://…/ mit Schrägstrich am Ende erwartet")

    ort = {"ort": k["ort"], "sprachen": sprachen, "standardsprache": sprachen[0], "basis_url": basis}
    for f in PFLICHT_SPRACHFELDER:
        ort[f] = sprachwert(k.get(f), sprachen, f)
    ort["herausgeber"] = k["herausgeber"]
    ort["meldeweg"] = k["meldeweg"]

    ka = k.get("karte") or {}
    for f in ("mitte", "haus_ziel"):
        v = ka.get(f)
        if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)):
            raise Fehler(f"karte.{f}: [Länge, Breite] erwartet")
    r = ka.get("rahmen")
    if not (isinstance(r, list) and len(r) == 4 and r[0] < r[2] and r[1] < r[3]):
        raise Fehler("karte.rahmen: [West, Süd, Ost, Nord] erwartet")
    for f in ("mitte", "haus_ziel"):
        x, y = ka[f]
        if not (r[0] <= x <= r[2] and r[1] <= y <= r[3]):
            raise Fehler(f"karte.{f} liegt außerhalb von karte.rahmen")
    for f in ("grundkarte", "luftbild"):
        q = ka.get(f)
        if q is not None and not (isinstance(q, dict) and q.get("type") and q.get("attribution")):
            raise Fehler(f"karte.{f}: MapLibre-Quelle mit type und attribution oder null erwartet")
    ort["karte"] = {"mitte": ka["mitte"], "rahmen": r, "haus_ziel": ka["haus_ziel"],
                    "grundkarte": ka.get("grundkarte"), "luftbild": ka.get("luftbild"),
                    "teile_attribution": sprachwert(ka.get("teile_attribution"), sprachen, "karte.teile_attribution"),
                    "teile_bildzeile": sprachwert(ka.get("teile_bildzeile"), sprachen, "karte.teile_bildzeile")}

    g = k.get("gliederung") or {}
    gruppen = g.get("gruppen") or []
    ids = [x["id"] for x in gruppen]
    if len(set(ids)) != len(ids) or not all(isinstance(x.get("ton"), int) and 0 <= x["ton"] < 360 for x in gruppen):
        raise Fehler("gliederung.gruppen: id eindeutig, ton 0 … 359 erwartet")
    anzeige = sprachwert(g.get("anzeige_muster"), sprachen, "gliederung.anzeige_muster")
    lokativ = sprachwert(g.get("lokativ_muster"), sprachen, "gliederung.lokativ_muster")
    teile = []
    for t in g.get("teile") or []:
        if t.get("gruppe") not in ids:
            raise Fehler(f"gliederung.teile {t.get('nr')}: Gruppe {t.get('gruppe')!r} unbekannt")
        if not re.fullmatch(r"\d{2}", str(t.get("nr", ""))):
            raise Fehler(f"gliederung.teile {t.get('nr')!r}: nr zweistellig erwartet")
        felder = {"nr": t["nr"], "roemisch": t.get("roemisch", ""), "name": t["name"]}
        teile.append({"nr": t["nr"], "roemisch": t.get("roemisch"), "name": t["name"], "gruppe": t["gruppe"],
                      "anzeige": muster_fuellen(anzeige, felder, f"Stadtteil {t['nr']}"),
                      "lokativ": muster_fuellen(lokativ, felder, f"Stadtteil {t['nr']}")})
    nrs = [t["nr"] for t in teile]
    if len(set(nrs)) != len(nrs):
        raise Fehler("gliederung.teile: doppelte nr")
    ort["gliederung"] = {"einheit": sprachwert(g.get("einheit"), sprachen, "gliederung.einheit"),
                         "einheit_mehrzahl": sprachwert(g.get("einheit_mehrzahl"), sprachen, "gliederung.einheit_mehrzahl"),
                         "gruppe": sprachwert(g.get("gruppe"), sprachen, "gliederung.gruppe"),
                         "zuordnung_geprueft": bool(g.get("zuordnung_geprueft")),
                         "anzeige_muster": anzeige, "lokativ_muster": lokativ,
                         "gruppen": [{"id": x["id"], "ton": x["ton"], "name": x["name"]} for x in gruppen],
                         "teile": teile}

    themen = []
    for i, t in enumerate(k.get("themen") or []):
        if not re.fullmatch(r"[a-z][a-z0-9_]*", t.get("id", "")) or not re.fullmatch(r"[a-z0-9_]+", t.get("h", "")):
            raise Fehler(f"themen[{i}]: id und h aus Kleinbuchstaben, Ziffern, _ erwartet")
        e = {"id": t["id"], "h": t["h"], "kurz": sprachwert(t.get("kurz"), sprachen, f"themen.{t['id']}.kurz"),
             "name": sprachwert(t.get("name"), sprachen, f"themen.{t['id']}.name")}
        for f in ("einheit", "quelle"):
            if f in t:
                e[f] = sprachwert(t[f], sprachen, f"themen.{t['id']}.{f}")
        if "nenner" in t:
            e["nenner"] = t["nenner"]
        if "mindestfallzahl" in t:
            if not isinstance(t["mindestfallzahl"], int) or isinstance(t["mindestfallzahl"], bool) or t["mindestfallzahl"] < 1:
                raise Fehler(f"themen[{i}]: mindestfallzahl als ganze Zahl ab 1 erwartet")
            e["mindestfallzahl"] = t["mindestfallzahl"]
        themen.append(e)
    if not themen or themen[0]["id"] != "stadtteile":
        raise Fehler("themen: erstes Thema muss stadtteile sein (Grundansicht)")
    for f in ("id", "h"):
        werte = [t[f] for t in themen]
        if len(set(werte)) != len(werte):
            raise Fehler(f"themen: {f} doppelt")
    ort["themen"] = themen

    seiten = [str(s) for s in k.get("seiten") or []]
    if len(set(seiten)) != len(seiten) or "index" not in seiten:
        raise Fehler("seiten: Liste ohne Doppelte mit index erwartet")
    ort["seiten"] = seiten
    rel = quelle.relative_to(WURZEL).as_posix() if quelle.is_relative_to(WURZEL) else quelle.name
    ort["herkunft"] = {"datei": rel, "sha256": hashlib.sha256(quelle.read_bytes()).hexdigest(),
                       "skript": "skripte/31_ort.py"}
    return ort


def text(ort: dict) -> str:
    kopf = (f"/* Ortskonfiguration der Seiten, erzeugt von skripte/31_ort.py aus {ort['herkunft']['datei']}. "
            "Nicht von Hand ändern; Vertrag: daten/schema/ort.json. */\n")
    return kopf + "window.KIEZ_ORT=" + json.dumps(ort, ensure_ascii=False, separators=(",", ":")) + ";\n"


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--aus", type=Path, default=WURZEL / "daten" / "ort.js")
    a.add_argument("--pruefen", action="store_true")
    o = a.parse_args()
    try:
        neu = text(erzeugen(ort_konfig.lade(), ort_konfig.pfad()))
    except (Fehler, KeyError) as e:
        print(f"{ort_konfig.pfad()}: {e}")
        return 1
    if o.pruefen:
        alt = o.aus.read_text(encoding="utf-8") if o.aus.exists() else ""
        if alt == neu:
            print(f"  ok    {o.aus.name} entspricht {ort_konfig.pfad().name} ({len(neu.encode())} Byte)")
            return 0
        print(f"  FEHLT {o.aus.name} ist nicht aktuell: python -I skripte/31_ort.py neu ausführen")
        return 1
    o.aus.parent.mkdir(parents=True, exist_ok=True)
    o.aus.write_text(neu, encoding="utf-8")
    print(f"{o.aus}  {len(neu.encode())} Byte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
