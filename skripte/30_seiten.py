"""Seitengenerator: erzeugt jede Seite in jeder Sprache aus vorlagen/ und texte/, damit die Fassungen synchron bleiben.

Für jede Seite aus der Ortskonfiguration (seiten) und jede Sprache (sprachen) entsteht eine fertige HTML-Datei:
die Standardsprache im Wurzelordner (index.html, karta.html …), die übrigen in <lang>/ mit denselben Dateinamen.
Die Seiten brauchen zur Laufzeit keinen Build und kein fetch (laufen per file://).

Eingänge
  vorlagen/_rahmen.html     Rahmen aller Seiten (Kopf, Sprachschalter, Hinweise, Fuß, Skripte)
  vorlagen/<seite>.html     Inhalt; erste Zeilen <!--seite … --> mit daten: (Datendateien), texte: (Namensräume),
                            robots: (index/noindex), optional css: (weitere Stylesheets nach rahmen.css) und
                            skripte: (Module nach rahmen.js, in dieser Reihenfolge, z. B. für eine Karte
                            vendor/maplibre-gl.js daten/grundkarte.js themen.js <modul>.js)
                            rahmen: eigen  die Vorlage ist die ganze Seite (eigener Kopf, eigene Skripte): kein
                            _rahmen.html; ersetzt werden {{t:…}}, {{plural:…}}, {{ort:…}}, {{block:…}}, {{liste:…}}
                            sowie {{lang}}, {{seite}}, {{wurzel}}, {{wurzel_sprache}}, sonst bleibt jedes Byte;
                            daten:, css:, skripte: sind dann nicht erlaubt
  texte/<lang>/*.js         kurze Texte (skripte/textschicht.py liest sie)
  texte/<lang>/bloecke/<name>.html   lange Texte; fehlt ein Block, bleibt die Stelle leer (kein Platzhaltersatz)
  daten/ort.js-Quelle       Ortskonfiguration config/<ort>.yaml (über skripte/ort_konfig.py)
Platzhalter in Vorlagen
  {{t:schluessel}}          Text der Sprache, HTML-maskiert
  {{plural:schluessel:teile}}  Pluraltext mit n = Zahl der Stadtteile
  {{ort:feld}}              sprachabhängiger Wert der Ortskonfiguration (name, stadt …)
  {{block:name}}            langer Text texte/<lang>/bloecke/<name>.html
  {{liste:spis}}            Inhaltsverzeichnis aus den Abschnitten <section id><h2> der Seite
  {{liste:teile}}, {{liste:themenseiten}}   Listen aus der Ortskonfiguration; themenseiten = Kartenraster aus
                            rubriken.<r>.karten (Titel und Satz je Seite), ohne Rubrik wie früher alle Seiten ohne
                            Navigation und Unterseiten; Seiten unter in_vorbereitung nie (erreichbar, aber nicht verlinkt)
  {{wurzel}}, {{wurzel_sprache}}   relativer Weg zum Wurzelordner bzw. zum Ordner der Sprache
Ausgabe ist deterministisch (kein Datum, kein Commit), damit --pruefen byte-gleich vergleichen kann.

Aufruf:
  python -I skripte/30_seiten.py            alle Seiten schreiben
  python -I skripte/30_seiten.py --pruefen  erzeugen und mit den eingecheckten Dateien vergleichen; dazu: keine
                                            fremde *.html im Wurzel- und in den Sprachordnern. Rückgabe 1 bei Abweichung.
Kein Netz, keine Datenbank.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "skripte"))   # python -I lässt das Skriptverzeichnis weg
import ort_konfig  # noqa: E402
import textschicht  # noqa: E402

VORLAGEN = WURZEL / "vorlagen"
OG_LOCALE = {"pl": "pl_PL", "en": "en_GB", "de": "de_DE"}
PLATZ = re.compile(r"\{\{([a-z_]+)(?::([^}]*))?\}\}")


class Fehler(Exception):
    pass


def schl(seite: str) -> str:
    return seite.replace("-", "_")


def sw(wert, lang: str):
    return wert[lang] if isinstance(wert, dict) else wert


def vorlage_lesen(seite: str) -> tuple[dict, str]:
    p = VORLAGEN / f"{seite}.html"
    if not p.exists():
        raise Fehler(f"Vorlage fehlt: vorlagen/{seite}.html")
    t = p.read_text(encoding="utf-8")
    m = re.match(r"<!--seite\n(.*?)\n-->\n", t, re.S)
    if not m:
        raise Fehler(f"vorlagen/{seite}.html: Kopf <!--seite … --> fehlt")
    kopf = {}
    for z in m.group(1).splitlines():
        k, _, v = z.partition(":")
        kopf[k.strip()] = v.split()
    for k in ("daten", "texte", "robots", "css", "skripte", "rahmen"):
        kopf.setdefault(k, [])
    if kopf["rahmen"] not in ([], ["eigen"]):
        raise Fehler(f"vorlagen/{seite}.html: rahmen: nur eigen vorgesehen")
    if kopf["rahmen"]:
        if kopf["daten"] or kopf["css"] or kopf["skripte"]:
            raise Fehler(f"vorlagen/{seite}.html: rahmen: eigen lädt Daten, Stile und Skripte selbst (daten:, css:, skripte: leer lassen)")
        return kopf, t[m.end():]
    for d in kopf["css"] + kopf["skripte"]:
        if not (WURZEL / d).is_file():
            raise Fehler(f"vorlagen/{seite}.html: {d} (css:/skripte:) gibt es nicht")
    if "kern" not in kopf["texte"]:
        raise Fehler(f"vorlagen/{seite}.html: texte: muss kern enthalten")
    return kopf, t[m.end():]


# {{liste:spis}}: Inhaltsverzeichnis aus den Abschnitten <section id="…"><h2>…</h2> der Seite (Reihenfolge wie im Text)
SPIS_MARKE = "<!--spis-->"
ABSCHNITT = re.compile(r'<section id="([a-z0-9-]+)">\s*<h2>(.*?)</h2>', re.S)


def spis(inhalt: str, seite: str, lang: str) -> str:
    z = [f'  <li><a class="link" href="#{i}">{re.sub(r"<[^>]+>", "", h).strip()}</a></li>' for i, h in ABSCHNITT.findall(inhalt)]
    if not z:
        raise Fehler(f"{seite} ({lang}): liste:spis ohne Abschnitte <section id><h2>")
    return '<ol class="spis__liste">\n' + "\n".join(z) + "\n</ol>"


class Erzeuger:
    def __init__(self) -> None:
        self.k = ort_konfig.lade()
        self.sprachen: list[str] = self.k["sprachen"]
        self.seiten: list[str] = [str(s) for s in self.k["seiten"]]
        self.texte = {l: textschicht.flach(l) for l in self.sprachen}
        self.rahmen = (VORLAGEN / "_rahmen.html").read_text(encoding="utf-8")
        self.unter = {s: g for g, l in (self.k.get("unterseiten") or {}).items() for s in l}
        self.vorbereitung = [str(s) for s in self.k.get("in_vorbereitung") or []]
        # Rubriken: Punkte der Hauptnavigation ohne eigene Seite (Ziel, Textschlüssel, Seiten der Übersicht)
        self.rubriken: dict = self.k.get("rubriken") or {}
        # Seitenstile der Stadt (Ortskonfiguration stile:), geladen nach basis.css und vor rahmen.css
        self.stile = [str(s) for s in self.k.get("stile", ["atlas.css"])]
        for s in self.stile:
            if not (WURZEL / s).is_file():
                raise Fehler(f"stile: {s} gibt es nicht")
        for s in [*self.unter, *self.vorbereitung, *(x for r in self.rubriken.values() for x in r.get("karten", []))]:
            if s not in self.seiten:
                raise Fehler(f"unterseiten/in_vorbereitung/rubriken: Seite {s} steht nicht in seiten")
        for s in [*self.k.get("navigation", []), *(self.k.get("unterseiten") or {})]:
            if s not in self.seiten and s not in self.rubriken:
                raise Fehler(f"navigation/unterseiten: {s} ist weder Seite noch Rubrik")

    # --- Wege
    def ordner(self, lang: str) -> str:
        return "" if lang == self.sprachen[0] else lang + "/"

    def ziel(self, seite: str, lang: str) -> Path:
        return WURZEL / self.ordner(lang) / f"{seite}.html"

    def von_nach(self, von: str, nach: str, seite: str) -> str:
        """Relativer Link von einer Seite in Sprache von zur Seite in Sprache nach."""
        hoch = "../" if self.ordner(von) else ""
        return hoch + self.ordner(nach) + f"{seite}.html"

    def absolut(self, seite: str, lang: str) -> str:
        return self.k["basis_url"] + self.ordner(lang) + ("" if seite == "index" else f"{seite}.html")

    # --- Texte
    def t(self, lang: str, k: str, roh: bool = False) -> str:
        if k not in self.texte[lang]:
            raise Fehler(f"Schlüssel {k} fehlt in texte/{lang}/")
        v = self.texte[lang][k]
        if not isinstance(v, str):
            raise Fehler(f"Schlüssel {k} ({lang}) ist kein einfacher Text")
        return v if roh else html.escape(v)

    def plural(self, lang: str, k: str, n: int) -> str:
        v = self.texte[lang].get(k)
        if not isinstance(v, dict):
            raise Fehler(f"Schlüssel {k} ({lang}) ist kein Pluraltext")
        form = textschicht.pluralform(lang, n)
        return html.escape(str(v.get(form, v.get("other"))).replace("{n}", str(n)))

    # --- Bausteine
    def liste(self, art: str, lang: str) -> str:
        ws = ""   # Links bleiben im Ordner der Sprache (gleiche Dateinamen in jeder Sprache)
        if art == "teile":
            g = self.k["gliederung"]
            muster = sw(g["anzeige_muster"], lang)
            z = []
            for t in g["teile"]:
                name = muster.replace("{roemisch}", t.get("roemisch") or "").replace("{nr}", t["nr"]).replace("{name}", t["name"])
                z.append(f'  <li><a class="link" href="{ws}dzielnica.html#st={t["nr"]}">{html.escape(name)}</a></li>')
            return '<ul class="teile-liste">\n' + "\n".join(z) + "\n</ul>"
        if art == "themenseiten":
            # Mit Rubrik „karten“: Kartenraster mit Titel und einem Satz je Seite, Reihenfolge der Konfiguration
            karten = [s for r in self.rubriken.values() for s in r.get("karten", []) if s not in self.vorbereitung]
            if karten:
                z = [f'  <li><a href="{s}.html"><span class="themenkarte__titel">{self.t(lang, f"seiten.{schl(s)}.h1")}</span>'
                     f'<span class="themenkarte__satz">{self.t(lang, f"seiten.{schl(s)}.beschreibung")}</span></a></li>'
                     for s in karten]
                return '<ul class="themenkarten">\n' + "\n".join(z) + "\n</ul>"
            nav = set(self.k.get("navigation", [])) | set(self.unter) | set(self.vorbereitung)
            z = [f'  <li><a class="link" href="{s}.html">{self.t(lang, f"seiten.{schl(s)}.h1")}</a></li>'
                 for s in self.seiten if s not in nav and s not in ("index", "404")]
            return "<ul>\n" + "\n".join(z) + "\n</ul>"
        if art == "spis":
            return SPIS_MARKE   # Inhaltsverzeichnis: wird nach dem Einsetzen der Blöcke aus deren Abschnitten gebaut
        raise Fehler(f"unbekannte Liste {art}")

    def block(self, name: str, lang: str) -> str:
        p = WURZEL / "texte" / lang / "bloecke" / f"{name}.html"
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
        return ""

    def ersetzen(self, text: str, lang: str, werte: dict[str, str]) -> str:
        def eins(m: re.Match) -> str:
            art, arg = m.group(1), m.group(2)
            if arg is None:
                if art not in werte:
                    raise Fehler(f"unbekannter Platzhalter {{{{{art}}}}}")
                return werte[art]
            if art == "t":
                return self.t(lang, arg)
            if art == "plural":
                k, _, menge = arg.partition(":")
                if menge != "teile":
                    raise Fehler(f"plural: nur :teile vorgesehen, nicht {menge}")
                return self.plural(lang, k, len(self.k["gliederung"]["teile"]))
            if art == "ort":
                v = sw(self.k.get(arg), lang)
                if not isinstance(v, str):
                    raise Fehler(f"ort:{arg} fehlt oder ist kein Text")
                return html.escape(v)
            if art == "block":
                return self.ersetzen(self.block(arg, lang), lang, werte)
            if art == "liste":
                return self.liste(arg, lang)
            raise Fehler(f"unbekannter Platzhalter {m.group(0)}")
        # zweimal: Rahmen setzt {{inhalt}} ein, dessen Platzhalter danach dran sind
        return PLATZ.sub(eins, text)

    def seite(self, seite: str, lang: str) -> str:
        kopf, inhalt = vorlage_lesen(seite)
        if kopf["rahmen"]:
            return self.eigene_seite(seite, lang, inhalt)
        w = "../" if self.ordner(lang) else ""
        k = schl(seite)
        titel = f"{self.t(lang, f'seiten.{k}.h1', roh=True)} · {sw(self.k['name'], lang)}"
        noindex = "noindex" in kopf["robots"]
        links = []
        if not noindex:
            for l in self.sprachen:
                links.append(f'<link rel="alternate" hreflang="{l}" href="{self.absolut(seite, l)}">')
            links.append(f'<link rel="alternate" hreflang="x-default" href="{self.absolut(seite, self.sprachen[0])}">')
            links.append(f'<link rel="canonical" href="{self.absolut(seite, lang)}">')
        og = [f'<meta property="og:locale" content="{OG_LOCALE[lang]}">'] + [
            f'<meta property="og:locale:alternate" content="{OG_LOCALE[l]}">' for l in self.sprachen if l != lang]
        nav = []
        gruppe = self.unter.get(seite, seite)
        for s in self.k.get("navigation", []):
            cur = ' aria-current="page"' if s == seite else (' aria-current="true"' if s == gruppe else "")
            r = self.rubriken.get(s)
            ziel = r["ziel"] if r else f"{s}.html"
            text = self.t(lang, r["text"]) if r else self.t(lang, f"seiten.{schl(s)}.nav")
            nav.append(f'        <li><a class="nav" href="{ziel}"{cur}><span>{text}</span></a></li>')
        unter = ""
        if seite in self.unter:
            g = self.unter[seite]
            seite_cur = ' aria-current="page"'
            z = [f'      <li><a class="nav" href="{s}.html"{seite_cur if s == seite else ""}><span>{self.t(lang, f"seiten.{schl(s)}.nav")}</span></a></li>'
                 for s in self.k["unterseiten"][g]]
            name = self.t(lang, self.rubriken[g]["text"]) if g in self.rubriken else self.t(lang, f"seiten.{schl(g)}.h1")
            unter = (f'  <nav class="kopf-unter" aria-label="{name}">\n    <ul>\n'
                     + "\n".join(z) + "\n    </ul>\n  </nav>\n")
        wahl, hinweis = [], []
        for l in self.sprachen:
            cur = ' aria-current="true"' if l == lang else ""
            name = self.t(l, "kern.sprache_name")
            wahl.append(f'        <li><a data-sprache="{l}" hreflang="{l}" lang="{l}" title="{name}" href="{self.von_nach(lang, l, seite)}"{cur}>{l.upper()}</a></li>')
            if l != lang:
                hinweis.append(f'<a class="link" data-sprache="{l}" hreflang="{l}" lang="{l}" data-schliessen="{self.t(l, "kern.schliessen")}" href="{self.von_nach(lang, l, seite)}">{self.t(l, "kern.sprache_auch")}</a>')
        skripte = [f'<script defer src="{w}daten/ort.js"></script>', f'<script defer src="{w}i18n.js"></script>']
        skripte += [f'<script defer src="{w}texte/{lang}/{ns}.js"></script>' for ns in kopf["texte"]]
        skripte += [f'<script defer src="{w}{d}"></script>' for d in kopf["daten"]]
        skripte.append(f'<script defer src="{w}kopf.js"></script>')
        skripte.append(f'<script defer src="{w}rahmen.js"></script>')
        skripte += [f'<script defer src="{w}{d}"></script>' for d in kopf["skripte"]]
        css = "".join(f'<link rel="stylesheet" href="{w}{d}">\n' for d in kopf["css"])
        # Seitenstile der Stadt zwischen Grundgestaltung (basis.css) und Rahmen (rahmen.css); ohne Angabe atlas.css
        stile = "".join(f'<link rel="stylesheet" href="{w}{d}">\n' for d in self.stile)
        werte = {
            "lang": lang, "seite": seite, "titel": html.escape(titel), "wurzel": w, "wurzel_sprache": "",
            "beschreibung": self.t(lang, f"seiten.{k}.beschreibung"),
            "robots": '<meta name="robots" content="noindex">\n' if noindex else "",
            "sprachlinks": "\n".join(links), "og_locale": "\n".join(og), "css": css,
            "html_klasse": ' class="kopf-zwei"' if unter else "", "body_klasse": "textseite",
            "navigation": "\n".join(nav), "unternavigation": unter, "sprachwahl": "\n".join(wahl),
            "sprachhinweis": " ".join(hinweis), "skripte": "\n".join(skripte) + "\n", "stile": stile,
            "herausgeber": html.escape(self.k["herausgeber"]), "meldeweg": html.escape(self.k["meldeweg"]),
        }
        werte["inhalt"] = self.ersetzen(inhalt.strip(), lang, werte)
        if SPIS_MARKE in werte["inhalt"]:
            werte["inhalt"] = werte["inhalt"].replace(SPIS_MARKE, spis(werte["inhalt"], seite, lang))
        # Lädt die Seite eine _odbl-Datei oder zeigt ein Block einen beim Bauen eingesetzten Wert aus einer
        # (data-feld="…_odbl:…", skripte/16_bloecke_krakow.py), steht der Vermerk sichtbar im Fuß (Werte auf OSM-Grenzen, ODbL)
        werte["odbl"] = (f' <span class="fuss-seite__odbl">{self.t(lang, "kern.odbl")} <a class="link" '
                         f'href="https://www.openstreetmap.org/copyright">openstreetmap.org/copyright</a>.</span>'
                         if any("_odbl" in d for d in kopf["daten"])
                         or re.search(r'data-feld="[a-z0-9_]*_odbl:', werte["inhalt"]) else "")
        text = self.ersetzen(self.rahmen, lang, werte)
        if "{{" in text:
            raise Fehler(f"{seite} ({lang}): Platzhalter übrig")
        return text

    def eigene_seite(self, seite: str, lang: str, inhalt: str) -> str:
        """Vorlage mit rahmen: eigen: nur die Platzhalter mit Argument ersetzen, keine Rahmenwerte."""
        w = "../" if self.ordner(lang) else ""
        text = self.ersetzen(inhalt, lang, {"lang": lang, "seite": seite, "wurzel": w, "wurzel_sprache": ""})
        if SPIS_MARKE in text:
            text = text.replace(SPIS_MARKE, spis(text, seite, lang))
        if "{{" in text:
            raise Fehler(f"{seite} ({lang}): Platzhalter übrig")
        return text

    def alle(self) -> dict[Path, str]:
        return {self.ziel(s, l): self.seite(s, l) for l in self.sprachen for s in self.seiten}


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--pruefen", action="store_true")
    o = a.parse_args()
    try:
        e = Erzeuger()
        neu = e.alle()
    except (Fehler, textschicht.Textfehler, KeyError) as x:
        print(f"  FEHLT Seitengenerator: {x}")
        return 1
    if not o.pruefen:
        for p, t in neu.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(t, encoding="utf-8")
        print(f"{len(neu)} Seiten geschrieben ({len(e.seiten)} Seiten × {len(e.sprachen)} Sprachen)")
        return 0
    befund = 0
    abweichend = [p for p, t in neu.items() if not p.exists() or p.read_text(encoding="utf-8") != t]
    for p in abweichend:
        print(f"  FEHLT {p.relative_to(WURZEL)} ist nicht aktuell")
    befund += len(abweichend)
    vorhanden = set(WURZEL.glob("*.html"))
    for l in e.sprachen[1:]:
        vorhanden |= set((WURZEL / l).glob("*.html"))
    fremd = sorted(vorhanden - set(neu))
    for p in fremd:
        print(f"  FEHLT {p.relative_to(WURZEL)} ist keine erzeugte Seite (Vorlage fehlt oder Datei entfernen)")
    befund += len(fremd)
    if not befund:
        print(f"  ok    {len(neu)} Seiten ({len(e.seiten)} × {len(e.sprachen)} Sprachen) entsprechen vorlagen/ und texte/; keine fremden Seiten")
        return 0
    print("  python -I skripte/30_seiten.py neu ausführen")
    return 1


if __name__ == "__main__":
    sys.exit(main())
