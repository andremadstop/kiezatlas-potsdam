# Quellen Paket A5a (Zulieferung für QUELLEN.md, Zusammenführung in I1)

Keine neue Quelle und kein Netzabruf. A5a rechnet nur aus Tabellen, die P0, A2 und der Bestand geladen haben:

| Ergebnis | Quelle | Vermerk |
|---|---|---|
| `auswertung.zelle_erreichbar`, Arten aus MBJS (Kita, Hort, Schulformen) | A2 `auswertung.einrichtung` aus MBJS-WFS (QUELLEN.md Nr. 7, 8); Zellmittelpunkte Zensus 2022 (Nr. 2) | © Ministerium für Bildung, Jugend und Sport, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung); Zellmittelpunkt und Einwohner: © Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) |
| `auswertung.zelle_erreichbar`, Gemeinbedarf aus ALKIS (Bibliothek, Feuerwehr, Sport, sonstiger Gemeinbedarf) | A2 aus ALKIS-Gebäuden (Snapshot, Nr. 5) und ALKIS-Nutzung (Nr. 6); Zensus wie oben | © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung); Zensus wie oben |
| `auswertung.zelle_erreichbar` Art `gruen`, `auswertung.zelle_gruen` | A2 `auswertung.gruenflaeche` (ALKIS-Nutzung, Nr. 6), Arten mit `zaehlt_vorschlag: true` in `config/richtwerte.yaml`; Einwohner im Kreis aus dem Zensus (Nr. 2) | © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0) (ALKIS-Nutzung: gruenanlage, park), Daten verändert (eigene Berechnung); Zensus wie oben |

Der Vermerk steht je Zeile in der Spalte `quelle_lizenz`. Kein OSM-Anteil, keine Adresse, kein Kontakt.
Alle Zeilen haben `methode = 'luftlinie'`; Fußweg-Zeilen (ODbL) kommen aus A5b.

Für die Methodenseite (A6/A7), sinngemäß:
- Entfernung in Luftlinie vom Mittelpunkt der 100-m-Zensuszelle zum nächsten Standort, gerechnet in ETRS89/UTM 33N.
  Genauigkeit rund 50 m (der Mittelpunkt kann bis zu 71 m vom Wohnort abweichen).
- Standorte außerhalb Potsdams zählen mit, soweit sie in Brandenburg liegen und abgerufen wurden (MBJS rund 3 km um
  die Stadt, ALKIS nur das Rechteck um die Stadt). Berlin fehlt. Werte am Rand, die deshalb nur Obergrenzen sind,
  stehen in `belege/A5a_rand_unsicher_<datum>.csv`.
- Grün im Umkreis: Fläche der Grünanlagen und Parks (ALKIS) im 500-m-Kreis und je Einwohner im selben Kreis.
  Vereinfachte Annäherung an die Methode des Umweltatlas Berlin, nicht deren Nachbildung.
