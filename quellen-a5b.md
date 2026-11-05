# Zulieferung A5b zum Lizenzregister (QUELLEN.md)

Paket A5b (Fußweg je Zelle), Stand 05.11.2026. Keine neue Rohquelle und kein Abruf: A5b liest nur Tabellen anderer
Pakete und rechnet offline. Wird in der Integration (I1) in `QUELLEN.md` übernommen.

| Objekt | Grundlage | Lizenz | Vermerk | Veröffentlicht in |
|---|---|---|---|---|
| `auswertung.zelle_erreichbar` (`methode = 'fussweg'`) | OSM-Wegenetz (A3) + Ziele aus A2 (MBJS, ALKIS), A3 (OSM), A4 (VBB) + Zensus-Zellmittelpunkte | ODbL 1.0 (abgeleitete Datenbank) | © OpenStreetMap-Mitwirkende, ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/); dazu je Ziel-Quelle deren Vermerk mit „Daten verändert (eigene Berechnung)“ und Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0) | nur `daten/erreichbar_fuss_odbl.js`, `daten/planer_fuss_odbl.js` (A6), `*_odbl.gpkg` (A8) |
| `auswertung.zelle_gruen` (`methode = 'fussweg'`) | OSM-Wegenetz + ALKIS-Grünflächen (A2) + Zensus | ODbL 1.0 | wie oben, Flächen: © GeoBasis-DE/LGB, dl-de/by-2-0, Daten verändert (eigene Berechnung) | wie oben |
| `berichte/A5b_fussweg.md` | Kennzahlen des Laufs | intern | – | nicht veröffentlicht (`berichte/` in `.gitignore`) |
