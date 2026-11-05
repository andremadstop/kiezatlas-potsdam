# B2 Genaue Jahre (Kaskadenstufe 1), Stand 05.11.2026 (Nachlauf N3: Wikidata eingelesen)

Skript `skripte/22_jahre_genau.py`, Tabelle `auswertung.jahr_beleg`, Bezug ist der Snapshot
`auswertung.gebaeude_stand_20261105`. Zählungen je Lauf: `berichte/B2_stand.json`. Prüfung:
`pruefen/B2_jahre.py`. Der Bericht nennt nur Zählungen, MIDAS-IDs und Regeln, keine Adressen und keine
Beschreibungstexte.

## Ergebnis

| | Gebäude |
|---|---:|
| genau datiert, nur Prüfspalte (Wikipedia, `art = 'bau'`, `genau`) | 343 |
| genau datiert, für die Kaskade zugelassen (`nur_pruefung = false`, Wikidata, CC0, Zuordnung über die Koordinate) | **106** |
| mit Wikidata-Jahr überhaupt (auch Jahrzehnt oder mehrere Jahre, nicht genau), veröffentlichter Weg | 150 |
| mit irgendeinem Baujahr (auch ungenau, „vor 1874“, Spannen), Prüfspalte | 385 |
| als Baudenkmal gekennzeichnet (BLDAM, ohne Jahr) | 2.319 |
| davon Mitglied eines Ensembles mit mehr als 4 Gebäuden | 783 |

Die Erwartung im Bauplan lag bei rund 1.000 bis 2.500 genau datierten Gebäuden. Beide Zahlen liegen deutlich
darunter, aus drei Gründen:

- Die DDB-API (H8) fehlt weiter (kein Key, das DDB-Formular ist defekt).
- Wikidata führt in Potsdam nur für 242 Denkmal-Objekte ein Erstellungsjahr (Handexport H9); nach dem
  Aussortieren von Nicht-Gebäuden und Rekonstruktionen bleiben 196 Zeilen, davon 120 mit genauem Jahr.
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
| Wikidata (Handexport H9, 05.11.2026 16:37) | 161 | 189 Zeilen mit Jahr (7 nur Jahrhundert verworfen), 176 Objekte; 161 über die eigene Koordinate zugeordnet, 27 ohne Gebäude (davon 6 ohne Koordinate, 7 nur bei Kleinbauten); 150 Gebäude, davon 106 genau | nein (CC0) |
| Wikidata, Zuordnung über BLDAM-ID (Gegenprobe Nachlauf) | 114 | 96 Objekte über die Denkmal-ID, 108 Gebäude; läuft über die Adressen der BLDAM-Liste | ja (Lizenz der BLDAM-Liste offen, E8) |
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
- In `auswertung.gebaeude_jahr` und in veröffentlichte Dateien dürfen nur Wikidata-Zeilen (seit N3) und künftig
  DDB-Zeilen (`nur_pruefung = false`). Wikipedia und OSM sind nur Prüfspalte, BLDAM hat keine geklärte Lizenz.

- Rekonstruktionen (zum Beispiel Stadtschloss/Landtag, Garnisonkirche): Wikidata kann dort das Jahr des
  Originals führen. Andre hat die bekannten Fälle beim Durchsehen der CSV aussortiert
  (`eingang/wikidata_potsdam_aussortiert.md`); die Stichprobe fand einen weiteren (Ausschlussliste im Skript).
  Das Skript erkennt solche Fälle nicht von selbst.

## Wikidata (Nachlauf N3)

Eingelesen mit `skripte/22_jahre_genau.py --quelle wikidata` aus `eingang/wikidata_potsdam_baujahr.csv`
(196 Zeilen, CC0 1.0, Abfrage `entwuerfe/2026-11-05-wikidata-abfrage-b2.rq`, Eigenschaft P2081 = BLDAM-Objektnummer).
Zählungen: `berichte/B2_stand.json`, Schlüssel `wikidata`.

Regeln:
- **Genauigkeit:** `precision` 9 (Jahr) und feiner ergibt ein genaues Jahr, 8 (Jahrzehnt) eine Spanne ohne
  `genau`, 7 (Jahrhundert) und gröber wird verworfen (7 Zeilen). Hat ein Objekt verschiedene Jahre, ist keines
  genau; gezählt werden verschiedene Spannen, nicht Zeilen (ein Objekt mit zwei Koordinaten und einem Jahr bleibt
  genau, Korrektur N3).
- **Ensembles:** nur, wenn die Bezeichnung mit Park, Garten, Friedhof, Siedlung, Allee, Platz, Anlage beginnt und
  keine Hausnummer trägt. Vorher fielen „… Allee 5“ oder „… Luisenplatz“ als Ensemble heraus (Teilwortsuche,
  Korrektur N3). Im Export sind keine Ensembles mehr; Andre hatte sie schon aussortiert.
- **Zuordnung (seit der Gegenprobe zum Nachlauf):** veröffentlicht wird nur die Zuordnung über die eigene
  Koordinate des Wikidata-Objekts: das Gebäude, in dessen Umriss der Punkt liegt, sonst das nächste Hauptgebäude
  bis 10 m mit mindestens 100 m² Grundfläche (7 Punkte lagen nur bei Kleinbauten und blieben ohne Gebäude,
  6 Objekte haben keine Koordinate). Die Zuordnung über die Denkmal-ID lief über die Adressen der BLDAM-Liste
  (B0); deren Lizenz ist offen (E8, § 87a UrhG), und die BLDAM-Liste ist laut `QUELLEN.md` nur intern. Sie
  steht deshalb nur noch als Prüfspalte in `jahr_beleg` (`quelle` „Wikidata, Zuordnung über BLDAM-ID (nur
  Prüfung)“, `nur_pruefung = true`), mit den Regeln aus N3: keine ID für mehrere Objekte, keine Ensemble-ID
  (mehr als 4 Gebäude, 4 Fälle), kein Widerspruch zwischen ID und Ort (Punkt mehr als 150 m von allen
  ID-Gebäuden, 3 Fälle), bei mehreren Gebäuden je ID nur Bauten ab 100 m² (2 Kleinbauten ausgelassen). Bei
  8 Objekten trifft die Koordinate ein anderes Gebäude als die ID. Die Handstichprobe N3 prüfte noch beide Wege;
  für den Koordinatenweg allein ist sie nicht wiederholt (offen).
- **Ausschlussliste** (`WD_AUSSCHLUSS` im Skript, mit Grund): Objekte, deren Erstellungsjahr nachweislich nicht
  das des heutigen Gebäudes ist. Derzeit eines (Gründungsjahr einer Anstalt, Neubau Jahrzehnte später).

Handstichprobe der Zuordnung (Bauplan B2, „20 Zuordnungen gegen Gebäudeumriss und Bezeichnung“): drei Durchgänge
zu je 20, geschichtet nach Zuordnungsweg, geprüft vom Agenten (eine Durchsicht durch Andre steht aus), Einzelheiten ohne Bezeichnungen und Adressen in
`belege/N3_wikidata_stichprobe.md`. Durchgang 1: 2 falsch (Gründungsjahr statt Baujahr; Punkt im Hof an einem
Kleinbau), Durchgang 2: 1 falsch (Nebenbau erbte das Jahr der Villa); nach jeder Korrektur neu gezogen.
**Durchgang 3: 18 richtig oder plausibel, 2 mit Einschränkung (Denkmale aus mehreren Bauten; ohne
veröffentlichtes Jahr), 0 falsch.**

Gegenprobe an 33 Gebäuden, die in Wikidata (veröffentlichter Weg) und in der Wikipedia-Prüfspalte ein genaues
Jahr haben: 16 gleiches Jahr, 17 anderes Jahr in derselben Bauzeitklasse, 0 in einer anderen Klasse (`berichte/B4_holdout.md`).

Was davon veröffentlicht wird (B4): Stufe 1 der Kaskade, 106 Gebäude „belegt“ (vor der Gegenprobe 129, mit
der Zuordnung über die BLDAM-ID). Ein Einzeljahr tragen nur die 53 Gebäude ohne Wohnraum; 2 weitere ohne
Wohnraum haben eine Spanne statt eines Jahrs und zeigen nur die Klasse; die 51 Gebäude mit Wohnraum zeigen nur die Klasse, weil ALKIS keine Wohneinheiten führt
und „weniger als 3 Wohneinheiten“ nicht entscheidbar ist (Prüfbericht Korrektur 6, Datenschutz).

## Abrufe

In diesem Lauf kein Netzabruf. Die Wikipedia-Seiten wurden in einem früheren B2-Lauf am 05.11.2026 abgerufen
(29 Anfragen, robots.txt zuerst, 5 s Abstand, im Abrufprotokoll). Das BLDAM-PDF stammt aus dem Erkundungslauf
und steht nicht im Abrufprotokoll (Altfall, H10).
