# B3 Luftbild-Pilot Bornstedt: Ergebnis

Stand 05.11.2026. Erzeugt von `skripte/23_luftbild_pilot.py auswerten`. Protokoll, Stichprobe und
Trefferregel stehen in `pruefen/B3_protokoll.md` und wurden vor diesem Lauf festgelegt (Commits f482058, 67bffd5, 2683650).
Dieser Bericht enthält nur Zählungen, keine Gebäudekennungen.

## Entscheidung

- **Ausrollen: nein.** Hauptkriterium (Bauplan B3): Die automatische Klammer trifft
  bei 44 von 56 (78,6 %) Referenzgebäuden, die erst nach dem Flug vom 20.05.2012 zu sehen sind (Schwelle 80 %,
  mindestens 50 Gebäude).
- Nebenbedingung: Von den Referenzgebäuden, die 2012 schon zu sehen sind, datiert die Automatik 44 von 137 (32,1 %)
  fälschlich auf „nach 2012“ (zulässig höchstens 10 %).
- Folge: Die 2.374 Zeilen in `auswertung.jahr_klammer` tragen die Quelle „LGB DOP-Zeitreihe, Pilot Bornstedt (nicht ausgerollt)“.
  B4 nimmt nur Zeilen ohne den Zusatz „nicht ausgerollt“ als Kaskadenstufe.

## Referenz und Treffer

| Gruppe | Treffer (k_auto = k_ref) |
|---|---|
| erstmals ab 2015 zu sehen (k_ref ≥ 4), Hauptkriterium | 44 von 56 (78,6 %) |
| davon Wohngebäude | 42 von 54 (77,8 %) |
| davon übrige Hauptgebäude | 2 von 2 (100,0 %) |
| erstmals 2012 zu sehen (k_ref = 3, 2007 bis 2012) | 19 von 29 (65,5 %) |
| bis 2007 zu sehen, Stufe sicher (k_ref ≤ 2) | 25 von 78 (32,1 %) |
| k_ref ≥ 4, höchstens eine Stufe daneben | 51 von 56 (91,1 %) |

Treffer im Hauptkriterium je Los: Los 1: 11 von 13 (84,6 %), Los 2: 6 von 6 (100,0 %), Los 3: 9 von 13 (69,2 %), Los 4: 11 von 14 (78,6 %), Los 5: 7 von 10 (70,0 %).

Referenz: 200 Gebäude in 5 Losen, davon 7 unklar (nicht gewertet).
Sichtprüfung durch den Agenten auf denselben Bildern; gemessen ist „Automatik gegen Sichtprüfung“.

Verwechslungstafel (Zeile = Sichtprüfung k_ref, Spalte = Automatik k_auto, ohne unklar):

| k_ref \ k_auto | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 (1953) | 1 | 11 | 11 | 0 | 11 | 0 | 6 | 1 |
| 1 (1996) | 1 | 9 | 9 | 0 | 6 | 1 | 1 | 0 |
| 2 (2007) | 0 | 2 | 27 | 2 | 4 | 0 | 4 | 1 |
| 3 (2012) | 0 | 0 | 1 | 19 | 7 | 2 | 0 | 0 |
| 4 (2015) | 0 | 0 | 1 | 3 | 16 | 1 | 2 | 0 |
| 5 (2018) | 0 | 0 | 0 | 0 | 1 | 13 | 0 | 2 |
| 6 (2021) | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 2 |
| 7 (2024) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |

## Automatik

- Gebäude im Rahmen: 2.374, davon mit Klammer: 2.374.
- Verteilung k_auto (erste Befliegung mit Gebäude): 1953: 30, 1996: 254, 2007: 512, 2012: 387, 2015: 539, 2018: 238, 2021: 266, 2024: 148.
- Median der Klammerbreite (ohne „schon 1953“): 3 Jahre.
- Schwellen (95-%-Quantil der Nullverteilung) je Befliegung: 1953: 0,40, 1996: 0,32, 2007: 0,34, 2012: 0,31, 2015: 0,36, 2018: 0,36, 2021: 0,37.
- Median des Werts am eigenen Ort je Befliegung: 1953: 0,18, 1996: 0,18, 2007: 0,29, 2012: 0,31, 2015: 0,51, 2018: 0,50, 2021: 0,62.

## Gegenprobe Zensus 2022 (beschreibend, kein Abbruchkriterium)

- 100-m-Zellen mit Mittelpunkt in Bornstedt: 240, Gebäude mit Wohnraum insgesamt 2.277,
  davon 2000 bis 2009: 770, 2010 bis 2015: 509, 2016 und später: 248
  (zusammen ab 2010: 757). Werte mit Cell-Key-Verfahren, „–“ als 0 gezählt; Stichtag 15.05.2022.
- Automatik, Wohngebäude im Rahmen, erstmals 2015 bis 2021 zu sehen: 947;
  erstmals 2015 bis 2024: 1.077.
- Vergleich nur in der Größenordnung: ALKIS zählt Gebäudeteile (Reihenhäuser einzeln), der Zensus Gebäude mit
  Wohnraum; Flugjahre und Zensus-Klassen decken sich nicht (Bauten von 2010 bis Mai 2012 sind schon im Flug 2012).

## Lizenz

Luftbilder: © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung).
Zensus: © Statistisches Bundesamt (Destatis), Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0),
Daten verändert (eigene Berechnung).

