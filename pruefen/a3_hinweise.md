# A3: Übergabe an A5b, A6, A8

Stand 05.11.2026. Code fertig und getestet. **Nachlauf N1 (05.11.2026):** mit dem BBBike-Auszug Potsdam (Stand
31.10.2026) geladen, `12_osm.sh pruefen` 5 von 5 erfüllt; Zahlen in `belege/N1_osm_fussweg_20261105.md`.

## Ablauf, sobald die PBF da ist

```sh
skripte/12_osm.sh test                                  # Mini-PBF, ohne Datenbank
A3_DB_TEST=1 skripte/12_osm.sh test                     # dazu Trockenlauf gegen die DB (ROLLBACK)
# PBF liegt unter $KIEZ_DATEN/osm/<stand>/ (aus eingang/ lädt das Skript nicht)
skripte/12_osm.sh laden --pbf "$KIEZ_DATEN/osm/<stand>/<datei>.osm.pbf" --trockenlauf
skripte/12_osm.sh laden --pbf "$KIEZ_DATEN/osm/<stand>/<datei>.osm.pbf"
skripte/12_osm.sh pruefen                               # fünf Abnahmekriterien, Ausgang 0 = alle erfüllt
```

`12_osm.sh` arbeitet mit `uv --offline` (numpy, scipy, psycopg aus dem lokalen Zwischenspeicher) und der Rolle
`kiezatlas_rechnen`. Ein Lauf ersetzt den Inhalt von `osm_poi`, `netz_knoten`, `netz_kante` vollständig (TRUNCATE
und INSERT in einer Transaktion).

## Was die Tabellen bedeuten

- `netz_knoten.id` ist die OSM-Knoten-ID. Jeder Knoten eines begehbaren Wegs ist Netzknoten (keine Vereinfachung
  auf Kreuzungen), damit Zellmittelpunkte nah an einem Knoten liegen.
- `netz_kante` ist ungerichtet, eine Zeile je Knotenpaar (`von < nach`), `laenge_m` in EPSG:25833 (Fehler
  gegenüber der wahren Länge unter 0,05 %). Gehrichtung spielt keine Rolle (Einbahnstraßen gelten für Fußgänger
  nicht).
- Ausschnitt: Kanten, die den Puffer „Stadtgebiet + 2 km“ berühren. Berlin liegt teilweise im Puffer.
  `osm_poi` enthält auch Einrichtungen im Berliner Teil des Puffers; es gibt keine Spalte dafür und keine
  Berliner Grenze in der Datenbank. Offen für Andre: Gilt E7 („Berlin vorerst nicht“, entschieden für MBJS)
  auch für OSM-Einrichtungen? Dann braucht es eine Grenze (z. B. aus der PBF, `boundary=administrative`).
- Abdeckung: Der Bericht prüft das Rechteck der Datei und zählt 1-km-Kacheln im Puffer ohne einen OSM-Knoten.
  Empfohlen ist der BBBike-Auszug Potsdam; Geofabrik Brandenburg endet an der Berliner Grenze.
- Dubletten: dieselbe Einrichtung als Punkt und Fläche (Abstand ≤ 25 m, gleiche Art): nur der Punkt bleibt.

## Für P0 (DDL)

`auswertung.netz_knoten` und `auswertung.osm_poi` haben keinen GiST-Index auf `geom`, `kiezatlas_rechnen` darf
keinen anlegen. A5 kann eine TEMP-Kopie mit Index nutzen oder in Python rechnen (cKDTree); ein Index in
`sql/002_ausbau.sql` wäre einfacher.
