# Quellen und Lizenzen (Lizenzregister)

Eine Zeile je Quelle des Kiezatlas Potsdam samt Ausbau (Planer-Ebene A, Gebäudejahre B). Angelegt von P0
am 05.11.2026, in der Integration (I1/I2, 05.11.2026) mit den Zulieferungen `quellen-<paket>.md` aller Pakete
zusammengeführt; die Zulieferungen bleiben als Belege im Repo. Herkunft der Rohdaten im Einzelnen: `$KIEZ_DATEN/<quelle>/<stand>/HERKUNFT.md`,
jede automatische Anfrage in `$KIEZ_DATEN/abrufprotokoll.tsv`.

## Vermerke

- **dl-de/by-2-0:** Bereitsteller, Lizenz mit Link zum Lizenztext und, sobald Daten verändert sind, der Zusatz
  „Daten verändert (eigene Berechnung)“. Muster: „© Statistische Ämter des Bundes und der Länder, Zensus 2022,
  dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)“.
- **ODbL 1.0:** „© OpenStreetMap-Mitwirkende, ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/)“. Nur in
  Dateien mit `_odbl` im Namen (`daten/*_odbl.js`, später `*_odbl.gpkg`). Die abgeleitete Datenbank wird auf der
  Download-Seite angeboten (Share-Alike, Prüfbericht 4).
- **CC BY 4.0 (VBB):** „VBB Verkehrsverbund Berlin-Brandenburg GmbH, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), Daten verändert (eigene Berechnung)“.

## Abrufregeln (gelten für jede Anfrage, auch HEAD, robots.txt, Verzeichnisseiten)

| Rechner | Weg | Mindestabstand | robots.txt (05.11.2026) |
|---|---|---|---|
| www.destatis.de | nur `/static/…` | 30 s | 200, `Crawl-delay: 30`, `/static/` erlaubt |
| schullandschaft.brandenburg.de | `/edugis/wfs/…` | 2 s | 404 (keine), Bedingungen in den Capabilities |
| isk.geobasis-bb.de | WFS `alkis_vereinf_wfs`, `alkis_nas_wfs` | 1 s | 404 (keine) |
| data.geobasis-bb.de | Verzeichnisse und Dateien | 1 s (genutzt: 2 s) | 404 (keine) |
| geobasis-bb.de, WMS (mapproxy) | DOP-Zeitreihe (B3) | 10 s | `crawl-delay: 10` laut Erkundung, vor B3 erneut lesen |
| www.vbb.de | `/gtfs` | 2 s | 200, `Allow: /`, Content-Signal `ai-train=no, use=reference` |
| www.potsdam.de, potsdam.de | PDFs unter `/system/files/` | 5 s | vor dem ersten Abruf lesen |

**Verboten automatisiert:** opendata.potsdam.de (alles), overpass-api.de, osmnx-Downloads, query.wikidata.org,
wikidata.org/w/, wikipedia.org/w/ und API, taginfo, nominatim, Geofabrik- und BBBike-Downloads, DDB-Websuche,
api.github.com, raw.githubusercontent.com. Dafür gibt es Handdownloads von Andre nach `$KIEZ_DATEN/eingang/`.
`skripte/abruf.py` lehnt diese Rechner ab und hält den Abstand je Rechner über das Protokoll ein.

## Register

Spalten: Paket = wer die Quelle nutzt. Weg: A = automatisch (Werkzeug), H = Handdownload Andre, L = lokal vorhanden.

| # | Quelle | Paket | URL | Lizenz | Vermerk | Weg | Stand / Abruf |
|---|---|---|---|---|---|---|---|
| 1 | Stadtteile der Landeshauptstadt Potsdam | Bestand | opendata.potsdam.de (Datensatz Stadtteile) | dl-zero-de/2.0 | © Landeshauptstadt Potsdam, dl-zero-de/2.0 | H (robots sperrt /api/ und Downloads) | 04.11.2026 |
| 2 | Zensus 2022, 100-m-Gitter: Bevölkerung, Alter (5 Klassen), Durchschnittsalter, Heizungsart, Energieträger, Wohnungen nach Baujahr | Bestand | https://www.destatis.de/static/DE/zensus/gitterdaten/ | dl-de/by-2-0 | © Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) | L (rohdaten/, Crawl-delay 30 eingehalten) | 03.11.2026 |
| 3 | Zensus 2022, 100-m-Gitter: infrastrukturelle Altersgruppen, Haushaltsgröße, Haushaltstyp, Kernfamilie, Seniorenstatus, Staatsangehörigkeit (Gruppen), Nettokaltmiete, Leerstandsquote, Wohnfläche je Bewohner | A1, A6 | https://www.destatis.de/static/DE/zensus/gitterdaten/<Datei>.zip | dl-de/by-2-0 | wie 2 | A (P0), 31 s Abstand; A1 lädt offline per `skripte/lauf.sh laden --nur zensus_struktur` | 05.11.2026, `zensus/2022/`; `public.zensus_struktur` 6.334 Zellen (Lauf 20261105T101043Z) |
| 4 | Zensus 2022: Gebäude nach Baujahr (Jahrzehnte), Gebäude nach Baujahr (Mikrozensus-Klassen), Gebäude mit Wohnraum nach Gebäudetyp | B1, B3 (Gegenprobe), B4 | wie 3 | dl-de/by-2-0 | wie 2 | A (P0), 31 s Abstand; B1 liest die Zips selbst (`skripte/21_jahre_zensus.py`) | 05.11.2026, `zensus/2022/`; `auswertung.zensus_gebaeude_jahr` 60.480 Zeilen, `daten/jahre_zellen.js` |
| 5 | ALKIS vereinfacht, Gebäude (`ave:GebaeudeBauwerk`) | Bestand, A2 (Gemeinbedarf), B (Snapshot) | https://isk.geobasis-bb.de/ows/alkis_vereinf_wfs | dl-de/by-2-0 | © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) | A, Pipeline `gebaeude_alkis` (seit Teil B `aktiv: false`) | 04.11.2026; Snapshot `auswertung.gebaeude_stand_20261105` |
| 6 | ALKIS vereinfacht, tatsächliche Nutzung (`ave:Nutzung`) | A2, A5a | wie 5 | dl-de/by-2-0 | wie 5 | A, Pipeline `alkis_nutzung`, 2-km-Kacheln, 1 s | 05.11.2026, 28.121 Flächen; `auswertung.gruenflaeche` 4.892 |
| 7 | MBJS Kita-Standorte (`ms:KITA_Standorte`) | A2, A5a, A6 | https://schullandschaft.brandenburg.de/edugis/wfs/kitas | dl-de/by-2-0 | © Ministerium für Bildung, Jugend und Sport, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) | A, Pipeline `mbjs_kita`; alle Standorte als GeoJSON | 05.11.2026, 220 Kitas / 240 Standorte; in Potsdam 151 Kitas, 20.953 Plätze |
| 8 | MBJS Schulstandorte (`ms:Schul_Standorte`) | A2, A5a, A6 | https://schullandschaft.brandenburg.de/edugis/wfs/schulen | dl-de/by-2-0 | wie 7 | A, Pipeline `mbjs_schule` | 05.11.2026, 106 Schulen, 78 in Potsdam |
| 9 | ALKIS NAS, Bestandsdatenauszug ohne Eigentümer, Potsdam (`alkis_p.zip`) | B0, B4 | https://data.geobasis-bb.de/geobasis/daten/alkis/Vektordaten/nas/alkis_p.zip | dl-de/by-2-0 | wie 5 | A (Freigabe H7), SHA256 `4b92f837…f094ce` in `alkis_nas/2026-10-01/HERKUNFT.md` | Stichtag 01.10.2026, Abruf 05.11.2026; `auswertung.alkis_nas_gebaeude` 52.351; Adressen nur intern |
| 10 | VBB-Fahrplandaten GTFS | A4, A5b (Landesfilter) | https://www.vbb.de/gtfs | CC BY 4.0 | VBB Verkehrsverbund Berlin-Brandenburg GmbH, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), Daten verändert (eigene Berechnung) | A (Freigabe H6), 84.657.543 B, SHA256 `78870d01…6fdbf` | 05.11.2026, Fahrplan ab 03.11.2026, Stichtag 10.11.2026; `auswertung.haltestelle` 315 |
| 11 | OpenStreetMap-Auszug (PBF) für Einrichtungen und Fußwegnetz | A3, A5b, B2 (nur Prüfspalte) | Handdownload H5: BBBike-Auszug Potsdam (empfohlen) oder Geofabrik Brandenburg | ODbL 1.0 | © OpenStreetMap-Mitwirkende, ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/) | H5 (automatisch verboten), danach offline `skripte/12_osm.sh laden` nach `$KIEZ_DATEN/osm/<stand>/` | BBBike-Auszug Potsdam, Stand 31.10.2026, abgelegt 05.11.2026 11:58 unter `osm/2026-11-05/potsdam.osm.pbf` (SHA256 in `HERKUNFT.md`); verarbeitet 05.11.2026 (N1): `osm_poi` 941, Netz 128.921 Knoten / 144.709 Kanten, Fußweg je Zelle in `zelle_erreichbar` |
| 12 | Planungsräume (19), Sozialräume (6), statistische Bezirke (86) | A6, A8, I1 | https://opendata.potsdam.de/explore/dataset/planungsraume-in-potsdam/ (und Geschwister) | dl-de/by-2-0 (laut Datensatz) | © Landeshauptstadt Potsdam, Planungsräume Stand 31.12.2025, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung; in `planungsraeume.js`: Grenzen auf 3 m vereinfacht, Koordinaten gerundet, Felder ausgewählt) | H1 nach `$KIEZ_DATEN/eingang/` | 05.11.2026; Planungsräume genutzt in `daten/planer.js`, `daten/planungsraeume.js`, Export; statistische Bezirke (Stand 31.12.2021) für die ÖPNV-Gebietsklasse (A4/N2, `config/richtwerte.yaml`), in `daten/planer.js` mit Vermerk „© Landeshauptstadt Potsdam, Statistische Bezirke, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)“ (N4); Sozialräume nicht genutzt; `public.planungsraum` ist leer (geprüft 06.11.2026, 0 Zeilen; der Planer liest die Grenzen aus `vorbereitet/planungsraeume.csv`, erzeugt von `skripte/03_planungsraeume.py` aus dem Handdownload in `$KIEZ_DATEN/eingang/`) |
| 13 | Grundschuleinzugsgebiete (Stand 2018) | A6 | opendata.potsdam.de | Nutzungsbedingungen der LHP (nicht dl-de), vor Veröffentlichung prüfen | – | H2 | liegt seit 05.11.2026 in `eingang/`; nur intern als Prüfspalte (`pruefen/n4_einzugsgebiete.py`, Ergebnis unter `$KIEZ_DATEN/intern/`, nicht im Repo, N4); nichts davon in `daten/` oder Export; Grundschulwerte bleiben vorläufig |
| 14 | Grünflächen in Potsdam (mit Spielplätzen) | A3 (Gegenprobe) | opendata.potsdam.de | Nutzungsbedingungen der LHP (nicht dl-de), vor Veröffentlichung prüfen | – | H3 | liegt seit 05.11.2026 in `eingang/`, nicht verarbeitet |
| 15 | Gebäude nach Baualter seit 1999, Einwohner- und Haushaltsreihen | B4, A6 | opendata.potsdam.de | dl-de/by-2-0 (Baualter) | © Landeshauptstadt Potsdam, dl-de/by-2-0 | H4 | Baualter seit N3 in B4 verarbeitet, nur Plausibilität (Stadtsummen 2022/2025, `berichte/B4_holdout.md`, Methodenseite); Einwohnerreihen fehlen |
| 16 | Bevölkerungsprognose je Planungsraum | A6 | Stadt Potsdam (Portal oder Bericht) | offen | offen | H11 | fehlt |
| 17 | Nahverkehrsplan 2019 (Richtwerte, Kap. 4.1) | A4, A6 | https://www.potsdam.de/system/files/documents/2020-09-29_nvp_potsdam_mit_anlagen.pdf | amtliches Dokument ohne Lizenzangabe; nur Fakten mit Seite übernommen | Quelle mit Seite in `config/richtwerte.yaml`, Abschnitt `oepnv` | A, ≥ 5 s, robots.txt vorher gelesen | gelesen 05.11.2026 (A4, `pruefen/a4_nvp_lesung.md`), Geltung 2019–2023, Nachfolger ungeprüft |
| 18 | Einzelhandelskonzept 2014 | A6 | Stadt Potsdam | nur Fakten | wie 17 | offen | Erkundung |
| 19 | Schülerfahrtkostensatzung 2016 | A6 | Stadt Potsdam | nur Fakten | wie 17 | offen | Erkundung |
| 20 | Potsdamer Baulandmodell, Fortschreibung 2019 (Anlage C, Versorgungsquoten) | A6 | https://www.potsdam.de/system/files/documents/anlage1potsdamerbaulandmodell-fortschreibung2019.pdf | keine Angabe; nur Fakten mit Fundstelle | „Richtlinie zur sozialgerechten Baulandentwicklung der Landeshauptstadt Potsdam, Stand 20.11.2019, Anlage C“ | A, ≥ 5 s, robots.txt vorher gelesen, 2 Anfragen | gelesen 05.11.2026 (A6), Anlage C S. 38; `config/richtwerte.yaml`, Abschnitt `baulandmodell` |
| 21 | Integrierte Kita- und Schulentwicklungsplanung 2021–2026 | A6 | https://vv.potsdam.de/vv/Integrierte-Kita-und-Schulentwicklungsplanung-Landeshauptstadt-Potsdam-2021-bis-2026-Teil-2-Schulentwicklungsplanung.pdf | nur Fakten | wie 17 | robots vv.potsdam.de vorher | nicht geöffnet |
| 22 | Umweltatlas Berlin, Methode Grünversorgung 2020 | A6 | https://www.berlin.de/umweltatlas/nutzung/oeffentliche-gruenanlagen/2020/methode/ | Methode (Text nicht übernommen) | „Berliner Methode“ mit Link | gelesen in der Erkundung | 05.11.2026 |
| 23 | LGB-Luftbilder als WMS: `dop100g_1953`, `dop50g_1992_1997`, `dop40g_2001_2009`, `dop20_2009_2012` bis `dop20_2019_2021`, `dop20c`, je mit `*_info` | B3 (Pilot Bornstedt) | https://isk.geobasis-bb.de/mapproxy/<dienst>/service/wms | dl-de/by-2-0 | © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) | A, ≥ 10 s (115 Anfragen, kleinster Abstand 10,0 s) | 05.11.2026; Pilot nicht ausgerollt, Bilder nur in `luftbild_lgb/2026-11-05/` |
| 24 | Messtischblätter DR25 (WMS der LGB) | B3 (vorgesehen) | wie 23 | dl-de/by-2-0 | Staatsbibliothek zu Berlin – Preußischer Kulturbesitz; © GeoBasis-DE/LGB | – | nicht abgerufen, nicht genutzt |
| 25 | Deutsche Digitale Bibliothek, API (Datengeber BLDAM) | B2 | https://api.deutsche-digitale-bibliothek.de | CC0 laut Pressemitteilung 2013, zu bestätigen | – | A mit API-Key (H8), ≥ 2 s; Websuche verboten | fehlt (H8) |
| 26 | Wikipedia, Listen der Baudenkmale in Potsdam (Übersicht und 27 Teillisten) | B2, B4 (nur Prüfspalte und Rücktest) | https://de.wikipedia.org/wiki/… | CC BY-SA 4.0 (auch Datenbankrecht) | nie in `gebaeude_jahr` oder `daten/` (Prüfbericht 5) | nur `/wiki/`-HTML, ≥ 2 s; Revisionen in `wikipedia_denkmale/2026-11-05/HERKUNFT.md` | 05.11.2026; `auswertung.jahr_beleg` nur `nur_pruefung = true` |
| 27 | Wikidata, SPARQL-Export | B2 | WDQS im Browser | CC0 | – | H9 | seit N3 eingelesen (196 Zeilen nach Aussortieren); veröffentlicht nur über die eigene Koordinate zugeordnet (150 Gebäude, davon 106 genau): Stufe 1 der Kaskade, Einzeljahr nur ohne Wohnraum. Zuordnung über die Denkmal-ID nur Prüfspalte (läuft über die BLDAM-Liste, siehe 28) |
| 28 | BLDAM-Denkmalliste Potsdam (PDF, Stand 01.01.2026) | B2 | https://bldam-brandenburg.de/wp-content/uploads/2026/03/04_P_Internet-25.pdf | offen (§ 87a UrhG) | – | A (einmal), SHA256 `45ede0d4…d7ae3`; Anfrage E8 als Entwurf | nur Schlüssel MIDAS-ID → Gebäude, ohne Jahr, nur intern (`nur_pruefung`); auch die Zuordnung der Wikidata-Jahre über diesen Schlüssel ist nur Prüfspalte |
| 29 | Broschüre „Potsdamer Platte“ (Landeshauptstadt Potsdam, Juli 2008, Bearbeitung Stadtkontor) | B4 | stadtkontor.de | keine offene Lizenz; nur Fakten (Bauzeiträume) | „Bauzeiten: Landeshauptstadt Potsdam, „Potsdamer Platte“, Juli 2008“; Beleg je Gebiet in `config/blocktypen.geojson` | einmal geladen, SHA256 `99778123…0f53` | 05.11.2026, `potsdamer_platte/2026-11-05/` |
| 30 | basemap.de Web Vektor (Grundkarte; Stil bm_web_gry gekürzt, `daten/grundkarte.js`); Web Raster grau nur noch als Rückfall | Bestand, 06.11.2026 | https://sgx.geodatenzentrum.de/gdz_basemapde_vektor/ | CC BY 4.0 (ersatzweise dl-de/by-2-0) | © GeoBasis-DE / BKG (2026) CC BY 4.0, Links auf https://www.bkg.bund.de und https://creativecommons.org/licenses/by/4.0/, Kartenstil verändert (Nutzungsbedingungen: kiezatlas-daten/eingang/basemapde/) | im Browser des Lesers (Kacheln und Kartenschrift) | laufend |
| 31 | Luftbild DOP20c (Hintergrund) | Bestand | https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms | dl-de/by-2-0 | © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), unverändert angezeigt | im Browser des Lesers | laufend |
| 32 | 3D-Gebäude LoD2 (nur Potsdam-West, lokal) | Bestand (nicht in der Pipeline) | https://inspire.brandenburg.de/services/bu-core3d_lod2_wfs | dl-de/by-2-0 | © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) | L | 03.11.2026 |
| 33 | visinage, Methodenvorbild (Kaskade, Rücktest) | B (Methodenseite) | berlin.visinage.com | keine Datenübernahme | einmal als Methodenvorbild nennen | – | – |
| 34 | Zensus 2022, Gemeindeergebnis Potsdam (12054000) als unabhängiger Bezugswert je Thema | A1 (Prüfung) | ergebnisse.zensus2022.de | dl-de/by-2-0 | wie 2 | H (Zensusdatenbank nicht in den Abrufregeln freigegeben) nach `$KIEZ_DATEN/eingang/zensus2022_gemeinde_potsdam.csv` | liegt seit 05.11.2026 in `eingang/`; ausgewertet von `pruefen/A1_zensus.py` (Nachlauf N2, 05.11.2026): Gitter gegen Gemeinde je Thema unter 3 %, Einwohner −0,07 %, 0 Befunde (`belege/A1_gemeindeabgleich_20261105.md`) |

Datenschutz: keine Personendaten. MBJS ohne Telefon, Fax, E-Mail, Straße; OSM ohne `name` bei Ärzten, Pflege
und Apotheken; Gebäudeadressen nur intern (`auswertung.gebaeude_adresse`), nie in `daten/` oder Exporte;
Gebäude mit Wohnraum nur mit Bauzeitklasse, ohne Einzeljahr, auch Denkmale (ALKIS führt keine Zahl der Wohneinheiten);
in `daten/jahre/` keine Gebäudekennung (oid, gml_id).

## Ausgaben und ihre Lizenz

| Ausgabe | Paket | Grundlage (Nr.) | Lizenz | veröffentlicht |
|---|---|---|---|---|
| `daten/zellen.js`, `kennzahlen.js`, `kennzahlen.json`, `gebaeude/<nr>.js`, `stadtteile.js` | Bestand | 1, 2, 5 | dl-de/by-2-0 bzw. dl-zero-de/2.0 | ja |
| `daten/einrichtungen.js` | A2, A6 | 5, 6, 7, 8 | dl-de/by-2-0 | ja, ohne Adresse und Kontakt |
| `daten/erreichbar.js` (Luftlinie) | A5a, A6 | 2, 5–8 | dl-de/by-2-0 | ja |
| `daten/planer.js` (Versorgung je Planungsraum) | A6 | 2, 3, 5–8, 10, 12, 17, 20 | dl-de/by-2-0 und CC BY 4.0 (ÖPNV-Werte) | ja |
| `daten/planungsraeume.js` (Grenzen für die Planer-Karte) | I1 | 12 | dl-de/by-2-0 | ja |
| `daten/*_odbl.js`, `daten/export/*_odbl.gpkg`, `csv_odbl/` | A3, A5b, A6, A8 | 11 und weitere (Haltestellen-Ziele: 10) | ODbL 1.0 | ja, seit 05.11.2026: `daten/*_odbl.js` (N1), `kiezatlas_potsdam_odbl.gpkg` und `csv_odbl/` (N4); alle auf der Download-Seite angeboten (Share-Alike) |
| `daten/export/kiezatlas_potsdam.gpkg`, `csv/*.csv`, `steckbriefe/<nr>.html` | A8 | wie `planer.js`, dazu Grünflächen und Haltestellen | je Ebene (Tabelle `lizenz`) | ja |
| `daten/jahre_zellen.js` | B1 | 4 | dl-de/by-2-0 | ja |
| `daten/jahre/<nr>.js`, `daten/jahre_methode.js`, `daten/download/bauzeiten.gpkg` | B4, B5 | 2, 4, 5, 9, 15 (nur `jahre_methode.js`), 27 (nur `jahre/<nr>.js`), 29 | dl-de/by-2-0; belegte Jahre (`q = "beleg"`) aus Wikidata CC0 1.0; Bauzeiten der Großsiedlungen als Fakten mit Nennung | ja; nur Klasse, kein Einzeljahr bei Gebäuden mit Wohnraum, keine Adresse, kein Denkmal-Kennzeichen aus der BLDAM-Liste. „belegt“ heißt: Baudenkmal laut Wikidata (CC0, öffentlich), so auch auf der Karte; ein Jahr gibt es dort nur ohne Wohnraum (Korrektur 6) |
| `auswertung.jahr_beleg` (BLDAM, Wikipedia) | B2 | 26, 28 | CC BY-SA 4.0 bzw. ungeklärt | nein, nur Prüfung |
| `auswertung.jahr_klammer` (Luftbild-Pilot) | B3 | 23 | dl-de/by-2-0 | nein, Pilot nicht ausgerollt |
| `auswertung.gebaeude_adresse` | B0 | 9 | dl-de/by-2-0 | nie (für `mosidi_lesen` gesperrt) |

