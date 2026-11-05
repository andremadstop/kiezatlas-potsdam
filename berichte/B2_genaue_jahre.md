# B2 Genaue Jahre (Kaskadenstufe 1), Stand 05.11.2026

Skript `skripte/22_jahre_genau.py`, Tabelle `auswertung.jahr_beleg`, Bezug ist der Snapshot
`auswertung.gebaeude_stand_20261105`. Zählungen je Lauf: `berichte/B2_stand.json`. Prüfung:
`pruefen/B2_jahre.py`. Der Bericht nennt nur Zählungen, MIDAS-IDs und Regeln, keine Adressen und keine
Beschreibungstexte.

## Ergebnis

| | Gebäude |
|---|---:|
| genau datiert, nur Prüfspalte (Wikipedia, `art = 'bau'`, `genau`) | 343 |
| genau datiert, für die Kaskade zugelassen (`nur_pruefung = false`) | **0** |
| mit irgendeinem Baujahr (auch ungenau, „vor 1874“, Spannen), Prüfspalte | 385 |
| als Baudenkmal gekennzeichnet (BLDAM, ohne Jahr) | 2.319 |
| davon Mitglied eines Ensembles mit mehr als 4 Gebäuden | 783 |

Die Erwartung im Bauplan lag bei rund 1.000 bis 2.500 genau datierten Gebäuden. Beide Zahlen liegen deutlich
darunter, aus zwei Gründen:

- Die Quellen, die in die Kaskade dürfen, fehlen: DDB-API (H8, kein Key in `eingang/ddb-key`) und Wikidata
  (H9, keine CSV in `eingang/`). Die Leser dafür sind gebaut bzw. vorbereitet, siehe unten.
- Wikipedia nennt in der Liste der Baudenkmale nur bei 462 von 1.822 Zeilen überhaupt ein Jahr in der
  Form, die die Regeln sicher lesen. Die Regeln sind bewusst streng; sie wurden nicht gelockert, um die
  Erwartung zu erreichen.

Verteilung der 343 genau datierten Gebäude (Prüfspalte) nach Bauzeit: 1700–1749: 15, 1750–1799: 196,
1800–1849: 19, 1850–1899: 77, 1900–1949: 35, ab 1950: 1. Das sind fast nur Denkmale vor 1919, also keine
Referenz für Neubauten (Prüfbericht Korrektur 7, wichtig für B3 und den Holdout in B4).

## Quellen im Lauf

| Quelle | Zeilen | Stand | `nur_pruefung` |
|---|---:|---|---|
| BLDAM Denkmalliste Potsdam (PDF, Teil D) | 2.393 | 1.660 IDs, 1.497 zugeordnet, 43 Ensembles > 4 Gebäude | ja (Lizenz offen, E8) |
| Wikipedia, Liste der Baudenkmale (27 Teillisten) | 497 | 438 Zeilen zugeordnet (375 über ID, 63 über Koordinate) | ja (CC BY-SA, Korrektur 5) |
| Wikidata (Handexport H9) | 0 | blockiert: `eingang/wikidata_potsdam_baujahr.csv` fehlt | nein (CC0) |
| DDB-API (H8) | 0 | blockiert: `eingang/ddb-key` fehlt; Leser nicht gebaut, weil Antwortformat und API-Bedingungen erst mit Key prüfbar sind | nein (CC0, vorher bestätigen) |
| OSM `start_date` (H5) | 0 | blockiert: kein Extrakt unter `eingang/osm/` | ja (E1) |

BLDAM-Zuordnung über die Adresse aus B0: 3.189 Adressen, 262 ohne Treffer in `gebaeude_adresse`, 50 mehrdeutig
(gleicher Straßenname in zwei Ortsteilen, nicht zugeordnet), 3 nur mit Nebengebäuden, 4 über den Ort entschieden.

Wikipedia-Zeilen nach Art: `bau` 366, `umbau` 62, `unklar` 35. Nach Regel: Feld „Baujahr“ 260, Zusatz im
Feld (Umbau, Aufstockung) 18, Satz mit Bauverb 132, Satz mit Umbau 43, nur Jahreszahl 10. 14 Zeilen sind
Ensembles (Park, Siedlung, Friedhof) und bekommen kein Jahr, 10 Zeilen fanden kein Gebäude.

## Regeln (Umbau nie als Baujahr)

- Feld „Baujahr“: Das erste Jahr am Anfang ist der Bau. Was danach kommt, ist ein eigener Beleg: mit Jahr und
  Umbauwort `umbau`, mit Jahr ohne Umbauwort `unklar`. Steht nach dem Jahr ohne weitere Jahreszahl ein
  Umbauwort, ist das Jahr selbst ein Umbau. Bei „rekonstruiert“ oder „Wiederaufbau“ ist das genannte Jahr
  das des Vorgängers und wird `unklar`, denn das heutige Gebäude ist jünger.
- „vor 1874“ ergibt nur `jahr_bis`, „nach 1873“ und „ab“ nur `jahr_von`; „um“, „ca.“, „ab“, „seit“, „bis“
  sind nie `genau`.
- Sätze: nur die ersten drei, Klammern entfernt, nur der erste Satz mit Bauverb. Ein Satz mit Umbauwort gibt
  `umbau`. Ist das Subjekt ein Bauteil (Säulengang, Turm, Anbau …), wird der Beleg `unklar`.
- `genau` heißt: Spanne höchstens 3 Jahre, kein Umbau, keine Unschärfe.
- Ensembles: Bezeichnung beginnt mit Park, Siedlung, Friedhof usw. → kein Jahr; Denkmal-ID mit mehr als
  4 Gebäuden → kein Jahr aus der Denkmalzeile. Haben mehrere Wikipedia-Zeilen dieselbe ID, wird jede nur
  über ihre eigene Koordinate zugeordnet.

## Handstichprobe (Abnahme „Umbau nie als Baujahr“)

Je 10 Einträge mit `art = 'bau'` aus den Regeln Feld und Satz, gezogen mit festem Seed. Die Texte liegen
nur intern unter `$KIEZ_DATEN/wikipedia_denkmale/2026-11-05/stichproben/` (CC BY-SA, teils mit Adressen).
Die ersten drei Durchgänge fanden Fehler; die Regeln wurden korrigiert und die Stichprobe neu gezogen:

| Durchgang | Seed | Ergebnis | Korrektur |
|---|---:|---|---|
| 1 | 22 | 19/20 | Klammerzusatz mit Erneuerungsjahr lief in die Bauspanne → Feldregel Kopf/Zusatz, „erneuert“ als Umbauwort |
| 2 | 2205 | 18/20 | „entstand ab 1744“ (Park) als genau; Jahr eines Säulengangs als Baujahr der Kirche → „ab/seit/bis“ ungenau, Ensemble-Bezeichnung nie mit Jahr, Bauteil-Subjekt `unklar` |
| 3 | 2206 | 20/20 Jahre, 1 Zuordnungsfehler | zwei Wikipedia-Zeilen mit derselben ID (09156161) hingen an denselben Gebäuden → Zuordnung über die Koordinate |
| 4 | 2207 | **20/20** | endgültiger Code, Abnahme |

Durchgang 4 im Einzelnen (Urteil: Jahr und Art stimmen mit dem Text überein):

| Nr. | MIDAS-ID | Regel | Jahr | genau | Urteil |
|---:|---|---|---|---|---|
| 1 | 09155917 | Feld | 1753 | ja | richtig |
| 2 | 09155195 | Feld | 1783 | ja | richtig (Aufstockung ohne Jahr bleibt außen vor) |
| 3 | 09156646 | Feld | 1864–1866 | ja | richtig |
| 4 | 09155565 | Feld | 1782 | ja | richtig (Aufstockung ohne Jahr) |
| 5 | 09156148 | Feld | 1893–1894 | ja | richtig |
| 6 | 09155183 | Feld | 1779 | ja | richtig |
| 7 | 09156149 | Feld | 1938–1939 | ja | richtig |
| 8 | 09155040 | Feld | 1771 | ja | richtig (späterer Umbau steht im Text, nicht im Feld) |
| 9 | 09155261 | Feld | 1736 | ja | richtig |
| 10 | 09155794 | Feld | 1858–1885 | nein | richtig (Bauzeit einer Häusergruppe, ungenau) |
| 11 | 09156552 | Satz | 1874–1875 | ja | richtig (Umbauten in späteren Sätzen nicht gezählt) |
| 12 | 09155010 | Satz | 1753–1755 | ja | richtig |
| 13 | ohne ID | Satz | 1768–1769 | ja | richtig (Umbauten 1884/85 nicht als Bau) |
| 14 | 09156115 | Satz | 1937 | ja | richtig |
| 15 | 09156650 | Satz | 1893–1894 | ja | richtig |
| 16 | ohne ID | Satz | 1768–1769 | ja | richtig |
| 17 | 09156772 | Satz | 1894–1900 | nein | richtig (zwei Bauabschnitte) |
| 18 | 09156116 | Satz | 1935 | ja | richtig |
| 19 | 09155233 | Satz | 1754–1755 | ja | richtig |
| 20 | 09156118 | Satz | 1938–1943 | nein | richtig |

## Bekannte Restfehler und Hinweise für B4

- 1 Gebäude trägt zwei verschiedene genaue Baujahre aus zwei benachbarten IDs (09155010, 09155011), die über
  die Adresse auf dasselbe ALKIS-Gebäude fallen. B4 sollte bei mehreren abweichenden Bau-Belegen kein
  genaues Jahr setzen.
- Denkmal-Kennzeichen für B4 (Korrektur 6, Denkmale dürfen ein genaues Jahr tragen): `quelle LIKE 'BLDAM%'`.
  Ensemble-Mitglieder tragen den Zusatz „(Ensemble, mehr als 4 Gebäude)“ in `quelle`.
- Kein Wert aus B2 darf derzeit in `auswertung.gebaeude_jahr` oder in veröffentlichte Dateien: Wikipedia und
  OSM sind nur Prüfspalte, BLDAM hat keine geklärte Lizenz. Freigegeben für die Kaskade wären nur Wikidata-
  und DDB-Zeilen (`nur_pruefung = false`), die es noch nicht gibt.

## Abrufe

In diesem Lauf kein Netzabruf. Die Wikipedia-Seiten wurden in einem früheren B2-Lauf am 05.11.2026 abgerufen
(29 Anfragen, robots.txt zuerst, 5 s Abstand, im Abrufprotokoll). Das BLDAM-PDF stammt aus dem Erkundungslauf
und steht nicht im Abrufprotokoll (Altfall, H10).
