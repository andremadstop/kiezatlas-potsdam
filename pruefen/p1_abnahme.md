# Abnahme Paket P1: gemeinsamer Themenkern (`themen.js`), 05.11.2026

Zweig `ausbau/p1` auf `ausbau/p0` (`ef0ffa6`). Vertrag: `daten/schema/themen.md`. Kein neues Thema.

## Was sich geändert hat

- **Neu `themen.js`** (`window.KIEZ_THEMEN`): Themen mit Hash-Schlüssel `h`, Klassen, Farben, Höhen,
  Geometrie, Stadtteilfarben, Texthelfer, Ebenen-Register (`ebenen.registrieren/liste/zellwerte`) und
  `laden` (per `<script>`, nie `fetch`). 3.522 B gz (Vertrag: höchstens 6 KB).
- **`atlas.js`, `karte.js`**: die doppelten Definitionen (Themenliste, Klassen, `farbe`, Höhe, Stadtteilfarben,
  `polys`, `umriss`, `GANZ`, Texthelfer) sind entfernt; beide lesen aus `KIEZ_THEMEN`. `atlas.js` übergibt
  den animierten Höhenfaktor als `hoehe(t, { faktor: hk.k })`. `window.KIEZ` trägt nur noch den Seitenzustand
  (`FRAGE`, `GZ`, `waehle`, `zustand`, `schritt`, `TITEL`, `schauGebiet`, `schaugrafik`).
- **`schaugrafik.js`**: Themen, Klassen, Farben, Geometrie und Texthelfer kommen aus `KIEZ_THEMEN` (Alias
  `KT`, weil `T` dort die Textfunktion ist); Seitenzustand weiter aus `window.KIEZ`.
- **`index.html`, `karte.html`**: je eine Zeile `<script defer src="themen.js">` vor `atlas.js` bzw. `karte.js`,
  wie im Vertrag vorgeschrieben. Sonst nichts an den Seiten (Eigentümer I1).
- **Neu `pruefen/p1_gleich.mjs`** (Gleichheitsprobe vorher/nachher) und **`pruefen/p1_themen.mjs`**
  (Vertragsprobe für Register, Nachladen, Zellwerte, eigene Klassen).

## Abnahme laut Bauplan

| Kriterium | Ergebnis | Beleg |
|---|---|---|
| Jeder Punkt in `pruefen/INVENTAR.md` einzeln abgehakt | ja | Tabelle unten |
| `pruefen/seiten.mjs` grün | ja | `node pruefen/seiten.mjs`: „grün“, Rückgabe 0 |
| Gewicht der Startseite höchstens ± 2 KB gz | ja, +1.964 B (Spielraum 84 B) | Summe zlib -9 je Datei wie in `seiten.mjs`, gegen `ef0ffa6`: `themen.js` +3.522, `atlas.js` −1.529 (auch ohne die Helfer-Aliase in `window.KIEZ`), `schaugrafik.js` −34, `index.html` +5. `seiten.mjs` gerundet: 468 → 470 KB JS, 601 → 603 KB gesamt. `karte.html`: +2.169 B (407 → 409 KB JS) |
| `grep -c "function stufen"` über `atlas.js` und `karte.js` = 0 | ja | `atlas.js:0`, `karte.js:0`; die Themenliste (`var THEMEN = [`, `TOENE`, `"Anteil unter 18 Jahre"`) steht nur in `themen.js` |
| Schaugrafik-SVG gleich wie vorher | ja, Diff leer | `p1_gleich.mjs`: Export-SVG mit eingebetteten Schriften für Kartenthema Einwohner, Fernwärme, Stadtteile (ganz Potsdam) und Durchschnittsalter (Vergleich 13 + 52), 4 von 4 Zeichen für Zeichen gleich (349 bis 539 KB). Das SVG trägt nur Datenstände (z. B. 4.11.2026), keinen Erstellungszeitpunkt, darum war nichts auszublenden |

## Inventar (`pruefen/INVENTAR.md`), einzeln

Grundlage: `node pruefen/seiten.mjs` (grün), `python -I pruefen/daten.py` (0 Abweichungen),
`node pruefen/p1_gleich.mjs` gegen `../kiezatlas-wt-P0` (Stand `ausbau/p0`) und gegen diesen Zweig, dann
`--vergleich`: 77 Abschnitte, alle gleich, 0 Seitenfehler.

| # | Punkt | Ergebnis | Beleg |
|---|---|---|---|
| S1 | `index.html`, `karte.html` per `file://` und HTTP ohne Konsolenfehler | ✓ | `seiten.mjs`: 0 Fehler in allen vier Läufen |
| S2 | sieben Fragen plus Auftakt und „Selbst erkunden“, Scroll-Steuerung | ✓ | Schritte 0–8 vorhanden, 1/3/5/7 werden aktiv; alle `data-q`-Texte gleich (`index_felder`) |
| S3 | alle sieben Themen auf beiden Seiten schaltbar | ✓ | je 7 Themen; MapLibre-Stil (`paint`, `filter`) von `zellen-flach`/`zellen-2d`, `zellen-3d`, `teile-flaeche` je Thema gleich (Startseite 7, freie Karte 7 × 2D/3D) |
| S4 | Hash-Links der freien Karte | ✓ | Rundreise `#thema=fern&st=52&3d=1&luft=1&geb=1&k=…` gleich; Hash je Thema und Lesen von `#thema=vor1949&st=13` gleich wie vorher |
| S5 | Schalter 3D, Luftbild, Gebäude | ✓ | `seiten.mjs` schaltet ohne Fehler |
| S6 | Schaugrafik-Export SVG, PNG, Druck/PDF | ✓ | SVG 524 KB mit `@font-face`, PNG 832 KB, PDF 226 KB (wie Ausgangswert); SVG-Diff leer (oben) |
| S7 | reduzierte Bewegung an und aus | ✓ | Bewegung an: 0 Fehler; `reduce` wird erkannt |
| S8 | Kopfzahlen | ✓ | rund 182.700, 17,9 %, 20,2 %, 25,7 %, 60,7 %; `#stadtzahlen` gleich |
| S9 | Register mit sechs Sortierungen | ✓ | je 32 Zeilen, 6 Spitzenreiter; `#teile` je Sortierung gleich |
| S10 | axe ohne Verstoß | ✓ | 0 Verstöße auf beiden Seiten, beide Wege |
| S11 | Steckbrief, Gegenprobe, Verteilungen; Grenzfall; Methode | ✓ | statt nur Sichtprüfung verglichen: `#kacheln` (Startseite, freie Karte, Stadtteil 13), `#grenz-figur`-SVG, Grenzfall-Texte und -Tabelle gleich |
| S12 | Gewicht beim Start | ✓ | siehe oben, +1.964 B gz auf der Startseite |
| D1–D6 | Daten | ✓ | `daten.py`: 0 Abweichungen (P1 ändert keine Datei in `daten/`) |

## Vertragsprobe (`node pruefen/p1_themen.mjs`, grün per `file://` und HTTP)

- `KIEZ_THEMEN` hat genau die 27 Namen aus dem Vertrag; Paare `id/h` wie im Vertrag.
- `laden`: zwei gleichzeitige Aufrufe erzeugen ein Script-Tag, beide bekommen dasselbe Objekt; liegt das
  Global schon vor, kommt `fertig` sofort; fehlende Datei: `fertig(null)` und Meldung in `#ladestatus`
  (`aria-live="polite"`, wird bei Bedarf angelegt).
- `ebenen.registrieren` hängt Themen an `THEMEN` an (mit `t.ebene`, `HASH`), doppelte `id` wird ignoriert;
  `ebenen.zellwerte` liefert für `daten/fixtures/erreichbar.js` 3.443 Werte, bei falscher `erste_id`, falscher
  `anzahl`, unbekannter Art oder Ebene `null` und eine Meldung.
- `farbe`/`klasse` mit eigenen Grenzen, `klassen` über übergebene Features, `hoehe` mit `faktor`.
- Ebenen-Thema ohne Werte (noch nicht eingemischt): `farbe(t)` gibt eine Farbe statt eines ungültigen
  `step`-Ausdrucks, die Klassen werden nicht gemerkt; MapLibre nimmt den Ausdruck an. Nach dem Einmischen von
  `erreichbar_fuss_odbl.js` (Art `hort`) und `setData` hat `farbe(t)` Quintile `[7,12,19,24]`.
- `ebenen.zellwerte` auf `jahre_zellen.js` (`gebaeude`, `vorherrschend`, `anteile`): je 3.443; nur Listen
  werden angenommen.
- `registrieren` mit vergebener Themen-`id` oder vergebenem `h`: das alte Thema bleibt, nichts doppelt.
- `laden` mit gleicher Datei und verschiedenem Global: getrennte Warteschlangen.

## Gegenprobe

`/code-review` (medium) auf `ef0ffa6..` samt Arbeitsstand. Behoben im zweiten Commit: leere Klassen bei
Ebenen-Themen (ungültiger MapLibre-Ausdruck, falscher Cache), Höhe bei Spannweite 0, Kollision von Themen-`id`/`h`
beim Registrieren, `laden` mit gleicher Datei und anderem Global, `zellwerte` nur für Listen. Nicht geändert,
begründet unten: Lesart von `art`, Legende bei Ebenen-Themen, kein Neuberechnen gemerkter Klassen, harte
Abhängigkeit von `themen.js`, eigene `werte()` in `atlas.js` (nur für den Median der Frage 1).

## Offen (nicht in P1 lösbar)

- **Lesart von `zellwerte(id, art)`.** Der Vertrag lässt offen, ob `art` die Ebenenart (`"zellwert"`) oder der
  Schlüssel einer Liste ist. `themen.js` liest es als Schlüssel: zuerst `werte[art]` (erreichbar*.js: `kita`,
  `hort` …), sonst eine Liste oben in der Datei (`jahre_zellen.js`: `gebaeude`, `vorherrschend`, `anteile`, die
  kein `werte` hat). Mit `"zellwert"` kommt `null`. Bitte in `themen.md` festhalten (P0/I1), A7 und B5 danach richten.
- **Legende bei Ebenen-Themen.** `atlas.js` und `karte.js` lesen in der Legende `KLASSEN[t.id]`. Für Ebenen-Themen
  steht dort erst nach dem Einmischen etwas (bzw. nie, wenn die Seite eigene Klassen übergibt). Solange keine Ebene
  in diese Seiten eingehängt ist, tritt das nicht auf; I1 muss die Legende beim Einhängen umstellen.
- **Gemerkte Klassen** werden nicht neu gerechnet, wenn eine Seite andere Werte in dieselbe Eigenschaft schreibt.
  Wer das braucht, löscht `KIEZ_THEMEN.KLASSEN[id]` vor dem neuen `farbe(t)`.
- **`themen.js` ist Pflicht.** Fehlt die Datei (Deploy, alter Cache), bleiben Startseite und Karte leer.

- **Konsolenfehler beim Ladefehler.** Der Vertrag verlangt bei einem Ladefehler „kein Konsolenfehler“. Der
  Browser selbst meldet eine fehlende Datei (`net::ERR_FILE_NOT_FOUND` bzw. 404) in der Konsole, das lässt
  sich aus dem Skript nicht unterdrücken. `themen.js` selbst wirft nichts. Klärung über P0/I1 im Vertrag.
- **`name()` braucht `KIEZ_KENNZAHLEN`**, der Vertrag nennt nur Zellen, Stadtteile und CSS-Variablen. Die
  Ladereihenfolge im Vertrag lädt `kennzahlen.js` zuerst, darum geht es; `themen.js` liest es erst beim Aufruf.
- **Gewicht der freien Karte** +2.169 B gz (Grenze im Bauplan gilt nur für die Startseite). Auf der Startseite bleiben 84 B Spielraum; I1 sollte neue Zeilen in `themen.js` gegen die Grenze rechnen.
- **Deploy**: `themen.js` muss mit ausgeliefert werden (neue Datei im Wurzelverzeichnis).
