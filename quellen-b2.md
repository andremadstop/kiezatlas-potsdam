# Quellenbeitrag Paket B2 (für QUELLEN.md, Zusammenführung in I2)

Stand 05.11.2026. **Aus B2 darf derzeit nichts veröffentlicht werden.** Alle Zeilen in `auswertung.jahr_beleg`
tragen `nur_pruefung = true`; die Gründe stehen je Quelle in der Tabelle.

| Quelle | Datei / Stand | Lizenz und Vermerk | Verwendung | Veröffentlichen |
|---|---|---|---|---|
| BLDAM, Denkmalliste des Landes Brandenburg, Stadt Potsdam | `04_P_Internet-25.pdf`, Stand 01.01.2026, https://bldam-brandenburg.de/wp-content/uploads/2026/03/04_P_Internet-25.pdf, SHA256 `45ede0d4…d7ae3` (`$KIEZ_DATEN/bldam/2026-01-01/HERKUNFT.md`) | keine Angabe im PDF und auf der Seite; Datenbankrecht § 87a UrhG kann greifen. Anfrage als Entwurf: `$KIEZ_DATEN/entwuerfe/2026-11-05-bldam-datenbanknutzung-b2.txt` (E8) | nur Schlüssel MIDAS-ID → Adresse → Gebäude (Kennzeichen „Baudenkmal“), ohne Jahr | nein, bis E8 beantwortet ist |
| Wikipedia, „Liste der Baudenkmale in Potsdam“ (Übersicht und 27 Teillisten) | HTML vom 05.11.2026, Revisionen je Seite in `$KIEZ_DATEN/wikipedia_denkmale/2026-11-05/HERKUNFT.md` | CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/deed.de); BY-SA umfasst das Datenbankrecht, Share-Alike ist mit dl-de und ODbL nicht vereinbar | Jahre nur als Prüfspalte | nein (Prüfbericht Korrektur 5) |
| Wikidata, Handexport aus dem Query Service (H9) | fehlt noch: `$KIEZ_DATEN/eingang/wikidata_potsdam_baujahr.csv`, Abfrage `$KIEZ_DATEN/entwuerfe/2026-11-05-wikidata-abfrage-b2.rq` | CC0 1.0 (https://creativecommons.org/publicdomain/zero/1.0/deed.de), Vermerk freiwillig: „Wikidata, CC0“ | Baujahr je Objekt, darf in die Kaskade | ja, sobald vorhanden |
| Deutsche Digitale Bibliothek, API, Datengeber BLDAM (H8) | fehlt noch: `$KIEZ_DATEN/eingang/ddb-key` | laut Pressemitteilung 2013 CC0 für Metadaten; vor Nutzung bestätigen (Prüfbericht Korrektur 28) | Denkmaljahre, darf in die Kaskade | erst nach Bestätigung der Lizenz |
| OpenStreetMap `start_date`, `building:year` (H5) | fehlt noch: `$KIEZ_DATEN/eingang/osm/*.pbf` | ODbL 1.0, „© OpenStreetMap-Mitwirkende“ | nur Prüfspalte (E1: Gebäudejahre ohne OSM) | nein in Gebäudejahren; nur in `_odbl`-Dateien |
| ALKIS NAS (B0) und Snapshot `gebaeude_stand_20261105` | siehe `quellen-b0.md` | „© GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)“ | Zuordnung über Adresse und Geometrie | Adressen nie |

Vertrag für B4:
- Denkmal: `quelle LIKE 'BLDAM%'`; Ensemble-Mitglied: zusätzlich „(Ensemble, mehr als 4 Gebäude)“ in `quelle`.
- In die Kaskade (`auswertung.gebaeude_jahr`) nur Zeilen mit `nur_pruefung = false` und `art = 'bau'`.
- `jahr_von` oder `jahr_bis` kann leer sein („vor 1874“ = nur `jahr_bis`).
- Wohngebäude mit weniger als 3 Wohneinheiten nur als Klasse veröffentlichen, außer Denkmale (Korrektur 6).
