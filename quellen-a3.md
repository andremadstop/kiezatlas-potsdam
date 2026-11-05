# Zulieferung A3 zum Lizenzregister (QUELLEN.md, Zeile 11)

Paket A3 (OSM-Einrichtungen und Fußwegnetz), Stand 05.11.2026. Wird in der Integration (I1) in `QUELLEN.md`
übernommen.

| # | Quelle | Paket | URL | Lizenz | Vermerk | Weg | Stand / Abruf |
|---|---|---|---|---|---|---|---|
| 11 | OpenStreetMap-Auszug (PBF) für Einrichtungen und Fußwegnetz | A3, A5b, B2 (nur Prüfspalte) | Handdownload H5: BBBike-Auszug Potsdam oder Geofabrik Brandenburg | ODbL 1.0 | © OpenStreetMap-Mitwirkende, ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/) | H (automatisch verboten), danach offline mit `skripte/12_osm.sh laden` | fehlt (05.11.2026) |

## Was aus OSM wird und wo es landet

| Objekt | Inhalt | Lizenz | Veröffentlicht in |
|---|---|---|---|
| `auswertung.osm_poi` | Ärzte (`amenity=doctors`, `healthcare=doctor`, Fachrichtung aus `healthcare:speciality`), Apotheken, Supermärkte und kleine Lebensmittelläden (`shop=supermarket/convenience`), Pflege (`amenity=nursing_home`, `social_facility=nursing_home/assisted_living`, betreute Gruppen für Senioren), öffentliche Spielplätze (`leisure=playground` ohne `access=private/no`). **Kein Name**, keine Adresse, kein Kontakt. | ODbL 1.0 | nur `daten/einrichtungen_odbl.js` (A6) und später `*_odbl.gpkg` (A8) |
| `auswertung.netz_knoten`, `auswertung.netz_kante` | Fußwegnetz Stadtgebiet + 2 km | ODbL 1.0 | nie direkt; Fußweg-Werte nur in `daten/erreichbar_fuss_odbl.js`, `daten/planer_fuss_odbl.js` (A5b/A6) |
| `berichte/A3_vollstaendigkeit.md` | Trefferquote OSM gegen MBJS (Kitas, Schulen) | intern | nicht veröffentlicht (`berichte/` ist in `.gitignore`) |

OSM-Kitas und -Schulen werden nur für den Vollständigkeitsbericht gelesen (TEMP-Tabelle), nicht gespeichert.
Gebäudejahre bleiben OSM-frei (E1).

## Abrufweg

Kein Agentenabruf: Geofabrik- und BBBike-Downloads, Overpass, osmnx und taginfo sind für Programme verboten
(Bauplan 0.3). Andre lädt die PBF im Browser und legt sie unter `$KIEZ_DATEN/osm/<stand>/` ab. Aus dem gemeinsamen
`$KIEZ_DATEN/eingang/` lädt das Skript nicht (es bricht mit der Bitte ab, die Datei zu verschieben), damit jede
Lieferung ihre eigene `HERKUNFT.md` hat. Fehlt sie im Zielordner, legt `skripte/12_osm.py` sie mit Größe, SHA256
und Dateikopf an; Bezugsadresse und Abrufdatum trägt Andre nach.

Empfohlen ist der **BBBike-Auszug Potsdam** (Rechteck, enthält den Berliner Teil des Puffers). Geofabrik
Brandenburg endet an der Landesgrenze: Der Berliner Teil des Puffers (Wannsee, Kladow) fehlt dann, der Bericht
zeigt das als leere 1-km-Kacheln.
