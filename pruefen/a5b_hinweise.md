# A5b: Übergabe an A6, A8 und I1

Stand 05.11.2026. Code fertig und getestet. **Nachlauf N1 (05.11.2026):** auf dem echten Netz (OSM Stand 31.10.2026)
gerechnet, `14b_fussweg.sh pruefen` K1–K4 und E7 erfüllt, Median Fußweg/Luftlinie 1,37; die Dateien `*_odbl.js` sind
erzeugt. Zahlen in `belege/N1_osm_fussweg_20261105.md`. Offen 1 (H5) und 3 sind damit erledigt.

## Ablauf, sobald A3 mit der PBF gelaufen ist

```sh
skripte/12_osm.sh laden --pbf "$KIEZ_DATEN/osm/<stand>/<datei>.osm.pbf"   # A3 füllt netz_knoten, netz_kante, osm_poi
skripte/14b_fussweg.sh test                          # Tests ohne Datenbank
A5B_DB_TEST=1 skripte/14b_fussweg.sh test            # dazu Probelauf mit 50-m-Gitternetz in TEMP-Tabellen (ROLLBACK)
skripte/14b_fussweg.sh rechnen --trockenlauf         # echtes Netz, am Ende ROLLBACK, Bericht berichte/A5b_fussweg.md
skripte/14b_fussweg.sh rechnen                       # schreibt (nur methode = 'fussweg')
skripte/14b_fussweg.sh pruefen                       # vier Abnahmekriterien + E7, Ausgang 0 = alle erfüllt
skripte/14b_fussweg.sh kreuzprobe                    # Güte des Landesfilters E7 (ohne Datenbank)
```

`14b_fussweg.sh` arbeitet wie `12_osm.sh` mit `uv --offline` (numpy, scipy, psycopg, pyyaml aus dem lokalen
Zwischenspeicher) und der Rolle `kiezatlas_rechnen`. Kein Netzabruf, kein pgRouting (E4).

## Was in der Datenbank steht

- `auswertung.zelle_erreichbar`, Zeilen mit `methode = 'fussweg'`: je Potsdamer Zelle (3.443, dieselbe Menge und
  Regel wie `daten/zellen.js` und A5a, darunter 3.411 bewohnte) und je Art `meter` (auf 0,1 m aufgerundet),
  `minuten` (4,8 km/h aus `config/richtwerte.yaml`), `ziel_id` (ID in der Quelltabelle), `quelle_lizenz` mit
  ODbL-Vermerk, Vermerk der Ziel-Quelle und Zensus-Vermerk. `meter` NULL = Zelle oder alle Ziele weiter als 300 m
  vom Netz.
- Arten: alle aus `auswertung.einrichtung` (A2, dieselben Namen wie A5a), `gruen` (A2-Grünflächen `gruenanlage`
  und `park`, wie A5a), alle aus `auswertung.osm_poi` (A3: arzt, apotheke, supermarkt, pflege, spielplatz) und
  `haltestelle` (A4, alle 315 Halte; Zusatz zur Luftlinie nach NVP, nicht deren Ersatz). Berliner Ziele fallen
  heraus (E7, siehe Offen 2).
- `auswertung.zelle_gruen`, `methode = 'fussweg'`, `radius_m = 500`: Fläche der Grünanlagen, deren Rand in 500 m
  Fußweg erreichbar ist. `m2_je_ew` bleibt leer (Berliner Methode teilt je Raumeinheit, das rechnet A6).
- Ein Lauf löscht nur die eigenen Fußweg-Zeilen und schreibt sie neu (eine Transaktion). Die Luftlinie-Zeilen von
  A5a bleiben unberührt (im Probelauf geprüft).
  Umgekehrt löscht A5a (`14_erreichbarkeit.py`, Stand 05.11.) nur `WHERE methode = 'luftlinie'`; die Reihenfolge der
  beiden Läufe ist damit egal (geprüft per grep am 05.11.2026).

## Lizenz (0.5, Korrektur 4)

Jede Fußweg-Zeile ist aus dem OSM-Netz abgeleitet: ODbL 1.0, © OpenStreetMap-Mitwirkende. Sie darf nur in
`daten/erreichbar_fuss_odbl.js`, `daten/planer_fuss_odbl.js` (A6) und `*_odbl.gpkg` (A8) landen, nie in
`erreichbar.js` oder `planer.js`. Die `_odbl`-Dateien gehören auf die Download-Seite (ODbL verlangt das Angebot der
abgeleiteten Datenbank).

## Offen

1. **H5 (Andre):** OSM-PBF unter `$KIEZ_DATEN/osm/<stand>/`, danach A3, danach dieser Ablauf. Erst dann gelten die
   Abnahmekriterien als auf echten Daten erfüllt.
2. **E7 umgesetzt (Brandenburg ja, Berlin nein), für OSM-Ziele als Näherung:** In der Datenbank gibt es keine
   Landesgrenze. Haltestellen fallen nach DHID heraus (`de:11…`; heute keine, A4 liefert nur 12054/12063/12069).
   OSM-Ziele bekommen das Land der nächsten VBB-Haltestelle (`stops.txt` aus `$KIEZ_DATEN/vbb_gtfs/<stand>/`,
   TEMP-Tabelle, KNN). Kreuzprobe (`skripte/14b_fussweg.sh kreuzprobe`, `belege/A5b_landfilter_kreuzprobe.txt`):
   15 von 1.800 Halten um Potsdam falsch, alle höchstens rund 1 km vom nächsten Halt des anderen Landes. Bekannte
   Orte beiderseits der Grenze (auch die Exklave Steinstücken) im DB-Test richtig. Besser wäre eine echte Grenze
   (`boundary=administrative`, `admin_level=4` aus der PBF): Das kann A3 mit H5 liefern, dann `ziele_anlegen`
   darauf umstellen. Fehlt das GTFS, bricht `rechnen` ab, statt Berliner Ziele mitzurechnen.
3. **Median Fußweg/Luftlinie:** Im Gitternetz 1,34 (Manhattan-Gitter, erwartbar um 4/π ≈ 1,27 plus
   Anbindungsstrecken). Auf dem echten Netz soll er zwischen 1,1 und 1,6 liegen; sonst steht die Ursache im Bericht.
4. **Grün-Definition:** `gruen_definition` in `richtwerte.yaml` ist noch `offen` (A6). Bis dahin `gruenanlage` und
   `park`, wie A5a. Liegt ein Zellmittelpunkt in einer Grünanlage, zählt der Weg bis zu ihrem Rand.
5. **Tabelle 0.4:** `skripte/14b_fussweg.py`, `skripte/14b_fussweg.sh`, `pruefen/a5b_*` sind neue Dateien von A5b
   (nicht `14_erreichbarkeit.py`, das gehört A5a). In I1 eintragen.
