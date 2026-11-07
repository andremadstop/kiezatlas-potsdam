# Rundgang: vom Rohdatensatz zur Seite

Der Weg aller Daten des Kiezatlas, Skript für Skript: was jedes liest, was es schreibt und womit es geprüft
wird. Für alle, die nachrechnen, übernehmen oder einen neuen Datenstand einspielen wollen. Geschrieben am
06.11.2026 zum Stand `6cb7efa` (Zweig `ausbau/3d-grundkarte`), Angaben aus den Kopfkommentaren der Skripte
und aus `pruefen/INVENTAR.md`. Wo ein Skript etwas nicht angibt, steht „nicht angegeben“.

Verwandte Dateien: Quellen und Lizenzen in [`QUELLEN.md`](../QUELLEN.md), Prüfsummen der Rohdaten in
[`belege/rohdaten.md`](../belege/rohdaten.md), alle Belege in [`belege/README.md`](../belege/README.md),
Ladebetrieb und Rollen in [`pruefen/INVENTAR.md`](../pruefen/INVENTAR.md).

## Was man braucht

| Was | Stand 06.11.2026 | Wofür |
|---|---|---|
| Python | 3.13.12 (über uv) | alle Skripte; Aufruf immer mit `-I` |
| uv | 0.11.3 | Pakete aus `requirements.txt`, `--offline` |
| Python-Pakete | `requirements.txt`: psycopg 3.3.6, PyYAML 6.0.3, numpy 2.5.4, scipy 1.18.1, pyproj 3.8.0, shapely 2.2.0, Pillow 13.0.0 (mit Prüfsummen); `requirements-pruefen.txt`: pytest 9.2.0 | Skripte und Prüfungen |
| Geodaten-Import-Pipeline | Repository daneben (`../geodaten-import-pipeline`), eigene `requirements.txt` | Laden (`pipeline.laden`) und Rollen (`pipeline.einrichten`) |
| Datenbank | Container `kiezatlas-potsdam-db-1` (`docker-compose.yml`, PostgreSQL 16, PostGIS 3.6), Port 55461 | alle Schritte mit Datenbank |
| `.env` | `POSTGRES_PASSWORD`, `IMPORT_PASSWORD`, `LESE_PASSWORD`, `RECHNEN_PASSWORD`, chmod 600; in Worktrees `../kiezatlas-potsdam/.env` | Rollen, nie auf der Kommandozeile ausschreiben |
| Rohdaten | `$KIEZ_DATEN` (Standard `../kiezatlas-daten`), dazu `rohdaten/` (Verweis auf `../kiezatlas-potsdam-west/rohdaten`) | Eingang, siehe `belege/rohdaten.md` |
| node | v22.23.4, Pakete aus `package.json` (Playwright 1.64.1, axe-core 4.14.0) | Browser-Prüfungen `pruefen/*.mjs` |
| 7z | 7-Zip 26.05 | `01_vorbereiten.py`, wenn Destatis eine 7z-Datei mit .zip-Endung liefert |
| pdftotext | 26.10.0 | `22_jahre_genau.py` (BLDAM-Liste) |
| WeasyPrint | 68.1 (eigenes Programm, nicht im uv-Zwischenspeicher) | nur für PDF aus den Steckbriefen von `16_export.py` |

### Wie die Python-Versionen ermittelt wurden

Ohne Netz, am 06.11.2026. Bis dahin gab es keine Versionsliste: `skripte/lauf.sh` nahm für `vorbereiten` die
`.venv` des Nachbar-Repos `kiezatlas-potsdam-west`, `12_osm.sh` und `14b_fussweg.sh` holten `--with numpy
--with scipy` ohne Version, die übrigen Skripte nutzen die `requirements.txt` der Pipeline.

1. Pakete aus den `import`-Zeilen von `skripte/` und `pruefen/` gesammelt.
2. `uv run --offline` hat aus dem lokalen Zwischenspeicher numpy 2.5.4, scipy 1.18.1, pyproj 3.8.0, shapely 2.2.0,
   Pillow 13.0.0 und pytest 9.2.0 aufgelöst. Die `.venv` von `kiezatlas-potsdam-west` enthält dieselben Fassungen
   von numpy, pyproj und shapely; psycopg 3.3.6 und PyYAML 6.0.3 stehen so in der `requirements.txt` der Pipeline.
3. `requirements.txt` und `requirements-pruefen.txt` sind mit `uv pip compile --offline --generate-hashes
   --python-version 3.13` aus `requirements.in` bzw. `requirements-pruefen.in` erzeugt; die Prüfsummen stammen aus
   den im Zwischenspeicher abgelegten Paketdaten des Paketindex, ein Netzabruf fand nicht statt. Ein `uv.lock`
   ist nicht angelegt, weil das Repository kein Python-Paket ist.
   Auf einem neuen Rechner ist der Zwischenspeicher leer, dann scheitert `--offline`. Einmal denselben Aufruf
   ohne `--offline` ausführen (`uv run --python 3.13 --no-project --with-requirements requirements.txt
   --with-requirements requirements-pruefen.txt python -c pass`) füllt ihn; die Prüfsummen in
   `requirements.txt` stellen sicher, dass es dieselben Pakete sind.
4. Gegenprobe: `01_vorbereiten.py` mit der neuen Umgebung erzeugt `vorbereitet/stadtteile.csv` und
   `vorbereitet/zensus_potsdam.csv` byte-gleich zu den Dateien vom 04.11.2026 im Haupt-Repo; die Tests von
   `12_osm.sh test` und `14b_fussweg.sh test` laufen grün (Prüfstand unten).

Was sich nicht mehr feststellen lässt: Im Zwischenspeicher liegen numpy 2.5.3 und 2.5.4. Welche von beiden die
Fußweg-Rechnung vom 05.11.2026 (`belege/N1_osm_fussweg_20261105.md`) benutzt hat, ist nirgends notiert.

### Stand der Pipeline

Die Laufberichte (`belege/2026110*.json`) enthalten keinen Commit der Pipeline. Am 06.11.2026 steht das
Pipeline-Repository auf `d7a90a0` (gleich `origin/main`) mit 392 vorgemerkten, nicht eingecheckten Änderungen,
darunter `pipeline/einrichten.py` und `pipeline/ziel.py`, die `lauf.sh einrichten` und `laden` brauchen
(`git write-tree` des vorgemerkten Stands: `cf90acccaae8ac6f2e749a3658cd49edaef57c07`, SHA256 der
`requirements.txt`: `430bed172559d1b6bdea438b8a80941385eb5b8375b47571a42d63ab1576a74f`). `pipeline/laden.py`,
`quellen.py` und `ziel.py` tragen die Dateizeit 06.11.2026 06:19 bis 06:22, also nach den Läufen vom 04. und
05.11. Mit welchem Pipeline-Stand die Laufberichte entstanden sind, lässt sich deshalb nicht mehr belegen. Seit
06.11.2026 schreibt `skripte/lauf.sh laden` den Stand (`git describe --always --dirty`) vor jedem Lauf auf die
Fehlerausgabe; ein fester Stand zum Festschreiben (Commit oder Tag der Pipeline) fehlt noch.

## Rollen

| Rolle | darf | genutzt von |
|---|---|---|
| `admin` | alles | `lauf.sh einrichten` |
| `pipeline_import` | schreibt die Pipeline-Ziele in `public` | `lauf.sh laden` |
| `kiezatlas_rechnen` | liest `public`, schreibt `auswertung` außer dem Gebäudestand, keine DDL | Skripte 11 bis 14b, 20 bis 24 |
| `mosidi_lesen` | nur SELECT, nicht auf `auswertung.gebaeude_adresse` | `02_auswerten.py`, `15_planer.py`, `16_export.py` |

## Schritte

Reihenfolge so, wie sie aufeinander aufbauen. „DB“ heißt Datenbank mit der genannten Rolle. Aufrufe mit allen
Umgebungsvariablen stehen im Kopf jedes Skripts. Die Python-Umgebung in diesen Köpfen ist der Stand vor dem
06.11.2026 (`.venv` von `kiezatlas-potsdam-west` in 01, 03, 15, 25 und `pruefen/b1_jahre.py`, sonst die
`requirements.txt` der Pipeline); seitdem gilt `requirements.txt` dieses Repositorys, also
`uv run --offline --python 3.13 --no-project --with-requirements requirements.txt python -I skripte/…`.

| Nr | Schritt | Skript, Aufruf | liest | schreibt | Prüfung |
|---|---|---|---|---|---|
| 0 | Datenbank einrichten | `skripte/lauf.sh einrichten` (`ausbau_einrichten.py`, dann `pipeline.einrichten --haerten`) | `sql/002_ausbau.sql`, `config/potsdam.yaml`, `.env` | Schema `auswertung`, neue `public`-Ziele, Rollen und Rechte (admin) | Rechtetest in `pruefen/INVENTAR.md` |
| 1 | Rohdaten aufbereiten | `skripte/lauf.sh vorbereiten` (`01_vorbereiten.py`) | `rohdaten/stadtteile.geojson`, `rohdaten/zensus/*.zip`, `$KIEZ_DATEN/zensus/2022/*.zip` | `vorbereitet/stadtteile.csv`, `zensus_potsdam.csv`, `zensus_struktur.csv` | `pruefen/A1_zensus.py` (DB) |
| 2 | Planungsräume aufbereiten | `03_planungsraeume.py --datei … --nr-feld pr --name-feld bez` | `$KIEZ_DATEN/eingang/planungsraume-in-potsdam.geojson` | `vorbereitet/planungsraeume.csv` | `belege/A6_pruefung_20261105.txt` |
| 3 | Laden, je Lauf eine Quelle | `skripte/lauf.sh laden --nur QUELLE` (`pipeline.laden`) | `vorbereitet/*.csv`, WFS der LGB und des MBJS laut `config/potsdam.yaml` | `public.stadtteil`, `zensus_zelle`, `gebaeude`, `zensus_struktur`, `mbjs_kita`, `mbjs_schule`, `alkis_nutzung`, `planungsraum`; Laufbericht (pipeline_import) | Laufberichte `belege/2026110*.txt/json` |
| 4 | Gebäudestand festhalten | in `sql/002_ausbau.sql` (Schritt 0) | `public.gebaeude` | `auswertung.gebaeude_stand_20261105` (85.046 Gebäude) | `pruefen/INVENTAR.md` Abschnitt 3 |
| 5 | Gebäudeform aus ALKIS-NAS (B0) | `20_alkis_nas.py` | `$KIEZ_DATEN/alkis_nas/2026-10-01/alkis_p.zip`, Gebäudestand | `auswertung.alkis_nas_gebaeude`, `auswertung.gebaeude_adresse` (nur intern), `berichte/B0_alkis_nas.md` (rechnen) | `pruefen/B0_nas.py` (DB) |
| 6 | Grundatlas auswerten | `skripte/lauf.sh auswerten` (`02_auswerten.py`) | `public.stadtteil`, `zensus_zelle`, `gebaeude`; Objekthöhe aus `auswertung.alkis_nas_gebaeude` | `daten/stadtteile.js`, `zellen.js`, `kennzahlen.js` und `.json`, `daten/gebaeude/<nr>.js` (lesen) | `pruefen/daten.py`, `pruefen/seiten.mjs` |
| 7 | Einrichtungen und Grün (A2) | `11_einrichtungen.py` | `public.mbjs_kita`, `mbjs_schule`, `alkis_nutzung`, `stadtteil`, Gebäudestand, `$KIEZ_DATEN/mbjs/2026-11-05/kitas_standorte.geojson`, `config/richtwerte.yaml` | `auswertung.einrichtung`, `auswertung.gruenflaeche`, `berichte/A2_gegenprobe.md` (rechnen) | `pruefen/A2_einrichtungen.py` (DB) |
| 8 | OSM-Einrichtungen und Fußwegnetz (A3) | `skripte/12_osm.sh laden --pbf DATEI` (`12_osm.py`, Leser `osm_pbf.py`) | `$KIEZ_DATEN/osm/2026-11-05/potsdam.osm.pbf` | `auswertung.osm_poi`, `netz_knoten`, `netz_kante`, `berichte/A3_vollstaendigkeit.md` (rechnen; ODbL) | `12_osm.sh pruefen` (DB), `12_osm.sh test` |
| 9 | ÖPNV-Haltestellen (A4) | `13_oepnv.py` | `$KIEZ_DATEN/vbb_gtfs/2026-11-05/GTFS.zip`, `config/richtwerte.yaml` | `auswertung.haltestelle` (rechnen) | `pruefen/a4_haltestelle.py`, `a4_gebietsklassen.py` (DB), `a4_stichprobe.py` |
| 10 | Erreichbarkeit in Luftlinie (A5a) | `14_erreichbarkeit.py` | Zellen, Stadtteile, `auswertung.einrichtung`, `gruenflaeche`, Gebäudestand, `config/richtwerte.yaml`, `config/potsdam.yaml` | `auswertung.zelle_erreichbar` und `zelle_gruen` (methode luftlinie), `belege/A5a_erreichbarkeit_<datum>.md`, `belege/A5a_rand_unsicher_<datum>.csv` (rechnen) | `pruefen/A5a_erreichbarkeit.py` (DB) |
| 11 | Fußweg je Zelle (A5b) | `skripte/14b_fussweg.sh rechnen` (`14b_fussweg.py`) | Netz aus Schritt 8, Ziele aus 7 bis 9, Zellen, `config/richtwerte.yaml`, `stops.txt` aus dem GTFS | `auswertung.zelle_erreichbar` und `zelle_gruen` (methode fussweg), `berichte/A5b_fussweg.md` (rechnen; ODbL) | `14b_fussweg.sh pruefen` (DB), `test`, `kreuzprobe` |
| 12 | Planer-Dateien (A6) | `15_planer.py` | `public.zensus_zelle`, `stadtteil`, `planungsraum`, `zensus_struktur`, `auswertung.*` aus 7 bis 11, `config/richtwerte.yaml`, `belege/A5a_rand_unsicher_*.csv`, `vorbereitet/planungsraeume.csv` | `daten/planer.js`, `erreichbar.js`, `einrichtungen.js`, `*_odbl.js`, `belege/A6_planer_<datum>.md` (lesen) | `pruefen/A6_planer.py` (DB), `A6_test_pfade.py`, `daten.py` |
| 13 | Grenzen der Planungsräume (I1) | `17_planungsraeume_js.py [--pruefen]` | `$KIEZ_DATEN/eingang/planungsraume-in-potsdam.geojson`, `daten/planer.js` | `daten/planungsraeume.js` | `--pruefen`, `daten.py` |
| 14 | GIS-Export (A8) | `16_export.py` | `daten/planer.js`, `einrichtungen.js`, `erreichbar.js`, `zellen.js`; Geometrie aus `public.stadtteil`/`planungsraum`, `auswertung.einrichtung`, `gruenflaeche`, `haltestelle` (lesen) | `daten/export/` (GPKG, CSV, QGIS-Projekt, Stile, Steckbriefe, README), `belege/A8_export_<stand>.md` | `pruefen/A8_export.py`, `A8_test_pfade.py` (DB) |
| 15 | Zensus-Baujahr im Gitter (B1) | `21_jahre_zensus.py` | `$KIEZ_DATEN/zensus/2022/Gebaeude_nach_Baujahr_*.zip`, Zellen, Stadtteile | `auswertung.zensus_gebaeude_jahr`, `daten/jahre_zellen.js`, `belege/B1_zensus_jahre.md` (rechnen) | `pruefen/b1_jahre.py` |
| 16 | Genaue Jahre (B2) | `22_jahre_genau.py [--quelle …]` | BLDAM-PDF, Wikipedia-Teillisten, `eingang/wikidata_potsdam_baujahr.csv`, `auswertung.gebaeude_adresse`, Gebäudestand | `auswertung.jahr_beleg`, `berichte/B2_genaue_jahre.md` (rechnen) | `pruefen/B2_jahre.py`, `N3_wd_stichprobe.py` (DB) |
| 17 | Luftbild-Pilot Bornstedt (B3) | `23_luftbild_pilot.py abrufen \| stichprobe \| auswerten` | DOP-Zeitreihe der LGB (Abruf mit `abruf.py`), Gebäudestand | `$KIEZ_DATEN/luftbild_lgb/…`, `auswertung.jahr_klammer`, `berichte/B3_pilot.md` (rechnen) | `pruefen/B3_pilot.py` (DB), `pruefen/B3_protokoll.md` |
| 18 | Kaskade der Gebäudejahre (B4) | `24_jahre_kaskade.py blocktypen \| rechnen \| ruecktest` | Gebäudestand, `auswertung.jahr_beleg`, `jahr_klammer`, `zensus_gebaeude_jahr`, `alkis_nas_gebaeude`, `config/blocktypen.geojson` | `config/blocktypen.geojson`, `auswertung.gebaeude_jahr`, `daten/jahre/<nr>.js`, `berichte/B4_holdout.md` (rechnen) | `pruefen/B4_kaskade.py` (DB), `pruefen/B4_protokoll.md` |
| 19 | Bauzeiten als GeoPackage (B5) | `25_jahre_gpkg.py` | `daten/jahre_zellen.js`, `zellen.js`, `stadtteile.js` | `daten/download/bauzeiten.gpkg` | `pruefen/B5_jahre.mjs` |
| 20 | Kennzahlen der Bauzeiten-Seite (B5) | `26_jahre_methode.py [--pruefen]` | `daten/jahre/<nr>.js`, `berichte/B4_holdout.md` | `daten/jahre_methode.js` | `--pruefen`, `pruefen/B5_methode.py` |
| 21 | Grundkarte | `27_grundkarte.py` | `$KIEZ_DATEN/eingang/basemapde/bm_web_gry.json` | `daten/grundkarte.js` | `daten.py`, Browser-Prüfungen |
| 22 | Kopie zum Hochladen | `deploy_kopie.py [--ziel …]` | Seiten, `daten/`, `fonts/`, `vendor/` | Ordner außerhalb des Repos mit `MD5SUMS` | Abgleich der live geladenen Dateien mit `MD5SUMS` |

Hilfsskripte: `skripte/abruf.py` (jeder Netzabruf, mit Mindestabstand je Rechner und Eintrag in
`$KIEZ_DATEN/abrufprotokoll.tsv`), `skripte/osm_pbf.py` (PBF-Leser für Schritt 8).

Berichte unter `berichte/` sind in `.gitignore` eingetragen; einige sind trotzdem eingecheckt (Übersicht in
`belege/README.md`). `berichte/A3_vollstaendigkeit.md` und `berichte/A5b_fussweg.md`
fehlen im Repository; die tragenden Zahlen stehen in `belege/N1_osm_fussweg_20261105.md`.

## Prüfungen

`./pruefen.sh` führt alle Prüfungen aus, die ohne Netz und ohne Datenbank laufen, zählt sie und gibt bei einem
Befund 1 zurück (`--ohne-browser` lässt die Browser-Prüfungen weg). Die übrigen brauchen die Datenbank und
laufen mit der Rolle aus dem Kopf des Skripts.

| Prüfskript | prüft | braucht | in `pruefen.sh` |
|---|---|---|---|
| `daten.py` | Summen gegen `kennzahlen.json`, jede Datei in `daten/` gegen ihren Vertrag in `daten/schema/`, Fixtures, ODbL-Trennung, keine Adressen und Gebäudekennungen | nur Dateien | ja |
| `B5_methode.py` | `daten/jahre_methode.js` gegen `pruefen/B5_schema/jahre_methode.json` | nur Dateien | ja |
| `A6_test_pfade.py` | Codepfade von `15_planer.py` mit erfundenen Eingaben | nur Dateien | ja |
| `A8_export.py [--odbl-erwartet]` | Export gegen die Datendateien, CSV gleich GPKG, kein OSM ohne `_odbl`; mit PG-Umgebung auch Zählung gegen die DB | Dateien, DB optional | ja, ohne DB |
| `a3_test_osm.py` (über `12_osm.sh test`) | PBF-Leser und Netzaufbau mit selbst erzeugter Mini-PBF (`a3_pbf_schreiben.py`) | nur Dateien; mit `A3_DB_TEST=1` auch DB | ja, ohne DB |
| `a5b_test_fussweg.py` (über `14b_fussweg.sh test`) | Wege in kleinen Netzen, Fußweg ≥ Luftlinie | nur Dateien; mit `A5B_DB_TEST=1` auch DB | ja, ohne DB |
| `a5b_landfilter_kreuzprobe.py` (über `14b_fussweg.sh kreuzprobe`) | Güte des Landesfilters E7 | GTFS unter `$KIEZ_DATEN` | ja |
| `seiten.mjs` | Startseite und Karte per `file://` und HTTP: Konsole, axe, Fragen, Themen, Hash-Links, Export, Gewicht; Startseite mit 3D-Häusern (Liste, Register, Luftbild); acht Breiten (`responsiv.mjs`) | Browser (Playwright) | ja |
| `A7_planer.mjs` | Planer-Seiten wie oben, dazu Startgewicht und Nachladen; acht Breiten (`responsiv.mjs`) | Browser | ja |
| `B5_jahre.mjs` | Bauzeiten-Seiten, Popups, GeoPackage-Abgleich; acht Breiten (`responsiv.mjs`) | Browser | ja |
| `responsiv.mjs` | Baustein der drei Skripte darüber; allein aufgerufen die Messtabelle vorher/nachher (Karte beim Lesen, Überstand, Überlappungen, Tippziele, Legende, Kopfleiste) | Browser, Server des Aufrufers (`--basis`) | nein (Messwerkzeug; die Prüfung läuft in den drei Skripten) |
| `p1_themen.mjs` | `themen.js` gegen den Vertrag `daten/schema/themen.md` | Browser | ja |
| `p1_gleich.mjs` | Zustandsabzug zweier Stände zum Vergleich | Browser, zwei Wurzeln | nein (Vergleichswerkzeug, kein Prüfergebnis) |
| `b1_jahre.py [BASIS]` | `daten/jahre_zellen.js`, dazu dass bestimmte Dateien seit `BASIS` (Standard `ausbau/integration`) unverändert sind | Dateien, git | nein: auf dem heutigen Stand meldet es 2 Abweichungen, weil `QUELLEN.md`, `skripte/02_auswerten.py` und `daten/jahre/` seit `ausbau/integration` geändert wurden (`77bd0d6`, `6cb7efa`) |
| `fixtures_erzeugen.py` | erzeugt die Fixtures unter `daten/fixtures/` | nur Dateien | nein (schreibt) |
| `a3_gegenprobe_gdal.py` | eigener PBF-Leser gegen GDAL | pyogrio (nicht im uv-Zwischenspeicher) | nein |
| `a4_stichprobe.py` | Abfahrten einzelner Haltestellen aus dem GTFS zum Abgleich mit dem Aushang | GTFS, Argumente | nein (Auszug, kein Prüfergebnis) |
| `A1_zensus.py`, `A2_einrichtungen.py`, `a3_pruefen.py`, `a4_haltestelle.py`, `a4_gebietsklassen.py`, `A5a_erreichbarkeit.py`, `a5b_pruefen.py`, `A6_planer.py`, `A8_test_pfade.py`, `B0_nas.py`, `B2_jahre.py`, `B3_pilot.py`, `B4_kaskade.py`, `N3_wd_stichprobe.py`, `n4_einzugsgebiete.py` | Abnahmen der Pakete gegen die Datenbank | DB | nein |

Protokolle und Vorgaben ohne eigenen Lauf: `pruefen/INVENTAR.md` (Abnahmekriterien), `p1_abnahme.md`,
`a3_hinweise.md`, `a4_nvp_lesung.md`, `a5b_hinweise.md`, `B3_protokoll.md`, `B4_protokoll.md`.

Letzter Prüfstand: `belege/pruefstand-20261106-1cf8d56/pruefen.log`, 18 Prüfungen, 16 grün, 2 mit Befund (siehe `belege/README.md`).

## Neuer Datenstand

Für jede neue Fassung einer Quelle gilt derselbe Weg; nichts wird überschrieben, was ein Beleg noch braucht.

1. Datei unter `$KIEZ_DATEN/<quelle>/<stand>/` ablegen, mit `HERKUNFT.md` (URL, Lizenz, Abrufzeit, robots-Befund,
   Bytes, SHA256). Automatische Abrufe nur über `skripte/abruf.py`, Handdownloads dort vermerken.
2. Prüfsumme in `belege/rohdaten.kiez_daten.sha256` (bzw. `rohdaten.sha256`) ergänzen, alte Zeile stehen lassen,
   solange ein Beleg sich darauf bezieht; `./pruefen.sh` prüft die Liste.
3. Pfad bzw. Stand im Skript oder in `config/potsdam.yaml` anpassen, dann die Schritte ab der betroffenen Stelle
   in der Reihenfolge der Tabelle neu laufen lassen (zum Beispiel neue Zensus-Datei: 1, 3, 6, danach 10 bis 14).
   Pipeline-Läufe einzeln und nacheinander (`pruefen/INVENTAR.md`, Ladebetrieb).
4. Neue Laufberichte und Belege nach `belege/`, `./pruefen.sh` laufen lassen, Log als neuen Prüfstand ablegen.

Sonderfall Gebäude: `gebaeude_alkis` steht in `config/potsdam.yaml` auf `aktiv: false`, weil Teil B sich auf
`auswertung.gebaeude_stand_20261105` bezieht und ein neuer WFS-Lauf Gebäude löschen könnte. Der Name dieses
Stands steht fest in 15 Dateien unter `skripte/`, `pruefen/` und `sql/` (`git grep -l gebaeude_stand_20261105 -- skripte pruefen sql`).
Ein neuer Gebäudestand heißt deshalb: neue Kopie unter neuem Namen, alle diese Stellen umstellen, Teil B (Schritte 5,
16 bis 18) und die Schritte 6, 7 und 10 neu rechnen. Der heutige Stand ist nicht außerhalb der Datenbank gesichert
(offen, `belege/rohdaten.md`).
