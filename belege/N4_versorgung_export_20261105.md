# N4: Versorgung (A6) und Export (A8) mit den neuen Daten, Lauf 05.11.2026

Zweig `nachlauf/n4` = `ausbau/integration` (7c16734) + `nachlauf/n1` (bd5f6b3) + `nachlauf/n2` (d25b34d), beide
Merges ohne Konflikt. Kein Netzabruf. Datenbank nur mit der Leserolle `mosidi_lesen` (SELECT); keine DDL, kein
Pipeline-Lauf. `uv run --offline` mit Paketen aus dem lokalen Zwischenspeicher.

## Was neu ist

1. **Pestalozza-Fall (MBJS 103512):** Die Lage ist nicht eindeutig, Entscheidung und Belege stehen in
   `belege/N4_pestalozza_20261105.md`. Der Punkt bleibt mit dem Feld `hinweis` in `einrichtungen.js` und zählt für
   keine Entfernung. 67 Zellen Luftlinie und 295 Zellen Fußweg sind ohne ihn neu gerechnet. Die Grundschulwerte
   von 101 und 103 bleiben leer. Die Oberfläche zeigt den Hinweis im Popup, in der Legende und in der
   Versorgungstabelle, die Methodenseite erklärt ihn.
2. **Grundschuleinzugsgebiete (LHP, Nutzungsbedingungen ungeprüft):** Sie dienen nur als interne Prüfspalte
   (`pruefen/n4_einzugsgebiete.py`), das Ergebnis liegt unter `$KIEZ_DATEN/intern/` außerhalb des Repos. Daraus geht
   nichts in `daten/` und nichts in den Export, der grep-Beleg steht in `belege/N4_grep_lhp_20261105.md`. Die
   Methodenseite nennt nur den Status. Die Grundschulwerte bleiben `vorlaeufig`.
3. **Fußweg (N1) im Export:** `daten/export/kiezatlas_potsdam_odbl.gpkg` und `csv_odbl/` sind erstmals geschrieben,
   mit den Ebenen `einrichtung_odbl` 941, `zelle_fuss_odbl` 3.443 und `versorgung_fuss_odbl` 190. Die Tabelle
   `lizenz` (auch als `csv_odbl/lizenz.csv`) nennt je Ebene ODbL und die übrigen Datenquellen der Datei, bei
   Haltestellen-Zielen auch VBB, CC BY 4.0. Auf
   der Download-Seite (`planer-daten.html`) sind die Dateien angeboten (Share-Alike).
4. **N1-Lücke geschlossen:** `erreichbar_fuss_odbl.js` nennt jetzt die Quelle `vbb`, weil Haltestellen Ziele sind.
5. **N2-Folgen:** Mit dem Neulauf ist `pruefen/A6_planer.py` wieder grün. Die ÖPNV-Werte haben sich so geändert:

   | Raum | Erschließung | Takt |
   |---|---|---|
   | 401 | null → 100 % | null → 27 % |
   | 601 | 75 → 77 % | 74 → 69 % |

   Die Stadtteile 43 und 44 haben Klasse I über die statistischen Bezirke. `planer.js` führt dafür die Quelle
   `statbezirk` und an den betroffenen Werten den Vermerk „© Landeshauptstadt Potsdam, Statistische Bezirke,
   dl-de/by-2-0, Daten verändert“. Im Export steht der Vermerk in der Tabelle `lizenz` und im README.

## Dateien (gzip -9)

| Datei | Bytes | gz | MD5 |
|---|---:|---:|---|
| `daten/planer.js` | 251.342 | 9.276 | `afa7d77662777c50e4de5296582d4f1b` |
| `daten/erreichbar.js` | 198.267 | 53.986 | `3a4017deded7a953703f8f5e6f86aee1` |
| `daten/einrichtungen.js` | 208.880 | 16.358 | `4836dd95b82ca3c078bd5ad0b1ec258e` |
| `daten/planer_fuss_odbl.js` | 107.955 | 4.301 | `6cce41d974410cc1c54240b95c3cb164` |
| `daten/erreichbar_fuss_odbl.js` | 296.082 | 89.465 | `2c44700382abb87eec5ac359c7dafe7c` |
| `daten/einrichtungen_odbl.js` | 153.226 | 14.687 | `8747b8d8b676a337359bff0fc65a6b74` (unverändert gegen N1) |
| `daten/export/kiezatlas_potsdam.gpkg` | | | `e7b0f46479280cc90bb4409eb947f398` |
| `daten/export/kiezatlas_potsdam_odbl.gpkg` | | | `a057346e82ebfc0e19948e35db6d548e` |

- `planer.js`, `erreichbar.js` und `einrichtungen.js` kommen zusammen auf 79,6 KB gz (Grenze 250 KB).
- Zwei Läufe von `15_planer.py` und zwei von `16_export.py` hintereinander ergeben byte-gleiche Dateien.
- Das Startgewicht von `planer.html` liegt mit echten Daten bei 299 von 300 KB gz JS, laut `A7_planer.mjs` wie
  vorher. Der Hinweis in `planer.js` kostet 93 B gz. Die Seite liegt an der Grenze.
- Lauf: `belege/N4_planer_lauf_20261105.txt`, Export: `belege/A8_export_20261105.md`.

## Prüfungen

| Prüfung | Ergebnis |
|---|---|
| `pruefen/A6_planer.py` (mit `--with numpy --with scipy`, neu A6-12) | 0 Befunde |
| `pruefen/A6_test_pfade.py` (neu: strittige Lage, Vermerk statistische Bezirke, VBB im Fußweg) | alle Tests bestanden |
| `pruefen/A8_export.py --odbl-erwartet` | 0 Befunde |
| `pruefen/A8_test_pfade.py` (angepasst: echte `_odbl`-Dateien liegen jetzt vor) | 0 Befunde |
| `pruefen/daten.py` | 0 Abweichungen |
| `node pruefen/A7_planer.mjs` | grün |
| `node pruefen/seiten.mjs` | grün |
| `ruff --select E,F,W,B --line-length 120` auf die berührten Python-Dateien | eigene Zeilen sauber; Altbefunde in eigenem Commit |
| `node --check planer.js` | ok |

## Außerhalb der Paketgrenze angefasst (begründet)

- `daten/schema/einrichtungen.json` (P0): Es gibt jetzt das optionale Feld `hinweis` je Einrichtung, sonst schlägt
  der Vertrag fehl.
- `planer.js` (A7): zwei Stellen. Der Hinweis erscheint im Popup und in der Legende, wie der Auftrag es verlangt
  („Hinweis in der Oberfläche“).
- `planer-methode.html` und `planer-daten.html`: nur die Abschnitte „Grundschule“ und „Für Geoinformationssysteme“.

## Offen

- Pestalozza: Die schriftliche Auskunft von MBJS bzw. Stadt fehlt. Was sie aufhebt, steht im Beleg.
- Nutzungsbedingungen der LHP für Grundschuleinzugsgebiete und Grünflächen: Sie liegen nicht lokal und sind
  nicht geprüft.
- Interner Befund der Prüfspalte: siehe `$KIEZ_DATEN/intern/N4_einzugsgebiete_20261105.md`, nicht veröffentlicht.
- Sozialräume (6) nicht eingebaut (N2, Entscheidung A6/A7).
- `public.planungsraum` weiter leer. Der Planer liest `vorbereitet/planungsraeume.csv`, die vor dem Lauf mit
  `skripte/03_planungsraeume.py` erzeugt wird.
