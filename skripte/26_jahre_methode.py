#!/usr/bin/env python3
"""Kiezatlas Potsdam, B5 Zweig 2: Kennzahlen der Gebäude-Schätzung für die Seiten „Bauzeiten“.

Schreibt daten/jahre_methode.js (window.KIEZ_JAHRE_METHODE). Liest nur Dateien, kein Netz, keine Datenbank:
- daten/jahre/<nr>.js (B4): Zahl der Gebäude je Stufe und je Status g, gezählt
- berichte/B4_holdout.md (B4): Abdeckung, Rücktest, Gegenprobe, Summenvergleich, Baualter-Statistik der LHP (H4),
  gelesen aus den Tabellen

Die Abdeckung im Bericht muss mit der Zählung aus den Dateien übereinstimmen, sonst bricht das Skript ab
(Bericht und Dateien aus verschiedenen Läufen). Der SHA256 des Berichts steht in der Ausgabe.
24_jahre_kaskade.py wird nicht gestartet (B4 gehört der Lauf).

Aufruf:  python3 -I skripte/26_jahre_methode.py [--pruefen]
         --pruefen: nichts schreiben, nur vergleichen, ob daten/jahre_methode.js aktuell ist (Rückgabe 1 sonst).
"""
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
BERICHT = WURZEL / "berichte" / "B4_holdout.md"
JAHRE = WURZEL / "daten" / "jahre"
ZIEL = WURZEL / "daten" / "jahre_methode.js"
STUFEN = {1: "genaues Jahr", 2: "Luftbildklammer", 3: "Blocktyp Großsiedlung", 4: "Zensus-Verteilung",
          5: "Nachbarn", 6: "nicht datiert"}


def fehler(text: str) -> None:
    print("FEHLER: " + text, file=sys.stderr)
    sys.exit(2)


def zahl(t: str):
    """„17.337“ → 17337, „3,5“ → 3.5, „+41 %“ → 41, „–“ → None."""
    t = t.strip().replace("−", "-").replace("%", "").replace("J.", "").strip()
    if t in ("", "–", "-"):
        return None
    t = t.replace(".", "").replace(",", ".").replace("+", "")
    try:
        v = float(t)
    except ValueError:
        fehler(f"keine Zahl: {t!r}")
    return int(v) if v.is_integer() else v


def treffer(t: str):
    """„125 von 169 (74,0 %)“ → (125, 169, 74.0); „–“ → (None, None, None)."""
    t = t.strip()
    if t in ("–", "-"):
        return None, None, None
    m = re.fullmatch(r"([\d.]+) von ([\d.]+) \(([\d,]+) %\)", t)
    if not m:
        fehler(f"Trefferangabe nicht lesbar: {t!r}")
    return zahl(m.group(1)), zahl(m.group(2)), zahl(m.group(3))


def abschnitte(text: str) -> dict:
    """Überschrift → Liste der Tabellen darunter (je Tabelle: Kopf, Zeilen), bis zur nächsten Überschrift."""
    aus, kopf, tab = {}, None, None
    for zeile in text.splitlines():
        if zeile.startswith("#"):
            kopf, tab = zeile.lstrip("#").strip(), None
            aus[kopf] = []
            continue
        if kopf is None:
            continue
        if zeile.startswith("|"):
            zellen = [z.strip() for z in zeile.strip().strip("|").split("|")]
            if tab is None:
                tab = {"kopf": zellen, "zeilen": []}
                aus[kopf].append(tab)
            elif not all(re.fullmatch(r":?-+:?", z) for z in zellen):
                tab["zeilen"].append(zellen)
        else:
            tab = None
    return aus


def suche(ab: dict, praefix: str) -> tuple:
    treffer_ = [k for k in ab if k.startswith(praefix)]
    if len(treffer_) != 1:
        fehler(f"Abschnitt „{praefix}…“ {len(treffer_)}-mal im Bericht")
    return treffer_[0], ab[treffer_[0]]


def ruecktest_tabelle(tab: dict, erste: str) -> list:
    aus = []
    for z in tab["zeilen"]:
        t, n_bew, q = treffer(z[3])
        aus.append({erste: z[0], "n": zahl(z[1]), "ohne_klasse": zahl(z[2]), "treffer": t, "bewertet": n_bew,
                    "quote": q,
                    "median_abstand": zahl(z[4]), "median_abstand_fehl": zahl(z[5])})
    return aus


def lade_js(p: Path) -> dict:
    t = p.read_text(encoding="utf-8")
    return json.loads(t[t.index("=") + 1:].rstrip().rstrip(";"))


def erzeugen() -> str:
    roh = BERICHT.read_bytes()
    ab = abschnitte(roh.decode("utf-8"))

    # Zählung aus den veröffentlichten Dateien
    je_stufe, je_g, stand, dateien, jahr = Counter(), Counter(), set(), 0, 0
    for p in sorted(JAHRE.glob("*.js")):
        d = lade_js(p)
        if d.get("fixture"):
            fehler(f"{p.name} ist eine Fixture")
        dateien += 1
        stand.add(d["stand"])
        for f in d["features"]:
            je_stufe[f["properties"]["s"]] += 1
            je_g[f["properties"]["g"]] += 1
            if f["properties"]["j"] is not None:   # Einzeljahr j (Korrektur 6: nur Denkmale oder ohne Wohnraum)
                jahr += 1
    if not dateien:
        fehler("keine Dateien in daten/jahre/")

    # Abdeckung: Bericht gegen Dateien
    _, tabs = suche(ab, "Abdeckung der Kaskade")
    stufen = []
    for z in tabs[0]["zeilen"]:
        m = re.match(r"(\d) ", z[0])
        if not m:
            continue
        s = int(m.group(1))
        g = zahl(z[1])
        if g != je_stufe.get(s, 0):
            fehler(f"Stufe {s}: Bericht {g}, Dateien {je_stufe.get(s, 0)} Gebäude")
        stufen.append({"s": s, "name": STUFEN[s], "gebaeude": g, "wohnraum": zahl(z[2]), "neben": zahl(z[3])})
    if [x["s"] for x in stufen] != [1, 2, 3, 4, 5, 6]:
        fehler("Abdeckungstabelle unvollständig")

    ruecktest = []
    for praefix, rid, art in (("Sichtprüfung Luftbilder", "luftbild",
                               "Sichtprüfung von Luftbildern, ein Stadtteil (Bornstedt)"),
                              ("Wikidata, genaue Jahre", "wikidata", "Baudenkmale mit genauem Jahr aus Wikidata; "
                               "die Schätzung wird ohne diese Jahre gerechnet"),
                              ("Wikipedia-Denkmalliste", "denkmale",
                               "Baudenkmale mit Jahr aus der Wikipedia-Liste, nur Prüfspalte")):
        kopf, tabs = suche(ab, praefix)
        if len(tabs) != 2:
            fehler(f"{kopf}: {len(tabs)} Tabellen statt 2")
        m = re.search(r":\s*([\d.]+) Gebäude$", kopf)
        ruecktest.append({"id": rid, "name": kopf.split(":")[0].split(" (")[0], "art": art,
                          "n": zahl(m.group(1)) if m else None,
                          "je_stufe": ruecktest_tabelle(tabs[0], "stufe"),
                          "je_bauzeit": ruecktest_tabelle(tabs[1], "bauzeit")})

    _, tabs = suche(ab, "Gegenprobe: Zensus-Verteilung")
    z = tabs[0]["zeilen"][0]
    gl, bew, q = treffer(z[3])
    gegenprobe = {"menge": z[0], "n": zahl(z[1]), "ohne_klasse": zahl(z[2]), "gleich": gl, "bewertet": bew, "quote": q,
                  "median_abstand": zahl(z[4]), "median_abstand_abw": zahl(z[5])}

    text = roh.decode("utf-8")
    m = re.search(r"([\d,]+) % Treffer über alle Schätzungen, Zensus ([\d,]+) %, "
                  r"Blocktyp ([\d,]+) %, Nachbarn ([\d,]+) %", text)
    if not m:
        fehler("Vergleichswerte Berlin nicht gefunden")
    berlin = dict(zip(("gesamt", "zensus", "blocktyp", "nachbarn"), (zahl(x) for x in m.groups()), strict=True))

    _, tabs = suche(ab, "Kaskade gesamt gegen den Zensus")
    schieflage = [{"klasse": z[0], "zensus": zahl(z[1]), "kaskade": zahl(z[2]), "abweichung": zahl(z[3]),
                   "stufe3": zahl(z[4]), "stufe4": zahl(z[5]), "stufe5": zahl(z[6])} for z in tabs[0]["zeilen"]]

    m = re.search(r"Geprüft: (\d+) Paare aus Stadtteil und Klasse; eingehalten (\d+), "
                  r"nur mit Lücke erklärbar (\d+), überschritten (\d+)", text)
    if not m:
        fehler("Ergebnis der Summenprüfung nicht gefunden")
    summen = dict(zip(("geprueft", "eingehalten", "mit_luecke", "ueberschritten"), (int(x) for x in m.groups()),
                      strict=True))

    # Baualter-Statistik der LHP (H4, Nachtrag N3): Stadtsummen in drei Gruppen
    _, tabs = suche(ab, "Plausibilität: Baualter-Statistik der LHP")
    lhp = [{"gruppe": z[0], "lhp_2022": zahl(z[1]), "zensus_2022": zahl(z[2]), "zensus_abw": zahl(z[3]),
            "lhp_2025": zahl(z[4]), "kaskade": zahl(z[5]), "kaskade_abw": zahl(z[6])} for z in tabs[0]["zeilen"]]
    m = re.search(r"Quelle: (© Landeshauptstadt Potsdam[^\n]*?)\.\s*$", text, re.MULTILINE)
    if not m:
        fehler("Vermerk der Baualter-Statistik nicht gefunden")
    lhp_vermerk = m.group(1)

    if len(stand) != 1:
        fehler(f"daten/jahre/ hat mehrere Stände {sorted(stand)}")
    inhalt = {
        "stand": stand.pop(),
        "herkunft": {"bericht": "berichte/B4_holdout.md", "sha256": hashlib.sha256(roh).hexdigest(),
                     "skript": "skripte/24_jahre_kaskade.py", "dateien": dateien},
        "gebaeude": sum(je_stufe.values()),
        "je_g": {k: je_g.get(k, 0) for k in ("belegt", "geschaetzt", "nicht_datiert")},
        "jahr": jahr,
        "stufen": stufen,
        "ruecktest": ruecktest,
        "gegenprobe": gegenprobe,
        "berlin": berlin,
        "schieflage": schieflage,
        "summen": summen,
        "lhp": {"vermerk": lhp_vermerk, "gruppen": lhp},
    }
    return "window.KIEZ_JAHRE_METHODE=" + json.dumps(inhalt, ensure_ascii=False, separators=(",", ":")) + ";\n"


def main() -> None:
    neu = erzeugen()
    if "--pruefen" in sys.argv:
        alt = ZIEL.read_text(encoding="utf-8") if ZIEL.exists() else ""
        print("aktuell" if alt == neu else "VERALTET: daten/jahre_methode.js neu erzeugen")
        sys.exit(0 if alt == neu else 1)
    ZIEL.write_text(neu, encoding="utf-8")
    print(f"{ZIEL.relative_to(WURZEL)}: {len(neu.encode())} Bytes", file=sys.stderr)


if __name__ == "__main__":
    main()
