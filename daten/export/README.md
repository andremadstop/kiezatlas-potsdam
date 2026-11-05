# Kiezatlas Potsdam: Daten zum Weiterverwenden

Stand der Auswertung 2026-11-05. Erzeugt mit `skripte/16_export.py` aus denselben Datendateien wie die
Seite (`daten/planer.js`, `daten/einrichtungen.js`, `daten/erreichbar.js`, `daten/zellen.js`) und der Geometrie aus
der Projektdatenbank. Raumebene: **Planungsraum (die 19 Planungsräume der Landeshauptstadt, Ebene der Kita- und Schulentwicklungsplanung); die 32 Stadtteile liegen zur Orientierung als eigene Ebene bei**.

## Dateien

| Datei | Inhalt | Lizenz |
|---|---|---|
| `kiezatlas_potsdam.gpkg` | GeoPackage, EPSG:25833 (ETRS89 / UTM 33N), ohne Anteil aus OpenStreetMap | je Ebene, siehe unten und Tabelle `lizenz` |
| `kiezatlas_potsdam_odbl.gpkg` | Ebenen aus OpenStreetMap (Fußweg, weitere Einrichtungen) | Open Database License 1.0 |
| `csv/*.csv` | dieselben Ebenen als CSV | wie die GeoPackage-Ebene |
| `csv_odbl/*.csv` | die ODbL-Ebenen als CSV | Open Database License 1.0 |
| `kiezatlas_potsdam.qgz` | QGIS-Projekt (relative Pfade, liegt neben der GPKG) | Apache-2.0 (Projektdatei) |
| `stile/*.qml` | QGIS-Stile; dieselben Stile stehen als Standardstil in der GPKG (`layer_styles`) | Apache-2.0 |
| `steckbriefe/<nr>.html` | druckbarer Steckbrief je Raumeinheit (A4) | wie die Werte |

Jede Zeile trägt in `lizenz` das Kürzel ihrer Lizenz; der vollständige Vermerk steht in der Tabelle `lizenz`
(GPKG und `csv/lizenz.csv`) und unten.

CSV: Trennzeichen Semikolon, UTF-8 mit BOM, Dezimalpunkt. Punkte mit Spalten `x`, `y`, Flächen mit `wkt`, beides
in EPSG:25833 auf 1 cm. Wahrheitswerte als 1 und 0.

## Ebenen ohne OpenStreetMap (`kiezatlas_potsdam.gpkg`, `csv/`)

| Ebene | Geometrie | Zeilen | Felder |
|---|---|---|---|
| `raumeinheit` | MULTIPOLYGON | 19 | `nr`, `name`, `raumebene`, `ew`, `flaeche_km2`, `zellen`, `anteil_kita_500m`, `anteil_grundschule_1000m`, `anteil_grundschule_2000m`, `anteil_gruen_500m`, `plaetze_je_kind_kita`, `plaetze_je_kind_hort`, `plaetze_je_bedarf_kita`, `schueler_je_kind_grundschule`, `ew_je_kita`, `ew_je_grundschule`, `ew_je_bibliothek`, `ew_je_sport`, `ew_je_feuerwehr`, `ew_je_sonstiger_gemeinbedarf`, `oepnv_erschliessung`, `oepnv_takt`, `gruen_m2_je_ew`, `stand`, `vermerk_grenze` |
| `versorgung` | Tabelle | 323 | `raum_nr`, `raum_name`, `raumebene`, `spalte`, `kennzahl`, `art`, `titel`, `zielgruppe`, `wert`, `einheit`, `methode`, `status`, `vorlaeufig`, `richtwert`, `richtwert_einheit`, `richtwert_quelle`, `richtwert_fundstelle`, `unsicherheit`, `quelle`, `stand`, `vermerk`, `prognose` |
| `einrichtung` | POINT | 679 | `id`, `art`, `art_text`, `unterart`, `name`, `plaetze`, `schueler`, `schueler_stand`, `status`, `in_potsdam`, `raum_nr`, `hinweis`, `quelle`, `stand`, `lizenz` |
| `zelle` | POLYGON | 3443 | `gitter_id`, `stadtteil`, `raum_nr`, `ew`, `m_bibliothek`, `m_feuerwehr`, `m_foerderschule`, `m_gruen`, `m_grundschule`, `m_gymnasium`, `m_hort`, `m_kita`, `m_osz`, `m_sek1`, `m_sonstige_schule`, `m_sonstiger_gemeinbedarf`, `m_sport`, `stand`, `lizenz` |
| `gruenflaeche` | MULTIPOLYGON | 4892 | `id`, `art`, `bez`, `flaeche_m2`, `zaehlt_gruenversorgung`, `quelle`, `stand`, `lizenz` |
| `haltestelle` | POINT | 315 | `stop_id`, `name`, `verkehrsmittel`, `fahrten_hvz_je_richtung`, `klasse`, `in_potsdam`, `raum_nr`, `stand`, `lizenz` |
| `stadtteil` | MULTIPOLYGON | 32 | `nr`, `name`, `flaeche_km2`, `vermerk_grenze` |
| `lizenz` | Tabelle | 7 | `ebene`, `lizenz`, `vermerk`, `lizenztext` |

- `raumeinheit`: Grenzen mit Einwohnern und je Kennzahl einer Spalte (Kurzname wie in `versorgung.spalte`).
- `versorgung`: jede Kennzahl als eigene Zeile mit `status`, `vorlaeufig`, Maßstab (`richtwert`, Quelle,
  Fundstelle), `unsicherheit`, Quelle und Stand. Die Breitform in `raumeinheit` enthält nur die Zahl; lesen Sie
  die Zahl immer mit dieser Zeile.
- `einrichtung`: Kitas, Horte und Schulen (MBJS) mit Plätzen bzw. Schülern, Gemeinbedarf aus ALKIS nur als Lage.
  `raum_nr` ist leer bei Standorten außerhalb Potsdams (sie zählen bei den Entfernungen mit).
- `zelle`: bewohnte 100-m-Zellen des Zensus 2022 mit Einwohnern und der Luftlinie in Metern zum nächsten
  Standort je Art (`m_<art>`, auf 10 m gerundet; leer = Zelle ohne Einwohner). Keine Altersklassen je Zelle.
- `gruenflaeche`: ALKIS-Nutzung; `zaehlt_gruenversorgung` = gruenanlage, park.
- `haltestelle`: Haltestellen mit Fahrten in der Hauptverkehrszeit und Taktklasse nach NVP 2019.
- `stadtteil`: die 32 Stadtteile mit Nummer, Name und Fläche, ohne Werte. In `zelle` steht der Stadtteil jeder
  Zelle in `stadtteil`, die Raumeinheit in `raum_nr`.
- `einrichtung.hinweis`: nur bei Standorten mit strittiger Lage (Ortsangabe widerspricht den Koordinaten). Ein
  solcher Standort zählt für keine Entfernung (`zelle`, `zelle_fuss_odbl`) und keine Kennzahl; die betroffenen
  Grundschulwerte je Raumeinheit stehen leer mit Grund in `unsicherheit`. Die Zellwerte (`zelle.m_grundschule`, `zelle_fuss_odbl.fuss_grundschule_m`) sind ohne diesen Standort gerechnet und tragen kein eigenes Kennzeichen. In den Raumeinheiten 101, 103 sind sie deshalb nicht belastbar: Je nachdem, wo die Schule tatsächlich unterrichtet, sind sie in einer der Raumeinheiten zu groß, am Stadtrand um Kilometer.

## Ebenen aus OpenStreetMap (`kiezatlas_potsdam_odbl.gpkg`, `csv_odbl/`)

| Ebene | Geometrie | Zeilen | Felder |
|---|---|---|---|
| `einrichtung_odbl` | POINT | 941 | `id`, `art`, `unterart`, `raum_nr`, `stand`, `lizenz` |
| `zelle_fuss_odbl` | POLYGON | 3443 | `gitter_id`, `raum_nr`, `ew`, `fuss_apotheke_m`, `fuss_arzt_m`, `fuss_bibliothek_m`, `fuss_feuerwehr_m`, `fuss_foerderschule_m`, `fuss_gruen_m`, `fuss_grundschule_m`, `fuss_gymnasium_m`, `fuss_haltestelle_m`, `fuss_hort_m`, `fuss_kita_m`, `fuss_osz_m`, `fuss_pflege_m`, `fuss_sek1_m`, `fuss_sonstige_schule_m`, `fuss_sonstiger_gemeinbedarf_m`, `fuss_spielplatz_m`, `fuss_sport_m`, `fuss_supermarkt_m`, `stand`, `lizenz` |
| `versorgung_fuss_odbl` | Tabelle | 190 | `raum_nr`, `raum_name`, `raumebene`, `spalte`, `kennzahl`, `art`, `titel`, `zielgruppe`, `wert`, `einheit`, `methode`, `status`, `vorlaeufig`, `richtwert`, `richtwert_einheit`, `richtwert_quelle`, `richtwert_fundstelle`, `unsicherheit`, `quelle`, `stand`, `vermerk`, `prognose` |

Diese Ebenen sind aus OpenStreetMap abgeleitet und stehen unter der Open Database License 1.0
(https://opendatacommons.org/licenses/odbl/1-0/), © OpenStreetMap-Mitwirkende. Wer sie verändert und weitergibt, gibt die veränderte Datenbank
unter derselben Lizenz weiter. Sie liegen absichtlich in einer eigenen Datei, damit die übrigen Daten frei von
dieser Bedingung bleiben.

## Lizenzen und Vermerke

Bei Weitergabe oder Veröffentlichung den Vermerk der genutzten Ebenen übernehmen:

- **Grenzen der Raumeinheiten:** © Landeshauptstadt Potsdam, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)
- **Grenzen der Stadtteile:** © Landeshauptstadt Potsdam, dl-zero-de/2.0 (https://www.govdata.de/dl-de/zero-2-0)
- **Einwohner, Zellen:** © Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)
- **Kitas, Horte, Schulen:** © Ministerium für Bildung, Jugend und Sport, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)
- **Gemeinbedarf, Grünflächen:** © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)
- **Haltestellen, ÖPNV-Werte:** VBB Verkehrsverbund Berlin-Brandenburg GmbH, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), Daten verändert (eigene Berechnung)
- **Ebenen mit _odbl:** © OpenStreetMap-Mitwirkende, Open Database License 1.0 (https://opendatacommons.org/licenses/odbl/1-0/), Daten verändert (eigene Berechnung); dazu die amtlichen Vermerke oben und, für die Spalte
  `fuss_haltestelle_m`, der VBB-Vermerk (Tabelle `lizenz` in der `_odbl.gpkg`, als CSV `csv_odbl/lizenz.csv`)
- **ÖPNV-Gebietsklasse, soweit über die statistischen Bezirke bestimmt (steht in `unsicherheit`):**
  © Landeshauptstadt Potsdam, Statistische Bezirke, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)

Die Maßstäbe (Nahverkehrsplan 2019, Baulandmodell 2019, Schülerfahrtkostensatzung, Umweltatlas Berlin) sind als
Zahl mit Fundstelle übernommen, nicht als Text. Der Code des Kiezatlas steht unter Apache-2.0, die Daten nicht.

## Methode in Kürze

- **Einwohner und Kinder:** Zensus 2022, 100-m-Gitter, Stichtag 15.05.2022. Das Cell-Key-Verfahren verändert
  kleine Werte; Summen vieler Zellen weichen deshalb ab. Einwohner je Raumeinheit auf 10 gerundet. Werte aus
  feinen Altersklassen nur für Raumeinheiten ab 100 Einwohnern, unter 20 Personen der Zielgruppe kein Wert.
  Neubau nach dem Stichtag (u. a. Krampnitz, Bornstedter Feld, Golm) fehlt.
- **Entfernung:** Luftlinie vom Zellmittelpunkt (bis 71 m vom Wohnort) zum nächsten Standort, aussagekräftig auf
  rund 50 m. Standorte in Brandenburg außerhalb der Stadt zählen mit, Berlin nicht; am Stadtrand ist der Wert
  deshalb teils nur eine Obergrenze.
- **Zuordnung zur Raumeinheit:** über den Zellmittelpunkt bzw. den Standort.
- **ÖPNV:** Die Gebietsklasse des Nahverkehrsplans gilt für Ortsteile; jede Zelle bekommt die Klasse ihres
  Stadtteils. Zellen mit gemischter oder offener Klasse zählen nicht mit; wohnt dort mehr als die Hälfte der
  Einwohner einer Raumeinheit, steht statt eines Werts ein Hinweis in `unsicherheit`.
- **Status:** `amtlich` mit `richtwert` = amtlicher Maßstab aus einem geltenden Potsdamer Dokument mit gelesener
  Fundstelle; `amtlich` ohne `richtwert` = amtliche Daten, kein Maßstab. `orientierung` = Maßstab ohne
  Primärbeleg, Fundstelle nicht gelesen, abgelaufene Geltung (Nahverkehrsplan 2019, Geltung bis 2023) oder
  Berliner Methode; kein Richtwert. `vorlaeufig` = Grundschulwert ohne Schulbezirk.
- **Methode:** `luftlinie` = Entfernung bzw. Radius in Luftlinie; `raumeinheit` = Quote je Raumeinheit ohne
  Entfernungsbezug (Plätze je Kind, Plätze je Bedarfsplatz, Schüler je Kind, Einwohner je Standort).
- **Vermerk:** `vermerk` nennt die Quelle der Einrichtungen bzw. Daten und immer den Zensus, weil jede Kennzahl
  gegen Zensus-Einwohner oder -Zielgruppen gerechnet ist.
- **Kita:** Kapazität laut Betriebserlaubnis, nicht Belegung; Kinder 2022, Plätze 2026. Tagespflege fehlt.
- **Grün:** vereinfachte Berliner Methode (Grünanlagen und Parks aus ALKIS im 500-m-Kreis je Einwohner), ohne
  Mindestgröße; SPSG-Parks lassen sich nicht abgrenzen und zählen mit.

Ausführlich: `config/richtwerte.yaml`, `QUELLEN.md` und die Methodenseite des Kiezatlas.

## Datenschutz

Keine Adressen, keine Kontaktdaten, keine Personendaten. Je Zelle nur Einwohnerzahl und Entfernungen, keine
Alters-, Haushalts- oder Staatsangehörigkeitsklassen. Einrichtungen aus OpenStreetMap ohne Namen.

## In QGIS öffnen

`kiezatlas_potsdam.qgz` neben `kiezatlas_potsdam.gpkg` liegen lassen und öffnen. Alternativ die GPKG per
Ziehen und Ablegen laden; QGIS übernimmt die hinterlegten Stile. Schriften der Beschriftung: Barlow Semi
Condensed (fehlt sie, nimmt QGIS eine Ersatzschrift).

## Steckbriefe drucken

Die Steckbriefe sind HTML für den Druck (A4) und laufen mit WeasyPrint (Python, mit installiertem `weasyprint`):

```
python -c "from weasyprint import HTML; \
  from weasyprint.text.fonts import FontConfiguration as F; f=F(); \
  HTML('daten/export/steckbriefe/101.html').write_pdf('101.pdf', font_config=f)"
```

Die Schriften kommen aus `fonts/` des Repositorys (relativer Pfad); im Browser über „Drucken“ geht es ebenso.
