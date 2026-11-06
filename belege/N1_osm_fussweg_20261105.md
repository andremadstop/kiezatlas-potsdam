# N1: OSM-Netz und Fußweg (Nachlauf A3 + A5b), Lauf 05.11.2026

Kein Netzabruf. Alle Läufe offline (`uv --offline`), Rolle `kiezatlas_rechnen` für A3/A5b, `mosidi_lesen` für A6.
Die ausführlichen Berichte liegen in `berichte/` (nicht versioniert); hier die Zahlen, die die Abnahme tragen.

## Eingang

- `$KIEZ_DATEN/osm/2026-11-05/potsdam.osm.pbf`, BBBike-Auszug Potsdam, Stand 31.10.2026, 118.777.183 Bytes,
  SHA256 `218d68b472b010cbdaadda8fa42e040efaf26aa516b5ff20d0db83bc9c6f3ded` (Herkunft dort in `HERKUNFT.md`).
- ODbL 1.0, © OpenStreetMap-Mitwirkende. Ableitungen nur in `*_odbl`-Dateien.

## A3: `skripte/12_osm.sh`

| Schritt | Ergebnis |
|---|---|
| `test` / `A3_DB_TEST=1 test` | 21 passed, 1 skipped / 22 passed |
| `laden --trockenlauf`, dann `laden` | PBF 8.203.982 Knoten, 1.413.638 Wege; im Leserechteck 1.230.202 Knoten; 60 s |
| `osm_poi` | 941: arzt 207, apotheke 42, supermarkt 111, pflege 42, spielplatz 539 (ohne Namen) |
| Netz | 128.921 Knoten, 144.709 Kanten, rund 3.724 km; 1-km-Kacheln im Puffer ohne Knoten: 0 von 419 |
| Vollständigkeit gegen MBJS | Kita 78,1 %, Schule 92,3 % |
| `pruefen` (a3_pruefen) | 5 von 5 ✓: keine Spalte `name`; Bericht mit Trefferquoten; größte Komponente 98,32 % der Knoten im Stadtgebiet; 3.410 von 3.411 bewohnten Zellen ≤ 150 m vom Netz (Median 20,2 m, größter 167,1 m); ODbL-Kommentar an allen drei Tabellen |

## A5b: `skripte/14b_fussweg.sh`

| Schritt | Ergebnis |
|---|---|
| `test` / `A5B_DB_TEST=1 test` | 14 passed, 3 skipped / 17 passed |
| `kreuzprobe` (Landesfilter E7) | 1.800 Halte im Rechteck, 15 falsch zugeordnet (0,8 %), Fehltreffer 200 bis 988 m vom nächsten Halt des anderen Landes |
| `rechnen --trockenlauf`, dann `rechnen` | 19 Arten × 3.443 Zellen; 2 Zellen über 300 m vom Netz ohne Wert; 13,6 s |
| Als Berlin ausgelassen (E7) | apotheke 1, arzt 3, pflege 5, spielplatz 29, supermarkt 3 |
| `pruefen` (a5b_pruefen) | K1, K2, K3, K4, E7 ok: K2 65.379 Zellwerte, Fußweg < Luftlinie 0; K3 Median Fußweg/Luftlinie 1,367 (je Art 1,24 bis 1,60); gegen A5a 44.733 Paare, Fußweg < Luftlinie 0 |

E7 (Brandenburg ja, Berlin nein) bleibt die Näherung aus A5b über die nächste VBB-Haltestelle. Eine echte
Landesgrenze aus der PBF (`boundary=administrative`, `admin_level=4`) ist nicht eingebaut.

## A6-Dateien (`skripte/15_planer.py`, unverändert)

- Neu: `daten/planer_fuss_odbl.js` (19 Planungsräume, 190 Werte, 0 wegen Geheimhaltung null),
  `daten/erreichbar_fuss_odbl.js` (19 Arten × 3.443 Zellen, auf 10 m gerundet), `daten/einrichtungen_odbl.js`
  (941 Punkte, Felder nur `id`, `art`, `unterart`, `q`). Jede mit ODbL-Kopfkommentar, ohne Feld `fixture`.
- `planer.js`, `erreichbar.js`, `einrichtungen.js` byte-gleich zum Integrationsstand (keine Fußweg-Werte darin).
- Kreuzprobe auf den veröffentlichten Dateien: `erreichbar_fuss_odbl.js` gegen `erreichbar.js`, 44.317 Paare,
  Fußweg < Luftlinie 0, Median 1,35.
- `pruefen/A6_planer.py`: 0 Befunde. `pruefen/daten.py`: 0 Abweichungen.

## ODbL-Grenze

`grep -i -e openstreetmap -e osm_id -e odbl -e fussweg -e '"osm"'` über `daten/` ohne `*_odbl.js`, `schema/`,
`fixtures/` und `LIZENZ.md`: einziger Treffer `daten/export/README.md` (Beschreibung der `_odbl`-Exportdateien,
keine Werte).

## Seiten

- `planer.html`, `planer-methode.html`: `data-odbl` nennt die drei Dateien; Schalter „Fußweg“ und OSM-Arten frei.
- `pruefen/A7_planer.mjs` grün (echte Daten: Fußweg und OSM-Arten nicht gesperrt, wie erwartet; Startgewicht 299 KB
  gz JS bei Grenze 300). Eigener Rauchtest `planer.html#…&weg=fuss&r=403` mit echten Daten: Tabelle „Werte als
  Fußweg“, ODbL-Vermerk sichtbar, 0 Konsolenfehler.
- `pruefen/seiten.mjs` grün, `pruefen/p1_themen.mjs` grün, `pruefen/p1_gleich.mjs` grün.
- `pruefen/A8_export.py`: 0 Befunde (ODbL-Grenze der Exportdateien; `*_odbl.gpkg` noch nicht erzeugt).
- `planer-methode.html` nennt beim Landesfilter E7 jetzt den VBB-Fahrplan (CC BY 4.0, Daten verändert) als
  Auswahlkriterium, wie in `quellen-a5b.md` für die Veröffentlichung verlangt.

## Offen

- `erreichbar_fuss_odbl.js` enthält die Art `haltestelle` (Ziele aus dem VBB-GTFS), `quellen` nennt aber kein `vbb`
  (`skripte/15_planer.py`, `erreichbar_datei`, Zweig Fußweg: Schlüssel `zensus, mbjs, lgb, osm`). Gehört A6.
- `belege/A6_planer_20261105.md` (von Hand, A6) sagt noch, die `_odbl`-Dateien seien nicht angelegt.
