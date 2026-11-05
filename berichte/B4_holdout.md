# B4: Kaskade der Gebäudejahre, Rücktest und Summenprüfung

Stand 2026-11-05. Erzeugt von `skripte/24_jahre_kaskade.py ruecktest`. Regeln vorab festgelegt in `pruefen/B4_protokoll.md`. Dieser Bericht enthält nur Zählungen, keine Gebäudekennungen und keine Adressen. Zensuswerte je Stadtteil sind auf 10 gerundet; sie sind durch das Geheimhaltungsverfahren (Cell-Key) verändert, Summen aus vielen Zellen sind absolut ungenauer als jede einzelne Zelle.

**Korrekturen nach Lauf 1** (Codefehler, Regeln unverändert; Lauf 1 liegt als `berichte/B4_holdout_lauf1.md` bei):

1. Die Gebietshülle der Blocktypen enthielt nicht alle Gebäude ihres Clusters (`ST_ConcaveHull` über Umrisse); jetzt Hülle vereinigt mit den Umrissen, dann 15 m Rand. Lauf 1: Am Stern 133 statt 148 Gebäude.
2. Die Jahrzehnte-Gegenprobe zählte „Waldstadt II“ bei „Waldstadt I“ mit (Teilwortsuche); jetzt genauer Gebietsname.

## Abdeckung der Kaskade

| Stufe | Gebäude | davon mit Wohnraum | davon Nebengebäude |
|---|---:|---:|---:|
| 1 genaues Jahr (B2, freigegeben) | 106 | 51 | 6 |
| 2 Luftbildklammer (B3, ausgerollt) | 0 | 0 | 0 |
| 3 Blocktyp Großsiedlung | 815 | 815 | 0 |
| 4 Zensus-Verteilung | 17.294 | 17.294 | 0 |
| 5 Nachbarn | 8.501 | 3.363 | 0 |
| 6 nicht datiert | 25.593 | 494 | 22.531 |
| Summe | 52.309 | 22.017 | 22.537 |

- Stufe 1: 106 Gebäude, Stufe 2: 0 Gebäude. Stufe 1 nimmt nur Zeilen aus `auswertung.jahr_beleg` ohne `nur_pruefung`; das sind derzeit nur die genauen Jahre aus dem Wikidata-Export H9 (CC0). OSM, Wikipedia und BLDAM-Liste sind Prüfwerte, die DDB-API (H8) fehlt, die BLDAM-Lizenz ist offen (E8). Stufe 2 nimmt nur ausgerollte Klammern (B3: nicht ausgerollt).
- Gebäude mit Einzeljahr `j`: 53, davon mit Wohnraum 0. ALKIS führt keine Zahl der Wohneinheiten (Spalte leer), deshalb tragen die 51 Gebäude mit Wohnraum in Stufe 1 nur die Klasse, auch Baudenkmale (Korrektur 6, Datenschutz: kein Jahr bei weniger als 3 Wohneinheiten).
- Wohngebäude in Zellen ohne Zensuswert: 1535; Wohngebäude über der Zensuszahl ihrer Zelle (mehr ALKIS-Umrisse als Zensus-Gebäude, auch Neubau nach dem 15.05.2022): 2369. Beide gehen an Stufe 5.
- Geheimhaltungslücken der 100-m-Zellen aufgefüllt aus: {'ohne_luecke': 1699, 'stadt_rest': 255, 'km_rest': 915} (km_rest = Rest der 1-km-Zelle, nur Zellen ganz in der Stadt; stadt_rest = Rest aller solcher 1-km-Zellen; eigene_klassen = Klassen der Zelle selbst).
- Formmodell gelernt in 701 reinen Zellen (eine Klasse ≥ 85 %, keine Lücke, mindestens 4 Gebäude).

## Rücktest

Die Prüfgebäude gehen in keine Stufe ein: Wikipedia-Jahre sind nur Prüfspalte (Korrektur 5), die B3-Referenz stammt aus einer Sichtprüfung von Luftbildern. Seit dem Wikidata-Export rechnet der Rücktest die Kaskade ein zweites Mal **ohne Stufe 1** (Protokoll, Nachtrag N3): Kein Prüfgebäude kennt dort sein genaues Jahr, die Wikidata-Jahre werden selbst zum dritten Prüfsatz. Die Stufen in den Tabellen sind die dieses Laufs. Gemessen wird die Klasse aus der Kaskade gegen die bekannte Bauzeit. **Treffer** = geschätzte Klasse überschneidet die bekannte Spanne. **Abstand** = Jahre zwischen Klassenspanne und bekannter Spanne (0 bei Treffer; „vor 1919“ und „ab 2020“ sind nach einer Seite offen).

### Sichtprüfung Luftbilder Bornstedt (B3-Referenz): 193 Gebäude

Je Stufe:

| Stufe | n | ohne Klasse | Treffer | Median Abstand (J.) | Median Abstand der Fehlgriffe (J.) |
|---|---:|---:|---:|---:|---:|
| 4 Zensus-Verteilung | 169 | 0 | 125 von 169 (74,0 %) | 0 | 7 |
| 5 Nachbarn | 18 | 0 | 14 von 18 (77,8 %) | 0 | 48 |
| 6 nicht datiert | 6 | 6 | – | – | – |
| alle Stufen | 193 | 6 | 139 von 187 (74,3 %) | 0 | 11 |

Je bekannter Bauzeit (alle Stufen):

| bekannte Bauzeit | n | ohne Klasse | Treffer | Median Abstand (J.) | Median Abstand der Fehlgriffe (J.) |
|---|---:|---:|---:|---:|---:|
| 2011–2019 | 39 | 0 | 25 von 39 (64,1 %) | 0 | 3,5 |
| ab 2020 | 8 | 2 | 5 von 6 (83,3 %) | 0 | 2 |
| mehrdeutig (Spanne über Klassengrenze) | 146 | 4 | 109 von 142 (76,8 %) | 0 | 18 |

### Wikidata, genaue Jahre (Stufe 1, im Rücktest zurückgehalten): 105 Gebäude

Je Stufe:

| Stufe | n | ohne Klasse | Treffer | Median Abstand (J.) | Median Abstand der Fehlgriffe (J.) |
|---|---:|---:|---:|---:|---:|
| 3 Blocktyp Großsiedlung | 1 | 0 | 0 von 1 (0,0 %) | 87 | 87 |
| 4 Zensus-Verteilung | 36 | 0 | 21 von 36 (58,3 %) | 0 | 109 |
| 5 Nachbarn | 34 | 0 | 25 von 34 (73,5 %) | 0 | 111 |
| 6 nicht datiert | 34 | 34 | – | – | – |
| alle Stufen | 105 | 34 | 46 von 71 (64,8 %) | 0 | 109 |

Je bekannter Bauzeit (alle Stufen):

| bekannte Bauzeit | n | ohne Klasse | Treffer | Median Abstand (J.) | Median Abstand der Fehlgriffe (J.) |
|---|---:|---:|---:|---:|---:|
| vor 1919 | 97 | 32 | 45 von 65 (69,2 %) | 0 | 125 |
| 1919–1948 | 7 | 1 | 1 von 6 (16,7 %) | 48,5 | 82 |
| 1979–1990 | 1 | 1 | – | – | – |

### Wikipedia-Denkmalliste (Prüfspalte B2): 343 Gebäude

Je Stufe:

| Stufe | n | ohne Klasse | Treffer | Median Abstand (J.) | Median Abstand der Fehlgriffe (J.) |
|---|---:|---:|---:|---:|---:|
| 3 Blocktyp Großsiedlung | 1 | 0 | 0 von 1 (0,0 %) | 86 | 86 |
| 4 Zensus-Verteilung | 198 | 0 | 141 von 198 (71,2 %) | 0 | 153 |
| 5 Nachbarn | 109 | 0 | 85 von 109 (78,0 %) | 0 | 111 |
| 6 nicht datiert | 35 | 35 | – | – | – |
| alle Stufen | 343 | 35 | 226 von 308 (73,4 %) | 0 | 134 |

Je bekannter Bauzeit (alle Stufen):

| bekannte Bauzeit | n | ohne Klasse | Treffer | Median Abstand (J.) | Median Abstand der Fehlgriffe (J.) |
|---|---:|---:|---:|---:|---:|
| vor 1919 | 320 | 30 | 220 von 290 (75,9 %) | 0 | 160 |
| 1919–1948 | 22 | 5 | 6 von 17 (35,3 %) | 15 | 24 |
| 1949–1978 | 1 | 0 | 0 von 1 (0,0 %) | 48 | 48 |

Überschneidung: 33 Gebäude stehen im Wikidata- und im Wikipedia-Satz; die beiden Sätze sind nicht unabhängig.

### Gegenprobe: Wikidata gegen Wikipedia an denselben Gebäuden

Gebäude, die in beiden Quellen ein genaues Baujahr (`genau`, `art = 'bau'`) haben. Vergleich je Gebäude über die Spanne [kleinstes Jahr, größtes Jahr]. Keine Schwelle; prüft die Zuordnung in B2, nicht die Schätzung.

| Gebäude in beiden | gleiches Jahr | anderes Jahr, gleiche Klasse | andere Klasse oder Spanne über Klassengrenze |
|---|---:|---:|---:|
| 33 | 16 | 17 | 0 |

### Gegenprobe: Zensus-Verteilung allein an den Blocktyp-Gebäuden

Stufe 4 ohne Vorgabe aus Stufe 3 gerechnet und gegen die Blocktyp-Klasse gestellt. Beide sind Schätzungen, das ist kein Rücktest gegen bekannte Jahre, sondern zeigt, wie weit Zensus und Blocktyp übereinstimmen.

| Menge | n | ohne Zensusklasse | gleiche Klasse | Median Abstand (J.) | Median Abstand der Abweichungen (J.) |
|---|---:|---:|---:|---:|---:|
| Blocktyp-Gebäude | 815 | 52 | 601 von 763 (78,8 %) | 0 | 11 |

Zum Vergleich Berlin (visinage, Methodenvorbild): 61,4 % Treffer über alle Schätzungen, Zensus 46,7 %, Blocktyp 37,6 %, Nachbarn 23,8 %. Potsdam hat kein Gegenstück zur Berliner Gebäudealterskarte 1992/93 und keine ausgerollte Luftbildklammer.

**Lesart.** Die Quoten sind nicht mit Berlin vergleichbar und gelten nicht für die ganze Stadt:
- Die Wikipedia-Prüfgebäude sind Denkmale, fast alle vor 1919, meist in Altbau-Zellen, in denen der Zensus selbst fast nur „vor 1919“ zeigt. Dort ist die Klasse leicht zu treffen.
- Der Wikidata-Satz sind ebenfalls Denkmale, darunter viele Schlösser, Kirchen und Parkbauten ohne Wohnraum. Ohne Stufe 1 bekommen solche Gebäude oft keine Klasse (Stufe 6), weil der Zensus nur Gebäude mit Wohnraum zählt; das zeigt, wofür Stufe 1 gebraucht wird, nicht wie gut sie ist. Er überschneidet sich mit dem Wikipedia-Satz (Zahl oben).
- Die Bornstedter Referenz deckt nur einen Stadtteil ab; viele ihrer Spannen liegen über einer Klassengrenze („mehrdeutig“) und zählen als Treffer, wenn eine der beiden Klassen stimmt.
- Für 1919 bis 1990 gibt es kaum unabhängige Prüfgebäude (1919–1948: wenige Wikipedia-Einträge, 1949–1990: höchstens einzelne). Dort bleibt nur die Gegenprobe Zensus gegen Blocktyp.
- Das Maß selbst ist großzügiger als in Berlin: acht Mikrozensus-Klassen statt Jahrzehnten, eine davon 30 Jahre breit (1949–1978), und eine Spanne über eine Klassengrenze zählt als Treffer, wenn eine der beiden Klassen stimmt. Ob Potsdam unter Berlins 61,4 % liegt (Erwartung im Bauplan), lässt sich mit diesem Maß nicht prüfen; die Quoten hier sind nicht „besser als Berlin“.
- Für die Seite heißt das: Jede Angabe bleibt „geschätzt“, und die Methodenseite nennt die Quoten zusammen mit n und Prüfsatz, nie als eine Zahl.

## Summenprüfung gegen den Zensus (Korrektur 7)

Stufe 4 verteilt die Zensuszahlen selbst; ein Vergleich der Stufe 4 mit dem Zensus prüft nichts und steht hier nur zur Information. Geprüft werden die Stufen 1 bis 3, die ohne Zensus entstehen: Je Stadtteil und Klasse darf ihre Zahl die Zensuszahl höchstens um 10 % übersteigen. Weil „–“-Werte als 0 zählen, gilt eine Überschreitung als erklärbar, wenn sie unter 110 % von Zensusklasse plus Geheimhaltungslücke des Stadtteils bleibt. Gezählt werden nur Gebäude mit Wohnraum, denn nur diese zählt der Zensus (Nachtrag N3; Schlösser und Kirchen aus Stufe 1 gehören nicht hinein). Der Vergleich mit der Potsdamer Baualter-Statistik (H4) steht im nächsten Abschnitt.

| Stadtteil | Klasse | Stufe 1–3 (Gebäude) | Zensus (gerundet) | Lücke Stadtteil (gerundet) | Anteil | Urteil |
|---|---:|---:|---:|---:|---:|---:|
| 21 Nauener Vorstadt | vor 1919 | 12 | 230 | 50 | 5 % | eingehalten |
| 21 Nauener Vorstadt | 1919–1948 | 1 | 130 | 50 | 1 % | eingehalten |
| 23 Berliner Vorstadt | vor 1919 | 2 | 160 | 70 | 1 % | eingehalten |
| 31 Brandenburger Vorstadt | vor 1919 | 1 | 320 | 40 | 0 % | eingehalten |
| 32 Potsdam West | 1949–1978 | 31 | 180 | 60 | 17 % | eingehalten |
| 41 Historische Innenstadt | vor 1919 | 17 | 690 | 70 | 2 % | eingehalten |
| 41 Historische Innenstadt | 1919–1948 | 2 | 50 | 70 | 4 % | eingehalten |
| 43 Zentrum Ost und Nuthepark | vor 1919 | 1 | 10 | 20 | 10 % | eingehalten |
| 43 Zentrum Ost und Nuthepark | 1949–1978 | 54 | 90 | 20 | 57 % | eingehalten |
| 44 Hauptbahnhof und Brauhausberg Nord | vor 1919 | 1 | 10 | 10 | 11 % | eingehalten |
| 51 Klein Glienicke | vor 1919 | 4 | 20 | 30 | 19 % | eingehalten |
| 52 Babelsberg Nord | vor 1919 | 8 | 650 | 240 | 1 % | eingehalten |
| 52 Babelsberg Nord | 1919–1948 | 2 | 540 | 240 | 0 % | eingehalten |
| 63 Schlaatz | 1979–1990 | 131 | 400 | 0 | 33 % | eingehalten |
| 64 Waldstadt I und Industriegelände | 1949–1978 | 54 | 280 | 40 | 20 % | eingehalten |
| 65 Waldstadt II | 1979–1990 | 125 | 460 | 10 | 27 % | eingehalten |
| 71 Stern | 1949–1978 | 148 | 670 | 150 | 22 % | eingehalten |
| 72 Drewitz | 1979–1990 | 62 | 210 | 90 | 29 % | eingehalten |
| 73 Kirchsteigfeld | 1991–2000 | 210 | 270 | 10 | 77 % | eingehalten |

Geprüft: 19 Paare aus Stadtteil und Klasse; eingehalten 19, nur mit Lücke erklärbar 0, überschritten 0.

Hinweis: ALKIS zählt Umrisse, der Zensus Gebäude (ein Plattenbau-Riegel kann ein Umriss oder mehrere Gebäude sein). Eine Überschreitung kann daher auch aus der Zählweise kommen.

### Blocktyp-Gebiete gegen die Zensus-Jahrzehnte ihrer Zellen

Je Gebiet: Zensus-Gebäude (Jahrzehnte) in den 100-m-Zellen, in denen Blocktyp-Gebäude liegen, und der Anteil in den Jahrzehnten der belegten Bauzeit. Unabhängig von Stufe 3 (andere Datei, andere Klassengrenzen).

| Gebiet | Bauzeit (Beleg) | Klasse | Blocktyp-Gebäude | Zellen | Zensus-Gebäude (gerundet) | Jahrzehnte der Bauzeit | Anteil darin | Fläche Polygon (ha) | Fläche Beleg (ha) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Waldstadt I | 1960–1964 | 1949–1978 | 54 | 32 | 230 | 1960–1969 | 80 % | 22,5 | 44,9 |
| Potsdam-West und Auf dem Kiewitt | 1966–1975 | 1949–1978 | 31 | 20 | 140 | 1960–1969, 1970–1979 | 63 % | 12,1 | 35 |
| Am Stern | 1971–1979 | 1949–1978 | 148 | 80 | 600 | 1970–1979 | 79 % | 54,3 | 114,3 |
| Zentrum Ost | 1972–1975 | 1949–1978 | 54 | 33 | 170 | 1970–1979 | 44 % | 22,7 | 33,5 |
| Waldstadt II | 1977–1986 | 1979–1990 | 125 | 63 | 460 | 1970–1979, 1980–1989 | 92 % | 43,3 | 87,3 |
| Am Schlaatz | 1980–1987 | 1979–1990 | 131 | 49 | 390 | 1980–1989 | 99 % | 46,5 | 76,2 |
| Drewitz | 1986–1991 | 1979–1990 | 62 | 26 | 260 | 1980–1989, 1990–1999 | 90 % | 19 | 37,7 |
| Kirchsteigfeld | 1990–1999 | 1991–2000 | 210 | 41 | 390 | 1990–1999 | 66 % | 35 | – |

Die Polygonfläche umfasst nur die Cluster der Bauform, die Belegfläche das ganze Neubaugebiet.

### Kaskade gesamt gegen den Zensus, Stadt (Gebäude mit Wohnraum)

Stufe 4 trifft die Zensuszahlen je Zelle nach Bauart, das ist für sie keine Prüfung. Die Summe über alle Stufen weicht trotzdem ab, aus zwei Gründen: Stufe 5 (Nachbarn) datiert Wohngebäude über der Zensuszahl ihrer Zelle, vor allem in der Altstadt, wo ein Block in viele ALKIS-Umrisse zerfällt; und ein Plattenbau-Riegel ist oft ein Umriss, aber mehrere Zensus-Gebäude, das verkleinert die Zahl der zu verteilenden Plätze. Folge für die Karte: Bauten vor 1919 erscheinen häufiger, DDR-Bauten seltener als im Zensus.

| Klasse | Zensus (gerundet) | Kaskade gesamt | Abweichung | davon Stufe 3 | Stufe 4 | Stufe 5 |
|---|---:|---:|---:|---:|---:|---:|
| vor 1919 | 3.250 | 4.585 | +41 % | 0 | 3.277 | 1.262 |
| 1919–1948 | 3.970 | 4.154 | +5 % | 0 | 3.533 | 616 |
| 1949–1978 | 2.570 | 1.964 | -23 % | 287 | 1.456 | 221 |
| 1979–1990 | 1.710 | 1.110 | -35 % | 318 | 710 | 82 |
| 1991–2000 | 3.350 | 3.451 | +3 % | 210 | 2.854 | 387 |
| 2001–2010 | 3.060 | 3.069 | +0 % | 0 | 2.702 | 367 |
| 2011–2019 | 2.800 | 2.765 | -1 % | 0 | 2.426 | 339 |
| ab 2020 | 360 | 425 | +18 % | 0 | 336 | 89 |

## Plausibilität: Baualter-Statistik der LHP (H4)

Die Landeshauptstadt führt eine Reihe „Gebäude nach Baualter“ (Wohngebäude, Stand jeweils 31.12.) in vier Gruppen: vor 1949, 1949 bis 1970, 1971 bis 1990, ab 1991. Die Mikrozensus-Klassen passen nur in drei Gruppen darauf (die Klasse 1949–1978 schneidet die Grenze 1970/71). Verglichen werden die Stadtsummen: Zensus 2022 (Summe der Klassen über die 100-m-Zellen, ohne Geheimhaltungslücke) gegen die LHP-Zeile 2022, die Kaskade (alle Stufen, Gebäude mit Wohnraum, ALKIS-Snapshot 2026) gegen die LHP-Zeile 2025. Nur zur Plausibilität, keine Schwelle: Die Zählweisen unterscheiden sich (Wohngebäude, Gebäude mit Wohnraum, ALKIS-Umrisse).

| Gruppe | LHP 2022 | Zensus 2022 (gerundet) | Zensus zu LHP | LHP 2025 | Kaskade (mit Klasse) | Kaskade zu LHP |
|---|---:|---:|---:|---:|---:|---:|
| vor 1949 | 8.445 | 7.220 | -14 % | 8.441 | 8.739 | +4 % |
| 1949–1990 | 4.517 | 4.280 | -5 % | 4.514 | 3.074 | -32 % |
| ab 1991 | 8.606 | 9.570 | +11 % | 9.065 | 9.710 | +7 % |
| zusammen | 21.568 | 21.070 | -2 % | 22.020 | 21.523 | -2 % |

**Lesart.** In der Gruppe 1949–1990 liegt die Kaskade -32 % neben der Statistik der LHP. Das ist dieselbe Schieflage wie gegen den Zensus (Abschnitt davor): Plattenbauten sind oft ein ALKIS-Umriss, aber mehrere gezählte Gebäude, und Stufe 5 füllt Altbau-Blöcke mit „vor 1919“ auf. Auf der Karte erscheinen DDR-Bauten daher seltener, Altbauten häufiger, als es Gebäude gibt.

Gebäude mit Wohnraum im ALKIS-Snapshot: 22.017, davon ohne Klasse (Stufe 6): 494. Quelle: © Landeshauptstadt Potsdam, Gebäude nach Baualter seit 1999 (Open-Data-Portal), dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung: Gruppen zusammengefasst).

