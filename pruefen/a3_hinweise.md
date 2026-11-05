# A3: Übergabe an A5b, A6, A8

Stand 05.11.2026. Code fertig und getestet, **echte Daten fehlen** (H5: OSM-PBF von Andre).

## Ablauf, sobald die PBF da ist

```sh
skripte/12_osm.sh test                                  # Mini-PBF, ohne Datenbank
A3_DB_TEST=1 skripte/12_osm.sh test                     # dazu Trockenlauf gegen die DB (ROLLBACK)
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
- Ausschnitt: Kanten, die den Puffer „Stadtgebiet + 2 km“ berühren. Berlin liegt teilweise im Puffer; E7 (Berlin
  vorerst nicht) betrifft die Ziele, nicht das Netz. `osm_poi` enthält auch Einrichtungen im Berliner Teil des
  Puffers: A5 filtert sie bei Bedarf.
- Dubletten: dieselbe Einrichtung als Punkt und Fläche (Abstand ≤ 25 m, gleiche Art): nur der Punkt bleibt.

## Für P0 (DDL)

`auswertung.netz_knoten` und `auswertung.osm_poi` haben keinen GiST-Index auf `geom`, `kiezatlas_rechnen` darf
keinen anlegen. A5 kann eine TEMP-Kopie mit Index nutzen oder in Python rechnen (cKDTree); ein Index in
`sql/002_ausbau.sql` wäre einfacher.
