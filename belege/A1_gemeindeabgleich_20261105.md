# A1: Zensus-Gitter gegen Gemeindeergebnis Potsdam (Nachlauf N2, 05.11.2026)

Lauf: `pruefen/A1_zensus.py` (Basis `ausbau/integration`), volle Ausgabe `belege/A1_zensus_n2_20261105.txt`, 0 Befunde.
Gitter = Summe der 100-m-Zellen mit Mittelpunkt in einem der 32 Stadtteile (`public.zensus_struktur`).
Gemeinde = Zensusdatenbank, Potsdam 12054, Stichtag 15.05.2022 (`$KIEZ_DATEN/eingang/zensus2022_gemeinde_potsdam.csv`,
SHA256 wie in `eingang/HERKUNFT.md`). Lizenz dl-de/by-2-0, © Statistische Ämter des Bundes und der Länder, Zensus 2022.

## Insgesamt je Thema (Prüfung, Grenze 3 %)

| Thema | Gitter | Gemeinde | Abweichung | Tabelle |
|---|---:|---:|---:|---|
| Altersgruppen (Personen) | 182.673 | 182.806 | −0,07 % | 1000A-1004 |
| Staatsangehörigkeit (Personen) | 182.673 | 182.806 | −0,07 % | 1000A-1020 |
| Haushaltsgröße (Haushalte) | 96.954 | 97.599 | −0,66 % | 5000H-1001 |
| Haushaltstyp (Haushalte) | 96.954 | 97.599 | −0,66 % | 5000H-1006 |
| Seniorenstatus (Haushalte) | 96.954 | 97.599 | −0,66 % | 5000H-1004 |
| Kernfamilie (Familien) | 44.366 | 45.003 | −1,42 % | 6000F-1002 |

Alle sechs unter 3 %. Die Gittersummen liegen durchweg leicht unter dem Gemeindeergebnis. Mögliche Ursachen (nicht
einzeln nachgewiesen): Randzellen, deren Mittelpunkt außerhalb der Stadtteilgrenzen liegt, und die Cell-Key-Methode,
die kleine Zellwerte auf „–“ (= 0) setzt.

## Je Klasse (nur Information, kein Prüfkriterium)

| Klasse | Gitter | Gemeinde | Abweichung |
|---|---:|---:|---:|
| deutsch | 164.133 | 164.263 | −0,1 % |
| Ausland | 18.536 | 18.544 | −0,0 % |
| 1 Person | 49.213 | 49.853 | −1,3 % |
| 2 Personen | 26.315 | 26.962 | −2,4 % |
| 3 Personen | 10.216 | 10.677 | −4,3 % |
| 4 Personen | 6.716 | 6.973 | −3,7 % |
| 5 Personen | 1.940 | 2.059 | −5,8 % |
| 6 und mehr | 955 | 1.071 | −10,8 % |
| Einpersonenhaushalt | 49.279 | 49.853 | −1,2 % |
| Paar ohne Kind | 20.301 | 20.714 | −2,0 % |
| Paar mit Kind | 15.693 | 16.035 | −2,1 % |
| Alleinerziehend | 7.901 | 8.253 | −4,3 % |
| Mehrpersonenhaushalt ohne Kernfamilie | 2.615 | 2.742 | −4,6 % |
| nur Senioren | 21.577 | 21.827 | −1,1 % |
| mit Senioren | 4.596 | 4.822 | −4,7 % |
| ohne Senioren | 70.253 | 70.950 | −1,0 % |

Je kleiner die Klasse, desto größer die Lücke (Haushalte mit 6 und mehr Personen −10,8 %). Das ist der bekannte
Cell-Key-Effekt: In vielen Zellen steht dort „–“. Für A6 heißt das: Anteile kleiner Klassen je Raumeinheit sind eher
zu niedrig; der Unsicherheitshinweis bleibt nötig. Altersgruppen und Kernfamilien-Klassen lassen sich nicht je Klasse
vergleichen (infrastrukturelle Altersgruppen gibt es auf Gemeindeebene nicht; die Gemeindedatei führt nur `kf_ges`).

## Paketgrenze

`A1_zensus.py` prüft jetzt je nach Basis: `ausbau/integration` (Standard, Nachlauf: A1-Dateien plus die freigegebenen
N2-Dateien), `ausbau/p0` (Paketzweig) oder `ausbau/p0...ausbau/a1` (nur die Commits von A1, ab dem gemeinsamen
Vorfahren). Auf dem Integrationsstand sind beide Lesarten grün; vorher war der Standard `ausbau/p0` dort immer rot,
weil alle anderen Pakete mit im Diff standen. Negativprobe: eine ungetrackte fremde Datei macht die Prüfung rot.
