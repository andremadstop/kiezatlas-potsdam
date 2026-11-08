# Film „Was der Kiezatlas beantwortet“

Kurzer Erklärfilm (74 s, 1920 × 1080, 30 fps, ohne Ton) auf fünf Blättern im Stil eines Zeichenblatts, in den
Farben und der Schrift des Kiezatlas. Er zeigt, warum es den Atlas gibt, wer welche Frage an ihn stellt, was man
dabei über Potsdam erfährt, was die Zahlen nicht sagen und wie sich alles nachprüfen lässt. Gebaut mit
[Manim Community](https://www.manim.community/) 0.22.1, ohne LaTeX.

- `film.mp4`: der Film (H.264, yuv420p, `+faststart`, rund 8 MB)
- `standbild.png`: Blatt 3 mit dem ersten Befund (Fernwärme) im Endzustand, als Vorschaubild
- `film.gif`: Aufbau von Blatt 3 (Sekunde 27,7 bis 35,7 des Films), 960 px breit, 12 Bilder je Sekunde
- `film.py`: der Film als Programm; liest alle Daten selbst, kein zweites Skript

## Was die Blätter zeigen

| Blatt | Inhalt |
|---|---|
| 1 Warum | Frage „Was erfährt man über eine Stadt allein aus offenen amtlichen Daten?“, die 32 Stadtteilgrenzen. Danach die sieben Importläufe (Quelle, WFS oder CSV, Objekte neu, Laufzeit als Balken nach `laufzeit_s`), die Pipeline und die Karte mit den 3.443 Zensuszellen in fünf Stufen nach Einwohnern. Darunter die Zuordnung: 32 Stadtteile, 182.673 Einwohner in 3.443 Zellen (von 6.348 im Abrufrechteck), 52.309 Gebäude (von 85.046 im Abrufrechteck). |
| 2 Für wen | Sechs Nutzergruppen, je mit einer Frage der Startseite (wörtlich) und der Stelle, an der der Atlas antwortet. |
| 3 Befunde über Potsdam | Vier Aussagen, je mit Karte der Stadtteile, großer Zahl und Skala aller Stadtteile: Fernwärme 60,7 % der Wohnungen (Schlaatz 99,7 %, Bornim 4,5 %), Wohnungen in Häusern von vor 1949 25,7 % (Teltower Vorstadt 63,7 %, Waldstadt II 0,0 %), die meisten Kinder und Jugendlichen in Bornstedt (3.176 unter 18, 21,1 % von 15.063), gleichrangig daneben der höchste Anteil unter 18 in Bornim (22,2 %), der höchste Anteil ab 65 in Waldstadt I und Industriegelände (30,1 %, Stadt 20,2 %, niedrigster Golm 12,2 %; Skala und Karte nur bis 40 %, im Bild vermerkt). |
| 4 Grenzen offen | Bauzeit je Gebäude: 106 belegt, 26.610 geschätzt, 25.593 nicht datiert. Rücktest Stufe 4: 125 von 169 (74,0 %, 95-%-Intervall 66,9 bis 80,0 %), 193 Prüfgebäude in Bornstedt, Referenz eine Sichtprüfung von Luftbildern durch einen KI-Agenten ohne zweite Bewertung. Einzeljahr nur bei 53 Gebäuden, davon mit Wohnraum 0. Grenzfall: 91 Grenzzellen mit 1.605 Einwohnern, nach Mittelpunkt 182.673, nach Flächenanteil 182.779, größte Abweichung ab 5.000 Einwohnern Nauener Vorstadt +3,0 %. |
| 5 Belege | Zwei Prüfstände von `pruefen.sh` (je 18 Kästchen), das Entscheidungsprotokoll A1 bis A20, „Nicht geprüft sind“ (6 Punkte), die 12 Kernzahlen im README-Kasten „Zur Prüfung“, Adresse aus `CITATION.cff`. |

## Woher jede Zahl kommt

`film.py` liest beim Rendern aus den Dateien des Repos (nur lesen) und bricht mit „Beleg weicht ab: …“ ab, wenn
eine Datei etwas anderes sagt als erwartet (Funktion `belege()`). Die gelesenen Werte schreibt es nach
`zahlen.json` im Arbeitsordner.

| Im Film | Datei |
|---|---|
| Sieben Läufe: Quelle, Typ, `status ok`, Objekte neu (32 / 6.348 / 85.046 / 220 / 106 / 28.121 / 6.334), Laufzeit | `belege/2026110*Z.json` (`quellen[0]`, `laufzeit_s`), Kopfzeile der gleichnamigen `.txt` als Gegenprobe |
| Kita-Lauf als unvollständig markiert, Warnung „Nur 220 von 240 gemeldeten Objekten erhalten“ | `belege/20261105T093628Z.json` (`quellen[0].unvollstaendig = true`, `unvollstaendig = ["mbjs_kita"]`, `warnungen[0]`, Satzanfang wörtlich) |
| 220 Kitas, 17 mit mehreren Häusern | `belege/README.md`, Zeile zu `20261105T093628Z` |
| 182.673 Einwohner, 3.443 Zellen, 52.309 Gebäude, 85.046 im Abrufrechteck | `daten/kennzahlen.json` (`stadt`, `kontrolle`); Zellen und Summe zusätzlich gegen `daten/zellen.js` |
| 6.348 Zellen im Abrufrechteck | `belege/20261104T132325Z.json` (`zensus_gitter`, neu) |
| Fragen auf Blatt 2 | `index.html`, `<h2 class="frage__titel">` der Fragen 1, 3, 6, 7, 8, 9; die Antwortzeilen sind gekürzt, ihre Kernstellen werden in `index.html` gesucht |
| 19 Planungsräume | `belege/A6_planer_20261105.md` |
| Befunde (Anteile, Zähler, Nenner, Extremwerte) | `daten/kennzahlen.json` (`stadt.kacheln`, `stadtteile.*.kacheln`); Anteile gegen Zähler / Nenner nachgerechnet; Extremwerte nur unter den 26 Stadtteilen ab 1.000 Einwohnern (Kinder: meiste nach Anzahl Bornstedt, höchster Anteil Bornim 22,2 %) |
| Stichtag 15.05.2022 in der Fußzeile von Blatt 3 | `daten/kennzahlen.json`, Feld `quelle` der Kacheln (alle fünf mit demselben Stichtag geprüft) |
| 100.998 Wohnungen | `daten/kennzahlen.json` (`stadt.verteilungen.baujahr.insgesamt` = Nenner der Kacheln Altbau und Fernwärme) |
| 106 / 26.610 / 25.593 | `daten/jahre_methode.js` (`je_g`), Summe = 52.309 |
| 125 von 169, 74,0 %, 66,9 bis 80,0 %, 193 Gebäude | `daten/jahre_methode.js` (`ruecktest[id=luftbild]`) und `berichte/B4_holdout.md` (Tabelle und Abschnitt „Rücktest“) |
| Einzeljahr 53, mit Wohnraum 0 | `berichte/B4_holdout.md` und `daten/jahre_methode.js` (`jahr`) |
| Grenzfall 91 / 1.605 / 182.673 / 182.779 | `daten/kennzahlen.json` (`grenzfall.stadt`) |
| Nauener Vorstadt +3,0 % | eigene Rechnung aus `grenzfall.stadtteile`: (Mittelpunkt − Flächenanteil) / Flächenanteil, nur Stadtteile ab 5.000 Einwohnern |
| A1 bis A20 (lückenlos, mindestens bis A20), A3, 6 Punkte „Nicht geprüft sind“ | `docs/entscheidungen.md` (Überschriften `## A…`) |
| Prüfstand 06.11.2026, `1cf8d56`: 18 Prüfungen, 16 grün, 2 mit Befund (`A6_test_pfade.py`, `p1_themen.mjs`), davon 4 im Browser | `belege/pruefstand-20261106-1cf8d56/pruefen.log` (Kopf und „== Zählung“), „ohne Netz und ohne Datenbank“ aus `belege/README.md` |
| Stand `4559a52`: 18 von 18 grün, Zitat „Stand 4559a52: 18/18 grün“ | `berichte/audit_20261106.md`, Tabellenzeile K29 (wörtlich gelesen) |
| optional ein dritter Prüfstand | nur über `PRUEFLOG`, und nur wenn die Datei unter `belege/` liegt (siehe unten) |
| 12 Kernzahlen | `README.md`, Tabelle „Zur Prüfung“ |
| souverain-systems.de/kiezatlas | `CITATION.cff` (`url`) |

## Was schematisch ist

Im Bild benannt: der Aufbau auf Blatt 1 („Aufbau schematisch, Karte aus den Daten“), die Reihenfolge der
Kästchen im Rücktest und bei den Prüfständen (Treffer bzw. grüne Prüfungen zuerst) und die Zelle auf der Grenze
(„Zelle schematisch“, keine echte Zelle, keine Einwohnerzahl). Maßstäblich sind die Laufzeitbalken
(`laufzeit_s`, linear), der Balken der Bauzeit-Herkunft und die Skalen auf Blatt 3. Die Karten sind aus
`daten/stadtteile.js` (auf 25 m vereinfacht) und `daten/zellen.js` gezeichnet, in Meter umgerechnet mit einer
lokalen Näherung um 52,42° N (Fehler unter 0,5 %).

Die Zuordnung der Nutzergruppen zu den Fragen auf Blatt 2 ist eine Auswahl für den Film und steht so im Bild.
Die Klassen der Karten auf Blatt 3: Anteile in Stufen zu 20 Prozentpunkten wie auf der Startseite, beim Anteil ab 65 in Stufen zu 8 Prozentpunkten auf einer Skala 0 bis 40 % (alle bewerteten Stadtteile liegen zwischen 12 und 31 %, das Skript prüft, dass keiner 40 % erreicht; im Bild vermerkt), Kinder
(Anzahl) in Fünfteln der 26 Stadtteile ab 1.000 Einwohnern. Die 6 kleineren Stadtteile sind grau und „nicht
bewertet“, weil die Geheimhaltung des Zensus dort zu unscharf ist.

## Datenschutz

Kein Einzeljahr, keine Adresse, keine Gebäudekennung und keine Zellkennung im Bild. Die Bauzeit erscheint nur
als Zählung der Herkunft (belegt, geschätzt, nicht datiert). Namen stehen nur für Stadtteile.

## Namensnennung

Im Bild steht je Blatt der Vermerk der gezeigten Daten, wörtlich aus `daten/LIZENZ.md`, `QUELLEN.md` und
`daten/jahre/*.js`; nur der Link in Klammern ist im Bild weggelassen. Vollständig:

- Stadtteilgrenzen: © Landeshauptstadt Potsdam, dl-de/zero-2-0
- Zensus, Zellen, Kennzahlen: © Statistische Ämter des Bundes und der Länder, Zensus 2022; Gebäudezahlen © GeoBasis-DE/LGB; jeweils dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)
- Gebäude, ALKIS-Nutzung: © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)
- Kitas, Schulen: © Ministerium für Bildung, Jugend und Sport, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)
- Bauzeit: © Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung); Gebäudeform © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung); belegte Bauzeiten: Wikidata, CC0 1.0

## Neu bauen

Voraussetzungen: Python 3.13 mit `manim==0.22.1`, `fonttools`, `brotli` und `shapely` (geprüft mit 4.68.0,
1.2.1, 2.2.0), die Systembibliotheken von Manim (Cairo, Pango), und ffmpeg. Eine Monospace-Schrift braucht der Film nicht (DESIGN.md: keine Monospace-Etiketten). Barlow
kommt aus `fonts/` des Repos: `film.py` wandelt die woff2-Dateien in ttf um (in den Arbeitsordner) und meldet
sie bei Pango an. Fehlt eine Schrift, bricht das Skript ab, statt still eine andere zu nehmen.

Aus der Repo-Wurzel, Arbeitsordner zum Beispiel `berichte/filme/erklaer` (von Git ausgeschlossen):

```sh
export FILM_ARBEIT=berichte/filme/erklaer
# optional: eingechecktes Protokoll eines weiteren Laufs von ./pruefen.sh (muss unter belege/ liegen)
# export PRUEFLOG=belege/<pruefstand-…>/pruefen.log
manim -qh --frame_rate 30 --disable_caching --media_dir $FILM_ARBEIT/media docs/filme/erklaer/film.py Erklaer
ffmpeg -i $FILM_ARBEIT/media/videos/film/1080p30/Erklaer.mp4 -c:v libx264 -crf 20 -preset slow \
    -pix_fmt yuv420p -movflags +faststart -an docs/filme/erklaer/film.mp4
# Standbild: Blatt 3, erster Befund
manim -qh -s --disable_caching --media_dir $FILM_ARBEIT/media docs/filme/erklaer/film.py Standbild
cp $FILM_ARBEIT/media/images/film/Standbild_ManimCE_v0.22.1.png docs/filme/erklaer/standbild.png
# GIF: Aufbau von Blatt 3
ffmpeg -ss 27.7 -t 8 -i docs/filme/erklaer/film.mp4 -vf "fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" docs/filme/erklaer/film.gif
```

Ohne `--frame_rate 30` rendert `-qh` mit 60 fps. Die Szene `Probe` rendert nur Blatt 1 und den ersten Befund.
`PRUEFLOG` darf Zeilen mit vorangestellter Uhrzeit enthalten („07:39:10.586 + 654.866s | …“), sie wird
abgeschnitten. Die Datei muss unter `belege/` liegen, sonst bricht das Skript ab: Jede sichtbare Zahl kommt aus
einer Datei im Repo. Die eingecheckte `film.mp4` ist ohne `PRUEFLOG` gebaut und zeigt die beiden belegten
Prüfstände (06.11.2026 und Stand `4559a52`); sie lässt sich aus dem Repo allein nachbauen.
