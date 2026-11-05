# Lizenz der Dateien in `daten/`

Der Code dieses Repositorys steht unter der Apache-Lizenz 2.0 (`LICENSE`). **Für die Dateien in `daten/` gilt
sie nicht.** Sie sind aus offenen amtlichen Daten berechnet und stehen unter der Lizenz ihrer Quellen
(Register mit Vermerken: `QUELLEN.md`).

| Datei | Lizenz | Namensnennung |
|---|---|---|
| `stadtteile.js` | dl-zero-de/2.0 | © Landeshauptstadt Potsdam |
| `zellen.js`, `kennzahlen.js`, `kennzahlen.json` | dl-de/by-2-0 | © Statistische Ämter des Bundes und der Länder, Zensus 2022; Gebäudezahlen © GeoBasis-DE/LGB; jeweils dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) |
| `gebaeude/<nr>.js` | dl-de/by-2-0 | © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) |
| `planer.js`, `erreichbar.js`, `einrichtungen.js` | dl-de/by-2-0 | je Wert über `quellen` in der Datei (Zensus, MBJS, LGB), mit „Daten verändert (eigene Berechnung)“ |
| `jahre_zellen.js`, `jahre/<nr>.js` | dl-de/by-2-0 (Zensus, LGB); einzelne Jahre aus CC0-Quellen (Wikidata, DDB) sind gekennzeichnet | je Wert über `quellen` |
| `*_odbl.js` (z. B. `einrichtungen_odbl.js`, `erreichbar_fuss_odbl.js`, `planer_fuss_odbl.js`) | Open Database License 1.0 (ODbL), Inhalte Database Contents License 1.0 | © OpenStreetMap-Mitwirkende, https://opendatacommons.org/licenses/odbl/1-0/ |
| `schema/*.json`, `schema/themen.md` | Apache-2.0 (Teil des Codes) | – |
| `fixtures/*` | Apache-2.0; unechte Beispielwerte (`fixture: true`), keine Daten | – |

## Regeln

- **ODbL nur in `_odbl`-Dateien.** Jede dieser Dateien trägt im Kopf einen Kommentar mit „ODbL“ und
  „OpenStreetMap“. Andere Dateien enthalten keinen aus OpenStreetMap abgeleiteten Wert (auch keine
  Fußweg-Kennzahl, Prüfbericht 4). Wer eine `_odbl`-Datei veröffentlicht, bietet sie auf der Download-Seite
  an (Share-Alike, Pflicht zum Angebot der abgeleiteten Datenbank).
- **Keine Wikipedia-Werte** (CC BY-SA 4.0) und keine OSM-Jahre in den Gebäudejahren; beide nur zur Prüfung.
- **Keine Personendaten, keine Adressen.** Feine Zensusklassen nur je Raumeinheit mit mindestens 100 Einwohnern.
- `pruefen/daten.py` prüft die ODbL-Grenze, Adress- und Kontaktfelder und feine Klassen in jeder Datei.

Vor dem ersten Push neuer Datendateien auf GitHub die aktuellen Nutzungsbedingungen der Plattform lesen
(Prüfbericht 24).
