# A5b: Übergabe an A6, A8 und I1

Stand 05.11.2026. Code fertig und getestet, **echte Werte fehlen**: Das OSM-Wegenetz (`auswertung.netz_*`) ist leer,
weil die OSM-PBF (H5) noch nicht von Hand geladen ist. Ohne Netz bricht `rechnen` mit einer klaren Meldung ab und
schreibt nichts.

## Ablauf, sobald A3 mit der PBF gelaufen ist

```sh
skripte/12_osm.sh laden --pbf "$KIEZ_DATEN/osm/<stand>/<datei>.osm.pbf"   # A3 füllt netz_knoten, netz_kante, osm_poi
skripte/14b_fussweg.sh test                          # Tests ohne Datenbank
A5B_DB_TEST=1 skripte/14b_fussweg.sh test            # dazu Probelauf mit 50-m-Gitternetz in TEMP-Tabellen (ROLLBACK)
skripte/14b_fussweg.sh rechnen --trockenlauf         # echtes Netz, am Ende ROLLBACK, Bericht berichte/A5b_fussweg.md
skripte/14b_fussweg.sh rechnen                       # schreibt (nur methode = 'fussweg')
skripte/14b_fussweg.sh pruefen                       # vier Abnahmekriterien, Ausgang 0 = alle erfüllt
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
  `haltestelle` (A4, alle 315 Halte; Zusatz zur Luftlinie nach NVP, nicht deren Ersatz).
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
2. **E7 für OSM-Ziele und Halte (Andre):** `osm_poi` enthält auch den Berliner Teil des Puffers (A3), `haltestelle`
   hat 32 Halte außerhalb Potsdams. A5b rechnet sie mit, weil es in der Datenbank keine Berliner Grenze gibt.
   Gilt „Berlin vorerst nicht“ auch hier, braucht es eine Grenze (z. B. `boundary=administrative` aus der PBF).
3. **Median Fußweg/Luftlinie:** Im Gitternetz 1,34 (Manhattan-Gitter, erwartbar um 4/π ≈ 1,27 plus
   Anbindungsstrecken). Auf dem echten Netz soll er zwischen 1,1 und 1,6 liegen; sonst steht die Ursache im Bericht.
4. **Grün-Definition:** `gruen_definition` in `richtwerte.yaml` ist noch `offen` (A6). Bis dahin `gruenanlage` und
   `park`, wie A5a. Liegt ein Zellmittelpunkt in einer Grünanlage, zählt der Weg bis zu ihrem Rand.
5. **Tabelle 0.4:** `skripte/14b_fussweg.py`, `skripte/14b_fussweg.sh`, `pruefen/a5b_*` sind neue Dateien von A5b
   (nicht `14_erreichbarkeit.py`, das gehört A5a). In I1 eintragen.
