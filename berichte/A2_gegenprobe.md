# A2 Gegenprobe: ALKIS-Gebäude gegen MBJS-Einrichtungen

Erzeugt von `skripte/11_einrichtungen.py` am 2026-11-05. Quellen: MBJS-WFS (Abruf 05.11.2026, © Ministerium für Bildung, Jugend und Sport), ALKIS-Gebäude (Snapshot `auswertung.gebaeude_stand_20261105`) und ALKIS-Nutzung (© GeoBasis-DE/LGB), jeweils dl-de/by-2-0, Daten verändert (eigene Berechnung). Abstände in EPSG:25833.

## 1. Bestand in `auswertung.einrichtung`

| art | status | in Potsdam | außerhalb (Rechteck) | Plätze in Potsdam | Schüler in Potsdam |
|---|---|---:|---:|---:|---:|
| bibliothek | lage_ohne_kapazitaet | 10 | 0 | – | – |
| feuerwehr | lage_ohne_kapazitaet | 18 | 8 | – | – |
| foerderschule | kapazitaet | 5 | 3 | – | 822 |
| grundschule | kapazitaet | 32 | 13 | – | 10.329 |
| grundschule | lage_ohne_kapazitaet | 2 | 0 | – | – |
| gymnasium | kapazitaet | 11 | 2 | – | 5.745 |
| gymnasium | lage_ohne_kapazitaet | 2 | 0 | – | – |
| hort | kapazitaet | 38 | 18 | 6.196 | – |
| hort | lage_ohne_kapazitaet | 9 | 0 | – | – |
| kita | kapazitaet | 113 | 51 | 14.757 | – |
| kita | lage_ohne_kapazitaet | 11 | 0 | – | – |
| osz | kapazitaet | 9 | 1 | – | 5.310 |
| osz | lage_ohne_kapazitaet | 1 | 0 | – | – |
| sek1 | kapazitaet | 14 | 6 | – | 7.357 |
| sek1 | lage_ohne_kapazitaet | 0 | 1 | – | – |
| sonstiger_gemeinbedarf | lage_ohne_kapazitaet | 130 | 23 | – | – |
| sonstige_schule | kapazitaet | 2 | 2 | – | 770 |
| sport | lage_ohne_kapazitaet | 106 | 38 | – | – |

## 2. Abgleich mit dem Bauplan

- **Kitas und Horte in Potsdam (MBJS, alle Einrichtungsarten):** 151 Einrichtungen (`id_kita`) mit 20.953 Plätzen laut Betriebserlaubnis; dazu 20 weitere Häuser derselben Einrichtungen, zusammen 171 Standorte. Der Bauplan nennt 171 Kitas mit 24.581 Plätzen: Das sind die Einträge des Dienstes (Häuser), deren Kapazität je Haus wiederholt wird. Je Einrichtung gezählt sind es die Werte hier; die weiteren Häuser stehen als `lage_ohne_kapazitaet` mit der Kennung `<id_kita>#haus<n>` in der Tabelle.
- **Horte:** 38 Einrichtungen mit 6.196 Plätzen (47 Standorte mit weiteren Häusern). Hort heißt: Altersstruktur „Kinder im Grundschulalter“ oder Einrichtungsart „Kinderhort …“. Der Bauplan nennt 39 ohne Herleitung; je Einrichtung sind es 38, je Haus 47. Zusätzlich betreuen 37 Kitas mit 5.906 Plätzen Kinder bis einschließlich Grundschulalter (`unterart` endet auf `_hort`); ihre Kapazität lässt sich aus den Quelldaten nicht auf Kita und Hort aufteilen.
- **Schulen in Potsdam:** 78, davon 34 Grundschulen (Schulform G). Weitere 3 Schulen haben einen Grundschulteil (Schulform G/S bzw. G/O/OG, `unterart` beginnt mit `G/`).

## 3. Altersstruktur der Kitas und Horte in Potsdam (Prüfbericht 9)

Normiert als `<ab Monate>m-<bis>`, `bis` = `schuleintritt`, `grundschulalter` oder eine Grenze in Monaten; `72m` steht für „ab Einschulung“. Kapazität je Einrichtung, weitere Häuser ohne Plätze.

| art | unterart | Einrichtungen | Plätze |
|---|---|---:|---:|
| hort | hort | 38 | 6.196 |
| kita | krippe_kindergarten | 81 | 8.675 |
| kita | krippe_kindergarten_hort | 21 | 4.190 |
| kita | kindergarten_hort | 8 | 1.716 |
| kita | krippe | 2 | 110 |
| kita | kindergarten | 1 | 66 |

## 4. Gegenprobe: liegt ein passendes ALKIS-Gebäude in der Nähe?

Je MBJS-Standort in Potsdam: Abstand zum nächsten ALKIS-Gebäude mit der genannten Funktion (Gebäudeumriss, nicht Mittelpunkt).

| MBJS | ALKIS-Funktion | Standorte | ≤ 25 m | ≤ 75 m | ≤ 150 m |
|---|---|---:|---|---|---|
| Kitas (Einrichtung, Hauptstandort) | Kinderkrippe, Kindergarten, Kindertagesstätte | 113 | 82 (73 %) | 90 (80 %) | 95 (84 %) |
| Kitas (alle Häuser) | Kinderkrippe, Kindergarten, Kindertagesstätte | 124 | 90 (73 %) | 99 (80 %) | 104 (84 %) |
| Horte (alle Häuser) | Kinderkrippe, Kindergarten, Kindertagesstätte / Allgemein bildende Schule | 47 | 35 (74 %) | 41 (87 %) | 44 (94 %) |
| Schulen ohne OSZ | Allgemein bildende Schule | 68 | 61 (90 %) | 63 (93 %) | 64 (94 %) |
| Oberstufenzentren und berufliche Schulen | Allgemein bildende Schule / Berufsbildende Schule / Gebäude für Bildung und Forschung | 10 | 6 (60 %) | 7 (70 %) | 9 (90 %) |

**Kennzahl der Abnahme:** Anteil der MBJS-Kitas mit ALKIS-Kitagebäude in 75 m = Zeile „Kitas (Einrichtung, Hauptstandort)“, Spalte „≤ 75 m“.

## 5. Umgekehrt: ALKIS-Gebäudegruppen ohne MBJS-Standort

Gebäude gleicher Funktion in höchstens 50 m Abstand sind eine Gruppe (DBSCAN, `ST_ClusterDBSCAN`, minpoints 1). Gezählt in Potsdam; „ohne MBJS“ = kein MBJS-Standort der passenden Art in 75 m. Gründe können sein: Kindertagespflege oder Betriebskita (nicht im Dienst), geschlossene oder umgenutzte Häuser, falsche Funktion im Kataster, Standortpunkt am Grundstücksrand.

| ALKIS-Funktion | Gebäude in Potsdam | Gruppen | Gruppen ohne MBJS in 75 m |
|---|---:|---:|---|
| Kinderkrippe, Kindergarten, Kindertagesstätte | 153 | 98 | 11 (11 %) |
| Allgemein bildende Schule | 174 | 68 | 13 (19 %) |

## 6. Gemeinbedarf aus ALKIS, nur Lage (Prüfbericht 12)

Standort = Gruppe aus Gebäuden bzw. Nutzungsflächen derselben Art in höchstens 50 m Abstand, Punkt auf der Fläche (`ST_PointOnSurface`). Ohne Kapazität, ohne Namen (ALKIS vereinfacht führt keine).

| art | unterarten (Gruppen enthalten) | Standorte in Potsdam | außerhalb |
|---|---|---:|---:|
| bibliothek | bibliothek | 10 | 0 |
| feuerwehr | feuerwehr | 18 | 8 |
| sonstiger_gemeinbedarf | kultur, oeffentliche_zwecke, soziale_zwecke, veranstaltung | 130 | 23 |
| sport | hallenbad, schwimmen, sportanlage, sportgebaeude, sporthalle | 106 | 38 |

Zuordnung der Funktionen:

- Gebäudefunktion „Feuerwehr“ → `feuerwehr` / `feuerwehr`
- Gebäudefunktion „Bibliothek, Bücherei“ → `bibliothek` / `bibliothek`
- Gebäudefunktion „Sport-, Turnhalle“ → `sport` / `sporthalle`
- Gebäudefunktion „Gebäude für Sportzwecke“ → `sport` / `sportgebaeude`
- Gebäudefunktion „Hallenbad“ → `sport` / `hallenbad`
- Gebäudefunktion „Gebäude für soziale Zwecke“ → `sonstiger_gemeinbedarf` / `soziale_zwecke`
- Gebäudefunktion „Gebäude für kulturelle Zwecke“ → `sonstiger_gemeinbedarf` / `kultur`
- Gebäudefunktion „Veranstaltungsgebäude“ → `sonstiger_gemeinbedarf` / `veranstaltung`
- Gebäudefunktion „Gebäude für öffentliche Zwecke“ → `sonstiger_gemeinbedarf` / `oeffentliche_zwecke`
- Nutzung „Sportanlage“ (Sport-, Freizeit- und Erholungsfläche) → `sport` / `sportanlage`
- Nutzung „Schwimmen“ (Sport-, Freizeit- und Erholungsfläche) → `sport` / `schwimmen`

**Lücke:** ALKIS vereinfacht hat keine eigene Funktion für Jugendfreizeiteinrichtungen, Seniorenbegegnung oder Bürgerhäuser. Im Snapshot gibt es dafür keinen Wert; sie stecken in „Gebäude für soziale Zwecke“ (`soziale_zwecke`) bzw. „Gebäude für kulturelle Zwecke“ (`kultur`) zusammen mit Pflegeheimen, Beratungsstellen, Museen und Ähnlichem. Getrennt ausweisen lassen sie sich nur mit einer weiteren Quelle (z. B. Einrichtungsliste der Stadt, Handdownload). Die Arten `jugend`, `senioren` und `buergerhaus` aus dem Tabellenkommentar bleiben deshalb leer.

## 7. Grünflächen (`auswertung.gruenflaeche`)

Zuordnung laut `config/richtwerte.yaml`, Abschnitt `gruen_definition.arten`. Fläche je ALKIS-Objekt, ganzes Rechteck des Abrufs (auch knapp außerhalb der Stadt, für den Randeffekt).

| art | Objekte | Fläche gesamt (ha) | davon in Potsdam (ha) | Objekte ≥ 0,5 ha |
|---|---:|---:|---:|---:|
| freizeit | 556 | 254 | 29 | 143 |
| friedhof | 46 | 228 | 62 | 24 |
| gruenanlage | 2.210 | 741 | 345 | 380 |
| kleingarten | 171 | 193 | 168 | 111 |
| park | 119 | 611 | 581 | 67 |
| wald | 1.790 | 9.967 | 4.707 | 1.230 |

Offen für A6 (Prüfbericht 14): ALKIS vereinfacht führt bei Parks keinen Namen; die SPSG-Parks (Sanssouci, Neuer Garten, Babelsberg) lassen sich daraus nicht getrennt kennzeichnen. Die größten Park-Objekte liegen bei 90 und 85 ha. Mindestgröße und die Frage, ob Kleingärten, Friedhöfe und Wald mitzählen, entscheidet A6 in `gruen_definition`.

