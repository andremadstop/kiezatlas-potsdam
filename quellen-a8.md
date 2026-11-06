# Zulieferung A8 (GIS-Export) zu QUELLEN.md und daten/LIZENZ.md

A8 ruft nichts aus dem Netz ab und nutzt keine neue Quelle. Der Export gibt die Daten von P0, A2, A4, A5a und A6
in anderen Formaten weiter. Für die Zusammenführung in I1 gibt es zwei Ergänzungen.

## Ergänzung für daten/LIZENZ.md (Tabelle „Datei, Lizenz, Namensnennung“)

| Datei | Lizenz | Namensnennung |
|---|---|---|
| `export/kiezatlas_potsdam.gpkg`, `export/csv/*.csv` | je Ebene: Grenzen der Planungsräume dl-de/by-2-0 (H1, Landeshauptstadt Potsdam), Grenzen der Stadtteile dl-zero-de/2.0, Werte, Einrichtungen, Zellen und Grünflächen dl-de/by-2-0, Haltestellen und ÖPNV-Werte CC BY 4.0 | Tabelle `lizenz` in der GPKG bzw. `csv/lizenz.csv`, dazu `export/README.md`; jeder dl-de-Vermerk mit „Daten verändert (eigene Berechnung)“ und Link |
| `export/kiezatlas_potsdam_odbl.gpkg`, `export/csv_odbl/*.csv` (entstehen erst mit A3/A5b) | Open Database License 1.0 | © OpenStreetMap-Mitwirkende, https://opendatacommons.org/licenses/odbl/1-0/ |
| `export/steckbriefe/*.html` | wie die Werte (dl-de/by-2-0, CC BY 4.0); Vermerke stehen im Steckbrief | je Steckbrief Abschnitt „Quellen und Lizenzen“ |
| `export/kiezatlas_potsdam.qgz`, `export/stile/*.qml` | Apache-2.0 (Projektdatei und Stile, keine Daten) | – |

## Hinweise für I1

- Die Download-Seite (Prüfbericht 4 und 29) bietet `kiezatlas_potsdam.gpkg`, `csv/` und, sobald vorhanden,
  `kiezatlas_potsdam_odbl.gpkg` mit `csv_odbl/` an. Die ODbL-Dateien müssen dort stehen (Share-Alike).
- Neu erzeugen: `skripte/16_export.py` nach jedem Lauf von `skripte/15_planer.py` (A6). Raumeinheit sind seit dem
  A6-Nachlauf die 19 Planungsräume (H1). Die Grenzen holt der Export auf demselben Weg wie A6 (`raumquelle` in
  `15_planer.py`): `public.planungsraum`, solange die leer ist `vorbereitet/planungsraeume.csv` aus
  `skripte/03_planungsraeume.py`. Der Vermerk der Grenzen kommt aus `planer.js` (`quellen.planungsraum`).
- Die 32 Stadtteile liegen als eigene Ebene `stadtteil` (nur Grenze, Name, Fläche) zur Orientierung bei; in `zelle`
  stehen Stadtteil und Planungsraum je Zelle.
- Größe: siehe `belege/A8_export_20261105.md`. Ob das ins öffentliche
  Repository gehört oder nur ins Release bzw. auf den Server, entscheidet Andre vor dem ersten Push.
- Zwei amtliche Kita-Namen enthalten eine Anschrift („Hort"Am Schulplatz 1"“, „KinderGarten Schulplatz 1“). Sie
  stehen so in den MBJS-Daten und in `daten/einrichtungen.js`; die Prüfung führt sie als benannte Ausnahme.
