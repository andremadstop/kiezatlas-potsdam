"""Prüfung B5 Zweig 2: daten/jahre_methode.js gegen das zugelieferte Schema pruefen/B5_schema/jahre_methode.json.

Nutzt die Prüfmaschine aus pruefen/daten.py (P0) unverändert: gleiche Validierung, gleiche Adress-, OSM- und
Feinklassenprüfung. Solange das Schema nicht nach daten/schema/ übernommen ist (Integration), meldet daten.py
für jahre_methode.js „kein Schema“; diese Prüfung deckt den Vertrag bis dahin ab.

Aufruf: python3 -I pruefen/B5_methode.py   Rückgabe 0 = Vertrag erfüllt, 1 = Befund.
"""
import importlib.util
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p0_daten", HIER / "daten.py")
p0 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p0)

schema_pfad = HIER / "B5_schema" / "jahre_methode.json"
schema = json.loads(schema_pfad.read_text(encoding="utf-8"))
_, _, Z = p0.js_lesen(p0.DATEN / "zellen.js")
p0.datei_pruefen(p0.DATEN / "jahre_methode.js", "jahre_methode.js", [(schema_pfad, schema)],
                 {"anzahl": len(Z["features"])}, fixture=False)
sys.exit(1 if p0.befunde else 0)
