# Quellenbeitrag Paket B0 (für QUELLEN.md, Zusammenführung in I1/I2)

| Quelle | Datei / Stand | Lizenz und Vermerk | Verwendung |
|---|---|---|---|
| ALKIS NAS, Kreisfreie Stadt Potsdam, Bestandsdatenauszug ohne Eigentümer (LGB) | `alkis_p.zip`, Stichtag 01.10.2026, abgerufen 05.11.2026 von https://data.geobasis-bb.de/geobasis/daten/alkis/Vektordaten/nas/alkis_p.zip, SHA256 `4b92f837…f094ce` (`$KIEZ_DATEN/alkis_nas/2026-10-01/HERKUNFT.md`) | „© GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)“ | `auswertung.alkis_nas_gebaeude` (Dachform, Bauweise, Geschosse, Objekthöhe je Gebäude, für die Schätzung in B4). Adressen nur intern in `auswertung.gebaeude_adresse`, nie veröffentlicht. |

Hinweise für die Veröffentlichung:
- Werte aus B0 erscheinen nur abgeleitet (B4), nie als Adressliste. Gebäudeadressen gehen in keine Datei unter `daten/` und in keinen Export (`pruefen/B0_nas.py`).
- `baujahr` ist im Auszug in keinem Gebäude gefüllt (0 von 50.795); ALKIS liefert kein Baujahr.
