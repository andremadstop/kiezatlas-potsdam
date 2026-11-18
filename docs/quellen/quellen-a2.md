# Quellen Paket A2 (Zulieferung für QUELLEN.md, Zusammenführung in I1)

Keine neue Quelle und kein neuer Abruf. A2 rechnet nur aus Daten, die P0 geladen hat (QUELLEN.md Nr. 5 bis 8):

| Ergebnis | Quelle | Vermerk |
|---|---|---|
| `auswertung.einrichtung`, Kitas, Horte, Schulen | MBJS-WFS `ms:KITA_Standorte`, `ms:Schul_Standorte` (Nr. 7, 8); weitere Häuser aus `$KIEZ_DATEN/mbjs/2026-11-05/kitas_standorte.geojson` | © Ministerium für Bildung, Jugend und Sport, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) |
| `auswertung.einrichtung`, Gemeinbedarf ohne Kapazität (`id` beginnt mit `alkis:`) | ALKIS-Gebäude, Snapshot `auswertung.gebaeude_stand_20261105` (Nr. 5); ALKIS-Nutzung `Sportanlage`, `Schwimmen` (Nr. 6) | © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) |
| `auswertung.gruenflaeche` | ALKIS-Nutzung (Nr. 6), Zuordnung `config/richtwerte.yaml` → `gruen_definition.arten` | wie Gemeinbedarf |

Der Vermerk steht je Zeile in der Spalte `lizenz`. Kein OSM-Anteil, keine Adresse, kein Kontakt.
