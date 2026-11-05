# B3 Luftbild-Pilot: Prüfprotokoll, vor dem Pilot festgelegt

Stand 05.11.2026. Diese Datei legt Stichprobe, Referenz und Trefferregel fest, **bevor** die automatische
Auswertung (`skripte/23_luftbild_pilot.py auswerten`) geschrieben wird. Beleg ist der Commit, der diese Datei
mit dem SHA256 der Referenz einführt; der Klassifikator kommt erst in einem späteren Commit.

## 1. Frage

Grenzt die DOP-Zeitreihe der LGB das Baujahr eines Gebäudes ein? Gemessen wird, ob eine automatische
Bildauswertung die Befliegung findet, in der ein heutiges Gebäude zum ersten Mal zu sehen ist.

## 2. Pilotgebiet und Bilder

- Stadtteil 13 Bornstedt (Gebäude, deren innerer Punkt im Stadtteil liegt), Snapshot `auswertung.gebaeude_stand_20261105`.
- Ausschnitt EPSG:25833 364800–367800 / 5808000–5810700, alle Befliegungen einheitlich mit 0,4 m je Pixel (1953 mit
  1 m und 1992–97 mit 0,5 m Bodenauflösung werden dabei hochgerechnet).
- Befliegungen (Index k): 0 `dop100g_1953`, 1 `dop50g_1992_1997`, 2 `dop40g_2001_2009`, 3 `dop20_2009_2012`,
  4 `dop20_2013_2015`, 5 `dop20_2016_2018`, 6 `dop20_2019_2021`, 7 `dop20c` (aktuell).
- Flugdatum je Befliegung und Blatt aus den `*_info`-Layern (GetFeatureInfo, Feld „Ersterstellung“, als Flugjahr
  gelesen). Über dem Ausschnitt gilt je Befliegung ein einziges Datum: 0 = 1953 (01.01.1953, nur Jahr), 1 = 07.06.1996,
  2 = 27.04.2007, 3 = 20.05.2012, 4 = 11.05.2015, 5 = 05.05.2018, 6 = 09.05.2021, 7 = 30.04.2024
  (Abfrage 05.11.2026, Dateien `info_*.txt`). Die Klammer eines Gebäudes ist
  `nicht_vor` = Flugjahr der letzten Befliegung ohne das Gebäude, `nicht_nach` = Flugjahr der ersten Befliegung mit ihm.

## 3. Stichprobenrahmen (Referenz)

- Rahmen: Bauwerksart „Gebäude“, Fläche ≥ 50 m², Funktion **nicht** in: Garage, Schuppen, Gartenhaus,
  Gebäude zur Freizeitgestaltung, Treibhaus/Gewächshaus, Gebäude zum Parken, Tiefgarage, Überdachung, Umformer,
  Toilette, Durchfahrt im Gebäude (Nebengebäude bleiben nach E5 undatiert).
- Reihenfolge: aufsteigend nach `md5(oid || 'B3-Referenz-2026-11-05')`. Die Reihenfolge hängt nicht vom Bild ab.
- Lose zu je 40 Gebäuden in dieser Reihenfolge. Es werden ganze Lose gesichtet, bis mindestens **50 Gebäude
  „nach 2009“ (k_ref ≥ 4)** in der Referenz stehen (sequentielles Nachziehen). Alle gesichteten Gebäude bleiben in der Referenz;
  die Gebäude vor 2009 dienen als Negativkontrolle.
- „Nach 2009“ heißt: im Flug vom 20.05.2012 (k = 3) noch nicht zu sehen, also erstmals ab k = 4 (2015).
  **Korrektur vor der Sichtprüfung (05.11.2026):** Der erste Entwurf setzte „nach 2009“ = erstmals ab k = 3. Die
  Flugdaten zeigen aber, dass die Befliegung `dop40g_2001_2009` über Bornstedt vom 27.04.2007 stammt. Ein Gebäude,
  das erst 2012 zu sehen ist, kann also 2007 oder 2008 entstanden sein. Deshalb zählt erst k ≥ 4 als sicher
  „nach 2009“. Gebäude mit k_ref = 3 (zwischen 2007 und 2012) werden getrennt ausgewiesen.

## 4. Referenz: Sichtprüfung

- Wer: der Agent (Claude) am 05.11.2026, **nicht** Andre. Grundlage: Kontaktbögen mit je einem Ausschnitt je
  Befliegung (Gebäudeumriss aus ALKIS eingezeichnet, Rand 15 m).
- Je Gebäude wird notiert: `k_ref` = erste Befliegung, in der der heutige Baukörper zu sehen ist (0 bis 7),
  `form_abweichend` = an der Stelle stand vorher ein anderer Baukörper (Ersatzneubau), `unklar` = nicht entscheidbar
  (Schatten, Bäume, Bildfehler). Unklare Gebäude zählen nicht zu den 50 und gehen nicht in die Trefferquote ein;
  ihre Zahl steht im Bericht.
- **Lesart, während der Sichtung festgelegt (vor dem Klassifikator):**
  - Ein Rohbau mit erkennbarem Umriss (Wände, Kran am Baukörper) zählt als „zu sehen“; Baugrube, Fundament und
    freigeräumtes Baufeld zählen nicht.
  - `frueher_moeglich = 1`: Das Gebäude ist in Befliegung k_ref sicher zu sehen, in der Befliegung davor ist an der Stelle
    ein unscharfer Körper, der derselbe sein kann (meist 1953 mit 1 m Graustufen). Für diese Gebäude ist nur „k_ref oder
    früher“ belegt. Sie zählen in der Nebenbedingung (alle haben k_ref ≤ 3), aber nicht in Trefferquoten mit genauem k.
  - Die Bögen hat der Agent in der Reihenfolge der Lose gesichtet, Los 1 vollständig vor Los 2 bis 4, diese vor Los 5.
- Ablage: `$KIEZ_DATEN/luftbild_lgb/2026-11-05/referenz/referenz.csv` (außerhalb des öffentlichen Repos, weil die oid
  über ALKIS auf eine Adresse führt; Korrektur 6). Ins Repo kommt nur der SHA256 (Abschnitt 7).
- **Zirkularität:** Referenz und Automatik lesen dieselben Bilder. Gemessen wird also „Automatik gegen Sichtprüfung“,
  nicht „Klammer gegen wahres Baujahr“. Ob „erstmals im Luftbild“ dem Baujahr entspricht (Rohbau gegen Fertigstellung),
  prüft nur die Zensus-Gegenprobe (Abschnitt 6), und auch die nur in der Summe.

## 5. Trefferregel und Abbruchkriterium

- **Treffer:** `k_auto = k_ref`. Damit ist die automatische Klammer genau ein Befliegungsschritt breit und enthält die
  Referenzklammer. Eine breitere Klammer zählt nie als Treffer.
- Zusätzlich im Bericht: Anteil mit |k_auto − k_ref| ≤ 1, Median der Klammerbreite in Jahren, Treffer nach Los
  und nach Funktion (Wohnhaus gegen Rest).
- **Hauptkriterium (Bauplan B3):** Trefferquote unter den Referenzgebäuden „nach 2009“ (k_ref ≥ 4, also erstmals
  2015 oder später zu sehen, nicht unklar),
  mindestens 50 Gebäude. Liegt sie unter 80 %, wird B3 **nicht ausgerollt**.
- **Nebenbedingung (vorab ergänzt):** Unter den Referenzgebäuden, die schon im Flug 2012 zu sehen sind (k_ref ≤ 3),
  darf die Automatik höchstens 10 % fälschlich „nach 2012“ (k_auto ≥ 4) datieren. Sonst ebenfalls nicht ausrollen.
- Zusätzlich im Bericht: Trefferquote für k_ref = 3 (2007 bis 2012) und für k_ref ≤ 2 getrennt.
- Ausgang „nicht ausrollen“: Die Pilotzeilen bleiben in `auswertung.jahr_klammer`, aber mit
  `quelle = 'LGB DOP-Zeitreihe, Pilot Bornstedt (nicht ausgerollt)'`, damit B4 sie nicht als Kaskadenstufe nimmt.
  Bei „ausrollen“ lautet die Quelle `'LGB DOP-Zeitreihe, Pilot Bornstedt'`.

## 6. Unabhängige Gegenprobe: Zensus 2022

- Datei `zensus/2022/Gebaeude_nach_Baujahr_Jahrzehnte.zip` (offline, Destatis, dl-de/by-2-0), 100-m-Gitter,
  Klassen `a2000bis2009`, `a2010bis2015`, `a2016undspaeter`, Stichtag 15.05.2022, nur Gebäude mit Wohnraum,
  Cell-Key-Verfahren („–“ = auf Null geändert).
- Vergleich: Zellen, deren Mittelpunkt im Stadtteil Bornstedt liegt. Zensus-Summe „2010 und später“ gegen die Zahl der
  Wohngebäude im Rahmen, die die Automatik zwischen dem Flug 2009–2012 und dem ersten Flug nach dem Zensus-Stichtag
  erstmals sieht. Rein beschreibend, kein Abbruchkriterium: Zählweise (ALKIS-Umriss gegen Zensus-Gebäude),
  Stichtag und Flugjahre passen nur ungefähr.

## 7. Referenz (wird nach der Sichtprüfung eingetragen, vor dem Klassifikator)

Eingetragen am 05.11.2026 nach der Sichtung, vor dem ersten Code des Klassifikators.

- Datei: `referenz.csv` (200 Zeilen, Spalten nr, los, oid, funktion, flaeche_m2, k_ref, unklar, frueher_moeglich,
  form_abweichend, notiz), SHA256 `6f5a0fb5ceb6ffb737292cca9852e414ea8f7794b5169f84291e1ae8270d4173`
- Gesichtete Lose: 1 bis 5 (Nr. 1 bis 200). Nach Los 4 standen 46 Gebäude mit k_ref ≥ 4 in der Referenz, deshalb
  wurde Los 5 vollständig nachgezogen.
- Gebäude gesamt 200 / k_ref ≥ 4 (nach 2009): **56** / k_ref = 3: 29 / k_ref ≤ 2: 108 / unklar: 7
- Verteilung k_ref (ohne unklar): 0: 41, 1: 27, 2: 40, 3: 29, 4: 23, 5: 16, 6: 9, 7: 8
- `frueher_moeglich`: 30 Gebäude (alle k_ref ≤ 2), `form_abweichend` (Vorgängerbau an der Stelle): 14 Gebäude

## 8. Methode der Automatik (vor dem ersten Lauf festgelegt)

Committet zusammen mit dem Code, **bevor** `auswerten` zum ersten Mal läuft. Kein Parameter wird an der Referenz
abgestimmt; ändert sich die Methode nach dem ersten Lauf, stehen beide Läufe im Bericht.

1. Je Hauptgebäude des Rahmens (2.374) und Befliegung k ein Ausschnitt um den heutigen ALKIS-Umriss in Graustufen,
   geglättet auf die Bodenauflösung der Befliegung (Gauß, sigma = halbe Bodenauflösung: 1953 1 m, 1996 0,5 m,
   2007 0,4 m, ab 2012 0,2 m).
2. Kantenbild (Sobel-Betrag). Vorlage ist das Kantenbild der aktuellen Befliegung (2024) am selben Ort, gleich geglättet.
3. Wert(k) = größte Pearson-Korrelation zwischen Vorlage und Kantenbild k in der Maske „Umriss + 1,5 m Puffer“,
   gesucht über Verschiebungen bis ±2 m (Lagefehler zwischen den Befliegungen).
4. Schwelle je Befliegung = 95-%-Quantil einer Nullverteilung: dieselbe Vorlage gegen den Ausschnitt um den
   Mittelpunkt eines anderen Rahmengebäudes (fester Partner: nächstes in der Los-Reihenfolge) in derselben Befliegung.
5. sichtbar(k) = Wert(k) > Schwelle(k); 2024 gilt als sichtbar. k_auto ist die Stufe der Treppe „ab k sichtbar“ mit
   den wenigsten Abweichungen von sichtbar(0…7); bei Gleichstand die spätere Stufe.
6. Klammer: `nicht_vor` = Flugjahr der Befliegung k_auto − 1 (bei k_auto = 0 leer), `nicht_nach` = Flugjahr k_auto.
   Geschrieben werden nur Gebäude des Rahmens im Pilotgebiet (keine Nebengebäude, E5).
7. Erst nach der Klammer liest das Skript `referenz.csv` (SHA256 wird vorher geprüft) und wertet nach §5 aus.
