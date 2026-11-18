"""Textschicht lesen (texte/<lang>/*.js) und Pluralregeln: gemeinsam für skripte/30_seiten.py und pruefen/texte.py.

Format einer Textdatei (Vertrag daten/schema/texte.md): je Schlüssel eine Zeile
    T["<namensraum>.<name>"] = <JSON-Wert>;
innerhalb von (function (T) { … })(window.KIEZ_TEXTE = window.KIEZ_TEXTE || {}); Kommentare und Leerzeilen sind
erlaubt, sonst nichts. So bleiben die Dateien für den Browser ausführbar und für Python ohne JS-Interpreter lesbar.
Kein Netz, keine Datenbank.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
TEXTE = WURZEL / "texte"
ZEILE = re.compile(r'^\s*T\[("(?:[^"\\]|\\.)*")\]\s*=\s*(.+);\s*$')
ERLAUBT = re.compile(r"^\s*(/\*.*\*/|//.*|\(function \(T\) \{|\}\)\(window\.KIEZ_TEXTE = window\.KIEZ_TEXTE \|\| \{\}\);)?\s*$")
SCHLUESSEL = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
PLURALFORMEN = {"pl": ("one", "few", "many", "other"), "en": ("one", "other"), "de": ("one", "other")}


class Textfehler(Exception):
    pass


def datei_lesen(p: Path) -> dict[str, object]:
    """Schlüssel → Wert einer Textdatei, in Dateireihenfolge. Fremde Zeilen oder doppelte Schlüssel sind Fehler."""
    aus: dict[str, object] = {}
    for i, z in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        m = ZEILE.match(z)
        if not m:
            if not ERLAUBT.match(z):
                raise Textfehler(f"{p.relative_to(WURZEL)}:{i}: Zeile nicht im Textformat (T[\"…\"] = JSON;)")
            continue
        try:
            k, v = json.loads(m.group(1)), json.loads(m.group(2))
        except json.JSONDecodeError as e:
            raise Textfehler(f"{p.relative_to(WURZEL)}:{i}: kein JSON ({e})") from e
        if k in aus:
            raise Textfehler(f"{p.relative_to(WURZEL)}:{i}: Schlüssel {k} doppelt")
        aus[k] = v
    return aus


def sprache_lesen(lang: str) -> dict[str, dict[str, object]]:
    """Namensraum (Dateiname) → {Schlüssel: Wert} für texte/<lang>/*.js."""
    return {p.stem: datei_lesen(p) for p in sorted((TEXTE / lang).glob("*.js"))}


def flach(lang: str) -> dict[str, object]:
    aus: dict[str, object] = {}
    for d in sprache_lesen(lang).values():
        aus.update(d)
    return aus


def pluralform(lang: str, n: int) -> str:
    """CLDR-Pluralregel für ganze Zahlen (wie Intl.PluralRules)."""
    if lang == "pl":
        if n == 1:
            return "one"
        if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
            return "few"
        return "many"
    return "one" if n == 1 else "other"
