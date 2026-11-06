# Belege

Alles, was eine Zahl, eine Prüfung oder eine Entscheidung des Kiezatlas nachweist, liegt hier in `belege/` oder in
`berichte/`. Diese Übersicht nennt jede Datei, was sie belegt und welches Skript sie geschrieben hat. Wie die
Skripte zusammenhängen, steht in [`docs/rundgang.md`](../docs/rundgang.md); `berichte/` ist in `.gitignore`
eingetragen, dort sind nur die unten genannten Dateien eingecheckt.

## Prüfstand und Rohdaten

| Datei | belegt | erzeugt von |
|---|---|---|
| `pruefstand-20261106-1cf8d56/pruefen.log` | Ergebnis aller Prüfungen ohne Netz und ohne Datenbank am Commit `1cf8d56` (sauberer Arbeitsstand): 18 Prüfungen, 16 grün, 2 mit Befund. Befunde: `pruefen/A6_test_pfade.py` (1 Fehler: „kein Luftlinien-Randhinweis am Fußweg“) und `pruefen/p1_themen.mjs` (4: `KIEZ_THEMEN` hat nicht mehr die 31 Namen des Vertrags, je per `file://` und HTTP). Beide liegen schon am Ausgangsstand `6cb7efa` vor; `p1_themen.mjs` war laut `3D_grundkarte_20261106.md` am Stand `77bd0d6` noch grün | `./pruefen.sh` |
| `rohdaten.md`, `rohdaten.sha256`, `rohdaten.kiez_daten.sha256` | Prüfsummen der Rohdaten (7 Kerndateien nachträglich am 06.11.2026 gehasht, 80 Dateien unter `$KIEZ_DATEN`) | `sha256sum`, Abgleich mit den `HERKUNFT.md` |

## Laufberichte der Pipeline

| Datei | belegt | erzeugt von |
|---|---|---|
| `20261104T132324Z.txt/.json` | 32 Stadtteile geladen | `skripte/lauf.sh laden --nur stadtteile` |
| `20261104T132325Z.txt/.json` | 6.348 Zensuszellen im Rechteck geladen | `… --nur zensus_gitter` |
| `20261104T132333Z.txt/.json` | 85.046 Gebäude aus dem WFS der LGB, vollständig, 519 s | `… --nur gebaeude_alkis` |
| `20261105T093628Z.txt/.json` | 220 Kitas (Dienst meldet 240, Grund unten) | `… --nur mbjs_kita` |
| `20261105T093707Z.txt/.json` | 106 Schulen im Rechteck | `… --nur mbjs_schule` |
| `20261105T093727Z.txt/.json` | 28.121 Nutzungsflächen | `… --nur alkis_nutzung` |
| `20261105T101043Z.txt/.json` | 6.334 Zellen mit Strukturmerkmalen | `… --nur zensus_struktur` |
| `quellenverzeichnis.md` | Quellenverzeichnis der Pipeline, Stand 04.11.2026 (neue Quellen in `QUELLEN.md`) | Pipeline |

## Belege je Paket (`belege/`)

| Datei | belegt | erzeugt von |
|---|---|---|
| `A1_zensus_20261105.txt`, `A1_zensus_n2_20261105.txt` | Strukturmerkmale: Prüfsummen der Zips, Summen, Geheimhaltung (Lauf A1 und Nachlauf N2) | `pruefen/A1_zensus.py` |
| `A1_gemeindeabgleich_20261105.md` | Gitter gegen Gemeindeergebnis Potsdam, 0 Befunde | `pruefen/A1_zensus.py`, Auswertung von Hand |
| `A3_pbf_leser_gegenprobe.txt` | eigener PBF-Leser gegen GDAL | `pruefen/a3_gegenprobe_gdal.py` |
| `a4_lauf_20261105.txt` | Haltestellen und Taktklassen am Stichtag 10.11.2026 | `skripte/13_oepnv.py` |
| `a4_pruefung_20261105.txt` | 315 Haltestellen, 283 in Potsdam, je mit Klasse | `pruefen/a4_haltestelle.py` |
| `a4_gebietsklassen_20261105.txt` | Gebietsklassen des Nahverkehrsplans je Bezirk | `pruefen/a4_gebietsklassen.py` |
| `a4_stichprobe_20261110.txt` | Abfahrten einzelner Haltestellen zum Abgleich mit dem Aushang | `pruefen/a4_stichprobe.py` |
| `A5a_erreichbarkeit_20261105.md`, `A5a_rand_unsicher_20261105.csv` | Luftlinie je Zelle und Art; Zellen, deren Wert nur eine Obergrenze ist | `skripte/14_erreichbarkeit.py` |
| `A5a_pruefung_20261105.txt` | Abdeckung und Gegenrechnung der Luftlinie | `pruefen/A5a_erreichbarkeit.py` |
| `A5b_landfilter_kreuzprobe.txt` | Landesfilter E7: 15 von 1.800 Haltepunkten falsch (0,8 %) | `pruefen/a5b_landfilter_kreuzprobe.py` |
| `A5b_probelauf_gitternetz.txt` | Fußweg-Rechnung mit Gitternetz gegen echte Zellen, ROLLBACK | `A5B_DB_TEST=1 skripte/14b_fussweg.sh test` |
| `A6_planer_20261105.md`, `A6_pruefung_20261105.txt` | Planer-Dateien: Raumebene, Geheimhaltung, was fehlt; Prüfprotokoll | `skripte/15_planer.py`, `pruefen/A6_planer.py` |
| `a7_pruefung_20261105.txt` | Planer-Seiten: Gewicht, Nachladen, axe | `pruefen/A7_planer.mjs` |
| `A8_export_20261105.md`, `A8_pruefung_20261105.txt` | GIS-Export: Ebenen, Prüfsummen; Prüfprotokoll | `skripte/16_export.py`, `pruefen/A8_export.py` |
| `B1_zensus_jahre.md` | Zensus-Baujahr im Gitter: Zellen, Summen | `skripte/21_jahre_zensus.py` |
| `N1_osm_fussweg_20261105.md` | OSM-Netz und Fußweg (Nachlauf A3, A5b) | `skripte/12_osm.sh`, `skripte/14b_fussweg.sh` |
| `N2_pruefungen_20261105.txt` | Prüfläufe des Nachlaufs N2 | `pruefen/b1_jahre.py` und weitere |
| `N3_wikidata_stichprobe.md` | Handstichprobe der Wikidata-Zuordnung | `pruefen/N3_wd_stichprobe.py` |
| `N4_grep_lhp_20261105.md` | keine Ableitung aus LHP-Nutzungsbedingungen-Daten in veröffentlichten Dateien | `grep`, von Hand |
| `N4_pestalozza_20261105.md` | Lage der Grundschule 103512, Entscheidung | Abfragen mit `mosidi_lesen` |
| `N4_planer_lauf_20261105.txt`, `N4_versorgung_export_20261105.md` | Planer und Export mit den neuen Daten | `skripte/15_planer.py`, `skripte/16_export.py` |
| `3D_grundkarte_20261106.md` | Herkunft der Gebäudehöhen (50.356 von 52.309 aus der ALKIS-Objekthöhe), Grundkarte | `skripte/02_auswerten.py`, `skripte/27_grundkarte.py` |

## Berichte (`berichte/`)

| Datei | belegt | erzeugt von |
|---|---|---|
| `A2_gegenprobe.md` | ALKIS-Gebäude gegen MBJS-Einrichtungen | `skripte/11_einrichtungen.py` |
| `B0_alkis_nas.md` | Gebäudeform und Zuordnung des NAS-Auszugs | `skripte/20_alkis_nas.py` |
| `B2_genaue_jahre.md`, `B2_stand.json` | genaue Jahre je Quelle | `skripte/22_jahre_genau.py` |
| `B3_pilot.md` | Luftbild-Pilot Bornstedt | `skripte/23_luftbild_pilot.py auswerten` |
| `B4_holdout.md`, `B4_holdout_lauf1.md` | Abdeckung der Kaskade, Rücktest, Summenprüfung (Lauf 1 vor zwei Codekorrekturen) | `skripte/24_jahre_kaskade.py ruecktest` |
| `audit_20261106.md`, `audit_20261106.json` | Audit Transparenz und Nutzen je Nutzergruppe | Prüfung von Hand |

Nicht im Repository: `berichte/A3_vollstaendigkeit.md` (`12_osm.py`) und `berichte/A5b_fussweg.md`
(`14b_fussweg.py`); die tragenden Zahlen stehen in `N1_osm_fussweg_20261105.md`.

## Import mit der Geodaten-Import-Pipeline (04.11.2026)

Laufberichte der Pipeline (Text und JSON) für die drei Quellen in `config/potsdam.yaml`, gegen eine frische
PostGIS-Datenbank (`docker-compose.yml`, PostgreSQL 16, PostGIS 3.6) mit den Tabellen aus `sql/`.

| Lauf | Quelle | Ergebnis |
|---|---|---|
| `20261104T132324Z` | `stadtteile` (lokale CSV aus dem Handdownload) | 32 Stadtteile neu |
| `20261104T132325Z` | `zensus_gitter` (lokale CSV aus den Destatis-Dateien) | 6 348 Zellen im Rechteck um Potsdam |
| `20261104T132333Z` | `gebaeude_alkis` (WFS der LGB, 1-km-Kacheln, 1 s Pause) | 85 046 Gebäude im Rechteck, vollständig (jede Kachel unter der Höchstzahl), 519 s |

Die Auswertung (`skripte/02_auswerten.py`) ordnet davon 52 309 Gebäude und 3 443 bewohnte Zellen den
32 Stadtteilen zu. Geprüft in der Datenbank: Die Stadtteile sind gültig, überlappen sich nicht und haben
keine Lücken; jede Zelle zählt genau einmal.

## Ausbau (05.11.2026, Paket P0)

Je Lauf genau eine Quelle (`skripte/lauf.sh laden --nur …`), Ziele in `sql/002_ausbau.sql`.

| Lauf | Quelle | Ergebnis |
|---|---|---|
| `20261105T093628Z` | `mbjs_kita` (WFS MBJS, eine Seite, 2 s Pause) | 220 Kitas (je `id_kita` ein Standort); „unvollständig“, weil der Dienst 240 Einträge meldet: 17 Kitas stehen mit mehreren Häusern und gleicher Kapazität darin. Nichts gelöscht |
| `20261105T093707Z` | `mbjs_schule` (WFS MBJS) | 106 Schulen im Rechteck, 78 in Potsdam |
| `20261105T093727Z` | `alkis_nutzung` (WFS der LGB, 2-km-Kacheln, 1 s Pause) | 28 121 Nutzungsflächen, vollständig, 150 s |

Das Quellenverzeichnis oben schreibt die Pipeline nur im eigenen Berichtsordner neu; es ist hier noch der Stand
vom 04.11. Die neuen Quellen stehen in `QUELLEN.md`.

## 3D-Gebäude und Vektor-Grundkarte (06.11.2026)

`3D_grundkarte_20261106.md`: Entscheidungen G1 bis G8, Herkunft der Gebäudehöhen (50.356 von 52.309 aus der
ALKIS-Objekthöhe), Nachweis, dass die Bauzeit-Schätzung unverändert blieb, Prüfungen, Netzabrufe und Grenzen.
