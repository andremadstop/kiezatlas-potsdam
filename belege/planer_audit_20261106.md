# Planer-Neulauf nach dem Audit vom 06.11.2026 (K4, K5, K7, K8, K14, K24, K27, K28, K32)

Zweig `audit/planer`, Basis `b0514f1`. Bearbeitet von Claude (KI) im Auftrag von Andre („alle wie empfohlen“).
Fundstellen der Funde: `berichte/audit_20261106.md`. Kein Netzabruf; Datenbank nur mit der Leserolle
`mosidi_lesen` (Container `kiezatlas-potsdam-db-1`, Port 55461), keine Rechte geändert, keine DDL.

## Vorgehen beim Vergleich

1. Basislauf: `skripte/15_planer.py` im Stand `b0514f1` (per `git archive` in einen Ordner außerhalb des Repos
   gelegt) gegen dieselbe Datenbank. Ergebnis: `planer.js`, `planer_fuss_odbl.js`, `erreichbar.js`,
   `erreichbar_fuss_odbl.js` und `einrichtungen.js` sind ohne das Feld `stand` inhaltsgleich mit den
   veröffentlichten Dateien vom 05.11.2026. Unterschiede unten gehen also allein auf die Änderungen zurück.
2. Neulauf mit dem geänderten Skript, dann `17_planungsraeume_js.py --pruefen` („aktuell“) und
   `16_export.py --ohne-beleg`.
3. Vergleich je Raumeinheit und Kennzahl, Schlüssel (Kennzahl, Art, Maßstab), Felder `wert`, `status`,
   `vorlaeufig`, `einheit`, `q`, `zielgruppe`, `methode` getrennt von den Texten (`unsicherheit`, `stand`).
   Einwohner je Raumeinheit: in allen 19 gleich.

`vorbereitet/planungsraeume.csv` fehlte im Worktree und ist mit `03_planungsraeume.py` neu erzeugt; die Datei
ist bytegleich mit der in den Worktrees A6, A8, INT, N1, N2 und N4.

## Primärquellen, am 06.11.2026 gelesen

- Baulandmodell 2019 (`$KIEZ_DATEN/baulandmodell/2019/anlage1potsdamerbaulandmodell-fortschreibung2019.pdf`,
  `pdftotext -layout`):
  - Nr. 3.4.3, S. 13: „Die Einwohner je Altersjahrgang … multipliziert mit der Zahl der Altersjahrgänge je
    sozialer Einrichtung und den Versorgungsquoten (beides siehe Tabelle in Anlage C) ergibt den Platzbedarf.“
  - Nr. 3.4.4, S. 14: „Kindertagesbetreuungseinrichtungen und Grundschulen in angrenzenden Planungsräumen sind in
    diese Betrachtung einzubeziehen, wenn sie in angemessener Entfernung liegen und absehbar freie
    Platzkapazitäten bieten.“ Erläuterung S. 15: „Einrichtungen in angrenzenden Planungsräumen sind in die
    Betrachtung einzubeziehen, diese werden im Sinne dieser Richtlinie als in angemessener Entfernung liegend
    betrachtet.“
  - Anlage C, S. 38: Versorgungsquote Grundschule 100 % (6 bis unter 12 Jahre), Hinweis: Quoten der Kitas um
    Kapazitätsreserven reduziert.
  - Folgerung (K4, K7): Anlage C ist eine Bedarfsquote für den Platzbedarf von Vorhaben, keine Norm für Schüler
    am Schulort, und Nr. 3.4.4 rechnet mit den angrenzenden Planungsräumen. Beide Kennzahlen stehen deshalb als
    Orientierung (`config/richtwerte.yaml`, `baulandmodell.status_je_kennzahl`). Das Baulandmodell spricht von 18
    Planungsräumen, die Grenzen von 2025 haben 19; das ist nicht weiter bewertet.
- VBB-GTFS (`$KIEZ_DATEN/vbb_gtfs/2026-11-05/GTFS.zip`, nur lesend): `calendar.txt` hat bei allen 3.185
  `service_id` `start_date` 20261103; `HERKUNFT.md`: „Fahrplan gültig ab 03.11.2026“. Neu in
  `config/richtwerte.yaml`: `oepnv.messung.fahrplan_gueltig_ab: 2026-11-03` und `stichtag_art: Schultag`
  (vorher nur im Kommentar). Der Wochentag kommt aus dem Datum (`date.weekday()`), 6 bis 9 Uhr aus `hvz_fenster`.

## Geänderte Werte (vorher → nachher)

`planer.js` (Luftlinie), 323 Werte in 19 Raumeinheiten:

| Raum | Kennzahl | vorher | nachher | Grund |
|---|---|---|---|---|
| 304 | Grundschüler je Kind | 0,87 | kein Wert | K4: Montessori-Oberschule mit Primarstufe (MBJS 112963) |
| 501 | Grundschüler je Kind | 1,03 | kein Wert | K4: Schulzentrum am Stern (MBJS 150010) |
| 604 | Grundschüler je Kind | 0,00 | kein Wert | K4: Oberschule Theodor Fontane mit Primarstufe (MBJS 113001) |
| 304 | Einwohner je Grundschulstandort | 8.160 | 4.080 | K4: zweiter Standort |
| 501 | Einwohner je Grundschulstandort | 8.490 | 5.660 | K4: dritter Standort |
| 604 | Einwohner je Grundschulstandort | kein Wert | 10.100 | K4: erster Standort |
| 601 | Kinder 6 bis 9 mit Grundschule bis 1000 m | 83 % | 84 % | K4: Nachbarraum-Schule näher |
| 604 | Kinder 6 bis 9 mit Grundschule bis 1000 m | 78 % | 100 % | K4 |

Status: 38 Werte von „amtlich“ auf „orientierung“, je Raumeinheit Plätze je Bedarfsplatz (K7) und Grundschüler je
Kind (K4). Danach trägt kein Wert mehr das Abzeichen „amtlicher Maßstab“. Alle übrigen Werte gleich. Texte:
`unsicherheit` an 138 Werten geändert (K4, K7, K8, K27), `stand` an den 38 ÖPNV-Werten (K32).

`planer_fuss_odbl.js` (Fußweg), 190 Werte, nur Kinder 6 bis 9 mit Grundschule bis 1000 m:
304 91 → 100 %, 403 91 → 92 %, 501 95 → 100 %, 601 59 → 60 %, 604 52 → 100 %. Alle übrigen Werte gleich;
`unsicherheit` an den 38 Grundschul-Anteilen geändert.

Zellwerte: `erreichbar.js` 188 Zellen Grundschule kürzer (191 vor der Rundung auf 10 m), `erreichbar_fuss_odbl.js`
180 Zellen kürzer (181); keine Zelle länger, alle anderen Arten gleich. `einrichtungen.js`: Punkte gleich, nur
`hinweis` und `stand`. `einrichtungen_odbl.js` hätte sich nur im `stand` geändert und ist auf dem Stand vom
05.11.2026 belassen.

Schulen mit Primarstufe (MBJS-Schulform „G/…“), die jetzt als Grundschulziel zählen: 105673 BBIS (außerhalb),
112008 Grund- und Oberschule Wilhelmshorst (außerhalb), 112963 Montessori-Oberschule mit Primarstufe (304),
113001 Oberschule Theodor Fontane mit Primarstufe (604), 130539 Grund- und Oberschule Carl von Ossietzky
(außerhalb), 150010 Schulzentrum am Stern (501). Die Grundschule Hanna von Pestalozza (MBJS 103512) bleibt
gesperrt.

## Neue Felder und Zählungen

- K14: 304 Werte mit `zaehler`/`nenner` in `planer.js`, davon 272 mit Zahl (ohne Wert ohne Zahl, außer Einwohner je
  Standort ohne Standort); 76 in `planer_fuss_odbl.js`. `differenz` nur bei Plätzen je Bedarfsplatz.
  `raeume.<nr>.kinder` (u3, 3_bis_5, 6_bis_unter_12) in allen 19 Räumen (kleinster: 103 mit 124 EW, Grenze 100).
  6 bis unter 12 ist eine eigene Schätzung (6 bis 9 plus ein Drittel von 10 bis 15), keine Zensusklasse.
- K24: `gesamt` mit 16 Werten (15 mit Wert; Grundschüler je Kind ohne Wert wegen der Schulen mit Primarstufe),
  Fußweg 4 Werte. Beispiele: Plätze je Bedarfsplatz 1,21 (20.953 Plätze von 17.330 Bedarfsplätzen, Differenz
  3.620), Kinder unter 6 mit Kita bis 500 m 86 % (9.650 von 11.160), ÖPNV-Erschließung 88 %, mit Soll-Takt 78 %.
- K27: eine Kita mit Häusern in zwei Planungsräumen: MBJS KTS 04806 (502 Hauptstandort, 503), 104 Plätze; in beiden
  Räumen genannt.
- K28: `pruefwerte` in `planer.js`, gelesen aus `belege/N1_osm_fussweg_20261105.md` (Kita in OSM 78,1 %, Umweg
  Fußweg 1,367) und `belege/A5b_landfilter_kreuzprobe.txt` (1.800 Haltepunkte, 15 falsch zugeordnet).
- K5: `daten/export/csv_de/` (8 Dateien, 7.433 Dezimalzahlen mit Komma) und `csv_odbl_de/` (4 Dateien, 1.901).

## Prüfstand

- `./pruefen.sh`: 18 Prüfungen, 18 grün (dafür im Worktree der Verweis `rohdaten -> ../kiezatlas-potsdam-west/rohdaten`
  wie im Haupt-Repo, in `.gitignore`). Neu darin: K4 bis K32 in `pruefen/A6_test_pfade.py`, Zähler/Nenner,
  ganz Potsdam, Vergleichstabelle und Prüfwerte in `pruefen/A7_planer.mjs`, `csv_de/` und Spalte Potsdam in
  `pruefen/A8_export.py`.
- `python3 -I pruefen/daten.py`: 0 Abweichungen.
- Mit Datenbank (Leserolle): `pruefen/A6_planer.py` 0 Befunde (72 Kriterien; neu A6-3 Status je Kennzahl, A6-12
  Grundschulziel mit Primarstufe auf zweitem Weg in SQL, Fußweg nachgebaut, A6-13 Zähler/Nenner = Wert mit
  Rundungstoleranz, gesamt = Summen, K4, K27, K28). `pruefen/A8_export.py --odbl-erwartet` mit Datenbank 0 Befunde
  (211 Kriterien).
- `pruefen/A8_test_pfade.py`: 1 Befund, schon am Stand `b0514f1` vorhanden (Fixture-Export: amtliche Ziele im
  Fußweg ohne MBJS-/LGB-Vermerk, weil die Beispieldaten die Quelle `bsp` tragen). Nicht behoben.
