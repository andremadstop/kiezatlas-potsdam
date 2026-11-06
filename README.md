# Kiezatlas Potsdam

Alle 32 Stadtteile der Landeshauptstadt Potsdam in Zahlen und Karte, nur aus offenen amtlichen Daten:
Zensus 2022 im 100-Meter-Gitter, die amtlichen Stadtteile und die Gebäudeumrisse der Landesvermessung.
Wer wo wohnt, wie alt die Häuser sind, womit geheizt wird, für die ganze Stadt und jeden Stadtteil, und
bei jeder Zahl, woher sie kommt.

Prototyp der Stiebitz Souverain Systems UG (haftungsbeschränkt), Potsdam, Stand November 2026.

## Zur Prüfung, Stand 06.11.2026

Jede Kernzahl mit dem Beleg, der sie trägt, und dem Skript, das sie erzeugt. Stand des Codes `6cb7efa` mit den
Ergänzungen dieses Kastens; der Weg aller Skripte steht in [`docs/rundgang.md`](docs/rundgang.md), alle Belege in
[`belege/README.md`](belege/README.md).

| Angabe | Beleg | Skript |
|---|---|---|
| 182.673 Einwohner in 3.443 Gitterzellen mit Mittelpunkt in Potsdam und Einwohnerwert, 32 Stadtteile ohne Abweichung | `belege/pruefstand-20261106-1cf8d56/pruefen.log` (Abschnitt `pruefen/daten.py`) | `skripte/02_auswerten.py`, geprüft von `pruefen/daten.py` |
| 52.309 Gebäude in den 32 Stadtteilen, 85.046 im Abrufrechteck | `belege/20261104T132333Z.txt`, `pruefstand-20261106-1cf8d56/pruefen.log` (`daten.py`) | Pipeline, `skripte/02_auswerten.py` |
| Gebäudehöhe: 50.356 von 52.309 aus der ALKIS-Objekthöhe, 73 aus Geschossen × 3 m, 1.880 mit 3 m | `belege/3D_grundkarte_20261106.md` | `skripte/20_alkis_nas.py`, `skripte/02_auswerten.py` |
| Planer auf 19 Planungsräumen | `belege/A6_planer_20261105.md`, `belege/N4_planer_lauf_20261105.txt` | `skripte/15_planer.py` |
| 315 Haltestellen, 283 davon in Potsdam, je mit Taktklasse | `belege/a4_pruefung_20261105.txt` | `skripte/13_oepnv.py` |
| Fußwegnetz aus OSM: 128.921 Knoten, 144.709 Kanten | `belege/N1_osm_fussweg_20261105.md` | `skripte/12_osm.py` |
| Landesfilter E7 (Ziele in Brandenburg zählen, in Berlin nicht): 15 von 1.800 Haltepunkten falsch zugeordnet (0,8 %) | `belege/A5b_landfilter_kreuzprobe.txt`, `pruefstand-20261106-1cf8d56/pruefen.log` | `pruefen/a5b_landfilter_kreuzprobe.py` |
| Zensus-Baujahr: 2.869 Zellen mit 23.155 Gebäuden mit Wohnraum | `belege/B1_zensus_jahre.md` | `skripte/21_jahre_zensus.py` |
| Bauzeit je Gebäude, Stufen 1 bis 6: 106 / 0 / 815 / 17.294 / 8.501 / 25.593 Gebäude | `berichte/B4_holdout.md` | `skripte/24_jahre_kaskade.py` |
| Rücktest an 193 Gebäuden in Bornstedt: Zensus-Verteilung trifft 125 von 169 (74,0 %) | `berichte/B4_holdout.md` | `skripte/24_jahre_kaskade.py ruecktest` |
| Einzeljahr nur bei 53 Gebäuden, keines davon mit Wohnraum | `berichte/B4_holdout.md`; Vertrag `daten/schema/jahre_gebaeude.json` geprüft in `pruefstand-20261106-1cf8d56/pruefen.log` (`daten.py`) | `skripte/24_jahre_kaskade.py` |
| Rohdaten: 7 Kerndateien und 78 Dateien unter `$KIEZ_DATEN` mit SHA256 (ohne die 2 nur intern genutzten) | `belege/rohdaten.md` | `./pruefen.sh` |

Nicht belegt sind bisher: welcher Stand der Geodaten-Import-Pipeline die Laufberichte vom 04. und 05.11.2026
erzeugt hat, und eine Sicherung des Gebäudestands `auswertung.gebaeude_stand_20261105` außerhalb der Datenbank
(beides in `docs/rundgang.md`).

## Wie es gebaut ist

```
rohdaten/ (lokal)          Geodaten-Import-Pipeline            PostGIS                    Seite
Stadtteile (Handdownload) ─┐                                 ┌ stadtteil          ┐
Zensus-Gitter (Destatis) ──┼─ 01_vorbereiten.py ─ CSV ─┐     │ zensus_zelle       ├─ 02_auswerten.py ─ daten/*.js ─ index.html
ALKIS-Gebäude ─────────────┴──────── WFS der LGB ──────┴─────┤ gebaeude           ┘   (Zuordnung, Summen,
                                                             └ pipeline_meta (Läufe, Protokoll)   Grenzfall in SQL)
```

Der Grundatlas entsteht in vier Schritten:

1. `skripte/01_vorbereiten.py` macht aus den lokal liegenden Rohdaten CSV-Dateien. Kein Netzabruf.
2. Die [Geodaten-Import-Pipeline](https://github.com/andremadstop/geodaten-import-pipeline) lädt Stadtteile,
   Zensus-Gitter und, direkt aus dem WFS der Landesvermessung, die Gebäude in PostGIS
   (`config/potsdam.yaml`): Abgleich je Quelle, Bericht je Lauf, Rhythmus, Rollen nach geringsten Rechten.
   Die Pipeline ist ein eigenes Projekt der UG für den automatischen Import amtlicher Geodaten; hier läuft sie
   nur mit einer anderen Konfiguration und eigenen Zieltabellen (`sql/001_kiezatlas.sql`).
3. `skripte/02_auswerten.py` rechnet in PostGIS mit der Leserolle: Zelle und Gebäude je Stadtteil,
   Kennzahlen, Verteilungen, den Grenzfall-Vergleich, und schreibt `daten/` für die Seite.
4. `index.html` zeigt das Ergebnis; Gebäude eines Stadtteils werden erst bei seiner Auswahl geladen.

Seit dem Ausbau (05. und 06.11.2026) kommen drei Teile dazu, jeder mit eigenen Skripten:

- **Planer** (`planer.html`): Einrichtungen, Grün und Haltestellen (`11_einrichtungen.py`, `12_osm.py`,
  `13_oepnv.py`), Entfernung je Zelle in Luftlinie und zu Fuß (`14_erreichbarkeit.py`, `14b_fussweg.py`),
  Versorgung je Planungsraum (`15_planer.py`, `17_planungsraeume_js.py`).
- **Bauzeiten** (`jahre.html`): Gebäudeform aus dem ALKIS-NAS-Auszug (`20_alkis_nas.py`), Zensus-Baujahr im
  Gitter (`21_jahre_zensus.py`), genaue Jahre (`22_jahre_genau.py`), Luftbild-Pilot (`23_luftbild_pilot.py`),
  Kaskade und Rücktest (`24_jahre_kaskade.py`), GeoPackage und Kennzahlen (`25_jahre_gpkg.py`,
  `26_jahre_methode.py`).
- **Export** (`planer-daten.html`, `daten/export/`): GeoPackage, CSV, QGIS-Projekt und Steckbriefe (`16_export.py`);
  Grundkarte aus dem Vektorstil von basemap.de (`27_grundkarte.py`).

Was jedes Skript liest und schreibt und womit es geprüft wird, steht in [`docs/rundgang.md`](docs/rundgang.md),
dort auch der Abschnitt „Neuer Datenstand“. Schrittweise für den Grundatlas: `skripte/lauf.sh vorbereiten |
laden --nur QUELLE | auswerten | einrichten` (braucht Docker, uv, `.env` mit den Passwörtern, daneben das
Repository der Pipeline). Jeder Lauf lädt nur eine Quelle; Rohdaten liegen außerhalb des Repos unter `KIEZ_DATEN`
(`../kiezatlas-daten`), Herkunft und Lizenzen in `QUELLEN.md`, Prüfsummen in `belege/rohdaten.md`, Lizenz der
Dateien in `daten/` in `daten/LIZENZ.md`.

## Prüfen

`./pruefen.sh` führt alle Prüfungen aus, die ohne Netz und ohne Datenbank laufen: Syntax, Datenverträge und
Summen (`pruefen/daten.py`), Export, Tests der Rechenwege, Rohdaten-Prüfsummen und die Browser-Prüfungen der
Seiten (`pruefen/*.mjs`, je mit eigenem Port, Fremdabrufe beantwortet der Prüfbrowser selbst). Es zählt grüne,
rote und übersprungene Prüfungen und gibt bei einem Befund 1 zurück; `--ohne-browser` lässt die Seitenprüfungen
weg. Das Log je geprüftem Stand liegt unter `belege/pruefstand-<datum>-<commit>/`. Die Abnahmen gegen die
Datenbank nennt der Rundgang.

## Umgebung

Python 3.13 über uv, Pakete mit exakten Versionen und Prüfsummen in `requirements.txt` (dazu
`requirements-pruefen.txt` für pytest), aufgelöst ohne Netz aus dem lokalen Zwischenspeicher; wie die Versionen
ermittelt wurden, steht im Rundgang. Auf einem neuen Rechner füllt ein Aufruf ohne `--offline` den Zwischenspeicher einmal (Rundgang). Die
Geodaten-Import-Pipeline bringt ihre eigene `requirements.txt` mit. Ihr
Stand am 06.11.2026 ist Commit `d7a90a0` mit nicht eingecheckten Änderungen; einen festen Stand (Commit oder Tag)
gibt es dafür noch nicht.

## Die Seite

https://souverain-systems.de/kiezatlas/ (oder `index.html` per Doppelklick, ohne Server)

- **Neun Fragen** führen durch die Karte, von „Wie viele Menschen wohnen in meiner Nachbarschaft?“ bis
  „Wann wurde mein Viertel gebaut?“, danach „Jetzt gehört die Karte Ihnen.“ zum freien Erkunden; jede stellt
  Stadtteil, Thema und Kamera ein und erklärt nebenbei eine Funktion.
  Alle Antworten rechnet der Browser aus den Daten in `daten/`, im Text steht keine Zahl von Hand.
- **3D-Gitter:** Jede Zensus-Zelle ist eine Säule, Höhe und Farbe zeigen denselben Wert. Gebäude in 3D und
  das Luftbild der Landesvermessung lassen sich zuschalten.
- **Register und Steckbrief** für alle 32 Stadtteile, sortierbar, mit Quelle je Zahl.
- **Schaugrafik:** ein bis vier Gebiete, Rubriken und Format wählen (A4 hoch und quer, halbe Seite, Spalte,
  Quadrat), dann als SVG, PNG mit 300 dpi oder über die Druckansicht als PDF herunterladen. Quellen und Lizenzen
  stehen in jeder Grafik; die Karte darin ist aus den eigenen Daten gezeichnet, ohne fremde Kartenkacheln.
- Bibliotheken (MapLibre GL JS, GSAP) und Schrift (Barlow, SIL Open Font License) liegen in `vendor/` und
  `fonts/`; von fremden Servern kommen nur die Grundkarte (basemap.de, Kacheln und
  Beschriftungsschrift) und das Luftbild (LGB).

## Grenzfall: Wem gehört eine Zelle auf der Grenze?

Gitterzellen und Stadtteilgrenzen passen nicht aufeinander. Die Seite ordnet jede Zelle dem Stadtteil zu,
in dem ihr Mittelpunkt liegt; zur Probe rechnet die Datenbank dieselben Einwohner nach dem Flächenanteil
jeder Zelle (in EPSG:3035, dem Bezugssystem des Gitters, damit die Zellen echte 100-m-Quadrate sind).
Für die ganze Stadt liegen beide Wege dicht beieinander, für einzelne Stadtteile nicht: bei großen um
bis zu drei Prozent, bei kleinen mit wenigen Grenzzellen deutlich mehr; die Seite zeigt die Tabelle. Vorher geprüft: Die amtlichen Stadtteile überlappen sich nicht,
haben keine Lücken und sind gültige Geometrien; jede Zelle wird genau einmal gezählt.

## Quellen, Abrufe und Grenzen

| Daten | Herkunft | Abruf |
|---|---|---|
| Stadtteile | Landeshauptstadt Potsdam, Open-Data-Portal, dl-zero-de/2.0 | von Hand: Die robots.txt des Portals sperrt `/api/` und die Downloads für Programme; eine Anfrage bei der Stadt läuft |
| Zensus 2022, 100-m-Gitter (Bevölkerung, Alter, Durchschnittsalter, Heizungsart, Energieträger, Baujahr der Wohnungen) | © Statistische Ämter des Bundes und der Länder; Destatis: freie Nutzung mit Namensnennung | einmalig, mit 30 s Pause (Crawl-delay der robots.txt) |
| Gebäude, ALKIS vereinfacht | © GeoBasis-DE/LGB, dl-de/by-2-0 | WFS `isk.geobasis-bb.de/ows/alkis_vereinf_wfs`, 1-km-Kacheln, 1 s Pause; der Dienst hat keine robots.txt, Bedingungen in den Capabilities |
| Gegenproben | Regionaldatenbank Deutschland (12411-01-01-5-B); Stadt Potsdam, „Stadtteile im Blick 2022“ | je eine Zahl von Hand übernommen |

- **Zensus-Geheimhaltung:** Fallzahlen sind mit der Cell-Key-Methode leicht verändert; Summen über viele
  Zellen weichen etwas von amtlichen Gebietssummen ab, kleine Einzelwerte sind unscharf.
- **Gebäudehöhen** in der 3D-Ansicht sind seit 06.11.2026 die ALKIS-Objekthöhe aus dem NAS-Auszug der LGB
  (50.356 von 52.309 Gebäuden), sonst Geschosse × 3 m bzw. 3 m; Dächer sind flach dargestellt. Dachformen
  (LoD2) gäbe es als CityGML-Download der LGB, für die ganze Stadt nicht geprüft
  (Beleg: `belege/3D_grundkarte_20261106.md`).
- **Nicht im Repository:** Rohdaten und die Datenbank. Die Seite liest nur die erzeugten Dateien in `daten/`.

## Lizenz

Code: Apache-2.0. Mitgelieferte Bibliotheken und Schriften unter ihren eigenen Lizenzen (`vendor/README.txt`,
`fonts/OFL.txt`). Daten: siehe Tabelle; die Quellenvermerke stehen auf der Seite und in der Kartenattribution.

## Code-Karte

[Code-Karte](docs/codekarte/README.md) (Stand Commit `77bd0d6`, 06.11.2026): der Code als Stadt, Fläche nach
Codezeilen, Höhe und Farbe nach Komplexität, erzeugt mit CodeCharta im Container ohne Netz; fremde Bibliotheken
und erzeugte Daten nicht gezählt.

## Kolophon

Zusammengestellt von André Stiebitz. Code mit KI-Unterstützung (Claude) geschrieben; Zahlen gegen die
amtliche Statistik gegengeprüft, Grenzfälle in der Datenbank nachgerechnet.
