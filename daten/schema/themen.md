# Vertrag: `themen.js` (`window.KIEZ_THEMEN`)

Festgelegt von P0 am 05.11.2026 (Prüfbericht, Korrektur 20). **P1** baut `themen.js` genau so; **A7**
(`planer.html`) und **B5** (`jahre.html`) bauen dagegen, bevor P1 fertig ist. Änderungen nur über P0 bzw.
die Integration, nicht still in P1.

Herkunft: Die Funktionen stehen heute doppelt in `atlas.js` (Zeilen 62–103, 141–144) und `karte.js`
(Zeilen 15–59). Der Vertrag beschreibt, was beide schon tun, mit einheitlichen Namen. Er bringt kein
neues Thema.

## Laden

```html
<script defer src="daten/kennzahlen.js"></script>
<script defer src="daten/stadtteile.js"></script>
<script defer src="daten/zellen.js"></script>
<script defer src="vendor/maplibre-gl.js"></script>
<script defer src="themen.js"></script>      <!-- vor atlas.js, karte.js, planer.js, jahre.js -->
<script defer src="atlas.js"></script>
```

- Reines ES5 wie die übrigen Dateien (`"use strict"`, IIFE), keine Module, kein `fetch` (Bauplan 0.1, `file://`).
- `themen.js` liest beim Laden `window.KIEZ_ZELLEN`, `window.KIEZ_STADTTEILE` und die CSS-Variablen
  `--k1 … --k5` von `document.documentElement`. Es zeichnet nichts und kennt keine Karte.
- Gewicht: höchstens 6 KB gz. Die Startseite darf durch P1 um höchstens 2 KB gz schwerer werden.

## Objekt

```js
window.KIEZ_THEMEN = {
  THEMEN,  THEMA,  HASH,          // Themenliste und Nachschlagen
  STUFEN,  GRAU,                  // Farben
  KLASSEN, klassen, klasse,       // Klassengrenzen
  farbe,   hoehe,  unscharf,      // MapLibre-Ausdrücke und Prüfung
  polys,   umriss, GANZ,          // Geometrie
  TEIL, FARBE, BEZIRKFARBE, proBezirk,   // Stadtteile
  fmt, fmt1, rundEw, proz, name, kachel, esc,   // Text
  ebenen,  laden,  v,             // Ebenen-Register, Nachladen, Cache-Busting
  grundkarte, grundLuft, GRUNDKARTE   // Vektor-Grundkarte (daten/grundkarte.js) einsetzen, Luftbild-Umschaltung, ob geladen
};
```

`grundkarte(stil, {vor})` ersetzt im MapLibre-Stil die Rasterebene `basemap` durch die Flächen und Linien aus
`KIEZ_GRUNDKARTE.unten` und fügt die Beschriftungen (`oben`) am Ende bzw. vor der Ebene `vor` ein. Fehlt
`daten/grundkarte.js`, bleibt der Stil unverändert (Rasterkarte als Rückfall). `grundLuft(map, an)` blendet bei
eingeschaltetem Luftbild die Flächen und Linien aus, die Beschriftungen bleiben; ursprünglich ausgeblendete Ebenen
bleiben aus. Seit 06.11.2026 (Beleg `belege/3D_grundkarte_20261106.md`).

### Themen

| Name | Typ | Bedeutung |
|---|---|---|
| `THEMEN` | `Thema[]` | Reihenfolge = Reihenfolge der Chips. Heute 7 Einträge, wie `karte.js:25-33` |
| `THEMA` | `{[id]: Thema}` | Nachschlagen per `id` |
| `HASH` | `{[h]: id}` | Nachschlagen per Hash-Schlüssel (`karte.html#thema=<h>`) |

```js
Thema = {
  id:      "q_u18",            // Eigenschaftsname in zellen.js (oder in einer nachgeladenen Ebene)
  h:       "u18",              // Hash-Schlüssel, bleibt stabil (geteilte Links)
  kurz:    "unter 18",         // Chip
  name:    "Anteil unter 18 Jahre",
  einheit: "%" | "Personen" | "Jahre" | "m" | "min" | undefined,
  nenner:  "a_ges" | "w_ges" | undefined,   // unter 10 im Nenner: grau und flach (unscharf)
  quelle:  "Zensus 2022, Alter in 5 Altersklassen",
  ebene:   undefined | "<id im Ebenen-Register>"   // neu: Thema, dessen Werte nachgeladen werden
}
```

Bestehende Paare `id`/`h`: `stadtteile/stadtteile`, `ew/ew`, `d_alter/alter`, `q_u18/u18`, `q_65p/65p`,
`q_v1949/vor1949`, `q_fern/fern`. Diese Schlüssel ändern sich nicht.

### Farben und Klassen

| Name | Signatur | Verhalten (wie heute) |
|---|---|---|
| `STUFEN` | `string[5]` | Werte von `--k1 … --k5` |
| `GRAU` | `"#d5d8d3"` | unscharfe Werte |
| `klassen(t, features?)` | `→ {grenzen:number[], min, max, fest?:true}` | Prozent: fest `[20,40,60,80]`, 0–100. Sonst Quintile über die Werte `features[i].properties[t.id]` (Standard: `KIEZ_ZELLEN.features`), doppelte Grenzen entfallen |
| `KLASSEN` | `{[id]: Klassen}` | `klassen(t)` für alle Themen außer `stadtteile`, beim Laden gerechnet |
| `klasse(t, v)` | `→ 0..4` | Index der Stufe für einen Wert |
| `farbe(t, k?)` | `→ Ausdruck` | `["step", ["get", t.id], STUFEN[0], g1, STUFEN[1], …]`; mit `nenner`: `case` Nenner < 10 → `GRAU` |
| `hoehe(t, opt?)` | `→ Ausdruck` | wie `karte.js:43-51`; `opt.faktor` (Zahl, Standard 1) multipliziert die Höhe; `atlas.js` übergibt seinen animierten Faktor `hk.k`. Höchstwert `opt.hoch` (Standard 1100 m) |
| `unscharf(t, props)` | `→ boolean` | `t.nenner` gesetzt und `props[t.nenner]` fehlt oder < 10 |

Neue Ebenen mit eigener Skala (Erreichbarkeit in Metern, Bauzeitklassen) übergeben die Klassen selbst:
`farbe(t, {grenzen:[300,500,1000,2000], min:0, max:5000})`. Eine Baujahr-Skala über Gelb, Orange oder Rot
ist verboten (B5: kein Farbton zwischen 20° und 70° Hue).

### Geometrie und Stadtteile

| Name | Signatur | Verhalten |
|---|---|---|
| `polys(f)` | `→ Ring[][]` | Polygon oder MultiPolygon als Liste von Polygonen |
| `umriss(f)` | `→ [[w,s],[o,n]]` | Hüllrechteck eines Features |
| `GANZ` | `[[w,s],[o,n]]` | Hüllrechteck aller Stadtteile |
| `TEIL` | `{[nr]: Feature}` | Stadtteil nach Nummer |
| `FARBE`, `BEZIRKFARBE`, `proBezirk` | wie `karte.js:15-21` | ein Farbton je Bezirk, heller/dunkler je Stadtteil |

### Text

`fmt` (de-DE ganzzahlig), `fmt1` (eine Nachkommastelle), `rundEw(v)` (≥ 1000 auf 100, sonst auf 10),
`proz(v)` („k. A.“ bei null), `name(nr)` („Potsdam“ bei leerem nr), `kachel(G, id)`, `esc(s)` (HTML).

### Ebenen-Register und Nachladen

```js
KIEZ_THEMEN.laden(src, global, fertig)
// Lädt daten/… per <script>-Tag (nie fetch), ruft fertig(window[global]) auf.
// Liegt window[global] schon vor, sofort. Gleichzeitige Aufrufe für dieselbe Datei laden einmal.
// Bei Ladefehler fertig(null) und eine Meldung im Element mit aria-live, kein Konsolenfehler.

KIEZ_THEMEN.v(src)
// Hängt ?v=<window.KIEZ_V> an, wenn die Deploy-Kopie (skripte/deploy_kopie.py) KIEZ_V setzt; sonst src unverändert.
// laden() nutzt es selbst; für eigene <script>-Tags (Gebäude, Schrifteinbettung) aufrufen. Ergänzt in I1.

KIEZ_THEMEN.ebenen.registrieren({
  id:      "erreichbar",                  // eindeutig
  datei:   "daten/erreichbar.js",         // Vertrag: daten/schema/erreichbar.json
  global:  "KIEZ_ERREICHBAR",
  art:     "zellwert" | "punkte" | "flaeche" | "gebaeude",
  themen:  [Thema, …],                    // werden an THEMEN angehängt, mit t.ebene = id
  hash:    "ein",                         // optionaler eigener Hash-Schlüssel, z. B. ein=kita,gs
  odbl:    false                          // true: Datei *_odbl.js, Vermerk im Quellenfeld zeigen
});
KIEZ_THEMEN.ebenen.liste()       // → registrierte Ebenen in Reihenfolge
KIEZ_THEMEN.ebenen.zellwerte(id, art)
// Für art "zellwert": liefert ein Array in der Reihenfolge von KIEZ_ZELLEN.features,
// geprüft gegen anzahl/erste_id/letzte_id der Datei; bei Abweichung null und Meldung.
```

Eine Seite mischt Zellwerte so in die Karte: `laden(...)`, dann `zellwerte(...)` in die Eigenschaften der
Zellen schreiben und `map.getSource("zellen").setData(KIEZ_ZELLEN)`. Neue Daten kommen nie in
`zellen.js` und nie in die Startseite (Bauplan 0.1).

## Was P1 nachweist

- `grep -c "function stufen"` über `atlas.js` und `karte.js` ergibt 0; `THEMEN` steht nur in `themen.js`.
- `pruefen/seiten.mjs` grün; Gewicht der Startseite ± 2 KB gz; Hash-Links wie vorher.
- Schaugrafik-SVG gleich (bis auf den Zeitstempel). `schaugrafik.js` liest weiter `window.KIEZ`
  (Seitenzustand aus `atlas.js`: `FRAGE`, `zustand`, `schritt`, `waehle`, `schauGebiet`, `TITEL`, `GZ`);
  die Helfer darin dürfen auf `KIEZ_THEMEN` verweisen.
