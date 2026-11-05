# Abnahme Paket P1: gemeinsamer Themenkern (`themen.js`), 05.11.2026

Zweig `ausbau/p1` auf `ausbau/p0` (`ef0ffa6`). Vertrag: `daten/schema/themen.md`. Kein neues Thema.

## Was sich geändert hat

- **Neu `themen.js`** (`window.KIEZ_THEMEN`): Themen mit Hash-Schlüssel `h`, Klassen, Farben, Höhen,
  Geometrie, Stadtteilfarben, Texthelfer, Ebenen-Register (`ebenen.registrieren/liste/zellwerte`) und
  `laden` (per `<script>`, nie `fetch`). 3,4 KB gz (Vertrag: höchstens 6 KB).
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
| Gewicht der Startseite höchstens ± 2 KB gz | ja, +1.875 B | Summe gzip -9 je Datei wie in `seiten.mjs`: `themen.js` +3.433, `atlas.js` −1.403 (gekürzt um die Helfer-Aliase), `schaugrafik.js` −34, `index.html` +5. `seiten.mjs` gerundet: 468 → 470 KB JS, 601 → 603 KB gesamt. `karte.html`: +2.080 B (409 KB JS) |
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
| S12 | Gewicht beim Start | ✓ | siehe oben, +1.875 B gz auf der Startseite |
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

## Offen (nicht in P1 lösbar)

- **Konsolenfehler beim Ladefehler.** Der Vertrag verlangt bei einem Ladefehler „kein Konsolenfehler“. Der
  Browser selbst meldet eine fehlende Datei (`net::ERR_FILE_NOT_FOUND` bzw. 404) in der Konsole, das lässt
  sich aus dem Skript nicht unterdrücken. `themen.js` selbst wirft nichts. Klärung über P0/I1 im Vertrag.
- **`name()` braucht `KIEZ_KENNZAHLEN`**, der Vertrag nennt nur Zellen, Stadtteile und CSS-Variablen. Die
  Ladereihenfolge im Vertrag lädt `kennzahlen.js` zuerst, darum geht es; `themen.js` liest es erst beim Aufruf.
- **Gewicht der freien Karte** +2.080 B gz (Grenze im Bauplan gilt nur für die Startseite).
- **Deploy**: `themen.js` muss mit ausgeliefert werden (neue Datei im Wurzelverzeichnis).
