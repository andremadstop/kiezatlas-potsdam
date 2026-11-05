# Zulieferung A8 (GIS-Export) zu QUELLEN.md und daten/LIZENZ.md

A8 ruft nichts aus dem Netz ab und nutzt keine neue Quelle. Der Export gibt die Daten von P0, A2, A4, A5a und A6
in anderen Formaten weiter. Für die Zusammenführung in I1 gibt es zwei Ergänzungen.

## Ergänzung für daten/LIZENZ.md (Tabelle „Datei, Lizenz, Namensnennung“)

| Datei | Lizenz | Namensnennung |
|---|---|---|
| `export/kiezatlas_potsdam.gpkg`, `export/csv/*.csv` | je Ebene: Grenzen dl-zero-de/2.0 (Stadtteile; Planungsräume laut H1), Werte, Einrichtungen, Zellen und Grünflächen dl-de/by-2-0, Haltestellen und ÖPNV-Werte CC BY 4.0 | Tabelle `lizenz` in der GPKG bzw. `csv/lizenz.csv`, dazu `export/README.md`; jeder dl-de-Vermerk mit „Daten verändert (eigene Berechnung)“ und Link |
| `export/kiezatlas_potsdam_odbl.gpkg`, `export/csv_odbl/*.csv` (entstehen erst mit A3/A5b) | Open Database License 1.0 | © OpenStreetMap-Mitwirkende, https://opendatacommons.org/licenses/odbl/1-0/ |
| `export/steckbriefe/*.html` | wie die Werte (dl-de/by-2-0, CC BY 4.0); Vermerke stehen im Steckbrief | je Steckbrief Abschnitt „Quellen und Lizenzen“ |
| `export/kiezatlas_potsdam.qgz`, `export/stile/*.qml` | Apache-2.0 (Projektdatei und Stile, keine Daten) | – |

## Hinweise für I1

- Die Download-Seite (Prüfbericht 4 und 29) bietet `kiezatlas_potsdam.gpkg`, `csv/` und, sobald vorhanden,
  `kiezatlas_potsdam_odbl.gpkg` mit `csv_odbl/` an. Die ODbL-Dateien müssen dort stehen (Share-Alike).
- Neu erzeugen: `skripte/16_export.py` nach jedem Lauf von `skripte/15_planer.py` (A6). Wechselt A6 auf
  Planungsräume, verlangt der Export `--raum-lizenz` mit dem Vermerk aus dem Handdownload H1.
- Größe: rund 14 MB unter `daten/export/` (GPKG 5,1 MB, CSV 4,8 MB, Steckbriefe 3,4 MB). Ob das ins öffentliche
  Repository gehört oder nur ins Release bzw. auf den Server, entscheidet Andre vor dem ersten Push.
- Zwei amtliche Kita-Namen enthalten eine Anschrift („Hort"Am Schulplatz 1"“, „KinderGarten Schulplatz 1“). Sie
  stehen so in den MBJS-Daten und in `daten/einrichtungen.js`; die Prüfung führt sie als benannte Ausnahme.
