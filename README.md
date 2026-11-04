# Kiezatlas Potsdam

Alle 32 Stadtteile der Landeshauptstadt Potsdam in Zahlen und Karte, nur aus offenen amtlichen Daten:
Zensus 2022 im 100-Meter-Gitter, die amtlichen Stadtteile und die Gebäudeumrisse der Landesvermessung.
Wer wo wohnt, wie alt die Häuser sind, womit geheizt wird, für die ganze Stadt und jeden Stadtteil, und
bei jeder Zahl, woher sie kommt.

Prototyp der Stiebitz Souverain Systems UG (haftungsbeschränkt), Potsdam, Stand November 2026.

## Wie es gebaut ist

```
rohdaten/ (lokal)          Geodaten-Import-Pipeline            PostGIS                    Seite
Stadtteile (Handdownload) ─┐                                 ┌ stadtteil          ┐
Zensus-Gitter (Destatis) ──┼─ 01_vorbereiten.py ─ CSV ─┐     │ zensus_zelle       ├─ 02_auswerten.py ─ daten/*.js ─ index.html
ALKIS-Gebäude ─────────────┴──────── WFS der LGB ──────┴─────┤ gebaeude           ┘   (Zuordnung, Summen,
                                                             └ pipeline_meta (Läufe, Protokoll)   Grenzfall in SQL)
```

1. `skripte/01_vorbereiten.py` macht aus den lokal liegenden Rohdaten zwei CSV-Dateien. Kein Netzabruf.
2. Die [Geodaten-Import-Pipeline](https://github.com/andremadstop/geodaten-import-pipeline) lädt Stadtteile,
   Zensus-Gitter und, direkt aus dem WFS der Landesvermessung, die Gebäude in PostGIS
   (`config/potsdam.yaml`): Abgleich je Quelle, Bericht je Lauf, Rhythmus, Rollen nach geringsten Rechten.
   Die Pipeline ist ein eigenes Projekt der UG für den automatischen Import amtlicher Geodaten; hier läuft sie
   nur mit einer anderen Konfiguration und eigenen Zieltabellen (`sql/001_kiezatlas.sql`).
3. `skripte/02_auswerten.py` rechnet in PostGIS mit der Leserolle: Zelle und Gebäude je Stadtteil,
   Kennzahlen, Verteilungen, den Grenzfall-Vergleich, und schreibt `daten/` für die Seite.
4. `index.html` zeigt das Ergebnis; Gebäude eines Stadtteils werden erst bei seiner Auswahl geladen.

Alles auf einmal: `skripte/lauf.sh` (braucht Docker, uv, `.env` mit drei Passwörtern, daneben das
Repository der Pipeline).

## Die Seite

https://souverain-systems.de/kiezatlas/ (oder `index.html` per Doppelklick, ohne Server)

- **Sieben Fragen** führen durch die Karte, von „Wie viele Menschen wohnen in meiner Nachbarschaft?“ bis
  „Wie kommt das ins Heft?“; jede stellt Stadtteil, Thema und Kamera ein und erklärt nebenbei eine Funktion.
  Alle Antworten rechnet der Browser aus den Daten in `daten/`, im Text steht keine Zahl von Hand.
- **3D-Gitter:** Jede Zensus-Zelle ist eine Säule, Höhe und Farbe zeigen denselben Wert. Gebäude in 3D und
  das Luftbild der Landesvermessung lassen sich zuschalten.
- **Register und Steckbrief** für alle 32 Stadtteile, sortierbar, mit Quelle je Zahl.
- **Schaugrafik:** ein bis vier Gebiete, Rubriken und Format wählen (A4 hoch und quer, halbe Seite, Spalte,
  Quadrat), dann als SVG, PNG mit 300 dpi oder über die Druckansicht als PDF herunterladen. Quellen und Lizenzen
  stehen in jeder Grafik; die Karte darin ist aus den eigenen Daten gezeichnet, ohne fremde Kartenkacheln.
- Bibliotheken (MapLibre GL JS, GSAP) und Schrift (Barlow, SIL Open Font License) liegen in `vendor/` und
  `fonts/`; von fremden Servern kommen nur die Hintergrundkarte (basemap.de) und das Luftbild (LGB).

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
- **Gebäudehöhen** in der 3D-Ansicht sind genähert (Geschosse × 3 m). Gemessene Höhen (LoD2) gibt es in der
  Einzelfassung für Potsdam-West; für die ganze Stadt wäre der CityGML-Download der LGB der richtige Weg,
  nicht tausende WFS-Abfragen.
- **Nicht im Repository:** Rohdaten und die Datenbank. Die Seite liest nur die erzeugten Dateien in `daten/`.

## Lizenz

Code: Apache-2.0. Mitgelieferte Bibliotheken und Schriften unter ihren eigenen Lizenzen (`vendor/README.txt`,
`fonts/OFL.txt`). Daten: siehe Tabelle; die Quellenvermerke stehen auf der Seite und in der Kartenattribution.

## Kolophon

Zusammengestellt von André Stiebitz. Code mit KI-Unterstützung (Claude) geschrieben; Zahlen gegen die
amtliche Statistik gegengeprüft, Grenzfälle in der Datenbank nachgerechnet.
