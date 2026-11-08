# ruff: noqa: F403, F405, E501
# Szenenskript für Manim: Sternimport ist dort üblich, Zeilen folgen dem Bildaufbau.
"""Erklärfilm „Was der Kiezatlas beantwortet“ (Kiezatlas Potsdam).

Bildsprache: Zeichenblatt mit Schriftfeld und Blattnummer, Farben und Schrift des Kiezatlas (DESIGN.md).
Alle Zahlen, Fragen, Vermerke und Grenzen werden beim Rendern aus Dateien des Repos gelesen (nur lesen) und in
`belege()` gegen die erwarteten Werte geprüft; weicht eine Datei ab, bricht das Skript ab. Die gelesenen Werte
schreibt es nach `zahlen.json` im Arbeitsordner. Die Geometrie kommt aus `daten/stadtteile.js` und
`daten/zellen.js`; kein Netzabruf.

Pfade: Repo-Wurzel = drei Ebenen über dieser Datei (docs/filme/erklaer/), sonst KIEZ_REPO.
Arbeitsordner = FILM_ARBEIT (relativ zum Arbeitsverzeichnis), sonst berichte/filme/erklaer in der Repo-Wurzel.
PRUEFLOG (optional) = Protokoll eines weiteren Laufs von pruefen.sh, das noch nicht unter belege/ liegt.
Rendern aus der Repo-Wurzel (Einzelheiten in README.md):
    manim -qh --frame_rate 30 --disable_caching --media_dir <arbeit>/media docs/filme/erklaer/film.py Erklaer
"""
import json
import math
import os
import re
from pathlib import Path

import manimpango
from fontTools.ttLib import TTFont
from manim import *
from shapely.geometry import Polygon as FlaecheS, shape

# ---------------------------------------------------------------------------
# Pfade
HIER = Path(__file__).resolve().parent
REPO = Path(os.environ.get("KIEZ_REPO") or HIER.parents[2])
ARBEIT = Path(os.environ.get("FILM_ARBEIT") or REPO / "berichte" / "filme" / "erklaer")
if not ARBEIT.is_absolute():
    ARBEIT = Path.cwd() / ARBEIT
ARBEIT.mkdir(parents=True, exist_ok=True)
PRUEFLOG = os.environ.get("PRUEFLOG")


def pruefe(bedingung, was):
    if not bedingung:
        raise SystemExit(f"Beleg weicht ab: {was}")


# ---------------------------------------------------------------------------
# Schrift: Barlow aus fonts/ des Repos (woff2 → ttf im Arbeitsordner), Familienname trägt das Gewicht
SCHRIFTEN = ARBEIT / "fonts"
SCHRIFTEN.mkdir(exist_ok=True)
for w in sorted((REPO / "fonts").glob("*.woff2")):
    ttf = SCHRIFTEN / (w.stem + ".ttf")
    if not ttf.exists():
        f = TTFont(str(w))
        f.flavor = None
        f.save(str(ttf))
    pruefe(manimpango.register_font(str(ttf)), f"Schrift {ttf.name} nicht registriert")
SANS, SANS_M, SANS_SB = "Barlow", "Barlow Medium", "Barlow SemiBold"
SCHMAL_M, SCHMAL_SB = "Barlow Semi Condensed Medium", "Barlow Semi Condensed SemiBold"
_da = set(manimpango.list_fonts())
for fam in (SANS, SANS_M, SANS_SB, SCHMAL_M, SCHMAL_SB):
    pruefe(fam in _da, f"Schrift „{fam}“ fehlt (Pango nähme still eine andere)")


# ---------------------------------------------------------------------------
# Belege
def lade_js(pfad):
    t = (REPO / pfad).read_text(encoding="utf-8")
    t = re.sub(r"^\s*/\*.*?\*/\s*", "", t, flags=re.S)
    return json.loads(t[t.index("=") + 1:].rstrip().rstrip(";"))


def text(pfad):
    return (REPO / pfad).read_text(encoding="utf-8")


def de(x, stellen=None):
    """Deutsche Schreibweise: 182.673 bzw. 60,7."""
    if isinstance(x, float) or stellen is not None:
        s = f"{x:,.{1 if stellen is None else stellen}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{x:,}".replace(",", ".")


def ohne_link(v):
    """Vermerk wörtlich aus dem Lizenzregister, nur der Link in Klammern fällt im Bild weg (README nennt ihn)."""
    return re.sub(r" \(https?://[^)]+\)", "", v)


def belege():
    q = {}
    # -- sieben Importläufe der Geodaten-Import-Pipeline
    laeufe = []
    for pj in sorted((REPO / "belege").glob("2026110*Z.json")):
        d = json.loads(pj.read_text(encoding="utf-8"))
        pruefe(len(d["quellen"]) == 1, pj.name)
        s = d["quellen"][0]
        kopf = pj.with_suffix(".txt").read_text(encoding="utf-8").splitlines()[0]
        m = re.match(r"Importlauf (\S+) · ([\d.]+) s", kopf)
        pruefe(m and m.group(1) == d["lauf_id"] and float(m.group(2)) == d["laufzeit_s"], f"Kopfzeile {pj.name}")
        laeufe.append({"lauf": d["lauf_id"], "quelle": s["quelle"], "typ": s["typ"], "status": s["status"],
                       "neu": s["zaehler"]["neu"], "laufzeit_s": d["laufzeit_s"], "warnungen": s["warnungen"],
                       "unvollstaendig": s["unvollstaendig"]})
    q["laeufe"] = laeufe
    L = {x["quelle"]: x for x in laeufe}
    pruefe(len(laeufe) == 7 and all(x["status"] == "ok" for x in laeufe), "sieben Läufe mit status ok")
    pruefe([L[k]["neu"] for k in ("stadtteile", "zensus_gitter", "gebaeude_alkis", "mbjs_kita", "mbjs_schule",
                                  "alkis_nutzung", "zensus_struktur")] == [32, 6348, 85046, 220, 106, 28121, 6334], "Zähler neu")
    kita = L["mbjs_kita"]
    pruefe(kita["unvollstaendig"] is True and [x["quelle"] for x in laeufe if x["unvollstaendig"]] == ["mbjs_kita"],
           "nur der Kita-Lauf ist als unvollständig markiert")
    mw = re.match(r"(Nur (\d+) von (\d+) gemeldeten Objekten erhalten)", kita["warnungen"][0])
    pruefe(mw and (int(mw.group(2)), int(mw.group(3))) == (220, 240), "Kita-Warnung")
    q["kita_warnung"] = mw.group(1)
    mk = re.search(r"(\d+) Kitas \(je `id_kita` ein Standort\).*?Dienst (\d+) Einträge meldet: (\d+) Kitas stehen mit mehreren Häusern",
                   text("belege/README.md"))
    pruefe(mk and (int(mk.group(1)), int(mk.group(2))) == (220, 240), "belege/README.md Kita")
    q["kita_mehrere_haeuser"] = int(mk.group(3))
    pruefe(q["kita_mehrere_haeuser"] == 17, "17 Kitas mit mehreren Häusern")

    # -- Zuordnung
    kz = json.loads(text("daten/kennzahlen.json"))
    pruefe(lade_js("daten/kennzahlen.js") == kz, "kennzahlen.js = kennzahlen.json")
    st = kz["stadt"]
    kach = {k["id"]: k for k in st["kacheln"]}
    q["einwohner"] = kach["einwohner"]["wert"]
    q["zellen"] = st["zellen"]
    q["gebaeude"] = st["gebaeude"]["anzahl"]
    q["gebaeude_rechteck"] = kz["kontrolle"]["gebaeude_im_rechteck"]
    pruefe((q["einwohner"], q["zellen"], q["gebaeude"], q["gebaeude_rechteck"]) == (182673, 3443, 52309, 85046), "Zuordnung")
    pruefe(q["gebaeude_rechteck"] == L["gebaeude_alkis"]["neu"], "Gebäude im Rechteck = Importlauf")
    q["zellen_rechteck"] = L["zensus_gitter"]["neu"]

    # -- Befunde über Potsdam: Stadt und Stadtteile ab 1.000 Einwohnern
    MIN_EW = 1000
    q["min_ew"] = MIN_EW
    stadt = {}
    for i in ("u18", "65p", "altbau", "fernwaerme"):
        k = kach[i]
        pruefe(round(100 * k["zaehler"] / k["nenner"], 1) == k["wert"], f"Anteil Stadt {i}")
        stadt[i] = {"prozent": k["wert"], "zaehler": k["zaehler"], "nenner": k["nenner"], "quelle": k["quelle"]}
    q["stadt"] = stadt
    teile = {}
    for nr, s in kz["stadtteile"].items():
        k = {x["id"]: x for x in s["kacheln"]}
        teile[nr] = {"name": s["name"], "ew": k["einwohner"]["wert"], "u18_n": k["u18"]["zaehler"],
                     "u18": k["u18"]["wert"], "65p": k["65p"]["wert"], "altbau": k["altbau"]["wert"],
                     "fernwaerme": k["fernwaerme"]["wert"]}
    q["teile"] = teile
    gross = {nr: t for nr, t in teile.items() if t["ew"] >= MIN_EW}
    q["anzahl_gross"] = len(gross)
    pruefe(len(teile) == 32 and len(gross) == 26, "26 von 32 Stadtteilen ab 1.000 Einwohnern")

    def ext(feld, fn):
        nr = fn(gross, key=lambda n: gross[n][feld])
        return nr

    q["ext"] = {f: {"max": ext(f, max), "min": ext(f, min)} for f in ("fernwaerme", "altbau", "u18_n", "u18", "65p")}
    E = q["ext"]
    pruefe(teile[E["u18"]["max"]]["name"] == "Bornim" and teile[E["u18"]["max"]]["u18"] == 22.2, "höchster Anteil unter 18: Bornim 22,2 %")
    # 65+: alle Stadtteile ab 1.000 Einwohnern unter 40 %, daher Skala 0 bis 40 % (steht im Bild)
    pruefe(max(t["65p"] for t in gross.values()) < 40, "65+ unter 40 % in allen bewerteten Stadtteilen")
    # Stichtag des Zensus aus dem Quellenvermerk der Kacheln
    stt = {re.search(r"Stichtag (\d\d\.\d\d\.\d{4})", kach[i]["quelle"]).group(1) for i in ("einwohner", "u18", "65p", "altbau", "fernwaerme")}
    pruefe(stt == {"15.05.2022"}, "Stichtag Zensus")
    q["stichtag"] = stt.pop()
    pruefe(stadt["fernwaerme"]["prozent"] == 60.7 and teile[E["fernwaerme"]["max"]]["name"] == "Schlaatz"
           and teile[E["fernwaerme"]["max"]]["fernwaerme"] == 99.7 and teile[E["fernwaerme"]["min"]]["name"] == "Bornim"
           and teile[E["fernwaerme"]["min"]]["fernwaerme"] == 4.5, "Befund Fernwärme")
    pruefe(stadt["altbau"]["prozent"] == 25.7 and teile[E["altbau"]["max"]]["name"] == "Teltower Vorstadt"
           and teile[E["altbau"]["max"]]["altbau"] == 63.7 and teile[E["altbau"]["min"]]["name"] == "Waldstadt II"
           and teile[E["altbau"]["min"]]["altbau"] == 0.0, "Befund Altbau")
    pruefe(teile[E["u18_n"]["max"]]["name"] == "Bornstedt" and teile[E["u18_n"]["max"]]["u18_n"] == 3176
           and teile[E["u18_n"]["max"]]["u18"] == 21.1 and stadt["u18"]["zaehler"] == 32631, "Befund Kinder")
    pruefe(teile[E["65p"]["max"]]["name"] == "Waldstadt I und Industriegelände" and teile[E["65p"]["max"]]["65p"] == 30.1
           and teile[E["65p"]["min"]]["name"] == "Golm" and teile[E["65p"]["min"]]["65p"] == 12.2
           and stadt["65p"]["prozent"] == 20.2, "Befund 65+")
    bj = st["verteilungen"]["baujahr"]
    q["wohnungen"] = bj["insgesamt"]
    pruefe(q["wohnungen"] == stadt["altbau"]["nenner"] == stadt["fernwaerme"]["nenner"] == 100998, "Wohnungen insgesamt")

    # -- Fragen der Startseite (nur die Titel sind fest, die Antworten füllt das Skript der Seite)
    idx = text("index.html")
    fragen = dict(re.findall(r'<li class="frage[^"]*" id="frage-(\d+)"[^>]*>\s*<p class="frage__nr">[^<]*</p>\s*'
                             r'<h2 class="frage__titel">([^<]+)</h2>', idx))
    q["fragen"] = {int(k): v for k, v in fragen.items()}
    pruefe(q["fragen"][1] == "Wie viele Menschen wohnen in meiner Nachbarschaft?" and q["fragen"][3] == "Wo wohnen die meisten Kinder?"
           and q["fragen"][6] == "Wem gehört eine Zelle auf der Grenze?" and q["fragen"][7] == "Und wie kommt das ins Heft?"
           and q["fragen"][8] == "Wie weit ist es zur nächsten Kita?" and q["fragen"][9] == "Wann wurde mein Viertel gebaut?",
           "Fragen der Startseite")
    for stelle in ("Eine Zelle anklicken oder antippen zeigt ihre Werte mit Quelle",
                   "Kennzahlen und Verteilungen weiter unten folgen der Auswahl",
                   "Versorgungstabelle mit Plätzen je Kind",
                   "als GeoPackage und CSV für QGIS",
                   "als SVG, als PNG in Druckauflösung oder über die Druckansicht als PDF",
                   "Titel, Stichtag und Quellenvermerk stehen immer mit drauf",
                   "wie oft sie im Rücktest stimmt"):
        pruefe(stelle in idx, f"index.html: {stelle}")
    mp = re.search(r"`daten/planer.js` \| (\d+) Planungsräume", text("belege/A6_planer_20261105.md"))
    q["planungsraeume"] = int(mp.group(1))
    pruefe(q["planungsraeume"] == 19, "19 Planungsräume")

    # -- Grenzen: Bauzeit, Rücktest, Einzeljahr, Grenzfall
    jm = lade_js("daten/jahre_methode.js")
    q["je_g"] = jm["je_g"]
    pruefe(jm["je_g"] == {"belegt": 106, "geschaetzt": 26610, "nicht_datiert": 25593}
           and sum(jm["je_g"].values()) == q["gebaeude"], "Bauzeit je Gebäude")
    rt = next(r for r in jm["ruecktest"] if r["id"] == "luftbild")
    s4 = next(x for x in rt["je_stufe"] if x["stufe"].startswith("4 "))
    q["rt"] = {"n": rt["n"], "treffer": s4["treffer"], "bewertet": s4["bewertet"], "ki": s4["ki"]}
    b4 = text("berichte/B4_holdout.md")
    m4 = re.search(r"\| 4 Zensus-Verteilung \| (\d+) \| \d+ \| (\d+) von (\d+) \(([\d,]+) %\)", b4)
    mb = re.search(r"Sichtprüfung Luftbilder Bornstedt \(B3-Referenz\): (\d+) Gebäude", b4)
    pruefe((rt["n"], s4["treffer"], s4["bewertet"]) == (int(mb.group(1)), int(m4.group(2)), int(m4.group(3))) == (193, 125, 169),
           "Rücktest Bornstedt")
    q["rt"]["quote"] = m4.group(4)
    pruefe(q["rt"]["quote"] == "74,0" and s4["ki"] == {"unten": 66.9, "oben": 80.0}, "Quote und Intervall")
    pruefe("Sichtprüfung von Luftbildern durch einen KI-Agenten" in b4 and "ohne zweite Bewertung" in b4, "Referenz des Rücktests")
    mj = re.search(r"Gebäude mit Einzeljahr `j`: (\d+), davon mit Wohnraum (\d+)", b4)
    q["einzeljahr"], q["einzeljahr_wohnraum"] = int(mj.group(1)), int(mj.group(2))
    pruefe(q["einzeljahr"] == jm["jahr"] == 53 and q["einzeljahr_wohnraum"] == 0, "Einzeljahr")
    gf = kz["grenzfall"]
    q["grenzfall"] = gf["stadt"]
    pruefe(gf["stadt"]["mittelpunkt"] == q["einwohner"] and gf["stadt"]["flaechenanteilig"] == 182779
           and gf["stadt"]["grenzzellen"] == 91 and gf["stadt"]["ew_in_grenzzellen"] == 1605, "Grenzfall Stadt")
    abw = []
    for nr, g in gf["stadtteile"].items():
        pruefe(g["mittelpunkt"] == teile[nr]["ew"], f"Grenzfall {nr}")
        if g["mittelpunkt"] >= 5000:
            abw.append((abs((g["mittelpunkt"] - g["flaechenanteilig"]) / g["flaechenanteilig"]), nr, g))
    _, nr, g = max(abw)
    q["grenzfall_gross"] = {"name": teile[nr]["name"], "prozent": round(100 * (g["mittelpunkt"] - g["flaechenanteilig"]) / g["flaechenanteilig"], 1)}
    pruefe(q["grenzfall_gross"] == {"name": "Nauener Vorstadt", "prozent": 3.0}, "Grenzfall größte Abweichung ab 5.000")
    ent = text("docs/entscheidungen.md")
    q["entscheidungen"] = re.findall(r"^## (A\d+): (.+)$", ent, re.M)
    # lückenlos A1 bis An; A20 (Belegfilme) ist die jüngste Entscheidung beim Bau dieses Films
    ids = [a for a, _ in q["entscheidungen"]]
    pruefe(len(ids) >= 20 and ids == [f"A{i}" for i in range(1, len(ids) + 1)], "Entscheidungen lückenlos ab A1, mindestens bis A20")
    ng = ent.split("## Nicht geprüft sind", 1)[1].split("\n## ", 1)[0]
    q["nicht_geprueft"] = len(re.findall(r"^- ", ng, re.M))
    pruefe(q["nicht_geprueft"] == 6, "Nicht geprüft sind: 6 Punkte")
    a3 = dict(q["entscheidungen"])["A3"]
    q["a3"] = a3
    pruefe(a3 == "Bauzeiten ohne Einzeljahr bei Wohnraum, ohne Adressen und ohne Kennung", "Titel A3")

    # -- Prüfstände von pruefen.sh
    log = text("belege/pruefstand-20261106-1cf8d56/pruefen.log")
    mz = re.search(r"== Zählung: (\d+) Prüfungen, (\d+) grün, (\d+) mit Befund, (\d+) übersprungen", log)
    mc = re.search(r"^Commit: ([0-9a-f]{7})", log, re.M)
    md = re.search(r"Prüflauf (\d\d)\.(\d\d)\.(\d{4})", log)
    bef = re.findall(r"^  BEFUND \(Rückgabe \d+\)\s+.*?\((pruefen/[^)]+)\)$|^  BEFUND \(Rückgabe \d+\)\s+Browser: (pruefen/\S+)$", log, re.M)
    q["stand1"] = {"commit": mc.group(1), "datum": ".".join(md.groups()), "pruefungen": int(mz.group(1)),
                   "gruen": int(mz.group(2)), "befund": int(mz.group(3)), "uebersprungen": int(mz.group(4)),
                   "befunde": [a or b for a, b in bef]}
    pruefe(q["stand1"]["commit"] == "1cf8d56" and (q["stand1"]["pruefungen"], q["stand1"]["gruen"], q["stand1"]["befund"]) == (18, 16, 2)
           and q["stand1"]["befunde"] == ["pruefen/A6_test_pfade.py", "pruefen/p1_themen.mjs"], "Prüfstand 06.11.")
    zblock = log.split("== Zählung", 1)[1]
    q["browser"] = len(re.findall(r"Browser: pruefen/", zblock))
    pruefe(q["browser"] == 4, "vier Browser-Prüfungen")
    pruefe(re.search(r"`pruefstand-20261106-1cf8d56/pruefen.log` \| Ergebnis aller Prüfungen ohne Netz und ohne Datenbank", text("belege/README.md")),
           "belege/README.md: ohne Netz und ohne Datenbank")
    k29 = re.search(r"^\| K29 \|.*?(Stand ([0-9a-f]{7}): (\d+)/(\d+) grün) \|$", text("berichte/audit_20261106.md"), re.M)
    q["stand2"] = {"commit": k29.group(2), "gruen": int(k29.group(3)), "pruefungen": int(k29.group(4))}
    q["k29_wortlaut"] = k29.group(1)
    pruefe(q["stand2"] == {"commit": "4559a52", "gruen": 18, "pruefungen": 18}, "Audit K29")
    q["stand3"] = None
    if PRUEFLOG:
        roh = [re.sub(r"^\S+ \+\s*[\d.]+s \| ?", "", z) for z in Path(PRUEFLOG).read_text(encoding="utf-8").splitlines()]
        roh = "\n".join(roh)
        mz3 = re.search(r"== Zählung: (\d+) Prüfungen, (\d+) grün, (\d+) mit Befund, (\d+) übersprungen", roh)
        mc3 = re.search(r"^Commit: ([0-9a-f]{7})", roh, re.M)
        md3 = re.search(r"Prüflauf (\d\d)\.(\d\d)\.(\d{4})", roh)
        mr3 = re.search(r"# Rückgabe pruefen.sh: (\d+)", roh)
        q["stand3"] = {"commit": mc3.group(1), "datum": ".".join(md3.groups()), "pruefungen": int(mz3.group(1)),
                       "gruen": int(mz3.group(2)), "befund": int(mz3.group(3)), "uebersprungen": int(mz3.group(4)),
                       "rueckgabe": int(mr3.group(1)) if mr3 else None, "zeile": mz3.group(0)}
        pruefe(q["stand3"]["pruefungen"] == 18, "weiterer Prüflauf: 18 Prüfungen")
        # Regel: jede sichtbare Zahl aus einer Datei im Repo; ein Protokoll außerhalb von belege/ wird nicht gezeigt
        pruefe(Path(PRUEFLOG).resolve().is_relative_to(REPO / "belege"), "PRUEFLOG muss unter belege/ liegen (eingecheckt)")
    rd = text("README.md")
    zp = rd.split("## Zur Prüfung", 1)[1].split("\n## ", 1)[0]
    q["zur_pruefung"] = len([z for z in zp.splitlines() if z.startswith("| ") and not z.startswith("| Angabe")])
    pruefe(q["zur_pruefung"] == 12, "README Zur Prüfung: 12 Angaben")

    # -- Namensnennung: Wortlaut aus daten/LIZENZ.md, QUELLEN.md und Dateiköpfen
    liz = text("daten/LIZENZ.md")

    def zeile_liz(datei):
        m = re.search(r"^\| " + re.escape(datei) + r" \| ([^|]+) \| ([^|]+) \|$", liz, re.M)
        return m.group(1).strip(), m.group(2).strip()

    lz_st, vm_st = zeile_liz("`stadtteile.js`")
    _, vm_z = zeile_liz("`zellen.js`, `kennzahlen.js`, `kennzahlen.json`")
    _, vm_g = zeile_liz("`gebaeude/<nr>.js`")
    mbjs = "© Ministerium für Bildung, Jugend und Sport, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)"
    pruefe(mbjs in text("QUELLEN.md"), "Vermerk MBJS in QUELLEN.md")
    vm_j = lade_js("daten/jahre/13.js")["quellen"]["zensus"]["vermerk"]
    pruefe("belegte Bauzeiten aus Wikidata (CC0 1.0" in liz, "Wikidata CC0 in LIZENZ.md")
    q["vermerk"] = {"stadtteile": f"{vm_st}, {lz_st}", "zensus": ohne_link(vm_z), "gebaeude": ohne_link(vm_g),
                    "mbjs": ohne_link(mbjs), "bauzeit": ohne_link(vm_j), "wikidata": "belegte Bauzeiten: Wikidata, CC0 1.0"}
    pruefe(q["vermerk"]["stadtteile"] == "© Landeshauptstadt Potsdam, dl-de/zero-2-0", "Vermerk Stadtteile")
    cit = text("CITATION.cff")
    q["url"] = re.search(r'^url: "https://([^"]+)"', cit, re.M).group(1).rstrip("/")
    pruefe(q["url"] == "souverain-systems.de/kiezatlas", "URL aus CITATION.cff")
    return q


B = belege()
(ARBEIT / "zahlen.json").write_text(json.dumps(B, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------------------------------------------------------------------------
# Geometrie: WGS84 → Meter (lokale Näherung um Potsdam, Fehler unter 0,5 %), Stadtteile vereinfacht auf 25 m
LAT0 = 52.42
KX, KY = math.cos(math.radians(LAT0)) * 111320.0, 110574.0


def meter(lon, lat):
    return ((lon - 13.0) * KX, (lat - LAT0) * KY)


ST_FEATS = lade_js("daten/stadtteile.js")["features"]
pruefe(len(ST_FEATS) == 32, "32 Stadtteile in stadtteile.js")
STADTTEILE = {}
for f in ST_FEATS:
    ringe = []
    g = shape(f["geometry"])
    for p in getattr(g, "geoms", [g]):
        pm = FlaecheS([meter(x, y) for x, y in p.exterior.coords]).simplify(25.0, preserve_topology=True)
        if not pm.is_empty and pm.area > 2000:
            ringe.append(list(pm.exterior.coords))
    STADTTEILE[f["properties"]["nr"]] = ringe
pruefe(set(STADTTEILE) == set(B["teile"]), "Stadtteil-Nummern = kennzahlen.json")
ZELLEN = []
for f in lade_js("daten/zellen.js")["features"]:
    ZELLEN.append(([meter(x, y) for x, y in f["geometry"]["coordinates"][0]], f["properties"]["ew"]))
pruefe(len(ZELLEN) == B["zellen"] and sum(e for _, e in ZELLEN) == B["einwohner"], "zellen.js = Kennzahlen")
_xs = [p[0] for r in STADTTEILE.values() for ring in r for p in ring]
_ys = [p[1] for r in STADTTEILE.values() for ring in r for p in ring]
BX, BY, BH = (max(_xs) + min(_xs)) / 2, (max(_ys) + min(_ys)) / 2, max(_ys) - min(_ys)

# ---------------------------------------------------------------------------
# Farbwelt des Kiezatlas (DESIGN.md, atlas.css): Kartenpapier, Tinte, Grenzviolett, fünf Stufen Wasser bis Tiefe
PAPIER = "#f1f2ee"
FLAECHE = "#fafbf8"
TINTE = "#13212a"
LEISE = "#4f5d64"
LINIE = "#cdd1cc"
LINIE_LEISE = "#e0e3de"
VIOLETT = "#6a2c82"
VIOLETT_HELL = "#efe6f3"
STUFEN = ["#dce6e2", "#a8c7c2", "#6fa1a3", "#3b7684", "#1c4a5b"]
GRAU = "#bcc0ba"  # GEB_ND in jahre.js: nicht datiert bzw. nicht bewertet
config.background_color = PAPIER


def T(s, size=24, font=SANS, color=TINTE, **kw):
    return Text(s, font=font, font_size=size, color=color, **kw)


def karte_stadtteile(hoehe, mitte, farbe=TINTE, breite=1.2, fuellung=None):
    s = hoehe / BH
    g = VGroup()
    for nr in sorted(STADTTEILE):
        teil = VGroup()
        for ring in STADTTEILE[nr]:
            vm = VMobject(stroke_color=farbe, stroke_width=breite)
            vm.set_points_as_corners([np.array([(x - BX) * s, (y - BY) * s, 0.0]) for x, y in ring])
            vm.set_fill(fuellung or PAPIER, opacity=1 if fuellung else 0)
            teil.add(vm)
        teil.nr = nr
        g.add(teil)
    g.shift(mitte)
    return g


def karte_zellen(hoehe, mitte):
    """3.443 Zellen in fünf Stufen nach Einwohnern (Fünftel aller Zellen, wie die Startseite); je Stufe ein Pfad."""
    s = hoehe / BH
    ew = sorted(e for _, e in ZELLEN)
    grenzen = [ew[int(len(ew) * k / 5)] for k in (1, 2, 3, 4)]
    stufen = [VMobject(stroke_width=0).set_fill(STUFEN[i], 1) for i in range(5)]
    pfade = [[] for _ in range(5)]
    for ring, e in ZELLEN:
        i = sum(e >= gr for gr in grenzen)
        pfade[i].append([np.array([(x - BX) * s, (y - BY) * s, 0.0]) for x, y in ring])
    for i, pp in enumerate(pfade):
        for ring in pp:
            stufen[i].start_new_path(ring[0])
            stufen[i].add_points_as_corners(ring[1:])
    g = VGroup(*stufen).shift(mitte)
    return g, grenzen


class Erklaer(Scene):
    # -------------------------------------------------------------- Rahmen
    def zeichenblatt(self):
        fein, grob = VGroup(), VGroup()
        w, h = config.frame_width / 2, config.frame_height / 2
        x, i = -w, 0
        while x <= w + 1e-6:
            (grob if i % 4 == 0 else fein).add(Line([x, -h, 0], [x, h, 0]))
            x += 0.25
            i += 1
        y, i = -h, 0
        while y <= h + 1e-6:
            (grob if i % 4 == 0 else fein).add(Line([-w, y, 0], [w, y, 0]))
            y += 0.25
            i += 1
        fein.set_stroke(LINIE_LEISE, 0.6)
        grob.set_stroke(LINIE, 0.8)
        rand = Rectangle(width=2 * w - 0.5, height=2 * h - 0.5).set_stroke(TINTE, 1.6)
        marken = VGroup()
        for k in range(1, 8):
            xx = -w + 0.25 + k * (2 * w - 0.5) / 8
            marken.add(Line([xx, h - 0.25, 0], [xx, h - 0.4, 0]), Line([xx, -h + 0.25, 0], [xx, -h + 0.4, 0]))
        for k in range(1, 4):
            yy = -h + 0.25 + k * (2 * h - 0.5) / 4
            marken.add(Line([-w + 0.25, yy, 0], [-w + 0.4, yy, 0]), Line([w - 0.25, yy, 0], [w - 0.4, yy, 0]))
        marken.set_stroke(TINTE, 1.2)
        # Feldbezeichnung am Rand wie auf einem Kartenblatt (A bis H oben, 1 bis 4 links)
        buch = VGroup()
        for k in range(8):
            xx = -w + 0.25 + (k + 0.5) * (2 * w - 0.5) / 8
            buch.add(T("ABCDEFGH"[k], 10, SCHMAL_M, LEISE).move_to([xx, h - 0.33, 0]))
        for k in range(4):
            yy = h - 0.25 - (k + 0.5) * (2 * h - 0.5) / 4
            buch.add(T(str(k + 1), 10, SCHMAL_M, LEISE).move_to([-w + 0.33, yy, 0]))
        return VGroup(fein, grob), VGroup(rand, marken, buch)

    def schriftfeld(self, blatt, titel):
        w, h = config.frame_width / 2, config.frame_height / 2
        box = Rectangle(width=4.6, height=0.62).set_stroke(TINTE, 1.4).set_fill(PAPIER, 1)
        box.move_to([w - 0.25 - 2.3, -h + 0.25 + 0.31, 0])
        trenn = Line(box.get_top() + RIGHT * 1.25, box.get_bottom() + RIGHT * 1.25).set_stroke(TINTE, 1.0)
        kopf = T("KIEZATLAS POTSDAM · ERKLÄRFILM", 11, SCHMAL_M, LEISE)
        kopf.move_to(box.get_left() + UP * 0.14).align_to(box.get_left() + RIGHT * 0.12, LEFT)
        tit = T(titel, 15, SCHMAL_SB, TINTE)
        tit.next_to(kopf, DOWN, buff=0.06).align_to(kopf, LEFT)
        bl = T(f"BLATT {blatt}/5", 15, SCHMAL_SB, VIOLETT)
        bl.move_to([trenn.get_x() + (box.get_right()[0] - trenn.get_x()) / 2, box.get_y(), 0])
        return VGroup(box, trenn, kopf, tit, bl)

    def blattwechsel(self, n, titel, *kommt):
        """Umblättern ohne leeres Blatt: das alte Blatt blendet aus, während Schriftfeld, Überschrift und Fußzeile
        des neuen schon einlaufen."""
        neu = self.schriftfeld(n, titel)
        fest = set(self.sf.get_family())
        weg = [m for m in self.mobjects if m not in (self.raster, self.rand) and not (set(m.get_family()) & fest)]
        self.play(AnimationGroup(*[FadeOut(m) for m in weg], run_time=0.45),
                  LaggedStart(AnimationGroup(*[ReplacementTransform(self.sf[i], neu[i]) for i in (2, 3, 4)]),
                              AnimationGroup(*[FadeIn(k, shift=UP * 0.06) for k in kommt]), lag_ratio=0.45, run_time=0.75))
        self.sf = VGroup(self.sf[0], self.sf[1], neu[2], neu[3], neu[4])

    def fuss(self, *zeilen, size=10):
        """Namensnennung der gezeigten Daten, links unten im Rahmen."""
        g = VGroup(*[T(z, size, SANS, LEISE) for z in zeilen]).arrange(DOWN, aligned_edge=LEFT, buff=0.05)
        g.scale_to_fit_width(min(g.width, 8.6))
        w, h = config.frame_width / 2, config.frame_height / 2
        g.align_to([-w + 0.5, 0, 0], LEFT).align_to([0, -h + 0.44, 0], DOWN)
        return g

    def ueberschrift(self, nummer, text_):
        n = T(nummer, 18, SCHMAL_SB, VIOLETT)
        t = T(text_, 40, SCHMAL_SB, TINTE)
        g = VGroup(n, t).arrange(RIGHT, buff=0.3, aligned_edge=DOWN)
        g.to_corner(UL, buff=0.62)
        strich = Line(g.get_left(), g.get_left() + RIGHT * 1.2).set_stroke(VIOLETT, 3)
        strich.next_to(g, DOWN, buff=0.14).align_to(g, LEFT)
        return VGroup(g, strich)

    def raeumen(self, behalten=(), zeit=0.5):
        fest = set(self.sf.get_family())
        weg = [m for m in self.mobjects if m not in (self.raster, self.rand, *behalten)
               and not (set(m.get_family()) & fest)]
        if weg:
            self.play(*[FadeOut(m) for m in weg], run_time=zeit)

    def schematisch(self, s, ref=None):
        t = T(s, 10, SANS, LEISE)
        if ref is None:
            w, h = config.frame_width / 2, config.frame_height / 2
            t.move_to([w - 0.5, -h + 1.05, 0], aligned_edge=RIGHT)
        return t

    # -------------------------------------------------------------- Ablauf
    def construct(self):
        self.raster, self.rand = self.zeichenblatt()
        self.sf = self.schriftfeld(1, "Warum")
        self.add(self.raster)
        self.play(Create(self.rand), FadeIn(self.sf), run_time=0.9)
        self.blatt1()
        self.blatt2()
        self.blatt3()
        self.blatt4()
        self.blatt5()

    # 1 ----------------------------------------------------------------------
    def blatt1(self):
        titel = VGroup(T("Was der Kiezatlas", 72, SCHMAL_SB), T("beantwortet", 72, SCHMAL_SB)).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        frage = VGroup(T("Was erfährt man über eine Stadt", 28, SANS, LEISE),
                       T("allein aus offenen amtlichen Daten?", 28, SANS, LEISE)).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        kopf = VGroup(titel, frage).arrange(DOWN, aligned_edge=LEFT, buff=0.4).move_to([0, 0.25, 0]).to_edge(LEFT, buff=1.0)
        strich = Line(ORIGIN, RIGHT * 1.6).set_stroke(VIOLETT, 4).next_to(kopf, UP, buff=0.3).align_to(kopf, LEFT)
        karte = karte_stadtteile(5.7, [3.9, 0.3, 0], TINTE, 1.3)
        f1 = self.fuss(f"{B['vermerk']['stadtteile'].split(',')[0]}: 32 Stadtteilgrenzen, dl-de/zero-2-0")
        self.play(Create(strich), FadeIn(kopf, shift=UP * 0.15), FadeIn(f1), run_time=1.0)
        self.play(LaggedStart(*[Create(t) for t in karte], lag_ratio=0.06), run_time=3.0)
        self.wait(1.2)
        if getattr(self, "nur_titel", False):
            return

        # Sieben Läufe → Pipeline → Atlas
        ueb = self.ueberschrift("01", "Sieben Quellen, ein Atlas")
        self.play(FadeOut(kopf), FadeOut(strich), run_time=0.4)
        self.play(karte.animate.scale(3.95 / 5.7).move_to([4.4, 0.75, 0]), FadeIn(ueb), run_time=0.9)

        namen = {"stadtteile": "Stadtteile", "zensus_gitter": "Zensus-Gitter 100 m", "zensus_struktur": "Zensus-Struktur",
                 "gebaeude_alkis": "ALKIS-Gebäude", "alkis_nutzung": "ALKIS-Nutzung", "mbjs_kita": "Kitas", "mbjs_schule": "Schulen"}
        reihen = VGroup()
        tmax = max(x["laufzeit_s"] for x in B["laeufe"])
        y0 = 1.75
        for i, x in enumerate(B["laeufe"]):
            yy = y0 - i * 0.5
            typ = T(x["typ"].upper(), 11, SCHMAL_SB, VIOLETT).move_to([-6.25, yy, 0], aligned_edge=LEFT)
            nm = T(namen[x["quelle"]] + ("*" if x["unvollstaendig"] else ""), 18, SCHMAL_SB).move_to([-5.65, yy, 0], aligned_edge=LEFT)
            zahl = T(de(x["neu"]), 19, SCHMAL_M).move_to([-2.85, yy, 0], aligned_edge=RIGHT)
            balken = Rectangle(width=max(0.012, 1.6 * x["laufzeit_s"] / tmax), height=0.11).set_stroke(width=0).set_fill(STUFEN[3], 1)
            balken.move_to([-2.65, yy, 0], aligned_edge=LEFT)
            sek = T(de(x["laufzeit_s"], 2 if x["laufzeit_s"] < 10 else 1) + " s", 12, SANS, LEISE)
            sek.next_to(balken, RIGHT, buff=0.08)
            reihen.add(VGroup(typ, nm, zahl, balken, sek))
        kopfz = VGroup(T("Importlauf", 11, SANS, LEISE).move_to([-5.65, y0 + 0.42, 0], aligned_edge=LEFT),
                       T("Objekte neu", 11, SANS, LEISE).move_to([-2.85, y0 + 0.42, 0], aligned_edge=RIGHT),
                       T("Laufzeit (Balken nach laufzeit_s)", 11, SANS, LEISE).move_to([-2.65, y0 + 0.42, 0], aligned_edge=LEFT))
        kita_n = VGroup(T(f"* Kita-Lauf als unvollständig markiert: „{B['kita_warnung']}“.", 11, SANS, LEISE),
                        T(f"Laut belege/README.md sind es 220 Kitas; {B['kita_mehrere_haeuser']} stehen im Dienst mit mehreren Häusern.", 11, SANS, LEISE)
                        ).arrange(DOWN, aligned_edge=LEFT, buff=0.04).move_to([-6.25, y0 - 6 * 0.5 - 0.62, 0], aligned_edge=UL)
        f2 = self.fuss(f"Stadtteile {B['vermerk']['stadtteile']} · Gebäude, Nutzung {B['vermerk']['gebaeude']}",
                       f"Zensus {B['vermerk']['zensus']}",
                       f"Kitas, Schulen {B['vermerk']['mbjs']}")
        self.play(FadeIn(kopfz), ReplacementTransform(f1, f2), run_time=0.5)
        # Laufzeit-Etikett erst, wenn der Balken steht (Ergebnisse nicht zu früh)
        self.play(LaggedStart(*[LaggedStart(FadeIn(r[0]), FadeIn(r[1], shift=RIGHT * 0.08), FadeIn(r[2]),
                                            Succession(GrowFromEdge(r[3], LEFT), FadeIn(r[4], run_time=0.5)), lag_ratio=0.15) for r in reihen],
                              lag_ratio=0.18), run_time=3.0)
        self.play(FadeIn(kita_n), run_time=0.5)

        pip = Rectangle(width=1.5, height=0.85).set_stroke(VIOLETT, 2).set_fill(FLAECHE, 1).move_to([0.95, 0.5, 0])
        pip_t = VGroup(T("Pipeline", 20, SCHMAL_SB, VIOLETT), T("Abrufen, Prüfen,", 10, SANS, LEISE),
                       T("Abgleichen", 10, SANS, LEISE)).arrange(DOWN, buff=0.04).move_to(pip)
        pfeile = VGroup(*[CubicBezier(np.array([-0.35, r.get_y(), 0]), np.array([0.0, r.get_y(), 0]),
                                      pip.get_left() + LEFT * 0.35, pip.get_left()).set_stroke(LINIE, 1.3) for r in reihen])
        zu = Arrow(pip.get_right(), [2.25, 0.5, 0], buff=0.05, stroke_width=2.5, max_tip_length_to_length_ratio=0.25, color=VIOLETT)
        self.play(LaggedStart(*[Create(p) for p in pfeile], lag_ratio=0.08), FadeIn(pip), FadeIn(pip_t), run_time=1.0)
        self.play(GrowArrow(zu), run_time=0.4)

        # Zuordnung: Zellen erscheinen in der Karte, darunter die Zahlen mit ihrer Bezugsfläche
        zel, _ = karte_zellen(karte.height, karte.get_center())
        self.play(FadeIn(zel), karte.animate.set_stroke(TINTE, 0.8), run_time=1.0)
        self.bring_to_front(karte)
        zuord = VGroup(T("32 Stadtteile", 22, SCHMAL_SB),
                       T(f"{de(B['einwohner'])} Einwohner in {de(B['zellen'])} Zellen", 15, SANS_M),
                       T(f"Zellen mit Mittelpunkt in Potsdam (von {de(B['zellen_rechteck'])} im Abrufrechteck)", 11, SANS, LEISE),
                       T(f"{de(B['gebaeude'])} Gebäude", 15, SANS_M),
                       T(f"in den 32 Stadtteilen (von {de(B['gebaeude_rechteck'])} im Abrufrechteck)", 11, SANS, LEISE)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.05)
        zuord.next_to(karte, DOWN, buff=0.15).align_to(karte, LEFT)
        leg = VGroup(*[Square(0.13).set_stroke(width=0).set_fill(c, 1) for c in STUFEN]).arrange(RIGHT, buff=0.02)
        leg_t = T("Einwohner je Zelle, Fünftel aller Zellen", 10, SANS, LEISE).next_to(leg, RIGHT, buff=0.1)
        legende = VGroup(leg, leg_t).next_to(karte, UP, buff=0.08).align_to(karte, LEFT)
        schem = self.schematisch("Aufbau schematisch, Karte aus den Daten")
        self.play(FadeIn(zuord, shift=UP * 0.08), FadeIn(legende), FadeIn(schem), run_time=0.8)
        self.wait(2.4)

    # 2 ----------------------------------------------------------------------
    def blatt2(self):
        ueb = self.ueberschrift("02", "Wer was fragt, und wo der Atlas antwortet")
        self.blattwechsel(2, "Für wen", ueb)
        F = B["fragen"]
        karten = [
            ("Bürgerinnen und Bürger", 1, ["Zelle anklicken: Werte der 100-m-Zelle", "mit Quelle"]),
            ("Quartiersarbeit", 3, ["Stadtteil wählen: Kennzahlen und", "Verteilungen folgen der Auswahl"]),
            ("Stadtplanung", 8, [f"Planer: Versorgung je Planungsraum ({B['planungsraeume']}),", "Plätze je Kind, Luftlinie und Fußweg"]),
            ("Verwaltung und GIS", 6, ["Grenzfall je Stadtteil nachgerechnet;", "Daten als GeoPackage und CSV für QGIS"]),
            ("Presse", 7, ["Schaugrafik als SVG, PNG oder PDF,", "mit Stichtag und Quellenvermerk"]),
            ("Forschung", 9, ["Methode der Bauzeiten, Rücktest je Stufe;", "zitierfähig über CITATION.cff"]),
        ]
        felder = VGroup()
        for i, (wer, nr, wo) in enumerate(karten):
            sp, ze = i % 3, i // 3
            mitte = np.array([-4.45 + sp * 4.45, 0.95 - ze * 2.45, 0])
            rahmen = Rectangle(width=4.15, height=2.15).set_stroke(TINTE, 1.1).set_fill(PAPIER, 1).move_to(mitte)
            block = Rectangle(width=0.12, height=2.15).set_stroke(width=0).set_fill(VIOLETT, 1).move_to(rahmen.get_left(), aligned_edge=LEFT)
            kopf = T(wer, 22, SCHMAL_SB, VIOLETT)
            fr = Paragraph(*self.umbrechen(f"„{F[nr]}“", 34), font=SANS_M, font_size=18, color=TINTE, line_spacing=0.7, alignment="left")
            nrz = T(f"Frage {nr} der Startseite", 11, SANS, LEISE)
            pf = T("→", 15, SANS_SB, VIOLETT)
            woz = VGroup(*[T(z, 13, SANS) for z in wo]).arrange(DOWN, aligned_edge=LEFT, buff=0.04)
            wo_g = VGroup(pf, woz).arrange(RIGHT, buff=0.1, aligned_edge=UP)
            inhalt = VGroup(kopf, fr, nrz, wo_g).arrange(DOWN, aligned_edge=LEFT, buff=0.11)
            inhalt.move_to(rahmen).align_to(rahmen.get_left() + RIGHT * 0.32, LEFT)
            felder.add(VGroup(rahmen, block, inhalt))
        for f in felder:
            f[1].stretch_to_fit_width(0.001).align_to(f[0], LEFT)
        self.play(LaggedStart(*[AnimationGroup(Create(f[0]), FadeIn(f[2], shift=RIGHT * 0.06)) for f in felder], lag_ratio=0.22), run_time=3.4)
        # einrasten: der violette Block füllt sich von links (Bewegungsverb aus DESIGN.md)
        self.play(*[f[1].animate.stretch_to_fit_width(0.12).align_to(f[0], LEFT) for f in felder], run_time=0.5)
        hinweis = self.fuss("Fragen wörtlich aus index.html; welche Gruppe welche Frage stellt, ist eine Auswahl für den Film")
        self.play(FadeIn(hinweis), run_time=0.4)
        self.wait(5.2)

    @staticmethod
    def umbrechen(s, breite):
        zeilen, z = [], ""
        for w in s.split():
            if z and len(z) + 1 + len(w) > breite:
                zeilen.append(z)
                z = w
            else:
                z = f"{z} {w}".strip()
        zeilen.append(z)
        return zeilen

    # 3 ----------------------------------------------------------------------
    def befund_karte(self, feld, klassen):
        """Stadtteile nach Wert gefärbt; unter MIN_EW grau (nicht bewertet)."""
        g = karte_stadtteile(5.75, [-3.45, -0.15, 0], PAPIER, 0.9, fuellung=GRAU)
        for t in g:
            d = B["teile"][t.nr]
            if d["ew"] < B["min_ew"]:
                t.set_fill(GRAU, 1)
            else:
                t.set_fill(STUFEN[klassen(d[feld])], 1)
        return g

    def blatt3(self, nur=None):
        ueb = self.ueberschrift("03", "Was man über Potsdam erfährt")
        S, E, TL = B["stadt"], B["ext"], B["teile"]

        def anteil(v):
            return min(4, int(v // 20))

        def anteil40(v):
            return min(4, int(v // 8))

        P100 = ["0", "20", "40", "60", "80", "100 %"]
        P40 = ["0", "8", "16", "24", "32", "40 %"]
        KA = TL[E["u18_n"]["max"]]  # meiste Kinder (Anzahl)
        KQ = TL[E["u18"]["max"]]  # höchster Anteil unter 18

        u18 = sorted(t["u18_n"] for t in TL.values() if t["ew"] >= B["min_ew"])
        u18_gr = [u18[int(len(u18) * k / 5)] for k in (1, 2, 3, 4)]

        def fuenftel(v):
            return sum(v >= gr for gr in u18_gr)

        befunde = [
            {"feld": "fernwaerme", "klassen": anteil, "thema": "Heizung", "zahl": de(S["fernwaerme"]["prozent"]) + " %",
             "satz": "der Wohnungen in Potsdam heizen mit Fernwärme. Sechs von zehn.",
             "einheit": f"Anteil an {de(S['fernwaerme']['nenner'])} Wohnungen", "max": E["fernwaerme"]["max"], "min": E["fernwaerme"]["min"],
             "skala": 100, "leg": P100, "leg_t": "Wohnungen mit Fernwärme"},
            {"feld": "altbau", "klassen": anteil, "thema": "Baualter", "zahl": de(S["altbau"]["prozent"]) + " %",
             "satz": "der Wohnungen liegen in Häusern von vor 1949. Ein Viertel.",
             "einheit": f"Anteil an {de(B['wohnungen'])} Wohnungen", "max": E["altbau"]["max"], "min": E["altbau"]["min"],
             "skala": 100, "leg": P100, "leg_t": "Wohnungen in Gebäuden vor 1949"},
            {"feld": "u18_n", "klassen": fuenftel, "thema": "Kinder", "zahl": de(KA["u18_n"]),
             "satz": f"Kinder und Jugendliche unter 18 leben in {KA['name']}, mehr als in jedem anderen Stadtteil. "
                     f"Den höchsten Anteil hat {KQ['name']}: {de(KQ['u18'])} %.",
             "einheit": f"{KA['name']}: {de(KA['u18'])} % von {de(KA['ew'])} Einwohnern; Stadt: {de(S['u18']['zaehler'])} unter 18, {de(S['u18']['prozent'])} %",
             "marken": [(E["u18_n"]["max"], "meiste", de(KA["u18_n"])), (E["u18"]["max"], "höchster Anteil", de(KQ["u18"]) + " %")],
             "skala": None, "leg": None, "leg_t": "Personen unter 18 (Anzahl), Fünftel der 26 Stadtteile"},
            {"feld": "65p", "klassen": anteil40, "thema": "Alter", "zahl": de(TL[E["65p"]["max"]]["65p"]) + " %",
             "satz": f"sind 65 oder älter in {TL[E['65p']['max']]['name']}, dem ältesten Stadtteil. Potsdam: {de(S['65p']['prozent'])} %.",
             "einheit": f"Anteil an den Einwohnern; niedrigster Anteil: {TL[E['65p']['min']]['name']} {de(TL[E['65p']['min']]['65p'])} %",
             "max": E["65p"]["max"], "min": E["65p"]["min"], "skala": 40, "leg": P40,
             "leg_t": "Personen ab 65 Jahren; Skala nur bis 40 %, alle Stadtteile liegen darunter"},
        ]
        for b in befunde:
            if "marken" not in b:
                b["marken"] = [(b[art], None, de(TL[b[art]][b["feld"]]) + " %") for art in ("max", "min") if b.get(art)]
        if nur is not None:
            befunde = [befunde[nur]]
        f3 = self.fuss(f"Zensus 2022, Stichtag {B['stichtag']}: {B['vermerk']['zensus']}",
                       f"Stadtteilgrenzen {B['vermerk']['stadtteile']}")
        grau_l = VGroup(Square(0.14).set_stroke(width=0).set_fill(GRAU, 1),
                        T(f"unter {de(B['min_ew'])} Einwohnern, nicht bewertet ({32 - B['anzahl_gross']} Stadtteile)", 10, SANS, LEISE)).arrange(RIGHT, buff=0.08)
        if nur is None:
            self.blattwechsel(3, "Befunde über Potsdam", ueb, f3)
        else:
            self.add(ueb, f3)
        karte = None
        for i, b in enumerate(befunde):
            neu = self.befund_karte(b["feld"], b["klassen"])
            marken = VGroup()
            for wo, art, wert in b["marken"]:
                t = next(t for t in neu if t.nr == wo)
                umriss = t.copy().set_fill(opacity=0).set_stroke(VIOLETT, 3.2)
                d = TL[wo]
                schild = VGroup(T(d["name"], 14, SCHMAL_SB, VIOLETT),
                                T(f"{wert} ({art})" if art else wert, 13, SANS_M, TINTE)).arrange(DOWN, aligned_edge=LEFT, buff=0.02)
                schild.set_z_index(3)
                hint = Rectangle(width=schild.width + 0.14, height=schild.height + 0.1).set_stroke(VIOLETT, 0.8).set_fill(PAPIER, 0.94)
                ziel = t.get_center()
                links = ziel[0] < -3.45
                pos = ziel + (LEFT if links else RIGHT) * 1.35 + UP * 0.35
                pos[0] = max(-6.0, min(-0.6, pos[0]))
                hint.move_to(pos)
                # zwei Schilder dicht beieinander (Bornstedt, Bornim): das zweite unter die Karte des ersten
                for m in marken:
                    alt = m[2]
                    if abs(alt.get_x() - hint.get_x()) < (alt.width + hint.width) / 2 + 0.05 and abs(alt.get_y() - hint.get_y()) < (alt.height + hint.height) / 2 + 0.05:
                        hint.next_to(alt, DOWN, buff=0.12).align_to(alt, RIGHT if links else LEFT)
                schild.move_to(hint)
                ln = VGroup(Line(ziel, hint.get_right() if links else hint.get_left()).set_stroke(VIOLETT, 1.2), Dot(ziel, radius=0.035, color=VIOLETT))
                marken.add(VGroup(umriss, ln, hint, schild))
            # Legende
            if b["leg"]:
                kast = VGroup(*[Rectangle(width=0.42, height=0.14).set_stroke(width=0).set_fill(c, 1) for c in STUFEN]).arrange(RIGHT, buff=0)
                zahlen = VGroup(*[T(z, 9, SANS, LEISE).move_to(kast.get_left() + RIGHT * 0.42 * k + DOWN * 0.17) for k, z in enumerate(b["leg"])])
                leg = VGroup(T(b["leg_t"], 10, SANS_M, TINTE), VGroup(kast, zahlen)).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
            else:
                kast = VGroup(*[Rectangle(width=0.42, height=0.14).set_stroke(width=0).set_fill(c, 1) for c in STUFEN]).arrange(RIGHT, buff=0)
                zahlen = VGroup(*[T(de(z), 9, SANS, LEISE).move_to(kast.get_left() + RIGHT * 0.42 * (k + 1) + DOWN * 0.17) for k, z in enumerate(u18_gr)])
                leg = VGroup(T(b["leg_t"], 10, SANS_M, TINTE), VGroup(kast, zahlen)).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
            gl = grau_l.copy()
            legende = VGroup(leg, gl).arrange(DOWN, aligned_edge=LEFT, buff=0.18).move_to([0.95, -2.05, 0], aligned_edge=UL)

            # Tafel rechts
            thema = T(b["thema"].upper(), 14, SCHMAL_SB, VIOLETT)
            zahl = T(b["zahl"], 96, SCHMAL_SB, TINTE)
            satz = VGroup(*[T(z, 23, SANS_M) for z in self.umbrechen(b["satz"], 36)]).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
            satz.scale_to_fit_width(min(satz.width, 5.5))
            einh = T(b["einheit"], 12, SANS, LEISE)
            tafel = VGroup(thema, zahl, satz, einh).arrange(DOWN, aligned_edge=LEFT, buff=0.16).move_to([0.95, 2.2, 0], aligned_edge=UL)
            teile = [tafel]
            if b["skala"]:
                x0, x1, ys = 0.95, 6.35, -1.25
                achse = Line([x0, ys, 0], [x1, ys, 0]).set_stroke(TINTE, 1.2)
                striche = VGroup(*[Line([x0 + (x1 - x0) * k / 5, ys - 0.06, 0], [x0 + (x1 - x0) * k / 5, ys + 0.06, 0]).set_stroke(TINTE, 1)
                                   for k in range(6)])
                beschr = VGroup(*[T(f"{b['skala'] * k // 5}", 10, SANS, LEISE).move_to([x0 + (x1 - x0) * k / 5, ys - 0.2, 0]) for k in range(6)])
                punkte = VGroup()
                for nr, t in TL.items():
                    if t["ew"] >= B["min_ew"]:
                        punkte.add(Dot([x0 + (x1 - x0) * t[b["feld"]] / b["skala"], ys + 0.18, 0], radius=0.045, color=STUFEN[3]))
                wert_st = S[b["feld"]]["prozent"]
                pot = VGroup(Line([x0 + (x1 - x0) * wert_st / b["skala"], ys - 0.02, 0], [x0 + (x1 - x0) * wert_st / b["skala"], ys + 0.42, 0]).set_stroke(TINTE, 2.2))
                pot.add(T(f"Potsdam {de(wert_st)} %", 11, SANS_SB).next_to(pot[0], UP, buff=0.04))
                sk_t = T(f"jeder Punkt ein Stadtteil ab {de(B['min_ew'])} Einwohnern, Anteil in %" + ("" if b["skala"] == 100 else f", Skala 0 bis {b['skala']} %"), 10, SANS, LEISE).move_to([x0, ys - 0.45, 0], aligned_edge=LEFT)
                skala = VGroup(achse, striche, beschr, punkte, pot, sk_t)
                teile.append(skala)
            rechts = VGroup(*teile)

            if karte is None:
                karte = neu
                self.play(LaggedStart(*[FadeIn(t) for t in karte], lag_ratio=0.02), FadeIn(legende), run_time=1.1)
                self.play(FadeIn(tafel[0]), FadeIn(tafel[1], shift=UP * 0.15), run_time=0.6)
            else:
                # erst das Alte weg, dann das Neue: keine zwei Zahlen übereinander
                self.play(FadeOut(self.alt_rechts), FadeOut(self.alt_marken), FadeOut(self.alt_leg), run_time=0.35)
                self.play(*[t.animate.set_fill(n.get_fill_color(), 1) for t, n in zip(karte, neu, strict=True)], FadeIn(legende),
                          FadeIn(tafel[0]), FadeIn(tafel[1], shift=UP * 0.15), run_time=0.7)
            self.play(FadeIn(tafel[2], shift=UP * 0.06), FadeIn(tafel[3]), *([Create(rechts[1][0]), FadeIn(rechts[1][1:3])] if b["skala"] else []),
                      run_time=0.6)
            if b["skala"]:
                self.play(LaggedStart(*[GrowFromCenter(p) for p in rechts[1][3]], lag_ratio=0.03), FadeIn(rechts[1][4]), FadeIn(rechts[1][5]),
                          run_time=0.8)
            self.play(LaggedStart(*[AnimationGroup(Create(m[0]), Create(m[1]), FadeIn(m[2]), FadeIn(m[3])) for m in marken], lag_ratio=0.4),
                      run_time=0.9)
            self.alt_rechts, self.alt_marken, self.alt_leg = rechts, marken, legende
            self.wait(2.2 if i < len(befunde) - 1 else 2.8)

    # 4 ----------------------------------------------------------------------
    def blatt4(self):
        ueb = self.ueberschrift("04", "Was die Zahlen nicht sagen")
        # drei Zeilen in voller Größe wie auf Blatt 1 und 3 (vorher zwei lange, auf 11 px geschrumpft)
        bz, gf_form = B["vermerk"]["bauzeit"].split("; ", 1)
        pruefe(gf_form.startswith("Gebäudeform © "), "Vermerk Bauzeit: zweiter Teil Gebäudeform")
        f4 = self.fuss(f"Bauzeit {bz}",
                       f"{gf_form} · {B['vermerk']['wikidata']}",
                       f"Grenzfall: Zensus {B['vermerk']['zensus']}")
        self.blattwechsel(4, "Grenzen offen", ueb, f4)
        trenner = VGroup(Line([0.55, 2.15, 0], [0.55, -2.75, 0]), Line([3.55, 2.15, 0], [3.55, -2.75, 0])).set_stroke(LINIE, 1.4)
        self.play(Create(trenner), run_time=0.3)

        # A: Bauzeit ist geschätzt
        jg = B["je_g"]
        ges = sum(jg.values())
        dat = jg["belegt"] + jg["geschaetzt"]
        pruefe(dat == 26716, "datierte Gebäude")
        breite = 6.5
        stuecke = [("belegt", jg["belegt"], VIOLETT), ("geschätzt", jg["geschaetzt"], STUFEN[3]), ("nicht datiert", jg["nicht_datiert"], GRAU)]
        balken, x = VGroup(), -6.25
        for name, n, c in stuecke:
            w = max(0.03, breite * n / ges)
            balken.add(Rectangle(width=w, height=0.32).set_stroke(PAPIER, 0.6).set_fill(c, 1).move_to([x, 1.3, 0], aligned_edge=LEFT))
            x += w
        a_kopf = VGroup(T("Bauzeit je Gebäude ist geschätzt", 22, SCHMAL_SB),
                        T(f"Herkunft der Bauzeit je Gebäude ({de(ges)}): datiert sind {de(dat)}, davon {de(jg['belegt'])} belegt", 12, SANS, LEISE)).arrange(DOWN, aligned_edge=LEFT, buff=0.05)
        a_kopf.move_to([-6.25, 2.15, 0], aligned_edge=UL)
        a_leg = VGroup(*[VGroup(Square(0.13).set_stroke(width=0).set_fill(c, 1), T(f"{name} {de(n)}", 12, SANS)).arrange(RIGHT, buff=0.07)
                         for name, n, c in stuecke]).arrange(RIGHT, buff=0.3).next_to(balken, DOWN, buff=0.1).align_to(balken, LEFT)
        self.play(FadeIn(a_kopf), run_time=0.4)
        self.play(LaggedStart(*[GrowFromEdge(b, LEFT) for b in balken], lag_ratio=0.3), FadeIn(a_leg), run_time=1.0)

        rt = B["rt"]
        gitter = VGroup(*[Square(0.155).set_stroke(TINTE, 0.6) for _ in range(rt["bewertet"])]).arrange_in_grid(cols=26, buff=0.03)
        gitter.move_to([-6.25, 0.3, 0], aligned_edge=UL)
        zahl = T(f"{rt['treffer']} von {rt['bewertet']}", 40, SCHMAL_SB, STUFEN[4])
        zahl.next_to(gitter, DOWN, buff=0.15).align_to(gitter, LEFT)
        rt_t = VGroup(T(f"Treffer der Stufe 4 (Zensus-Verteilung) im Rücktest: {rt['quote']} %, 95-%-Intervall {de(rt['ki']['unten'])} bis {de(rt['ki']['oben'])} %", 12, SANS_M),
                      T(f"Rücktest an {rt['n']} Gebäuden in Bornstedt; Referenz: Sichtprüfung von Luftbildern", 12, SANS),
                      T("durch einen KI-Agenten, ohne zweite Bewertung. Reihenfolge der Kästchen schematisch.", 12, SANS)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.04).next_to(zahl, DOWN, buff=0.08).align_to(gitter, LEFT)
        self.play(Create(gitter), run_time=0.6)
        self.play(LaggedStart(*[q.animate.set_fill(STUFEN[3], 1).set_stroke(STUFEN[3], 0.6) for q in gitter[:rt["treffer"]]], lag_ratio=0.01),
                  run_time=1.3)
        self.play(FadeIn(zahl, shift=UP * 0.1), FadeIn(rt_t), run_time=0.6)

        # B: Einzeljahr
        b_zahl = T(str(B["einzeljahr"]), 84, SCHMAL_SB, TINTE).move_to([2.05, 1.05, 0])
        b_t = VGroup(T("Gebäude mit Einzeljahr", 20, SCHMAL_SB),
                     T(f"davon mit Wohnraum: {B['einzeljahr_wohnraum']}", 16, SANS_M, VIOLETT),
                     T("Sonst nur Klassen und Spannen:", 12, SANS, LEISE),
                     T("kein Baujahr für ein Wohnhaus,", 12, SANS, LEISE),
                     T("keine Adresse, keine Kennung", 12, SANS, LEISE),
                     T("(Entscheidung A3)", 12, SANS, LEISE)).arrange(DOWN, buff=0.06)
        b_t.next_to(b_zahl, DOWN, buff=0.2)
        self.play(FadeIn(b_zahl, scale=0.9), FadeIn(b_t), run_time=0.8)

        # C: Grenzfall, eine Zelle auf der Grenze (schematisch)
        gf = B["grenzfall"]
        zelle = Square(1.3).set_stroke(TINTE, 1.6).set_fill(STUFEN[1], 1).move_to([5.2, 0.95, 0])
        oben_g, unten_g = zelle.get_corner(UL) + RIGHT * 1.12, zelle.get_corner(DL) + RIGHT * 0.78
        teil_a = Polygon(zelle.get_corner(UL), oben_g, unten_g, zelle.get_corner(DL)).set_stroke(width=0).set_fill(STUFEN[2], 1)
        grenze = Line(oben_g + (oben_g - unten_g) * 0.09, unten_g - (oben_g - unten_g) * 0.09).set_stroke(VIOLETT, 3.2)
        mp = Dot(zelle.get_center(), radius=0.06, color=TINTE)
        links = T("A", 16, SCHMAL_SB, LEISE).move_to(zelle.get_center() + LEFT * 0.85 + UP * 0.5)
        rechts = T("B", 16, SCHMAL_SB, LEISE).move_to(zelle.get_center() + RIGHT * 0.85 + UP * 0.5)
        c_kopf = T("Wem gehört die Zelle?", 20, SCHMAL_SB).move_to([5.2, 2.15, 0], aligned_edge=UP)
        c_t = VGroup(T("Mittelpunkt in A: zählt ganz für A", 12, SANS_M),
                     T(f"{gf['grenzzellen']} Grenzzellen, {de(gf['ew_in_grenzzellen'])} Einwohner", 12, SANS),
                     T(f"Mittelpunkt: {de(gf['mittelpunkt'])}", 12, SANS),
                     T(f"nach Flächenanteil: {de(gf['flaechenanteilig'])}", 12, SANS),
                     T("größte Abweichung ab 5.000 Einwohnern:", 12, SANS, LEISE),
                     T(f"{B['grenzfall_gross']['name']} {'+' if B['grenzfall_gross']['prozent'] > 0 else ''}{de(B['grenzfall_gross']['prozent'])} %", 14, SANS_SB, VIOLETT),
                     T("nach Mittelpunkt " + ("mehr" if B['grenzfall_gross']['prozent'] > 0 else "weniger") + " als nach Fläche", 10, SANS, LEISE),
                     T("Zelle schematisch", 10, SANS, LEISE)).arrange(DOWN, buff=0.06)
        c_t.scale_to_fit_width(min(c_t.width, 2.75)).next_to(zelle, DOWN, buff=0.22).set_x(5.1)
        self.play(FadeIn(c_kopf), Create(zelle), run_time=0.5)
        self.play(Create(grenze), FadeIn(links), FadeIn(rechts), run_time=0.5)
        teil_a.set_z_index(1)
        umriss_z = zelle.copy().set_fill(opacity=0).set_z_index(2)
        grenze.set_z_index(3)
        mp.set_z_index(4)
        self.add(umriss_z)
        self.play(FadeIn(teil_a), GrowFromCenter(mp), Flash(mp, color=VIOLETT, line_length=0.15), run_time=0.6)
        self.play(FadeIn(c_t, shift=UP * 0.06), run_time=0.6)
        self.wait(3.4)

    # 5 ----------------------------------------------------------------------
    def blatt5(self):
        ueb = self.ueberschrift("05", "Nachprüfbar, auch die Fehler")
        self.blattwechsel(5, "Belege", ueb)
        trenner = VGroup(Line([1.25, 2.15, 0], [1.25, -2.0, 0])).set_stroke(LINIE, 1.4)

        # Prüfstände von pruefen.sh: je Stand 18 Kästchen
        s1, s2, s3 = B["stand1"], B["stand2"], B["stand3"]
        stände = [(f"{s1['datum']} · {s1['commit']}", s1["gruen"], s1["pruefungen"], f"{s1['befund']} mit Befund: " + ", ".join(p.split('/')[-1] for p in s1["befunde"]),
                   "belege/pruefstand-20261106-1cf8d56/pruefen.log"),
                  (f"Stand {s2['commit']}", s2["gruen"], s2["pruefungen"], f"Nachprüfung laut Audit: „{B['k29_wortlaut']}“",
                   "berichte/audit_20261106.md, Punkt K29")]
        if s3:
            stände.append((f"{s3['datum']} · {s3['commit']}", s3["gruen"], s3["pruefungen"],
                           f"{s3['befund']} mit Befund, {s3['uebersprungen']} übersprungen",
                           str(Path(PRUEFLOG).resolve().relative_to(REPO))))
        kopf = VGroup(T("./pruefen.sh", 22, SCHMAL_SB), T(f"{s1['pruefungen']} Prüfungen ohne Netz und ohne Datenbank, darunter {['keine', 'eine', 'zwei', 'drei', 'vier', 'fünf'][B['browser']]} im Browser; Lage der Kästchen schematisch", 12, SANS, LEISE)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.05).move_to([-6.25, 2.15, 0], aligned_edge=UL)
        zeilen = VGroup()
        for k, (wann, gruen, alle, was, datei) in enumerate(stände):
            kaest = VGroup(*[Square(0.22).set_stroke(TINTE, 0.8) for _ in range(alle)]).arrange(RIGHT, buff=0.05)
            t1 = VGroup(T(wann, 15, SCHMAL_SB), T(f"{gruen} von {alle} grün", 15, SANS_M, STUFEN[4] if gruen == alle else VIOLETT)).arrange(RIGHT, buff=0.25)
            t2 = VGroup(T(was, 11, SANS), T(datei, 10, SANS, LEISE)).arrange(DOWN, aligned_edge=LEFT, buff=0.03)
            z = VGroup(t1, kaest, t2).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
            z.move_to([-6.25, 1.2 - k * 1.25, 0], aligned_edge=UL)
            z.gruen = gruen
            zeilen.add(z)
        self.play(FadeIn(kopf), Create(trenner), run_time=0.4)
        for z in zeilen:
            self.play(FadeIn(z[0][0]), Create(z[1]), run_time=0.35)
            # Befunde: die Kästchen am Ende bleiben offen und violett gerandet (Position schematisch)
            anim = [q.animate.set_fill(STUFEN[3], 1).set_stroke(STUFEN[3], 0.8) for q in z[1][:z.gruen]]
            anim += [q.animate.set_stroke(VIOLETT, 2.2) for q in z[1][z.gruen:]]
            self.play(LaggedStart(*anim, lag_ratio=0.03), run_time=0.7)
            self.play(FadeIn(z[0][1]), FadeIn(z[2]), run_time=0.3)
        self.wait(0.6)

        # Entscheidungsprotokoll und Zur Prüfung
        ent = B["entscheidungen"]
        r_kopf = VGroup(T("Entscheidungsprotokoll", 22, SCHMAL_SB),
                        T(f"docs/entscheidungen.md: {ent[0][0]} bis {ent[-1][0]}, je mit Begründung", 12, SANS, LEISE)
                        ).arrange(DOWN, aligned_edge=LEFT, buff=0.05).move_to([1.6, 2.15, 0], aligned_edge=UL)
        reg = VGroup()
        for a, titel in ent:
            kurz = titel if len(titel) <= 37 else titel[:titel.rfind(" ", 0, 36)]
            if kurz != titel:
                kurz = (kurz[:kurz.index("„")].rstrip() if kurz.count("„") > kurz.count("“") else kurz).rstrip(",:") + " …"
            reg.add(VGroup(T(a, 10, SCHMAL_SB, VIOLETT), T(kurz, 10, SANS)).arrange(RIGHT, buff=0.12))
        for r in reg:
            r[1].move_to(r[0].get_right() + RIGHT * 0.12, aligned_edge=LEFT)
        reg.arrange_in_grid(rows=10, cols=2, col_alignments="ll", buff=(0.35, 0.07), flow_order="dr")
        for r in reg:
            r[1].align_to(r[0].get_left() + RIGHT * 0.42, LEFT)
        reg.scale_to_fit_width(min(reg.width, 5.1)).move_to([1.6, 1.3, 0], aligned_edge=UL)
        weitere = VGroup(T(f"„Nicht geprüft sind“: {B['nicht_geprueft']} Punkte, offen benannt", 13, SANS_M),
                         T(f"README „Zur Prüfung“: {B['zur_pruefung']} Kernzahlen, je mit Beleg und Skript", 13, SANS_M)
                         ).arrange(DOWN, aligned_edge=LEFT, buff=0.08).next_to(reg, DOWN, buff=0.22).align_to(reg, LEFT)
        self.play(FadeIn(r_kopf), LaggedStart(*[FadeIn(r, shift=RIGHT * 0.05) for r in reg], lag_ratio=0.05), run_time=1.4)
        self.play(FadeIn(weitere), run_time=0.5)
        self.wait(1.6)

        # Schluss
        link = T(B["url"], 26, SCHMAL_SB, VIOLETT)
        name = T("André Stiebitz · Stiebitz Souverain Systems UG (haftungsbeschränkt)", 14, SANS, LEISE)
        schluss = VGroup(link, name).arrange(DOWN, buff=0.12).move_to([-1.8, -2.75, 0])
        linie = Line(schluss.get_corner(UL) + UP * 0.12, schluss.get_corner(UR) + UP * 0.12).set_stroke(TINTE, 1)
        self.play(Create(linie), FadeIn(link, shift=UP * 0.08), run_time=0.7)
        self.play(FadeIn(name), run_time=0.4)
        self.wait(3.0)


class Standbild(Erklaer):
    """Blatt 3, erster Befund (Fernwärme) im Endzustand: manim -s ... film.py Standbild"""

    def construct(self):
        self.raster, self.rand = self.zeichenblatt()
        self.sf = self.schriftfeld(3, "Befunde über Potsdam")
        self.add(self.raster, self.rand, self.sf)
        self.blatt3(nur=0)


class Probe(Erklaer):
    """Kurze Probe: Blatt 1 und der erste Befund von Blatt 3."""

    def construct(self):
        self.raster, self.rand = self.zeichenblatt()
        self.sf = self.schriftfeld(1, "Warum")
        self.add(self.raster, self.rand, self.sf)
        self.blatt1()
        self.raeumen()
        self.blattwechsel(3, "Befunde über Potsdam")
        self.blatt3(nur=0)
