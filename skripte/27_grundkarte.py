"""Grundkarte: gekürzter Auszug aus dem Vektorstil von basemap.de (bm_web_gry) als daten/grundkarte.js.

Liest nur die lokal abgelegte Kopie in $KIEZ_DATEN/eingang/basemapde/ (Herkunft und Prüfsummen in
eingang/HERKUNFT.md). Kein Netzabruf. Die Kacheln lädt später der Browser direkt bei sgx.geodatenzentrum.de.

Was wegfällt und warum:
  - Gebäude, Adressen, Gebäudesymbole: die Seiten zeichnen eigene Gebäude (sonst doppelt bzw. Z-Fighting)
  - Ebenen mit Sprite-Bildern (icon-image, *-pattern): kein Sprite-Abruf, die Seiten bleiben bei Ausfall ruhig
  - Themen ohne Potsdam-Bezug (Meer, Watt, Gebirge, Bergbau, Flughafen, Staats- und Landesgrenzen …)
  - Hintergrundfläche: die Seiten haben ihre eigene Papierfarbe

Ausgabe: window.KIEZ_GRUNDKARTE = {quelle, glyphs, unten, oben, vermerk}
  unten = Flächen und Linien (unter den Zellen), oben = Beschriftungen (über allen eigenen Ebenen).

Lizenz: CC BY 4.0, Quellenvermerk nach den Nutzungsbedingungen (eingang/basemapde/nutzungsbedingungen_basemapde.pdf),
Stil verändert. Aufruf: python -I skripte/27_grundkarte.py
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
KIEZ_DATEN = Path(os.environ.get("KIEZ_DATEN") or (WURZEL.parent / "kiezatlas-daten"))
EINGANG = KIEZ_DATEN / "eingang" / "basemapde"
ZIEL = WURZEL / "daten" / "grundkarte.js"

QUELLE_ALT = "smarttiles_de"
QUELLE = "bm"
WEG_SCHICHT = {"Gebaeudeflaeche", "Adresse", "Gebaeudepunkt", "Grenze_Flaeche", "Versorgungslinie", "Reliefpunkt",
               "Gewaesserpunkt", "Bauwerkspunkt", "Vegetationspunkt", "Reliefflaeche", "Relieflinie",
               "Historischer_Punkt", "Historische_Linie", "Historische_Flaeche", "Barrierenlinie",
               "Weitere_Nutzung_Flaeche"}
WEG_ID = re.compile(r"Meer|Watt|Priel|Eis|Fels|Bergbau|Tagebau|Landebahn|Flug|Halde|Heide|Moor|Duene|Staatsgrenze|"
                    r"Landesgrenze|Regierungsbezirk|Autobahnknoten|Kilometer|Staumauer|Sperrwerk|Wellenbrecher|"
                    r"Hafendamm|Furt|Faehr")
VERMERK = ('Grundkarte © <a href="https://www.bkg.bund.de">GeoBasis-DE / BKG</a> (2026) '
           '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>, Kartenstil verändert')


def braucht_sprite(schicht: dict) -> bool:
    text = json.dumps(schicht)
    return "icon-image" in text or "fill-pattern" in text or "line-pattern" in text


def main() -> None:
    stil = json.loads((EINGANG / "bm_web_gry.json").read_text(encoding="utf-8"))
    tj = json.loads((EINGANG / "bm_web_de_3857.json").read_text(encoding="utf-8"))
    unten, oben = [], []
    for s in stil["layers"]:
        if s.get("source") != QUELLE_ALT or s.get("source-layer") in WEG_SCHICHT or WEG_ID.search(s["id"]):
            continue
        if s["type"] == "background" or s["id"] == "Hintergrund" or braucht_sprite(s):
            continue
        s = {**s, "id": "bm-" + s["id"], "source": QUELLE}
        (oben if s["type"] == "symbol" else unten).append(s)
    if not unten or not oben:
        sys.exit("Stilauszug leer: Ebenennamen von basemap.de geändert?")
    inhalt = {
        "stand": tj.get("description", ""),
        "quelle": {"type": "vector", "tiles": tj["tiles"], "minzoom": tj["minzoom"], "maxzoom": tj["maxzoom"],
                   "bounds": tj["bounds"], "attribution": VERMERK},
        "glyphs": stil["glyphs"],
        "unten": unten,
        "oben": oben,
        "vermerk": VERMERK,
    }
    text = json.dumps(inhalt, ensure_ascii=False, separators=(",", ":"))
    kopf = ("/* Grundkarte: Auszug aus dem Kartenstil bm_web_gry von basemap.de, verändert (skripte/27_grundkarte.py).\n"
            "   © GeoBasis-DE / BKG (2026), CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ */\n")
    ZIEL.write_text(kopf + f"window.KIEZ_GRUNDKARTE={text};\n", encoding="utf-8")
    gz = len(gzip.compress(ZIEL.read_bytes(), 9))
    print(f"geschrieben: {ZIEL.relative_to(WURZEL)}: {len(unten)} Ebenen unten, {len(oben)} oben, {gz / 1024:.1f} KB gz",
          file=sys.stderr)


if __name__ == "__main__":
    main()
