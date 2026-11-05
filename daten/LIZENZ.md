# Lizenz der Dateien in `daten/`

Der Code dieses Repositorys steht unter der Apache-Lizenz 2.0 (`LICENSE`). **Für die Dateien in `daten/` gilt
sie nicht.** Sie sind aus offenen amtlichen Daten berechnet und stehen unter der Lizenz ihrer Quellen
(Register mit Vermerken: `QUELLEN.md`).

| Datei | Lizenz | Namensnennung |
|---|---|---|
| `stadtteile.js` | dl-zero-de/2.0 | © Landeshauptstadt Potsdam |
| `planungsraeume.js` | dl-de/by-2-0 | © Landeshauptstadt Potsdam, Planungsräume Stand 31.12.2025, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (Grenzen auf 3 m vereinfacht, Koordinaten gerundet, Felder ausgewählt) |
| `zellen.js`, `kennzahlen.js`, `kennzahlen.json` | dl-de/by-2-0 | © Statistische Ämter des Bundes und der Länder, Zensus 2022; Gebäudezahlen © GeoBasis-DE/LGB; jeweils dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) |
| `gebaeude/<nr>.js` | dl-de/by-2-0 | © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) |
| `erreichbar.js`, `einrichtungen.js` | dl-de/by-2-0 | je Wert über `quellen` in der Datei (Zensus, MBJS, LGB), mit „Daten verändert (eigene Berechnung)“ |
| `planer.js` | dl-de/by-2-0 (darin statistische Bezirke der LHP für die ÖPNV-Gebietsklasse einzelner Stadtteile) und CC BY 4.0 (ÖPNV-Werte aus dem VBB-GTFS) | je Wert über `quellen` in der Datei; VBB: „VBB Verkehrsverbund Berlin-Brandenburg GmbH, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), Daten verändert (eigene Berechnung)“ |
| `jahre_zellen.js`, `jahre/<nr>.js`, `jahre_methode.js` | dl-de/by-2-0 (Zensus, LGB); belegte Bauzeiten aus Wikidata (CC0 1.0, Zuordnung über die Koordinate des Objekts) sind mit `q = "beleg"` gekennzeichnet (Stand 05.11.2026: 106 Gebäude, davon 53 mit Einzeljahr, alle ohne Wohnraum; DDB derzeit keine) | je Wert über `quellen`; Bauzeiten der Großsiedlungen als Fakten: Landeshauptstadt Potsdam, „Potsdamer Platte“, Juli 2008; in `jahre_methode.js` (Schlüssel `lhp`, nur Plausibilität): © Landeshauptstadt Potsdam, Gebäude nach Baualter seit 1999 (Open-Data-Portal), dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung: Gruppen zusammengefasst) |
| `download/bauzeiten.gpkg` | dl-de/by-2-0 | wie `jahre_zellen.js` (Vermerk in der Datei) |
| `export/kiezatlas_potsdam.gpkg`, `export/csv/*.csv` | je Ebene: Planungsräume dl-de/by-2-0, Stadtteile dl-zero-de/2.0, Werte, Einrichtungen, Zellen und Grünflächen (ALKIS) dl-de/by-2-0, Haltestellen und ÖPNV-Werte CC BY 4.0; ÖPNV-Gebietsklasse einzelner Stadtteile über die statistischen Bezirke der LHP (dl-de/by-2-0) | Tabelle `lizenz` in der GPKG bzw. `export/csv/lizenz.csv` und `export/README.md` |
| `export/steckbriefe/<nr>.html` | wie die Werte (dl-de/by-2-0, CC BY 4.0) | Abschnitt „Quellen und Lizenzen“ je Steckbrief |
| `export/kiezatlas_potsdam.qgz`, `export/stile/*.qml`, `export/README.md` | Apache-2.0 (Projektdatei, Stile, Beschreibung; keine Daten) | – |
| `*_odbl.js` (z. B. `einrichtungen_odbl.js`, `erreichbar_fuss_odbl.js`, `planer_fuss_odbl.js`), `export/*_odbl.gpkg`, `export/csv_odbl/` (seit 05.11.2026 aus dem OSM-Auszug Stand 31.10.2026: die `.js` mit N1, `export/kiezatlas_potsdam_odbl.gpkg` und `export/csv_odbl/` mit N4) | Open Database License 1.0 (ODbL), Inhalte Database Contents License 1.0 | © OpenStreetMap-Mitwirkende, https://opendatacommons.org/licenses/odbl/1-0/; dazu die amtlichen Vermerke aus `quellen` je Datei (Zensus, MBJS, LGB, VBB), in `export/csv_odbl/lizenz.csv` je Ebene |
| `schema/*.json`, `schema/themen.md` | Apache-2.0 (Teil des Codes) | – |
| `fixtures/*` | Apache-2.0; unechte Beispielwerte (`fixture: true`), keine Daten | – |

## Regeln

- **ODbL nur in `_odbl`-Dateien.** Jede dieser Dateien trägt im Kopf einen Kommentar mit „ODbL“ und
  „OpenStreetMap“. Andere Dateien enthalten keinen aus OpenStreetMap abgeleiteten Wert (auch keine
  Fußweg-Kennzahl, Prüfbericht 4). Wer eine `_odbl`-Datei veröffentlicht, bietet sie auf der Download-Seite
  an (Share-Alike, Pflicht zum Angebot der abgeleiteten Datenbank).
- **Keine Wikipedia-Werte** (CC BY-SA 4.0) und keine OSM-Jahre in den Gebäudejahren; beide nur zur Prüfung.
- **Keine Personendaten, keine Adressen.** Feine Zensusklassen (feiner als die fünf Altersklassen des Hauptatlas, etwa die infrastrukturellen Altersgruppen) nur je Raumeinheit mit mindestens 100 Einwohnern. Je 100-m-Zelle stehen nur die Anteile, die der Zensus selbst je Gitterzelle veröffentlicht (fünf Altersklassen, Baujahr, Heizung; geschützt durch sein Cell-Key-Verfahren), dazu Einwohner und Entfernungen.
- `pruefen/daten.py` prüft die ODbL-Grenze, Adress- und Kontaktfelder und feine Klassen in jeder Datei.

Vor dem ersten Push neuer Datendateien auf GitHub die aktuellen Nutzungsbedingungen der Plattform lesen
(Prüfbericht 24).
