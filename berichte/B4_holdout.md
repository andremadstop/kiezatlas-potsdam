# B4: Kaskade der Gebäudejahre, Rücktest und Summenprüfung

Stand 2026-11-05. Erzeugt von `skripte/24_jahre_kaskade.py ruecktest`. Regeln vorab festgelegt in `pruefen/B4_protokoll.md`. Dieser Bericht enthält nur Zählungen, keine Gebäudekennungen und keine Adressen. Zensuswerte je Stadtteil sind auf 10 gerundet; sie sind durch das Geheimhaltungsverfahren (Cell-Key) verändert, Summen aus vielen Zellen sind absolut ungenauer als jede einzelne Zelle.

**Korrekturen nach Lauf 1** (Codefehler, Regeln unverändert; Lauf 1 liegt als `berichte/B4_holdout_lauf1.md` bei):

1. Die Gebietshülle der Blocktypen enthielt nicht alle Gebäude ihres Clusters (`ST_ConcaveHull` über Umrisse); jetzt Hülle vereinigt mit den Umrissen, dann 15 m Rand. Lauf 1: Am Stern 133 statt 148 Gebäude.
2. Die Jahrzehnte-Gegenprobe zählte „Waldstadt II“ bei „Waldstadt I“ mit (Teilwortsuche); jetzt genauer Gebietsname.

## Abdeckung der Kaskade

| Stufe | Gebäude | davon mit Wohnraum | davon Nebengebäude |
|---|---:|---:|---:|
| 1 genaues Jahr (B2, freigegeben) | 0 | 0 | 0 |
| 2 Luftbildklammer (B3, ausgerollt) | 0 | 0 | 0 |
| 3 Blocktyp Großsiedlung | 816 | 816 | 0 |
| 4 Zensus-Verteilung | 17.337 | 17.337 | 0 |
| 5 Nachbarn | 8.507 | 3.364 | 0 |
| 6 nicht datiert | 25.649 | 500 | 22.537 |
| Summe | 52.309 | 22.017 | 22.537 |

- Stufe 1: 0 Gebäude, Stufe 2: 0 Gebäude. Stufe 1 nimmt nur Zeilen aus `auswertung.jahr_beleg` ohne `nur_pruefung` (OSM, Wikipedia und BLDAM-Liste sind Prüfwerte; DDB-API H8 und Wikidata-Export H9 fehlen, BLDAM-Lizenz offen, E8). Stufe 2 nimmt nur ausgerollte Klammern (B3: nicht ausgerollt). Gebäude mit Einzeljahr `j`: 0.
- Wohngebäude in Zellen ohne Zensuswert: 1535; Wohngebäude über der Zensuszahl ihrer Zelle (mehr ALKIS-Umrisse als Zensus-Gebäude, auch Neubau nach dem 15.05.2022): 2369. Beide gehen an Stufe 5.
- Geheimhaltungslücken der 100-m-Zellen aufgefüllt aus: {'ohne_luecke': 1699, 'stadt_rest': 255, 'km_rest': 915} (km_rest = Rest der 1-km-Zelle, nur Zellen ganz in der Stadt; stadt_rest = Rest aller solcher 1-km-Zellen; eigene_klassen = Klassen der Zelle selbst).
- Formmodell gelernt in 701 reinen Zellen (eine Klasse ≥ 85 %, keine Lücke, mindestens 4 Gebäude).

## Rücktest

Die Prüfgebäude gehen in keine Stufe ein: Wikipedia-Jahre sind nur Prüfspalte (Korrektur 5), die B3-Referenz stammt aus einer Sichtprüfung von Luftbildern. Gemessen wird die Klasse aus der Kaskade gegen die bekannte Bauzeit. **Treffer** = geschätzte Klasse überschneidet die bekannte Spanne. **Abstand** = Jahre zwischen Klassenspanne und bekannter Spanne (0 bei Treffer; „vor 1919“ und „ab 2020“ sind nach einer Seite offen).

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

### Gegenprobe: Zensus-Verteilung allein an den Blocktyp-Gebäuden

Stufe 4 ohne Vorgabe aus Stufe 3 gerechnet und gegen die Blocktyp-Klasse gestellt. Beide sind Schätzungen, das ist kein Rücktest gegen bekannte Jahre, sondern zeigt, wie weit Zensus und Blocktyp übereinstimmen.

| Menge | n | ohne Zensusklasse | gleiche Klasse | Median Abstand (J.) | Median Abstand der Abweichungen (J.) |
|---|---:|---:|---:|---:|---:|
| Blocktyp-Gebäude | 816 | 52 | 601 von 764 (78,7 %) | 0 | 11 |

Zum Vergleich Berlin (visinage, Methodenvorbild): 61,4 % Treffer über alle Schätzungen, Zensus 46,7 %, Blocktyp 37,6 %, Nachbarn 23,8 %. Potsdam hat kein Gegenstück zur Berliner Gebäudealterskarte 1992/93 und keine ausgerollte Luftbildklammer.

**Lesart.** Die Quoten sind nicht mit Berlin vergleichbar und gelten nicht für die ganze Stadt:
- Die Wikipedia-Prüfgebäude sind Denkmale, fast alle vor 1919, meist in Altbau-Zellen, in denen der Zensus selbst fast nur „vor 1919“ zeigt. Dort ist die Klasse leicht zu treffen.
- Die Bornstedter Referenz deckt nur einen Stadtteil ab; viele ihrer Spannen liegen über einer Klassengrenze („mehrdeutig“) und zählen als Treffer, wenn eine der beiden Klassen stimmt.
- Für 1919 bis 1990 gibt es kaum unabhängige Prüfgebäude (1919–1948: wenige Wikipedia-Einträge, 1949–1990: höchstens einzelne). Dort bleibt nur die Gegenprobe Zensus gegen Blocktyp.
- Das Maß selbst ist großzügiger als in Berlin: acht Mikrozensus-Klassen statt Jahrzehnten, eine davon 30 Jahre breit (1949–1978), und eine Spanne über eine Klassengrenze zählt als Treffer, wenn eine der beiden Klassen stimmt. Ob Potsdam unter Berlins 61,4 % liegt (Erwartung im Bauplan), lässt sich mit diesem Maß nicht prüfen; die Quoten hier sind nicht „besser als Berlin“.
- Für die Seite heißt das: Jede Angabe bleibt „geschätzt“, und die Methodenseite nennt die Quoten zusammen mit n und Prüfsatz, nie als eine Zahl.

## Summenprüfung gegen den Zensus (Korrektur 7)

Stufe 4 verteilt die Zensuszahlen selbst; ein Vergleich der Stufe 4 mit dem Zensus prüft nichts und steht hier nur zur Information. Geprüft werden die Stufen 1 bis 3, die ohne Zensus entstehen: Je Stadtteil und Klasse darf ihre Zahl die Zensuszahl höchstens um 10 % übersteigen. Weil „–“-Werte als 0 zählen, gilt eine Überschreitung als erklärbar, wenn sie unter 110 % von Zensusklasse plus Geheimhaltungslücke des Stadtteils bleibt. Der Vergleich mit der Potsdamer Baualter-Statistik (H4) ist blockiert: Die Datei fehlt in `eingang/`.

| Stadtteil | Klasse | Stufe 1–3 (Gebäude) | Zensus (gerundet) | Lücke Stadtteil (gerundet) | Anteil | Urteil |
|---|---:|---:|---:|---:|---:|---:|
| 32 Potsdam West | 1949–1978 | 31 | 180 | 60 | 17 % | eingehalten |
| 43 Zentrum Ost und Nuthepark | 1949–1978 | 55 | 90 | 20 | 59 % | eingehalten |
| 63 Schlaatz | 1979–1990 | 131 | 400 | 0 | 33 % | eingehalten |
| 64 Waldstadt I und Industriegelände | 1949–1978 | 54 | 280 | 40 | 20 % | eingehalten |
| 65 Waldstadt II | 1979–1990 | 125 | 460 | 10 | 27 % | eingehalten |
| 71 Stern | 1949–1978 | 148 | 670 | 150 | 22 % | eingehalten |
| 72 Drewitz | 1979–1990 | 62 | 210 | 90 | 29 % | eingehalten |
| 73 Kirchsteigfeld | 1991–2000 | 210 | 270 | 10 | 77 % | eingehalten |

Geprüft: 8 Paare aus Stadtteil und Klasse; eingehalten 8, nur mit Lücke erklärbar 0, überschritten 0.

Hinweis: ALKIS zählt Umrisse, der Zensus Gebäude (ein Plattenbau-Riegel kann ein Umriss oder mehrere Gebäude sein). Eine Überschreitung kann daher auch aus der Zählweise kommen.

### Blocktyp-Gebiete gegen die Zensus-Jahrzehnte ihrer Zellen

Je Gebiet: Zensus-Gebäude (Jahrzehnte) in den 100-m-Zellen, in denen Blocktyp-Gebäude liegen, und der Anteil in den Jahrzehnten der belegten Bauzeit. Unabhängig von Stufe 3 (andere Datei, andere Klassengrenzen).

| Gebiet | Bauzeit (Beleg) | Klasse | Blocktyp-Gebäude | Zellen | Zensus-Gebäude (gerundet) | Jahrzehnte der Bauzeit | Anteil darin | Fläche Polygon (ha) | Fläche Beleg (ha) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Waldstadt I | 1960–1964 | 1949–1978 | 54 | 32 | 230 | 1960–1969 | 80 % | 22,5 | 44,9 |
| Potsdam-West und Auf dem Kiewitt | 1966–1975 | 1949–1978 | 31 | 20 | 140 | 1960–1969, 1970–1979 | 63 % | 12,1 | 35 |
| Am Stern | 1971–1979 | 1949–1978 | 148 | 80 | 600 | 1970–1979 | 79 % | 54,3 | 114,3 |
| Zentrum Ost | 1972–1975 | 1949–1978 | 55 | 33 | 170 | 1970–1979 | 44 % | 22,7 | 33,5 |
| Waldstadt II | 1977–1986 | 1979–1990 | 125 | 63 | 460 | 1970–1979, 1980–1989 | 92 % | 43,3 | 87,3 |
| Am Schlaatz | 1980–1987 | 1979–1990 | 131 | 49 | 390 | 1980–1989 | 99 % | 46,5 | 76,2 |
| Drewitz | 1986–1991 | 1979–1990 | 62 | 26 | 260 | 1980–1989, 1990–1999 | 90 % | 19 | 37,7 |
| Kirchsteigfeld | 1990–1999 | 1991–2000 | 210 | 41 | 390 | 1990–1999 | 66 % | 35 | – |

Die Polygonfläche umfasst nur die Cluster der Bauform, die Belegfläche das ganze Neubaugebiet.

### Kaskade gesamt gegen den Zensus, Stadt (Gebäude mit Wohnraum)

Stufe 4 trifft die Zensuszahlen je Zelle nach Bauart, das ist für sie keine Prüfung. Die Summe über alle Stufen weicht trotzdem ab, aus zwei Gründen: Stufe 5 (Nachbarn) datiert Wohngebäude über der Zensuszahl ihrer Zelle, vor allem in der Altstadt, wo ein Block in viele ALKIS-Umrisse zerfällt; und ein Plattenbau-Riegel ist oft ein Umriss, aber mehrere Zensus-Gebäude, das verkleinert die Zahl der zu verteilenden Plätze. Folge für die Karte: Bauten vor 1919 erscheinen häufiger, DDR-Bauten seltener als im Zensus.

| Klasse | Zensus (gerundet) | Kaskade gesamt | Abweichung | davon Stufe 3 | Stufe 4 | Stufe 5 |
|---|---:|---:|---:|---:|---:|---:|
| vor 1919 | 3.250 | 4.574 | +41 % | 0 | 3.311 | 1.263 |
| 1919–1948 | 3.970 | 4.153 | +5 % | 0 | 3.538 | 615 |
| 1949–1978 | 2.570 | 1.965 | -23 % | 288 | 1.456 | 221 |
| 1979–1990 | 1.710 | 1.109 | -35 % | 318 | 710 | 81 |
| 1991–2000 | 3.350 | 3.453 | +3 % | 210 | 2.854 | 389 |
| 2001–2010 | 3.060 | 3.072 | +0 % | 0 | 2.704 | 368 |
| 2011–2019 | 2.800 | 2.766 | -1 % | 0 | 2.428 | 338 |
| ab 2020 | 360 | 425 | +18 % | 0 | 336 | 89 |

