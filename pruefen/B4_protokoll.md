# B4: Protokoll für Rücktest und Summenprüfung (vor dem Lauf festgelegt)

Stand 05.11.2026. Festgelegt und committet, bevor `skripte/24_jahre_kaskade.py rechnen` und `ruecktest`
zum ersten Mal laufen. Nach dem Lauf wird an Regeln, Schwellen und Prüfgebäuden nichts mehr verändert;
gefundene Fehler im Code werden behoben und im Bericht genannt, die Regeln bleiben.

## Kaskade (fest)

| Stufe | Quelle | Regel |
|---|---|---|
| 1 | `auswertung.jahr_beleg` (B2) | nur `nur_pruefung = false`, `genau`, `art = 'bau'`, Quelle ohne OSM/Wikipedia, Lizenz ohne ODbL/BY-SA/„ungeklärt“. Klasse, wenn die Spanne in einer Klasse liegt. Einzeljahr nur bei `jahr_von = jahr_bis` und nur für Gebäude ohne Wohnraum oder Denkmale aus freigegebener Quelle (Korrektur 6). |
| 2 | `auswertung.jahr_klammer` (B3) | nur Quellen ohne „nicht ausgerollt“; Klasse, wenn die Klammer in einer Klasse liegt |
| 3 | `config/blocktypen.geojson` | Gebäude mit Wohnraum, Punkt im Umriss im Gebiet, Bauform des Gebiets (Objekthöhe, Dachform); Klasse = Mikrozensus-Klasse mit den meisten Jahren der belegten Bauzeit |
| 4 | Zensus 2022, Mikrozensus-Klassen, 100 m | je Zelle Anteile; Lücke (insgesamt − Σ Klassen) auf die „–“-Klassen nach dem Rest der 1-km-Zelle (nur 1-km-Zellen ganz in der Stadt), sonst nach dem Rest aller solcher 1-km-Zellen; Kapazität je Klasse = Anteil × min(ALKIS-Wohngebäude, Zensus-Gebäude), größter Rest; Stufe-1-bis-3-Gebäude verbrauchen ihre Klasse; übrige Gebäude gierig nach Formwahrscheinlichkeit (naiver Bayes über Dachform, Höhe, Grundfläche, Bauweise, Funktionsgruppe, gelernt in Zellen mit einer Klasse ≥ 85 %, ohne Lücke, ≥ 4 Gebäude) |
| 5 | Nachbarn | Hauptgebäude ohne Stufe 1–4 (auch Wohngebäude ohne Zensuszelle oder über der Zensuszahl): häufigste Klasse der bis zu 10 nächsten Gebäude aus Stufe 1–4 im Umkreis von 100 m, mindestens 3; Gleichstand: Klasse des nächsten |
| 6 | nicht datiert | Nebengebäude (Liste `NEBEN` im Skript, E5) und alles ohne Ergebnis |

Gebäude mit Wohnraum: ALKIS-Funktion enthält „wohn“ oder ist „Forsthaus“. Nebengebäude: Garagen,
Lauben („Gebäude zur Freizeitgestaltung“), Schuppen, Gartenhäuser, Parkbauten, Überdachungen, Umformer,
Durchfahrten, Gewächshäuser, Schornsteine, Toiletten, Keller, Tanks, Silos, Masten, Kräne, „Nach
Quellenlage nicht zu spezifizieren“ und „Land- und forstwirtschaftliches Betriebsgebäude“ (beide im
Median 25 m² Grundfläche), „Gebäude für Vorratshaltung“.

## Prüfgebäude (fest, gehen in keine Stufe ein)

1. **Wikipedia-Denkmalliste** (Prüfspalte aus B2, CC BY-SA 4.0, nur intern): Zeilen mit `genau`,
   `art = 'bau'`; je Gebäude Spanne [kleinstes `jahr_von`, größtes `jahr_bis`]; Gebäude mit Spanne über
   20 Jahre fallen heraus.
2. **B3-Referenz Bornstedt** (Sichtprüfung der Luftbilder, `$KIEZ_DATEN/luftbild_lgb/2026-11-05/referenz/referenz.csv`,
   nur intern): ohne `unklar = 1`. `k_ref` = erste Befliegung mit Gebäude; Spanne [Befliegung k−1, Befliegung k]
   mit den Befliegungen 1953, 1996, 2007, 2012, 2015, 2018, 2021, 2024; `k_ref = 0` oder
   `frueher_moeglich = 1`: untere Grenze offen.

## Maße (fest)

- **Treffer:** geschätzte Klasse überschneidet die bekannte Spanne.
- **Abstand:** Jahre zwischen Klassenspanne und bekannter Spanne, 0 bei Treffer. „vor 1919“ ist nach
  unten, „ab 2020“ nach oben offen.
- Ausgewiesen je Prüfsatz: je Stufe und je bekannter Bauzeit (Klasse der Spanne, sonst „mehrdeutig“),
  jeweils n, Zahl ohne Klasse (Stufe 6), Treffer, Median des Abstands, Median des Abstands der Fehlgriffe.
  Keine Gesamtquote über beide Sätze.
- Zusatz: Stufe 4 ohne Vorgabe gegen die Blocktyp-Klasse (Schätzung gegen Schätzung, kein Rücktest).

## Summenprüfung (fest, Korrektur 7)

- Nur Stufen 1 bis 3 gegen den Zensus (Mikrozensus-Klassen, 100-m-Zellen mit Mittelpunkt im Stadtteil):
  je Stadtteil und Klasse „eingehalten“, wenn Zahl ≤ 1,1 × Zensus; „nur mit Geheimhaltungslücke
  erklärbar“, wenn ≤ 1,1 × (Zensus + Lücke des Stadtteils); sonst „überschritten“.
- Je Blocktyp-Gebiet: Anteil der Zensus-Gebäude (Jahrzehnte) in den Zellen des Gebiets, die in die
  Jahrzehnte der belegten Bauzeit fallen.
- Stufe 4 gegen den Zensus nur zur Information (tautologisch).
- Potsdamer Baualter-Statistik (H4): blockiert, Datei fehlt.

## Erwartung (keine Zielvorgabe)

Unter Berlins 61,4 % (visinage, mit Gebäudealterskarte 1992/93 und Luftbilddatierung).
