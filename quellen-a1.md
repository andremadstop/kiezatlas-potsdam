# Zulieferung A1 zu QUELLEN.md (Bevölkerungsstruktur, Zensus 2022)

Paket A1, 05.11.2026. Führt die Integration (I1) in `QUELLEN.md` zusammen. Zeile 3 dort ist schon richtig angelegt;
hier stehen der vollständige Vermerk, der Ladestand und was A6 beim Aggregieren beachten muss.

## Quelle

| Feld | Wert |
|---|---|
| Daten | Zensus 2022, 100-m-Gitter, Stichtag 15.05.2022: infrastrukturelle Altersgruppen, Größe des privaten Haushalts, Typ des privaten Haushalts, Typ der Kernfamilie nach Kindern, Seniorenstatus des Haushalts, Staatsangehörigkeit (Gruppen), durchschnittliche Nettokaltmiete, Leerstandsquote, Wohnfläche je Bewohner |
| Bereitsteller | Statistische Ämter des Bundes und der Länder |
| Abruf | `https://www.destatis.de/static/DE/zensus/gitterdaten/<Datei>.zip`, 05.11.2026 (Paket P0, 31 s Abstand, robots `/static/` erlaubt, Crawl-delay 30). A1 hat nichts nachgeladen. |
| Rohdaten | `$KIEZ_DATEN/zensus/2022/` (Hashes in `HERKUNFT.md`, von `pruefen/A1_zensus.py` nachgerechnet) |
| Lizenz | Datenlizenz Deutschland – Namensnennung – Version 2.0 |
| Vermerk | © Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) |
| Ziel | `public.zensus_struktur`, 6.334 Zellen im Rechteck um Potsdam, Pipeline-Lauf `20261105T101043Z` (`skripte/lauf.sh laden --nur zensus_struktur`, Bericht in `belege/`) |
| Vorbereitung | `skripte/01_vorbereiten.py` → `vorbereitet/zensus_struktur.csv` (nicht im Repo) |

Hinweis zu Zeile 2 in `QUELLEN.md`: Dort fehlt im Vermerk noch der Link zum Lizenztext (Prüfbericht 26). Richtig ist
der Vermerk oben, für den Bestand mit „Zensus 2022“ und demselben Zusatz.

## Kodierung in `public.zensus_struktur`

- `–` heißt laut Datensatzbeschreibung „genau Null oder auf Null geändert“ (Cell-Key-Methode). Zählwerte werden 0,
  der Feldname steht in `geaendert`.
- Fehlt eine Zelle in einer Themen-Datei, leben dort keine Personen bzw. gibt es keine Haushalte oder Familien.
  Zählwerte sind dann 0 ohne Eintrag in `geaendert`.
- Mittelwerte (`miete_qm`, `leer_quote`, `wfl_je_bew`): Zelle fehlt = leer (kein Wert, nie 0). `–` beim Leerstand ist
  ein echter Wert 0 (laut Destatis „genau Null oder auf Null geändert“) und steht in `geaendert`.
- Das werterläuternde Zeichen `KLAMMERN` („Aussagewert eingeschränkt, da der Zahlenwert statistisch relativ unsicher ist“)
  steht als `<feld>:unsicher` in `geaendert` (Potsdam: 17 Zellen Miete, 259 Zellen Leerstand).
- Zwei Zellen haben Haushalte, aber keine Personen (Cell-Key). Sie fehlen in `zensus_zelle`; eine liegt in Potsdam
  (`CRS3035RES100mN3262200E4521200`, 3 Haushalte).

## Abdeckung und Summen in Potsdam (Zellmittelpunkt in einem der 32 Stadtteile)

| Thema | Einheit | Insgesamt | Summe der Klassen | Zellen mit Wert | Einwohner in diesen Zellen |
|---|---|---:|---:|---:|---:|
| Altersgruppen (infrastrukturell) | Personen | 182.673 | 180.891 (−1,0 %) | 3.411 von 3.411 | 100 % |
| Staatsangehörigkeit | Personen | 182.673 | 182.669 (−0,0 %) | 3.411 | 100 % |
| Haushaltsgröße | Haushalte | 96.954 | 95.355 (−1,6 %) | 3.080 | 98,6 % |
| Haushaltstyp | Haushalte | 96.954 | 95.789 (−1,2 %) | 3.080 | 98,6 % |
| Seniorenstatus | Haushalte | 96.954 | 96.426 (−0,5 %) | 3.080 | 98,6 % |
| Kernfamilie nach Kindern | Familien | 44.366 | 41.547 (−6,4 %) | 2.859 | 96,9 % |
| Nettokaltmiete | €/m² | Mittel 8,02 (nach EW gewichtet) | – | 2.039 | 87,7 % |
| Leerstandsquote | % | – | – | 3.073 | 97,7 % |
| Wohnfläche je Bewohner | m² | Mittel 47,6 (nach EW gewichtet) | – | 3.078 | 98,6 % |

Bezugswerte je Thema (Korrektur 25): Personen gegen die Einwohner im Bevölkerungsgitter (182.673, Abweichung 0,00 %);
Haushalte gegeneinander (Destatis weist das Insgesamt je Zelle in allen drei Haushaltsdateien gleich aus, das ist
eine Stimmigkeitsprüfung); Familien gegen Haushalte mit Kernfamilie (43.895, +1,07 %). Das unabhängige
Zensus-Gemeindeergebnis Potsdam fehlt noch (Handdownload, siehe unten). `pruefen/A1_zensus.py` prüft es, sobald
`$KIEZ_DATEN/eingang/zensus2022_gemeinde_potsdam.csv` (Spalten `merkmal;wert;quelle`) vorliegt.

Nenner der Abdeckung: 3.411 Zellen mit Einwohnern. Die 3.443 Zellen aus `pruefen/INVENTAR.md` (D1) zählen 32 Zellen
mit Mittelpunkt in Potsdam, aber 0 Einwohnern, mit.

## Für A6 (Aggregation)

- Nicht per INNER JOIN an `zensus_zelle` hängen: Das ließe die Potsdamer Zelle mit 3 Haushalten ohne Personen weg.

- Feine Klassen nie je Zelle in `daten/` (prüfen `pruefen/daten.py` und `pruefen/A1_zensus.py`).
- Klassensummen unterschätzen auf Stadtebene: Altersgruppen −1,0 %, Haushalte −0,5 bis −1,6 %, Kernfamilien −6,4 %.
  Anteile deshalb gegen die Summe der Klassen bilden (nicht gegen „Insgesamt“), Zahlen runden (z. B. auf 10) und je
  Wert einen Unsicherheitshinweis geben (Prüfbericht 15).
- Mindestgröße der Aggregationseinheit laut `config/richtwerte.yaml` (Bauplan A6: ≥ 100 EW).
- Planungsräume statt Stadtteile, sobald `public.planungsraum` gefüllt ist (H1). Die Zuordnung nach Zellmittelpunkt
  passt zur Seite (`02_auswerten.py`).
- Stichtag 15.05.2022: Neubaugebiete (Krampnitz, Bornstedter Feld, Golm) fehlen teilweise.

## Offen

- **Kommentar in `sql/002_ausbau.sql` (P0) angleichen:** Dort steht zu den Mittelwerten „leer = geheim oder ohne Wert,
  nie 0“. A1 schreibt beim Leerstand `–` als 0,00 mit Eintrag in `geaendert`, weil Destatis `–` als „genau Null oder
  auf Null geändert“ definiert. Leer bleibt eine Zelle nur, wenn sie in der Datei fehlt. Für P0 bzw. I1.
- **Kernfamilien:** Die Summe der 13 Klassen liegt 6,4 % unter „Insgesamt“ (Grenze 3 %). Das sind die Daten
  (viele kleine Klassen mit `–`), kein Ladefehler. A6 zeigt Familienanteile nur gegen die Klassensumme und mit Hinweis.

- **Zensus-Gemeindeergebnis Potsdam (12054000)** als unabhängiger Bezugswert je Thema: Personen nach Alter, private
  Haushalte nach Größe/Typ/Seniorenstatus, Familien, Staatsangehörigkeit. Liegt in der Zensusdatenbank
  (ergebnisse.zensus2022.de), die in den Abrufregeln nicht freigegeben ist. Braucht einen Handdownload von Andre nach
  `$KIEZ_DATEN/eingang/zensus2022_gemeinde_potsdam.csv`.
- Zweite Stufe (Eigentümerquote, 10er-Jahresgruppen, Geburtsland) nur nach Bedarf, nicht geladen.
