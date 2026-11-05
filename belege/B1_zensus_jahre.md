# B1: Zensus-Baujahr im Gitter (Bericht)

Erzeugt von `skripte/21_jahre_zensus.py` am 2026-11-05. Quelle: Zensus 2022 (Stichtag 15.05.2022), Gebäude mit Wohnraum, Destatis-Gitterdaten (`$KIEZ_DATEN/zensus/2022/`, HERKUNFT.md dort). © Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung).

„–“ heißt laut Datensatzbeschreibung „genau Null oder auf Null geändert“ (Cell-Key-Methode). In `auswertung.zensus_gebaeude_jahr` steht dafür `anzahl = 0, geaendert = true`.

## Gelesen und geschrieben

| Merkmal | Raster | Zeilen im Rahmen um Potsdam (1 km Rand) |
|---|---|---:|
| jahrzehnte | 100m | 5999 |
| jahrzehnte | 1km | 298 |
| mz_klassen | 100m | 5999 |
| mz_klassen | 1km | 298 |

`auswertung.zensus_gebaeude_jahr`: 60480 Zeilen. 100-m-Zellen mit Mittelpunkt in einem der 32 Stadtteile (wie `02_auswerten.py`), 1-km-Zellen, deren Quadrat die Stadt schneidet.

## Potsdam, 100-m-Zellen (Mittelpunkt im Stadtteil)

| Merkmal | Zellen mit Gebäuden | Σ Gesamtwert | Σ Klassen | Lücke | Zellen, in denen alle Klassen „–“ sind | davon in zellen.js | Σ Gesamtwert in zellen.js-Zellen | Zellen ohne Einwohner (nicht in zellen.js) | Gebäude dort |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mz_klassen | 2869 | 23155 | 21067 | 2088 (9,0 %) | 458 | 2869 | 23155 | 0 | 0 |
| jahrzehnte | 2869 | 23155 | 20741 | 2414 (10,4 %) | 502 | 2869 | 23155 | 0 | 0 |

Gesamtwert je Zelle in beiden Dateien gleich: 2869 von 2869 Zellen; Zellen nur in einer der beiden Dateien: 0.

**Erwartung aus der Erkundung:** 2.869 Zellen mit Gebäuden, 23.155 Gebäude, gerechnet über die 3.443 bewohnten Zellen von `zellen.js` (Mikrozensus-Klassen). Spalten „davon in zellen.js“ und „Σ Gesamtwert in zellen.js-Zellen“ sind der Vergleichswert; Zellen mit Gebäuden, aber ohne gemeldete Einwohner, fehlen in `zellen.js` und damit in `jahre_zellen.js`.

### Klassen, Stadt (Σ über die 100-m-Zellen)

**mz_klassen**

| Klasse | Gebäude | Zellen mit „–“ |
|---|---:|---:|
| insgesamt | 23155 | 0 |
| vor_1919 | 3253 | 2257 |
| 1919_1948 | 3970 | 2126 |
| 1949_1978 | 2567 | 2366 |
| 1979_1990 | 1710 | 2561 |
| 1991_2000 | 3349 | 2301 |
| 2001_2010 | 3060 | 2292 |
| 2011_2019 | 2798 | 2351 |
| ab_2020 | 360 | 2781 |

**jahrzehnte**

| Klasse | Gebäude | Zellen mit „–“ |
|---|---:|---:|
| insgesamt | 23155 | 0 |
| vor_1919 | 3234 | 2262 |
| 1919_1949 | 3915 | 2136 |
| 1950_1959 | 585 | 2733 |
| 1960_1969 | 560 | 2752 |
| 1970_1979 | 1392 | 2598 |
| 1980_1989 | 1435 | 2613 |
| 1990_1999 | 3082 | 2342 |
| 2000_2009 | 3079 | 2287 |
| 2010_2015 | 1968 | 2488 |
| ab_2016 | 1491 | 2571 |

## 1-km-Zellen gegen Σ der 100-m-Zellen

Die 1-km-Werte sind eigenständig geheim gehalten. Für 1-km-Zellen, die ganz in der Stadt liegen, zeigt der Vergleich, wie stark sich die Veränderung kleiner Werte bei der Summe von 100 Zellen auswirkt. B4 verteilt die 1-km-Summen.

| Merkmal | 1-km-Zellen, die Potsdam schneiden | davon ganz in der Stadt | Σ Gesamtwert 1 km (ganz) | Σ Gesamtwert 100 m darin | Σ Klassen 1 km (ganz) | Σ Klassen 100 m darin |
|---|---:|---:|---:|---:|---:|---:|
| mz_klassen | 155 | 93 | 19527 | 19039 | 19457 | 17519 |
| jahrzehnte | 155 | 93 | 19527 | 19039 | 19471 | 17258 |

## Gegenprobe: Wohnungen nach Baujahr (Bestand `zensus_zelle.w_*`)

Zellen in Potsdam mit Wohnungen (`w_ges > 0`): 3142, zusammen 100998 Wohnungen. Zellen mit Wohnungen, aber ohne Gebäude im Baujahr-Gitter: 277; Zellen mit Gebäuden, aber ohne Wohnungen: 4. (Wohnungen und Gebäude sind getrennt geheim gehalten, kleine Abweichungen sind zu erwarten.)

## Je Stadtteil (Mikrozensus-Klassen, 100 m, Zellen in zellen.js)

| Stadtteil | Zellen mit Gebäuden | Σ Gesamtwert | Σ Klassen | Lücke |
|---|---:|---:|---:|---:|
| 11 Bornim | 151 | 1037 | 865 | 172 |
| 12 Nedlitz | 13 | 48 | 29 | 19 |
| 13 Bornstedt | 240 | 2277 | 2129 | 148 |
| 14 Sacrow | 13 | 58 | 47 | 11 |
| 15 Eiche | 89 | 915 | 911 | 4 |
| 16 Grube | 25 | 140 | 124 | 16 |
| 17 Golm | 116 | 841 | 720 | 121 |
| 21 Nauener Vorstadt | 119 | 834 | 782 | 52 |
| 22 Jägervorstadt | 40 | 365 | 326 | 39 |
| 23 Berliner Vorstadt | 68 | 414 | 345 | 69 |
| 31 Brandenburger Vorstadt | 80 | 645 | 602 | 43 |
| 32 Potsdam West | 103 | 814 | 759 | 55 |
| 41 Historische Innenstadt | 134 | 1299 | 1227 | 72 |
| 43 Zentrum Ost und Nuthepark | 31 | 210 | 189 | 21 |
| 44 Hauptbahnhof und Brauhausberg Nord | 30 | 199 | 189 | 10 |
| 51 Klein Glienicke | 20 | 109 | 75 | 34 |
| 52 Babelsberg Nord | 237 | 2062 | 1826 | 236 |
| 53 Babelsberg Süd | 187 | 1556 | 1487 | 69 |
| 61 Templiner Vorstadt | 51 | 350 | 293 | 57 |
| 62 Teltower Vorstadt | 98 | 753 | 740 | 13 |
| 63 Schlaatz | 52 | 421 | 424 | -3 |
| 64 Waldstadt I und Industriegelände | 83 | 632 | 595 | 37 |
| 65 Waldstadt II | 66 | 492 | 486 | 6 |
| 71 Stern | 208 | 1749 | 1598 | 151 |
| 72 Drewitz | 91 | 701 | 612 | 89 |
| 73 Kirchsteigfeld | 41 | 403 | 390 | 13 |
| 81 Uetz-Paaren | 25 | 124 | 114 | 10 |
| 82 Marquardt | 44 | 315 | 257 | 58 |
| 83 Satzkorn | 23 | 165 | 162 | 3 |
| 84 Fahrland | 137 | 1279 | 1185 | 94 |
| 85 Neu Fahrland | 72 | 548 | 389 | 159 |
| 86 Groß Glienicke | 182 | 1400 | 1190 | 210 |
| **Σ** | 2869 | 23155 | 21067 | 2088 |

Die Summen je Stadtteil sind Summen veränderter Zellwerte; bei kleinen Stadtteilen ist die Lücke zwischen Gesamtwert und Klassen anteilig groß. Für Aussagen je Stadtteil auf 10 Gebäude runden und den Gesamtwert, nicht die Klassensumme, als Bezug nennen.

## daten/jahre_zellen.js

3443 Zellen in `zellen.js`-Reihenfolge, davon 2869 mit Gebäuden (Σ 23155). Ohne ablesbare Verteilung (alle Klassen „–“, `anteile` und `vorherrschend` null): 458. Gleichstand zweier Klassen (`vorherrschend` null): 283. Größe 114539 Byte, gzip -9 13066 Byte (Grenze 120 KB). Nur Zellwerte, keine Gebäude-IDs, keine Färbung einzelner Gebäude.
