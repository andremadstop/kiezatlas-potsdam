# Feature-Inventar und Ladebetrieb (Paket P0, 05.11.2026)

Was nach dem Ausbau (Planer-Ebene A, Gebäudejahre B) noch genau so funktionieren muss (globale Regel 16).
Jeder Punkt ist das Abnahmekriterium für P1 und die Integration, nicht „sauberer Code“. Ausgangswert ist
der unveränderte Stand `e737b50`, geprüft mit `node pruefen/seiten.mjs` und `python -I pruefen/daten.py`.

## 1. Seiten

| # | Was muss funktionieren | Wie geprüft | Ausgangswert 05.11.2026 |
|---|---|---|---|
| S1 | `index.html` und `karte.html` laden per Doppelklick (`file://`) und per HTTP, ohne Konsolenfehler | `seiten.mjs`, beide Wege | grün, 0 Fehler |
| S2 | Sieben Fragen (Schritte 1–7) plus Auftakt (0) und „Selbst erkunden“ (8); Scroll-Steuerung setzt die aktive Frage (GSAP ScrollTrigger, sonst IntersectionObserver) | `seiten.mjs`: Fragen 1, 3, 5, 7 werden beim Scrollen aktiv; seit 07.11. je Frage `zellen-3d` aus und 0 gerendert, Zellen flach (`zellen-2d`) und von oben, Klick auf eine Zelle öffnet ihr Fenster, „3D-Häuser“ zeigt Gebäude; seit Gegenprobe 2 Doppelklick ohne Fenster, „3D-Häuser“ vorn, Zoom ab 15,5, flache Zellen darunter, Weiterlesen behält 3D | grün |
| S3 | Alle sieben Themen lassen sich auf beiden Seiten schalten | `seiten.mjs` | grün (7 Themen je Seite) |
| S4 | Hash-Links der freien Karte: `thema`, `st`, `3d`, `luft`, `geb`, `k=zoom/lat/lng/pitch/bearing` überstehen Neuladen | `seiten.mjs` Hash-Rundreise | grün: `#thema=fern&st=52&3d=1&luft=1&geb=1&k=14.20/52.39350/13.07000/45/-12` |
| S5 | Schalter 3D-Häuser, Luftbild, Gebäude (freie Karte); Gebäude je Stadtteil werden erst bei Auswahl nachgeladen. Seit 07.11.: „3D-Häuser“ zeigt nur Gebäude als Körper (keine Zensus-Säulen), wählt ohne Stadtteil einen und leert den Hinweis | `seiten.mjs` (schalten ohne Fehler; „3D-Häuser“ ohne Stadtteil bei 1440 und 390 px) | grün |
| S6 | Schaugrafik-Export: SVG mit eingebetteten Schriften, PNG 300 dpi, Druck/PDF | `seiten.mjs`: Download SVG (524 KB, `@font-face`), PNG (832 KB), Druckblatt + PDF (226 KB) | grün |
| S7 | Reduzierte Bewegung: Kamera springt (Säulen gibt es seit 07.11. auf keiner Seite mehr), keine Leerlaufdrehung; ohne Einstellung laufen Animationen fehlerfrei | `seiten.mjs` mit `reducedMotion` an und aus | grün |
| S8 | Kopfzahlen im Auftakt: fünf Kacheln (Einwohner gerundet, unter 18, 65+, vor 1949, Fernwärme) | `seiten.mjs` | grün: rund 182.700, 17,9 %, 20,2 %, 25,7 %, 60,7 % |
| S9 | Register der 32 Stadtteile mit sechs Sortierungen | `seiten.mjs`: je 32 Zeilen, verschiedene Spitzenreiter | grün (6 Sortierungen) |
| S10 | Barrierefreiheit: axe ohne Verstoß | `seiten.mjs` (per `file://` ohne CSS-Vorladen von axe) | 0 Verstöße auf beiden Seiten |
| S11 | Steckbrief mit Gebietswahl, Gegenprobe, Verteilungen; Grenzfall-Abschnitt; Methode und Quellen | Sichtprüfung (nicht automatisiert) | vorhanden |
| S12 | Gewicht beim Start (eigene Dateien bis `KIEZ_BEREIT`, gzip -9) | `seiten.mjs` | `index.html` 468 KB gz JS / 601 KB gz gesamt; `karte.html` 407 KB gz JS / 536 KB gz gesamt |

Keine Fremdabrufe beim Prüfen: Kacheln von basemap.de und das Luftbild der LGB beantwortet der Prüfbrowser
selbst mit einem leeren Bild (je Lauf rund 110 bzw. 70 Anfragen ersetzt).

## 2. Daten

| # | Was muss stimmen | Wie geprüft | Ausgangswert |
|---|---|---|---|
| D1 | Σ Einwohner über `zellen.js` = Kachel Einwohner Stadt; je Stadtteil Einwohner und Zellen | `daten.py` | 182.673 in 3.443 Zellen, 32 Stadtteile ohne Abweichung |
| D2 | Gebäude je Stadtteil in `daten/gebaeude/<nr>.js` = `kennzahlen`; Σ = `kontrolle.gebaeude_in_potsdam` | `daten.py` | 52.309 (85.046 im Rechteck) |
| D3 | Anteile der Kacheln = zaehler/nenner; `kennzahlen.js` = `kennzahlen.json` | `daten.py` | 0 Abweichungen |
| D4 | Jede Datei in `daten/` hat einen Vertrag in `daten/schema/` und besteht ihn; Werte in Zellreihenfolge haben die Länge von `zellen.js` | `daten.py` | 35 Dateien, 0 Abweichungen |
| D5 | ODbL nur in `*_odbl`-Dateien; keine Adress-/Kontaktfelder; keine feinen Zensusklassen als Feld | `daten.py` | 0 Abweichungen |
| D6 | Jede Fixture besteht ihren Vertrag und trägt `fixture: true` | `daten.py` | 8 Fixtures, 0 Abweichungen |

## 3. Datenbank (gemeinsamer Container `kiezatlas-potsdam-db-1`)

- `sql/002_ausbau.sql` eingespielt (als admin über `skripte/ausbau_einrichten.py`): Schema `auswertung` mit 15 Tabellen,
  neue Ziele `public.zensus_struktur`, `public.mbjs_kita`, `public.mbjs_schule`, `public.alkis_nutzung`, `public.planungsraum`.
- Rolle `kiezatlas_rechnen` (Passwort `RECHNEN_PASSWORD` in `../kiezatlas-potsdam/.env`, chmod 600, nur als SCRAM-Hash an den Server).
  **Entscheidung:** kein CREATE in `auswertung` (DDL nur aus P0, Bauplan 0.2); Zwischenergebnisse in TEMP-Tabellen.
  Rechte: CONNECT, TEMPORARY; SELECT auf `public`; SELECT/INSERT/UPDATE/DELETE/TRUNCATE auf `auswertung`, außer dem Snapshot (nur SELECT).
- `mosidi_lesen` liest `auswertung`, aber nicht `auswertung.gebaeude_adresse` (Adressen nie in `daten/`).
- Snapshot `auswertung.gebaeude_stand_20261105`: 85.046 Gebäude, Kopie von `public.gebaeude`. Teil B bezieht sich nur darauf.
- `pipeline.einrichten --haerten` lief **einmal** (05.11.2026, über `skripte/lauf.sh einrichten`), mit allen Zielen der YAML.

Rechtetest (05.11.2026, als `kiezatlas_rechnen`):

| Versuch | Ergebnis |
|---|---|
| `INSERT INTO public.stadtteil …` | `permission denied for table stadtteil` (richtig) |
| `CREATE TABLE public.versuch …` | `permission denied for schema public` (richtig) |
| `CREATE TABLE auswertung.versuch …` | `permission denied for schema auswertung` (richtig) |
| `UPDATE auswertung.gebaeude_stand_20261105 …` | `permission denied` (richtig) |
| `INSERT INTO auswertung.osm_poi …` (mit ROLLBACK) | `INSERT 0 1` (richtig) |
| `INSERT INTO auswertung.gebaeude_jahr … quelle 'OpenStreetMap start_date'` | `violates check constraint gebaeude_jahr_quelle_check` (richtig) |
| `SELECT … FROM auswertung.gebaeude_adresse` als `mosidi_lesen` | `permission denied` (richtig) |

## 4. Ladebetrieb

**Einzelquelle: ja.** `pipeline.laden` kennt `--nur QUELLE` (`geodaten-import-pipeline/pipeline/laden.py`, Argument `--nur`);
mit `--nur` wird der Rhythmus übergangen, `aktiv: false` aber nicht (solche Quellen lädt auch `--nur` nicht).

Regeln:
1. **Jeder Lauf nur mit `--nur <quelle>`.** `skripte/lauf.sh laden` bricht ohne `--nur` ab. Ein Lauf ohne `--nur` lädt jede
   fällige Quelle, auch `gebaeude_alkis` (die Pipeline löscht dann Gebäude, die der Dienst nicht mehr liefert, und die `oid`
   von Teil B wären weg).
2. **Kein Gebäude-Lauf, solange Teil B läuft.** Teil B nutzt den Snapshot. `gebaeude_alkis` steht deshalb in der YAML auf
   `aktiv: false`; die Pipeline lädt sie dann auch mit `--nur` nicht (Rechte bleiben).
3. **`einrichten` startet nur P0 bzw. der Ladekoordinator** (`skripte/lauf.sh einrichten`). Eine neue Quelle braucht einen
   YAML-Eintrag und ein Ziel in `sql/002` und danach genau einen Lauf von `einrichten`.
4. **Seriell.** Pipeline-Läufe nie parallel; die Pipeline sperrt selbst (`LaufLaeuftNoch`), trotzdem nacheinander starten.
5. Eigene Ladeskripte (B1 `zensus_gebaeude_jahr`, B0 NAS) schreiben mit `kiezatlas_rechnen` nach `auswertung`, nicht über die Pipeline.
6. Rohdaten nur unter `$KIEZ_DATEN/<quelle>/<stand>/` mit `HERKUNFT.md`; jede Anfrage über `skripte/abruf.py` (Abstand je Rechner, Protokoll).

Quellen in `config/potsdam.yaml` und wer sie lädt:

| Quelle | Ziel | Lädt | Liest | Stand |
|---|---|---|---|---|
| `stadtteile`, `zensus_gitter`, `gebaeude_alkis` | `stadtteil`, `zensus_zelle`, `gebaeude` | Bestand (nicht neu laden) | alle | 04.11.2026 |
| `zensus_struktur` | `public.zensus_struktur` | A1 (`vorbereitet/zensus_struktur.csv`, Spalten = Zielspalten, dazu `gitter_id;x;y` in EPSG:3035) | A6 | leer |
| `mbjs_kita` | `public.mbjs_kita` | P0 | A2 | 220 Zeilen (05.11.) |
| `mbjs_schule` | `public.mbjs_schule` | P0 | A2 | 106 Zeilen (05.11.) |
| `alkis_nutzung` | `public.alkis_nutzung` | P0 | A2 | 28.121 Zeilen (05.11.) |
| `planungsraeume` | `public.planungsraum` | Ladekoordinator nach H1 (`skripte/03_planungsraeume.py`) | A6, A8 | leer, H1 fehlt |

Nicht in der YAML (Korrektur 17): `auswertung.zensus_gebaeude_jahr` schreibt B1 selbst aus den Zips.

## 5. Ergänzungen zu Tabelle 0.4 (Eigentümer)

| Datei / Objekt | Eigentümer | Andere |
|---|---|---|
| `public.mbjs_kita`, `public.mbjs_schule`, `public.alkis_nutzung` | P0 lädt per `--nur` | A2 liest |
| `public.planungsraum` | Ladekoordinator (P0 bzw. I1) | A6, A8 lesen |
| `auswertung.gebaeude_stand_20261105` | P0 | nur lesen |
| `auswertung.zelle_gruen` (Korrektur 22) | A5 | lesen |
| `auswertung.jahr_beleg.nur_pruefung` (OSM, Wikipedia) | B2 | lesen |
| `config/richtwerte.yaml` | A6; Abschnitt `oepnv` zwischen den Markern nur A4 | lesen |
| `skripte/abruf.py`, `skripte/ausbau_einrichten.py`, `skripte/03_planungsraeume.py` | P0 | nutzen |
| `pruefen/seiten.mjs`, `pruefen/daten.py`, `pruefen/fixtures_erzeugen.py` | P0 | eigene `pruefen/<paket>_*` |

## 6. Befunde aus dem Laden (für A2)

- MBJS Kitas: 240 Einträge, 220 `id_kita`; 17 Kitas mit mehreren Häusern, gleiche Kapazität je Eintrag. In Potsdam
  151 Kitas (nicht 171) mit 20.953 Plätzen (nicht 24.581, das war je Eintrag summiert). Alle Standorte:
  `$KIEZ_DATEN/mbjs/2026-11-05/kitas_standorte.geojson`.
- MBJS Schulen: 78 in Potsdam (75 mit Ort „Potsdam“, 3 mit „Potsdam/OT …“), 31 mit Schulform „Grundschule“
  (weitere Grundschulteile in kombinierten Schulformen).
- ALKIS-Nutzung: keine Fläche mit „Spiel“ in `bez`; Spielplätze also nicht aus ALKIS.
