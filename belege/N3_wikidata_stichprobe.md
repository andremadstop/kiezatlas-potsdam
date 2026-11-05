# N3: Handstichprobe Wikidata-Zuordnung (B2), 05.11.2026

Je Durchgang 20 Zuordnungen aus `auswertung.jahr_beleg` (Quelle Wikidata), geschichtet gezogen mit
`pruefen/N3_wd_stichprobe.py <seed>`: 6 × Denkmal-ID mit einem Gebäude, 4 × ID mit 2 bis 4 Gebäuden,
3 × Koordinate nach Ensemble-ID, 7 × Koordinate. Geprüft hat der Agent (Claude, Nachlauf N3), nicht Andre; eine
menschliche Durchsicht steht aus. Geprüft wurde Zeile für Zeile gegen die Bezeichnung in Wikidata,
die ALKIS-Funktion, die Lage des Wikidata-Punkts zum Umriss und die Grundfläche; in Zweifelsfällen gegen den
Text der Wikipedia-Denkmalliste (nur intern, Prüfspalte).

Datenschutz: Diese Datei nennt keine Bezeichnungen (sie enthalten oft Adressen) und keine Gebäudekennungen.
Bei Gebäuden mit Wohnraum fehlen auch Wikidata-Objekt, Denkmal-ID, Grundfläche und Jahr (statt des Jahrs steht
nur die Bauzeitklasse, wie in `daten/jahre/`), damit sich kein Wohngebäude über seine Fläche in den
veröffentlichten Umrissen wiederfinden und mit einem Einzeljahr verbinden lässt (Korrektur 6). Die vollständigen Listen liegen nur intern
unter `$KIEZ_DATEN/wikidata_zuordnung/2026-11-05/stichprobe_seed<seed>.csv`.

Nachtrag (Gegenprobe zum Nachlauf, 05.11.2026): Veröffentlicht wird inzwischen nur die Zuordnung über die
eigene Koordinate. Die Schichten „ID, …“ unten sind seitdem nur Prüfspalte (die Zuordnung über die Denkmal-ID läuft
über die Adressen der BLDAM-Liste, Lizenz offen, E8). Eine Stichprobe allein für den Koordinatenweg steht aus.
Die Liste, aus der diese Stichprobe gezogen wurde, liegt unverändert unter `zuordnung.csv`, die neue unter
`zuordnung_nachlauf_koordinate.csv` (beide `$KIEZ_DATEN/wikidata_zuordnung/2026-11-05/`).

## Durchgang 1 (Seed 2211), Regeln wie im ersten Lauf

| Nr. | Objekt | Denkmal-ID | Schicht | Gebäude je ID (BLDAM) | ALKIS-Funktion | Wohnraum | Punkt | Fläche m² | Jahr | genau | Urteil |
|---:|---|---|---|---:|---|---|---|---:|---|---|---|
| 1 | Q16781959 | 09155988 | ID, ein Gebäude | 1 (1) | Gebäude für religiöse Zwecke | nein | 20 m daneben | 319 | 1933 | ja | richtig |
| 2 | Q104398059 | 09155084 | ID, ein Gebäude | 1 (1) | Polizei | nein | im Umriss | 1936 | 1752 | ja | richtig (Punkt im Umriss; großer Baukomplex, Jahr gilt dem Altbau) |
| 3 | Q52240606 | 09155011 | ID, ein Gebäude | 1 (1) | Museum | nein | im Umriss | 1241 | 1750 | ja | richtig |
| 4 | Q136447897 | 09155604 | ID, ein Gebäude | 1 (1) | Gaststätte, Restaurant | nein | im Umriss | 188 | 1740–1749 | nein | richtig (Jahrzehnt, nicht genau) |
| 5 | (intern) | (intern) | ID, ein Gebäude | 1 (1) | Wohnhaus | ja | 0 m daneben | (intern) | Klasse 1919–1948 | ja | richtig |
| 6 | Q1475597 | 09155238 | ID, ein Gebäude | 1 (1) | Kirche | nein | im Umriss | 1472 | 1860–1869 | nein | richtig (Jahrzehnt, nicht genau) |
| 7 | Q1549185 | 09155145 | ID, 2 bis 4 Gebäude | 3 (3) | Gebäude für kulturelle Zwecke | nein | 46 m daneben | 385 | 1724 | ja | **falsch**: 1724 ist die Gründung der Anstalt, der heutige Bau entstand 1771–77 (Wikipedia-Prüfspalte) → Ausschlussliste |
| 8 | (intern) | (intern) | ID, 2 bis 4 Gebäude | 2 (2) | Wohnhaus | ja | 42 m daneben | (intern) | Klasse vor 1919 | nein | richtig (zwei Jahre, nicht genau) |
| 9 | (intern) | (intern) | ID, 2 bis 4 Gebäude | 2 (2) | Wohnhaus | ja | im Umriss | (intern) | Klasse 1919–1948 | ja | richtig (Doppelhaus, zwei Umrisse) |
| 10 | Q801329 | 09157234 | ID, 2 bis 4 Gebäude | 3 (3) | Empfangsgebäude | nein | 71 m daneben | 463 | 1958 | ja | richtig |
| 11 | (intern) | (intern) | Koordinate nach Ensemble-ID | 1 (10) | Wohngebäude mit Handel und Dienstleistungen | ja | 8 m daneben | (intern) | Klasse vor 1919 | ja | plausibel (Punkt 8 m neben dem Umriss, Kasernenbau) |
| 12 | (intern) | (intern) | Koordinate nach Ensemble-ID | 1 (5) | Wohnhaus | ja | 3 m daneben | (intern) | Klasse vor 1919 | ja | **falsch**: Punkt im Hof, nächster Umriss ist ein Kleinbau unter 100 m² → Regel Mindestfläche 100 m² außerhalb des Umrisses |
| 13 | (intern) | (intern) | Koordinate nach Ensemble-ID | 1 (19) | Wohnhaus | ja | im Umriss | (intern) | Klasse vor 1919 | nein | richtig |
| 14 | Q316058 | 09155233 | Koordinate | 1 (0) | Gaststätte, Restaurant | nein | im Umriss | 413 | 1755 | ja | richtig |
| 15 | (intern) | (intern) | Koordinate | 1 (0) | Wohnhaus | ja | im Umriss | (intern) | Klasse vor 1919 | ja | richtig |
| 16 | Q451555 | 09156911 | Koordinate | 1 (0) | Museum | nein | 5 m daneben | 1450 | 1764 | ja | richtig |
| 17 | Q564199 | 09156100 | Koordinate | 1 (0) | Kirche | nein | im Umriss | 348 | 1844 | ja | richtig |
| 18 | Q320569 | – | Koordinate | 1 (0) | Gaststätte, Restaurant | nein | im Umriss | 120 | 1826 | ja | plausibel (Funktion heute Gaststätte) |
| 19 | Q321783 | 09156864 | Koordinate | 1 (0) | Schloss | nein | 4 m daneben | 3792 | 1914 | ja | richtig |
| 20 | Q101647277 | 09156897 | Koordinate | 1 (0) | Gebäude zur Wasserversorgung | nein | im Umriss | 434 | 1840–1849 | nein | richtig (Jahrzehnt, nicht genau) |

## Durchgang 2 (Seed 2212), nach Korrektur 1 und 2

| Nr. | Objekt | Denkmal-ID | Schicht | Gebäude je ID (BLDAM) | ALKIS-Funktion | Wohnraum | Punkt | Fläche m² | Jahr | genau | Urteil |
|---:|---|---|---|---:|---|---|---|---:|---|---|---|
| 1 | Q19308773 | 09155014 | ID, ein Gebäude | 1 (1) | Freizeit- und Vergnügungsstätte | nein | im Umriss | 570 | 1748 | ja | richtig |
| 2 | (intern) | (intern) | ID, ein Gebäude | 1 (1) | Wohnhaus | ja | im Umriss | (intern) | Klasse vor 1919 | ja | richtig |
| 3 | Q962542 | 09155001 | ID, ein Gebäude | 1 (1) | Museum | nein | im Umriss | 407 | 1843 | ja | richtig |
| 4 | (intern) | (intern) | ID, ein Gebäude | 1 (1) | Gebäude für Handel und Dienstleistung mit Wohnen | ja | im Umriss | (intern) | Klasse vor 1919 | ja | richtig |
| 5 | (intern) | (intern) | ID, ein Gebäude | 1 (1) | Wohngebäude mit Handel und Dienstleistungen | ja | im Umriss | (intern) | Klasse vor 1919 | ja | richtig |
| 6 | (intern) | (intern) | ID, ein Gebäude | 1 (1) | Wohnhaus | ja | im Umriss | (intern) | Klasse vor 1919 | ja | richtig (vorher als Ensemble verworfen, Regel korrigiert) |
| 7 | (intern) | (intern) | ID, 2 bis 4 Gebäude | 2 (2) | Wohnhaus | ja | 42 m daneben | (intern) | Klasse vor 1919 | nein | richtig (nicht genau) |
| 8 | Q125636259 | 09155734 | ID, 2 bis 4 Gebäude | 2 (2) | Gebäude für Wirtschaft oder Gewerbe | nein | 55 m daneben | 55 | 1914 | ja | **falsch**: Nebenbau 55 m² erbt das Jahr der Villa → Regel: bei mehreren ID-Gebäuden nur Bauten ab 100 m² |
| 9 | Q801329 | 09157234 | ID, 2 bis 4 Gebäude | 3 (3) | Empfangsgebäude | nein | 89 m daneben | 419 | 1958 | ja | richtig |
| 10 | Q801329 | 09157234 | ID, 2 bis 4 Gebäude | 3 (3) | Empfangsgebäude | nein | 71 m daneben | 463 | 1958 | ja | richtig |
| 11 | (intern) | (intern) | Koordinate nach Ensemble-ID | 1 (10) | Wohngebäude mit Handel und Dienstleistungen | ja | 8 m daneben | (intern) | Klasse vor 1919 | ja | plausibel |
| 12 | (intern) | (intern) | Koordinate nach Ensemble-ID | 1 (5) | Wohngebäude mit Gemeinbedarf | ja | im Umriss | (intern) | Klasse vor 1919 | ja | richtig |
| 13 | (intern) | (intern) | Koordinate nach Ensemble-ID | 1 (19) | Wohnhaus | ja | im Umriss | (intern) | Klasse vor 1919 | nein | richtig (nicht genau) |
| 14 | Q110608740 | 09157092 | Koordinate | 1 (0) | Überdachung | nein | im Umriss | 136 | 1932 | ja | richtig (Pavillon) |
| 15 | Q801326 | 09156006 | Koordinate | 1 (0) | Empfangsgebäude | nein | im Umriss | 1595 | 1913 | nein | richtig (zwei Jahre, nicht genau) |
| 16 | Q451555 | 09156911 | Koordinate | 1 (0) | Museum | nein | 5 m daneben | 1450 | 1764 | ja | richtig |
| 17 | (intern) | (intern) | Koordinate | 1 (0) | Wohnhaus | ja | im Umriss | (intern) | Klasse vor 1919 | ja | richtig |
| 18 | Q64025600 | 09156735 | Koordinate | 1 (0) | Kirche | nein | im Umriss | 362 | 1709 | ja | richtig |
| 19 | Q115785345 | 09157043 | Koordinate | 1 (0) | Gebäude im Zoo | nein | im Umriss | 263 | 1789 | ja | plausibel (Funktion nicht prüfbar, Punkt im Umriss) |
| 20 | Q819742 | 09156915 | Koordinate | 1 (0) | Gebäude für kulturelle Zwecke | nein | im Umriss | 1089 | 1854 | ja | richtig |

## Durchgang 3 (Seed 2213), endgültige Regeln, Abnahme

| Nr. | Objekt | Denkmal-ID | Schicht | Gebäude je ID (BLDAM) | ALKIS-Funktion | Wohnraum | Punkt | Fläche m² | Jahr | genau | Urteil |
|---:|---|---|---|---:|---|---|---|---:|---|---|---|
| 1 | (intern) | (intern) | ID, ein Gebäude | 1 (1) | Gebäude für Handel und Dienstleistung mit Wohnen | ja | keine Koordinate | (intern) | Klasse vor 1919 | ja | richtig (ohne Koordinate, nur ID) |
| 2 | (intern) | (intern) | ID, ein Gebäude | 1 (1) | Wohnhaus | ja | im Umriss | (intern) | Klasse vor 1919 | nein | richtig (nicht genau) |
| 3 | (intern) | (intern) | ID, ein Gebäude | 1 (1) | Wohngebäude mit Handel und Dienstleistungen | ja | im Umriss | (intern) | Klasse vor 1919 | nein | richtig (zwei Jahre, nicht genau) |
| 4 | (intern) | (intern) | ID, ein Gebäude | 1 (1) | Wohnhaus | ja | 0 m daneben | (intern) | Klasse 1919–1948 | ja | richtig |
| 5 | Q1403252 | 09155830 | ID, ein Gebäude | 1 (1) | Bürogebäude | nein | 35 m daneben | 3005 | 1902 | ja | richtig (großer Bau, Punkt 35 m entfernt) |
| 6 | Q464437 | 09155789 | ID, ein Gebäude | 1 (1) | Kapelle | nein | 2 m daneben | 117 | 1829 | ja | richtig |
| 7 | (intern) | (intern) | ID, 2 bis 4 Gebäude | 4 (4) | Wohnhaus | ja | 29 m daneben | (intern) | Klasse vor 1919 | ja | mit Einschränkung: Klasse richtig, das genaue Jahr gilt der Station als Ganzes, nicht jedem der Bauten (Wohnraum, daher ohnehin kein Jahr veröffentlicht) |
| 8 | Q122418081 | 09155821 | ID, 2 bis 4 Gebäude | 4 (4) | Krankenhaus | nein | 101 m daneben | 194 | 1860–1869 | nein | mit Einschränkung: Krankenhauskomplex mit jüngeren Erweiterungen; ohne Wirkung, weil nicht genau |
| 9 | Q801329 | 09157234 | ID, 2 bis 4 Gebäude | 3 (3) | Freizeit- und Vergnügungsstätte | nein | 64 m daneben | 582 | 1958 | ja | plausibel (Teil des Bahnhofs nach ID) |
| 10 | (intern) | (intern) | ID, 2 bis 4 Gebäude | 2 (2) | Wohnhaus | ja | 26 m daneben | (intern) | Klasse vor 1919 | nein | richtig (nicht genau) |
| 11 | (intern) | (intern) | Koordinate nach Ensemble-ID | 1 (10) | Wohngebäude mit Handel und Dienstleistungen | ja | 8 m daneben | (intern) | Klasse vor 1919 | ja | plausibel |
| 12 | (intern) | (intern) | Koordinate nach Ensemble-ID | 1 (5) | Wohngebäude mit Gemeinbedarf | ja | im Umriss | (intern) | Klasse vor 1919 | ja | richtig |
| 13 | (intern) | (intern) | Koordinate nach Ensemble-ID | 1 (19) | Wohnhaus | ja | im Umriss | (intern) | Klasse vor 1919 | nein | richtig (nicht genau) |
| 14 | Q321783 | 09156864 | Koordinate | 1 (0) | Schloss | nein | 4 m daneben | 3792 | 1914 | ja | richtig |
| 15 | Q702477 | 09156881 | Koordinate | 1 (0) | Schloss | nein | im Umriss | 1116 | 1835 | ja | richtig |
| 16 | Q115785345 | 09157043 | Koordinate | 1 (0) | Gebäude im Zoo | nein | im Umriss | 263 | 1789 | ja | plausibel |
| 17 | Q117111130 | 09157760 | Koordinate | 1 (0) | Nach Quellenlage nicht zu spezifizieren | nein | im Umriss | 10 | 1748 | ja | richtig (Kleinbau im Park, Punkt im Umriss) |
| 18 | Q19310912 | 09156991 | Koordinate | 1 (0) | Verwaltungsgebäude | nein | im Umriss | 149 | 1848 | ja | richtig |
| 19 | Q1450578 | 09155239 | Koordinate | 1 (0) | Kirche | nein | im Umriss | 395 | 1750–1759 | nein | richtig (nicht genau) |
| 20 | (intern) | (intern) | Koordinate | 1 (0) | Wohnhaus | ja | im Umriss | (intern) | Klasse vor 1919 | ja | richtig |

## Ergebnis

| Durchgang | richtig oder plausibel | mit Einschränkung | falsch | Korrektur danach |
|---|---:|---:|---:|---|
| 1 | 18 | 0 | 2 | Ausschlussliste (Gründungsjahr statt Baujahr); außerhalb des Umrisses nur Bauten ab 100 m²; ID und Koordinate mehr als 150 m auseinander → Koordinate |
| 2 | 19 | 0 | 1 | bei mehreren Gebäuden je ID erben nur Bauten ab 100 m² das Jahr |
| 3 | 18 | 2 | 0 | keine; Abnahme |

Die drei Durchgänge sind nicht 60 unabhängige Prüfungen: Die Schicht „Koordinate nach Ensemble-ID“ hat nur drei
Kandidaten (Zeilen 11 bis 13 sind in jedem Durchgang dieselben), und einzelne Objekte kommen in mehreren Durchgängen
vor (etwa Q801329, Q451555).

Die beiden Einschränkungen in Durchgang 3 betreffen Denkmale aus mehreren Bauten (eine Station, ein Krankenhaus).
Die Klasse stimmt; ein genaues Jahr wird dort nicht veröffentlicht (Wohnraum bzw. nicht genau).
Nicht geprüft und offen: Rekonstruktionen, bei denen Wikidata das Jahr des Originals führt. Andre hat beim
Durchsehen der CSV die bekannten Fälle aussortiert (`eingang/wikidata_potsdam_aussortiert.md`); die Stichprobe
fand einen weiteren (Militärwaisenhaus), es kann weitere geben.
