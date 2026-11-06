# A5a Erreichbarkeit in Luftlinie: Lauf 20261105T103300Z

Erzeugt von `skripte/14_erreichbarkeit.py` (Rolle `kiezatlas_rechnen`, kein Netzabruf). Gerechnet in EPSG:25833 vom Mittelpunkt der Zensus-Zelle aus. Der Mittelpunkt kann bis zu 71 m vom tatsächlichen Wohnort abweichen; Meterwerte sind auf 0,1 m gespeichert, aussagekräftig sind sie auf rund 50 m.

**Zellen:** 3.443 mit Mittelpunkt in Potsdam (Menge von `daten/zellen.js`), davon 3.411 bewohnt mit 182.673 Einwohnern (Zensus 2022).

## Nächste Einrichtung je Art

Mediane und P90 nach Einwohnern gewichtet (bewohnte Zellen). „außerhalb“ = die nächste Einrichtung liegt außerhalb der Stadtgrenze (E7: Brandenburg wird mitgerechnet). „Rand unsicher“ siehe unten.

| art | bewohnte Zellen | Standorte (gesamt) | Median m | P90 m | max m | Zellen mit Ziel außerhalb | EW dort |
|---|---|---|---|---|---|---|---|
| bibliothek | 3.411 | 10 | 1.142 | 3.123 | 9.566 | 0 | 0 |
| feuerwehr | 3.411 | 26 | 1.118 | 2.223 | 3.722 | 29 | 289 |
| foerderschule | 3.411 | 8 | 2.123 | 5.599 | 12.527 | 342 | 6.908 |
| gruen | 3.411 | 2.329 | 74 | 181 | 1.497 | 0 | 0 |
| grundschule | 3.411 | 47 | 444 | 1.056 | 6.245 | 21 | 135 |
| gymnasium | 3.411 | 15 | 854 | 2.891 | 8.248 | 77 | 1.396 |
| hort | 3.411 | 65 | 464 | 1.824 | 7.303 | 131 | 1.653 |
| kita | 3.411 | 175 | 257 | 565 | 2.772 | 54 | 504 |
| osz | 3.411 | 11 | 1.258 | 3.999 | 12.089 | 137 | 2.827 |
| sek1 | 3.411 | 21 | 814 | 3.131 | 9.574 | 105 | 983 |
| sonstiger_gemeinbedarf | 3.411 | 153 | 308 | 713 | 3.753 | 40 | 415 |
| sonstige_schule | 3.411 | 4 | 2.302 | 4.416 | 11.544 | 365 | 8.166 |
| sport | 3.411 | 144 | 296 | 651 | 1.986 | 46 | 502 |

Art `gruen`: nächste Grünfläche der Arten gruenanlage, park (Abstand zum Flächenrand; 0 m = Zellmittelpunkt liegt in der Fläche). Standorte = ALKIS-Objekte.

## Randeffekt (E7)

Abrufrechtecke laut `config/potsdam.yaml` (EPSG:25833): MBJS [353000, 5798000, 379000, 5823000], ALKIS/LGB [356000, 5801000, 376000, 5820000]. Das ALKIS-Rechteck endet fast an der Stadtgrenze; Bibliotheken, Feuerwehren, Sport und sonstiger Gemeinbedarf jenseits davon fehlen. Berlin liefert weder MBJS noch LGB (E7: Berlin nein).

Berlin-Ersatz: 935 bewohnte Zellen außerhalb Potsdams ohne LGB-Gebäude im LGB-Rechteck, davon 882 mit mindestens 3 solchen Nachbarn in 150 m (24.582 EW; x 371.639–375.916, y 5.805.827–5.819.346). Das ist das Berliner Gebiet östlich der Stadt.

„berlin“: nach E7 vorerst nicht gerechnet; eine Berliner Einrichtung könnte näher liegen. „rechteck“: der Abruf der Quelle endete dort.

Zellen, deren Wert nur eine Obergrenze ist (die nächste Einrichtung liegt weiter weg als der Rand des Datengebiets; jenseits davon könnte eine nähere liegen). Liste: `belege/A5a_rand_unsicher_20261105.csv`.

| art | Zellen | EW | davon Rechteckrand | davon Berlin |
|---|---|---|---|---|
| bibliothek | 873 | 26.405 | 480 | 724 |
| feuerwehr | 433 | 18.729 | 50 | 383 |
| foerderschule | 1.121 | 45.408 | 366 | 1.054 |
| gruen | 16 | 491 | 1 | 15 |
| gruen_500m | 124 | 3.979 | 0 | 124 |
| grundschule | 316 | 8.272 | 7 | 316 |
| gymnasium | 390 | 10.251 | 62 | 335 |
| hort | 234 | 5.423 | 31 | 203 |
| kita | 138 | 3.819 | 0 | 138 |
| osz | 627 | 16.574 | 202 | 556 |
| sek1 | 615 | 18.138 | 105 | 544 |
| sonstige_schule | 1.263 | 56.901 | 282 | 1.200 |
| sonstiger_gemeinbedarf | 262 | 7.694 | 15 | 247 |
| sport | 157 | 3.702 | 1 | 156 |

## Grün im Umkreis (`auswertung.zelle_gruen`, Korrektur 22)

- Radius 500 m, bewohnte Zellen 3.411: Median Grünfläche 37.666 m², Median 22 m² je EW im Kreis; 38 Zellen ohne Grün im Kreis; 629 Zellen unter 6 m² je EW; größter Wert 590.470 m² (Kreisfläche 785.398 m²).

Definition: ALKIS-Nutzung der Arten gruenanlage, park (`gruen_definition.arten`, `zaehlt_vorschlag: true`), vereinigt, Mindestfläche keine (mindestflaeche_m2: null). Nicht gezählt: Arten mit offenem Vorschlag (freizeit) und mit `false`. `gruen_definition.status` ist `offen`: entscheidet A6 anders, muss dieses Skript neu laufen.

`m2_je_ew` = Grünfläche im Kreis geteilt durch die Einwohner aller Zensus-Zellen, deren Mittelpunkt im selben Kreis liegt (auch außerhalb der Stadt). Das ist eine vereinfachte Annäherung an die Berliner Methode (Umweltatlas 2020), nicht deren Nachbildung: dort zählen Grünanlagen ab einer Mindestgröße und die Fläche wird auf alle Einwohner im Einzugsbereich verteilt. Der Kreis ist ein Polygon mit 256 Ecken (Flächenfehler unter 0,01 %). Kreise, die über das LGB-Rechteck oder nach Berlin reichen, unterschätzen das Grün (Berliner Einwohner zählen im Nenner, Berliner Parks fehlen im Zähler); sie stehen mit `gruen_<radius>m` in der CSV.

## Fußweg-Zeilen (A5b) unberührt

Vor dem Lauf: zelle_erreichbar 0, zelle_gruen 0 Zeilen mit methode „fussweg“. Nach dem Lauf: 0 bzw. 0. Gelöscht und neu geschrieben wurden nur Zeilen mit methode „luftlinie“.

## Hinweise für A6

- `minuten` ist bei Luftlinie leer. Luftlinie ist für ÖPNV (NVP 2019) und Nahversorgung (EHK 2014) die Potsdamer Messart; als Gehzeit taugt sie nicht.
- Grundschule: Art `grundschule` = Schulform G. Grundschulteile in kombinierten Schulformen (sek1 `G/S`, `G/O/OG`) zählen nicht dazu; die nächste Grundschule kann deshalb näher liegen als angegeben. Ohne Schulbezirke (H2) bleibt der Wert vorläufig.
- Kita und Hort: Entfernung zum nächsten Haus (auch weitere Häuser `#haus<n>` ohne Plätze). Kitas haben in Brandenburg keine Einzugsbereiche (Wunsch- und Wahlrecht); Entfernung ist Lage, keine Versorgung.
- Gemeinbedarf aus ALKIS (Bibliothek, Feuerwehr, Sport, sonstiger Gemeinbedarf): nur Lage, ohne Kapazität; am Stadtrand Obergrenze (siehe Randeffekt).
- Jugend, Senioren, Bürgerhaus: A2 erzeugt diese Arten erst, wenn B0 `auswertung.alkis_nas_gebaeude` gefüllt hat. Danach A2 und dieses Skript neu laufen lassen; das Skript liest die Arten aus der Tabelle.

