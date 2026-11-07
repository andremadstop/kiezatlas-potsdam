# Voll responsive (07.11.2026)

Anlass: Andre am Abend des 07.11.2026, nachdem die Gegenprobe zu „3D heißt Häuser“ gezeigt hatte, dass die Handy-Karte
der Bauzeiten beim Lesen nur 223 px hoch ist: „ja mach lieber voll responsive“, danach „mach mal fertig“. Zweig
`ausbau/responsive`, Ausgangsstand `8858643` (gleich `main`, live als `stand-2026-11-07`). Dazu drei Reste der
Startseite aus `belege/3D_haeuser_20261107.md` (Grenzen) und ein neues Vorschaubild.

Fest vorgegeben: Das Mausrad scrollt am Desktop weiter die Seite; keine Daten neu gerechnet, keine neuen Felder,
Kennungen oder Einzeljahre; nichts aus `daten/jahre/` beim Laden; `GEB_ZOOM` bleibt.

## Entscheidungen

| Nr. | Entscheidung | Begründung | Verworfen |
|---|---|---|---|
| R1 | Kopfleiste klappt beim Lesen nach oben weg und kommt beim Hochscrollen oder bei Tastaturfokus in ihr wieder (`kopf.js`, für alle vier Kartenseiten; die alte ScrollTrigger-Regel der Startseite entfällt). Schwelle 12 px, oberhalb von 60 px immer sichtbar. Startseite und Bauzeiten bei jeder Breite (Fensterscroll); Karte und Planer nur bis 860 px Breite oder 500 px Höhe, dort beim Scrollen im Blatt bzw. in der Seitenleiste; Blatt zu holt sie zurück. | Die Leiste ist auf Bauzeiten und Planer zweizeilig (88 px am Handy). Schwelle gegen Zittern am Seitenende und durch die Adressleiste. | Kopfleiste am Desktop von Karte und Planer einklappen (dort ist Platz, die Seitenleiste müsste mitrutschen) |
| R2 | Die Kopfleiste liegt über der Karte; Bühne und Karte ändern beim Ein- und Ausklappen ihre Größe nicht. Chips und Kartenknöpfe rücken mit (`html.kopf-weg`); Bauzeiten-Bühne ab Oberkante (`top: 0`, Desktop 100svh, Handy 68svh), Karte und Planer schmal bzw. niedrig mit `inset: 0`, die Seitenleiste mit Innenabstand in Höhe der Kopfleiste. Beim Einpassen (Bauzeiten, Karte, Planer schmal) zählt die Höhe der Kopfleiste zum oberen Abstand, damit der Bildausschnitt bleibt. | Wüchse die Bühne mit, zeichnete MapLibre bei jedem Richtungswechsel neu, und die Verschiebung der Seite drehte die Richtungserkennung um (Flackern). Die Startseite arbeitete schon so. | Bühne mitwachsen lassen (`top`/`height` per Scroll) |
| R3 | Gestapelt (Karte oben, Text darunter) nur am Handy hoch: `(max-width:599px),(max-width:699px) and (orientation:portrait)`, wörtlich gleich in `kopf.js` (`window.KIEZ_GESTAPELT`) und in `atlas.css`, `karte.css`, `jahre.css`; `seiten.mjs` prüft die Gleichheit. Breiter oder quer (844 × 390, 768 × 1024) stehen Karte und Text nebeneinander wie am Desktop; Karte und Planer zeigen dort die Seitenleiste (320 px bis 860 px Breite) statt des Blatts. JS fragt die Abfrage für Blatt, Scroll-Auslöser und Bühnen-Scroll; Kamera-Abstände und Zoom bleiben an `max-width:860px`. | Quer war die Karte vorher 0 bis 202 px hoch (Bühne 52svh von 390 px, Leiste der Bauzeiten 48 % der Höhe). Eine Abfrage an zwei Orten hätte bei 844 px die Seitenleiste per JS geschlossen und ihren Inhalt per CSS versteckt. | Breakpoint 860 px für alles (quer gestapelt); eigene Handy-quer-Ansicht |
| R4 | Höhen: Startseite am Handy 60svh (vorher 52svh), Bauzeiten 68svh ab Oberkante (vorher 68svh minus Kopfleiste), Blatt von Karte und Planer offen 72svh (vorher 78dvh). `svh` statt `dvh`. | Startseite: Karte beim Lesen 438 → 506 px bei 390 × 844; der Lesebereich darunter bleibt 40 % (vorher 48 %). Bauzeiten: gleicher Lesebereich wie vorher, die Karte gewinnt Kopfleiste und Legende. `dvh` ändert sich beim Ein- und Ausfahren der Adressleiste, die Karte spränge. | Startseite 65svh (Fragen zu eng) |
| R5 | Überlappung heißt: zwei sichtbare Bedienelemente schneiden sich um mehr als 1 px. Was das offene Blatt ganz verdeckt, ist verdeckt, nicht überlappend (Prüfung per Treffertest an fünf Punkten); die Kopfleiste über dem Innenabstand der Seitenleiste ist gewollt (R2). Kartenknöpfe stehen auf Touch und schmal 62 px über dem unteren Rand, also über dem Quellen-„i“; bei höchstens 500 px Höhe stehen Zoom und Standort nebeneinander. Bauzeiten am Handy hoch und bei höchstens 500 px Höhe ebenso: unten an der Karte, in einer Zeile (Gegenprobe G1, G2; vorher oben an der Kopfleiste). Planer schmal: Legende höchstens 300 px breit, unten über dem Blatt. | Vorher lag „Meinen Standort zeigen“ auf Karte, Planer und (mit „Nach Norden“) Bauzeiten 9 bis 19 px unter dem „i“; quer lagen die Chips der Karte über dem Blatt. | Knöpfe beim offenen Blatt ausblenden |
| R6 | Tippziele auf Touch (`pointer:coarse`) mindestens 44 × 44 px: Chips, Zoom, Kompass, Standort, Quellen-„i“, Hauptnavigation, Marke, „Legende“, „Nacheinander“. Mit Maus bleibt alles wie vorher (34 px). Chipzeile auf Touch und schmal in einer wischbaren Zeile. | Vorher 5 bis 20 Hauptschalter je Seite unter 44 px. Neun Chips in 44 px Höhe brächen am Tablet in drei Zeilen um. | 44 px auch am Desktop |
| R7 | Legende der Bauzeiten-Leiste einklappbar (Knopf „Legende“, `aria-expanded`), am Handy hoch und quer beim Laden eingeklappt, sonst offen. Niedrig (bis 500 px) ist die Leiste so knapp wie am Handy. Bei höchstens 500 px Höhe liegt die offene Legende als Ebene über der Karte, links neben den Knöpfen, bis unter die Chips hoch, der Rest scrollt; die Quelle steht dort nur im „i“ (Gegenprobe G2). Die Legenden der anderen Seiten bleiben kompakt wie bisher (schmal oder niedrig ohne Quelle und Bezirke). | Die Leiste nahm am Handy 28 bis 32 %, quer 48 % der Höhe. Die anderen Legenden liegen bei 3 bis 32 %. Quer drückte die offene Legende in der Leiste die Karte auf 180 von 390 px, alle Knöpfe lagen unter der Leiste. | Legende als Ebene über der Karte bei mehr als 500 px Höhe (dort reicht der Platz in der Leiste); Leiste ganz einklappen (Bauzeit ist das Thema der Seite) |
| R8 | Aussparungen: `viewport-fit=cover` auf den vier Kartenseiten; `--gut` nie kleiner als die seitliche Aussparung, Kopfleiste mit `safe-area-inset-top`, Kartenknöpfe und Maßstab seitlich, Blatt und Leiste unten. | Ohne `viewport-fit=cover` sind alle Werte 0; mit ihm muss jede Kante es berücksichtigen. | Ohne `viewport-fit` (Safari rahmt dann quer ein, unten bliebe die Leiste unter dem Home-Balken) |
| B1 | Startseite mit 3D-Häusern: Wahl eines Stadtteils aus der Liste im Steckbrief oder im Register fliegt zu seinen Häusern (Mitte der dichtesten Zellen, Zoom 16,2, Neigung bleibt oder 58), schon nah und mittendrin nur neigen; wie `zuDenHaeusern` in `karte.js`. | Vorher luden die Häuser des neuen Stadtteils außerhalb des Bildes. | |
| B2 | Startseite: Mit 3D-Häusern wählt ein Klick in den gewählten Stadtteil ihn nicht ab (Karte und Register). | Ohne Stadtteil stünden keine Häuser mehr (wie auf der freien Karte). | |
| B3 | Startseite: „Luftbild einblenden“ in Frage 5 schaltet nur das Luftbild, wenn 3D-Häuser selbst eingeschaltet sind; Stadtteil, Häuser und Kamera bleiben. | Vorher setzte der Knopf die ganze Frage (3D aus). | |
| C1 | `og.png` neu (1200 × 630) aus einer eigenen Aufnahme der Bauzeiten-Seite mit 3D-Häusern, Innenstadt um den Platz der Einheit (Zoom 16,15, Neigung 58), Titel „Kiezatlas Potsdam“, Zeile „Bauzeiten der Gebäude, Haus für Haus geschätzt. Innenstadt“, Quellenvermerk wörtlich aus dem „i“ der Seite, je Quelle eine Zeile (Stadtteile, Gebäude mit dl-de/by-2-0 und „Daten verändert“, Zensus 2022, Grundkarte; Gegenprobe G6, vorher der verkürzte Text „Grundkarte © GeoBasis-DE / BKG (2026) CC BY 4.0, Gebäude © GeoBasis-DE/LGB“). Skript `skripte/28_vorschaubild.mjs`. | Das alte Bild zeigte den Chip „Gebäude 3D“ und die Startseite vor A18. | Aufnahme der Startseite |
| P1 | Pre-existing, eigener Commit: Die Methode der Startseite stand bei 360 px um 29 px seitlich über (langer Belegpfad in `code` sprengte die Spalte `1fr`). Jetzt `minmax(0,1fr)` und Umbruch im Pfad. | Fiel erst auf, als die Messung `clientWidth` statt `innerWidth` nahm: auf dem Handy (isMobile) wächst `innerWidth` mit dem Überstand. | |

## Zählungen vorher und nachher

Gemessen mit `node pruefen/responsiv.mjs` (headless Chromium aus `node_modules`, reduzierte Bewegung, Fremdabrufe
leer beantwortet, Touch-Breiten mit `isMobile` und `hasTouch`), vorher gegen einen Abzug von `main` (`8858643`),
nachher gegen diesen Stand, je über `python3 -m http.server` auf 127.0.0.1. „Karte beim Lesen“: Bildpunkte einer
senkrechten Linie durch die Kartenmitte, an denen oben Karte oder eine ihrer Auflagen liegt (nicht Kopfleiste, Blatt,
Leiste, Text), nachdem die Seite bis Frage 2 gescrollt ist (Startseite, Bauzeiten) bzw. das Blatt geöffnet und
420 px gescrollt (Karte, Planer). Überstand: `scrollWidth − clientWidth`. Überlappungen: Paare über Start und Lesen.
Tippziele: Hauptschalter unter 44 px, nur auf Touch-Breiten gezählt. Legende: ganze Höhe als Anteil der Fensterhöhe,
Bauzeiten: die ganze Leiste unter der Karte.

| Seite | Breite | Karte beim Lesen vorher | nachher | Überstand vorher / nachher | Überlappungen vorher / nachher | Tippziele < 44 px vorher / nachher | Legende bzw. Leiste vorher / nachher | Kopfleiste beim Lesen vorher / nachher | Konsolenfehler vorher / nachher |
|---|---|---:|---:|---|---|---|---|---|---|
| index | 360x740 | 384 px (48 %) | 442 px (60 %) | 29 / 0 px | 0 / 0 | 5 / 0 | 15 % / 17 % | weg / weg | 0 / 0 |
| index | 390x844 | 438 px (52 %) | 506 px (60 %) | 0 / 0 px | 0 / 0 | 5 / 0 | 15 % / 15 % | weg / weg | 0 / 0 |
| index | 844x390 | 202 px (52 %) | 390 px (100 %) | 0 / 0 px | 0 / 0 | 5 / 0 | 32 % / 32 % | weg / weg | 0 / 0 |
| index | 768x1024 | 532 px (52 %) | 1024 px (100 %) | 0 / 0 px | 0 / 0 | 16 / 0 | 12 % / 12 % | weg / weg | 0 / 0 |
| index | 1024x768 | 768 px (100 %) | 768 px (100 %) | 0 / 0 px | 0 / 0 | 18 / 0 | 27 % / 27 % | weg / weg | 0 / 0 |
| index | 1280x800 | 800 px (100 %) | 800 px (100 %) | 0 / 0 px | 0 / 0 | 0 / 0 | 26 % / 26 % | weg / weg | 0 / 0 |
| index | 1440x900 | 900 px (100 %) | 900 px (100 %) | 0 / 0 px | 0 / 0 | 0 / 0 | 23 % / 23 % | weg / weg | 0 / 0 |
| index | 1920x1080 | 1080 px (100 %) | 1080 px (100 %) | 0 / 0 px | 0 / 0 | 0 / 0 | 19 % / 19 % | weg / weg | 0 / 0 |
| karte | 360x740 | 110 px (15 %) | 206 px (28 %) | 0 / 0 px | 1 / 0 | 20 / 0 | 5 % / 5 % | da / weg | 0 / 0 |
| karte | 390x844 | 152 px (18 %) | 236 px (28 %) | 0 / 0 px | 1 / 0 | 20 / 0 | 4 % / 4 % | da / weg | 0 / 0 |
| karte | 844x390 | 32 px (8 %) | 390 px (100 %) | 0 / 0 px | 21 / 0 | 20 / 0 | 8 % / 8 % | da / weg | 0 / 0 |
| karte | 768x1024 | 332 px (32 %) | 1024 px (100 %) | 0 / 0 px | 1 / 0 | 20 / 0 | 3 % / 3 % | da / weg | 0 / 0 |
| karte | 1024x768 | 712 px (93 %) | 712 px (93 %) | 0 / 0 px | 0 / 0 | 20 / 0 | 18 % / 18 % | da / da | 0 / 0 |
| karte | 1280x800 | 744 px (93 %) | 744 px (93 %) | 0 / 0 px | 0 / 0 | 0 / 0 | 17 % / 17 % | da / da | 0 / 0 |
| karte | 1440x900 | 844 px (94 %) | 844 px (94 %) | 0 / 0 px | 0 / 0 | 0 / 0 | 15 % / 15 % | da / da | 0 / 0 |
| karte | 1920x1080 | 1024 px (95 %) | 1024 px (95 %) | 0 / 0 px | 0 / 0 | 0 / 0 | 13 % / 13 % | da / da | 0 / 0 |
| jahre | 360x740 | 180 px (24 %) | 352 px (48 %) | 0 / 0 px | 1 / 0 | 5 / 0 | 32 % / 20 % | da / weg | 0 / 0 |
| jahre | 390x844 | 250 px (30 %) | 424 px (50 %) | 0 / 0 px | 0 / 0 | 5 / 0 | 28 % / 18 % | da / weg | 0 / 0 |
| jahre | 844x390 | 0 px (0 %) | 262 px (67 %) | 0 / 0 px | 0 / 0 | 5 / 0 | 48 % / 33 % | da / weg | 0 / 0 |
| jahre | 768x1024 | 420 px (41 %) | 790 px (77 %) | 0 / 0 px | 0 / 0 | 9 / 0 | 18 % / 23 % | da / weg | 0 / 0 |
| jahre | 1024x768 | 468 px (61 %) | 546 px (71 %) | 0 / 0 px | 0 / 0 | 14 / 0 | 27 % / 29 % | da / weg | 0 / 0 |
| jahre | 1280x800 | 500 px (63 %) | 590 px (74 %) | 0 / 0 px | 0 / 0 | 0 / 0 | 26 % / 26 % | da / weg | 0 / 0 |
| jahre | 1440x900 | 600 px (67 %) | 690 px (77 %) | 0 / 0 px | 0 / 0 | 0 / 0 | 23 % / 23 % | da / weg | 0 / 0 |
| jahre | 1920x1080 | 798 px (74 %) | 890 px (82 %) | 0 / 0 px | 0 / 0 | 0 / 0 | 17 % / 18 % | da / weg | 0 / 0 |
| planer | 360x740 | 74 px (10 %) | 206 px (28 %) | 0 / 0 px | 1 / 0 | 16 / 0 | 6 % / 6 % | da / weg | 0 / 0 |
| planer | 390x844 | 116 px (14 %) | 236 px (28 %) | 0 / 0 px | 1 / 0 | 16 / 0 | 5 % / 5 % | da / weg | 0 / 0 |
| planer | 844x390 | 0 px (0 %) | 390 px (100 %) | 0 / 0 px | 3 / 0 | 16 / 0 | 11 % / 11 % | da / weg | 0 / 0 |
| planer | 768x1024 | 296 px (29 %) | 1024 px (100 %) | 0 / 0 px | 1 / 0 | 16 / 0 | 4 % / 4 % | da / weg | 0 / 0 |
| planer | 1024x768 | 676 px (88 %) | 676 px (88 %) | 0 / 0 px | 0 / 0 | 16 / 0 | 7 % / 7 % | da / da | 0 / 0 |
| planer | 1280x800 | 708 px (89 %) | 708 px (89 %) | 0 / 0 px | 0 / 0 | 0 / 0 | 7 % / 7 % | da / da | 0 / 0 |
| planer | 1440x900 | 808 px (90 %) | 808 px (90 %) | 0 / 0 px | 0 / 0 | 0 / 0 | 6 % / 6 % | da / da | 0 / 0 |
| planer | 1920x1080 | 988 px (92 %) | 988 px (92 %) | 0 / 0 px | 0 / 0 | 0 / 0 | 5 % / 5 % | da / da | 0 / 0 |

Die Desktop-Werte von Startseite, Karte und Planer ändern sich nicht (gewollt). Am Handy hoch bleibt die Karte von
Karte und Planer mit offenem Blatt bei 28 %: das Blatt ist zum Lesen da; geschlossen zeigt es 79 bis 86 % Karte wie
vorher. Bildschirmfotos aller 64 Zustände je vorher und nachher liegen außerhalb des Repos (Prüfordner der Sitzung),
MD5 zum Beispiel Bauzeiten 390 × 844 beim Lesen vorher `a1fafa53a7e2d08813267da8b09442de`, nachher
`42698b0a242a983733b50b79cb49748a`; Karte 844 × 390 vorher `16944135ceda1aeb3a301f00cd4188f7`, nachher
`c6587da3cd89b2e4a5a830b2910411c1`; keine zwei Fotos eines Laufs sind gleich.

## Prüfungen

| Prüfung | Ergebnis |
|---|---|
| `node --check` auf `kopf.js`, `atlas.js`, `karte.js`, `jahre.js`, `planer.js`, `pruefen/responsiv.mjs`, `pruefen/seiten.mjs`, `pruefen/B5_jahre.mjs`, `pruefen/A7_planer.mjs`, `skripte/28_vorschaubild.mjs` | ohne Fehler |
| `pruefen/seiten.mjs`: Abfrage „Gestapelt“ in `kopf.js` und drei Stylesheets gleich; B1 Liste (72) und Register (15) fliegen zu den Häusern, Kartenmitte im gewählten Stadtteil, Zoom 16,2, 189 bzw. 532 Häuser; B2 Klick in 15 lässt 15 gewählt und 3D an; B3 Luftbild an, 3D an, Häuser stehen; dazu Startseite und Karte über acht Breiten | grün; gegen `main`: 25 Befunde (Abfrage fehlt, B1 bis B3 rot, alle Handy-, Quer- und Tablet-Breiten rot) |
| `pruefen/B5_jahre.mjs`: Bauzeiten über acht Breiten (Karte beim Lesen mindestens 42 bis 78 %, Leiste höchstens 25 % am Handy hoch) | grün; gegen `main` (`--wurzel`): 13 Befunde, jede Breite rot |
| `pruefen/A7_planer.mjs`: Planer über acht Breiten | grün; gegen `main`: 9 Befunde |
| Schwellen: je Seite und Breite in `pruefen/responsiv.mjs` (`MINDEST`), abgeleitet aus der Messung vorher, über dem alten Wert, wo sich etwas bessern sollte | Startseite 1024 bis 1920 sowie Karte und Planer ab 1024 sind Untergrenzen gegen Rückschritte (vorher schon darüber) |
| `./pruefen.sh` vollständig | 18 Prüfungen, 17 grün, 0 Befund, 1 übersprungen (Prüfsummen Kerndaten: `rohdaten/` fehlt im Worktree, wie bisher); nach der Gegenprobe siehe dort |
| `pruefen/p1_gleich.mjs` `main` gegen nachher (1440 × 900: Stile, Legenden, Register, Steckbriefe, Hash, Schaugrafik-SVG) | gleich, 0 Abweichungen; die gewollten Änderungen liegen unter 861 px, auf Touch oder niedrig und erscheinen dort nicht |
| `skripte/28_vorschaubild.mjs` zweimal | gleiches Bild, MD5 `a0a0b118c1f7fdad209383b9458cc1fc`, 393.452 B, 1200 × 630, 2.652 Häuser im Bild; angesehen: Titel, Zeile und Vermerk lesbar. Nach der Gegenprobe (G6) neu: MD5 `d0314b13c2dc51e05806c4c34ef554dd`, 407.663 B, zweimal gleich |

## Netzabrufe für diese Änderung

- `https://sgx.geodatenzentrum.de/robots.txt` einmal (sperrt nur `/gdz_geoviewserver/` und `/gdz_geoviewserv/`).
- Für das Vorschaubild je Lauf 12 bis 18 Kacheln und Schriften unter `/gdz_basemapde_vektor/` (sechs Läufe beim Bau,
  drei davon zur Fehlersuche). Alles andere aus dem Netz beantwortete der Browser leer; die Prüfungen laufen ohne Netz.
- Gegenprobe G6: das Vorschaubild zweimal neu, je 16 Abrufe unter `/gdz_basemapde_vektor/`, dazu ein Probelauf mit
  `--ohne-netz` (kein Abruf). Die Messungen der Gegenprobe liefen ohne Netz.

## Grenzen

- Echte Geräte nicht geprüft, nur Chromium mit Handy- und Tablet-Maßen (isMobile, hasTouch). Safari auf iOS und
  Firefox auf Android nicht gesehen; Kerbe und Home-Balken (`safe-area-inset-*`) kann der Prüfbrowser nicht
  nachstellen, die Werte sind dort immer 0.
- Adressleiste: `svh` hält die Bühne beim Scrollen fest; wie ruhig die Kopfleiste mit ein- und ausfahrender
  Adressleiste wirkt, ist nur auf einem Gerät zu sehen.
- Die acht Felder der Bauzeiten-Leiste sind bei 360 px rund 42 px breit; sie zählen hier nicht zu den Hauptschaltern
  (Regler und Pfeiltasten wählen dieselbe Spanne).
- Karte und Planer am Desktop (ab 861 px und über 500 px Höhe) behalten die feste Kopfleiste.
- Startseite quer (844 × 390): Legende 32 % der Höhe, wie vorher; Grenze 35 %.
- Beim Laden steht die Bühne nur noch auf der Startseite am Desktop mit Maus (ab 861 px Breite, über 500 px Höhe) unter
  der Kopfleiste; Chips liegen dort eine Kopfleistenhöhe tiefer, bis die Bühne oben klebt, und das „i“ liegt unter dem
  Fensterrand (wie auf main, nicht geändert). Überall sonst beginnt sie an der Oberkante (Gegenprobe G3).
- Bauzeiten quer unter rund 380 px Höhe (etwa 740 × 360): Mit zurückgekehrter Kopfleiste berührt die Knopfzeile die
  Chipzeile, und die Legenden-Ebene zeigt nur rund 30 px (der Rest scrollt). Beim Lesen (Kopfleiste weg) ist Platz.
  Nicht in den acht Prüfbreiten.
- Planer schmal oder niedrig: Zwischen 72 und 88 px Scrollstand im Blatt ist die Kopfleiste schon weg, der feste
  Innenabstand oben aber noch bis zu 16 px zu sehen (leerer Streifen, Gegenprobe G7).
- Drehen des Geräts: Blatt, Scroll-Auslöser und Legende folgen der Abfrage; die ScrollTrigger-Linien der Startseite
  werden beim Laden gesetzt und nach dem Drehen erst beim nächsten Neuladen angepasst.

## Gegenprobe

Zwei Gegenproben mit frischem Blick (Code und eigener Prüfbrowser) meldeten acht Funde. Jeder Fund wurde hier selbst
nachgemessen: eigener `python3 -m http.server` auf 127.0.0.1, headless Chromium aus `node_modules`, Viewport beim Start
gesetzt, Handy und Tablet mit `isMobile` und `hasTouch`, reduzierte Bewegung, Fremdabrufe leer beantwortet. „vorher“ ist
`670f2b2` (Stand vor der Gegenprobe), „main“ ist `8858643`. Knöpfe: „3/3“ heißt, alle drei Prüfpunkte (Mitte, oben
links, unten rechts) treffen den Knopf selbst. Alle acht Funde sind bestätigt, keiner verworfen. Zwei Teile standen
schon auf main und sind als „Pre-existing“ eigens committet (`286f781`), alles andere in `f7bbbbb`.

| Nr. | Fund | Urteil | Messung vorher | Messung nachher | Behebung |
|---|---|---|---|---|---|
| G1 | Bauzeiten Handy hoch: mit zurückgekehrter Kopfleiste oder offener Legende liegen Kartenknöpfe unter dem „i“, der Leiste oder dem Legenden-Knopf (`jahre.css`, Knöpfe hingen an der Kopfleiste) | bestätigt | 360 × 740, Kopf zurück: Standort y 298–342, 0/3 (unter dem „i“); Legende offen: Verkleinern 0/3, Nach Norden 1/3, Standort 0/3. 390 × 844, Legende offen: Nach Norden 2/3, Standort 1/3 | 360 × 740: Knopfzeile y 247–291 (Kopf zurück) bzw. 149–193 (Legende offen, Chips enden bei 139), alle 3/3; 390 × 844: 317–361 bzw. 220–264, alle 3/3. Bilder `jahre_360x740_kopf` `76235b9ffbbf30978d0710efcb30df9f`, `jahre_360x740_legende` `37ae3d9da2de91f697fdeb4067d24787` | Knöpfe am Handy hoch und bei höchstens 500 px Höhe unten an der Karte (`bottom: 62px`), in einer Zeile wie quer auf den anderen Seiten. Senkrecht gestapelt (rund 188 px) wären sie bei offener Legende in die Chips gelaufen |
| G2 | Bauzeiten quer 844 × 390: offene Legende drückt die Karte auf 180 px, alle Knöpfe unter der Leiste | bestätigt | Karte y 0–180, Leiste 180–390, alle vier Knöpfe y 157–201 je 1/3 (unter `#zeitleiste`) | Karte y 0–263 (wie mit geschlossener Legende), Legende als Ebene x 361–612, y 150–230 (scrollt 102 von 78 px; mit eingeklappter Kopfleiste ganz zu sehen), Knöpfe y 156–200 alle 3/3. Bild `leg_844x390_0_kopf` `e0e09743417a2923fb359baaef69ad73` | Bei höchstens 500 px Höhe ist die offene Legende eine Ebene über der Karte links neben den Knöpfen, Höhe bis unter die Chips (`max-height` aus 100svh minus Leiste, Kopfleiste und Abständen), Quelle nur im „i“. R7 entsprechend geändert. Eine bloße Höhenbegrenzung der Leiste hätte nicht gereicht: zwischen Knöpfen, „i“ und 127 px Leiste blieben 10 bis 20 px |
| G3 | Startseite und Bauzeiten nebeneinander: beim ersten Aufruf schweben die Chips eine Kopfleistenhöhe zu tief, Knöpfe abgeschnitten bzw. mitten im Bild | bestätigt; quer und 768 × 1024 neu durch den Umbau, Startseite 1024 × 768 mit Touch schon auf main (Pre-existing), Bauzeiten am Desktop neu (main: Chips bei y 102) | Startseite 844 × 390: Bühne y 88, Chips y 182, Knöpfe y 371–415 je 1/3, „i“ unter dem Fensterrand; 768 × 1024: Standort y 1005–1049 1/3; 1024 × 768: Standort 1/3, „i“ 0/3. Bauzeiten 844 × 390: Chips y 182, Knöpfe y 245–289; 1440 × 900: Bühne y 92, Chips y 194 | Bühne überall y 0; Chips y 94 (quer, Tablet), 98 (1024 × 768), 102 (Bauzeiten 1440, wie main); Startseite 844 × 390 Knöpfe y 283–327, „i“ 336–380; 768 × 1024 Standort 917–961; 1024 × 768 alle 3/3; Bauzeiten 844 × 390 Knöpfe y 156–200. Nach Tipp auf „3D-Häuser“ ohne Scrollen bleibt die Chipzeile unter der Kopfleiste | Die Bühne beginnt nebeneinander schon beim Laden an der Oberkante (`margin-top: calc(-1 * var(--kopf))`), die Kopfleiste liegt darüber wie danach beim Kleben. Startseite: schmal, niedrig und Touch; Desktop mit Maus unverändert (Grenzen). Bauzeiten: jede Breite nebeneinander. Gestapelt setzt es zurück |
| G4 | Startseite Tablet hoch: Kopfzahlen in drei engen Spalten, „rund 182.700“ bricht um | bestätigt; 768 × 1024 und 844 × 390 neu, 900 bis 1100 px Breite schon auf main (Spalte 357 bis 406 px), daher als Pre-existing committet | 768 × 1024: Spalte 304 px, 3 Spalten, „rund 182.700“ über 2 Zeilen; ebenso 844 × 390 (335 px), 900 × 1200 (357 px), 1024 × 768 (406 px); 1280 × 800 (508 px) einzeilig | 2 Spalten, die erste Zahl über beide, alles einzeilig bei 304 bis 406 px; 1280 × 800 unverändert 3 Spalten. Bild `index_768x1024_zahlen` (nachher) angesehen | Container-Abfrage auf den Auftakt (`container-type: inline-size`), unter 480 px Spaltenbreite zwei Spalten mit `min-height: 14rem` wie die Regel bis 560 px Fensterbreite |
| G5 | Karte und Planer: Scrollstände der verschachtelten Listen (`#treffer`, `#raeume`) und des Blatts landen in derselben Variablen, die Kopfleiste kommt beim Abwärtsscrollen zurück (`kopf.js` Zeile 24) | bestätigt | Mausrad nur nach unten, Karte 844 × 390: Kopfleiste W60 D180 W300; Planer 768 × 1024: W60 D840 W960 D960 …. Neuer Prüffall gegen `670f2b2`: auf Karte und Planer bei 360, 390, 844 × 390 und 768 × 1024 jeweils „W60 D180 W240“, 8 Befunde | Mausrad: nur W60; Prüffall: „W60“, bleibt eingeklappt, 8 grün | Nur `#seite` (nebeneinander) und `#seite-inhalt` (gestapelt) werten den Scrollstand aus |
| G6 | `og.png`: Quellenvermerk unvollständig (Lizenz und „Daten verändert“ bei den Gebäuden, Zensus 2022 fehlte) | bestätigt | Vermerk „Grundkarte © GeoBasis-DE / BKG (2026) CC BY 4.0, Gebäude © GeoBasis-DE/LGB“, MD5 `a0a0b118c1f7fdad209383b9458cc1fc` | Vier Zeilen, wörtlich aus dem „i“ der Seite: „Stadtteile © Landeshauptstadt Potsdam, dl-de/zero-2-0“, „Gebäude © GeoBasis-DE/LGB, dl-de/by-2-0, Daten verändert (eigene Berechnung); Bauzeit je Gebäude geschätzt“, „Zensus 2022 © Statistische Ämter des Bundes und der Länder, dl-de/by-2-0, Daten verändert (eigene Berechnung)“, „Grundkarte © GeoBasis-DE / BKG (2026) CC BY 4.0, Kartenstil verändert“. MD5 `d0314b13c2dc51e05806c4c34ef554dd`, 407.663 B, 1200 × 630, zweimal gleich, angesehen | Das Skript liest den Vermerk nach dem Einrichten der Kamera aus `.maplibregl-ctrl-attrib-inner` (nur sichtbare Quellen) statt eines eigenen Textes; der vorgeschlagene Wortlaut „Bauzeit geschätzt u. a. aus Zensus 2022“ ist nicht übernommen, weil er die Methode verkürzt |
| G7 | Karte und Planer schmal oder niedrig: der Innenabstand des Blatts wechselt beim Einklappen, der Inhalt springt (gemeldet als `karte.css` Zeile 451; die Regel steht in Zeile 42 und 43) | bestätigt | Höhe des Blatts Karte 768 × 1024: 3796 → 3744, Planer: 3257 → 3169; Bezugsabsatz springt beim Einklappen um −52 bzw. −88 px; Prüffall gegen `670f2b2`: 844 × 390 und 768 × 1024 rot | Höhe gleich (3796, 3257, 3802, 3264), Sprung 0 px bei allen vier Messungen | Fester Innenabstand oben, ohne Umschalten und ohne Übergang; er scrollt mit dem Inhalt weg. Rest: Grenzen |
| G8 | Bauzeiten Handy: nach „Auf der Karte zeigen“ bleibt zwischen Bühne und „Selbst erkunden“ eine Lücke, weil `scroll-padding-top` doppelt zählt | bestätigt | Lücke 126 px bei 360, 375 und 390 px Breite (main: 38 px) | Lücke 30 px bei allen drei Breiten. Die vorgeschlagene Grenze „unter 24 px“ hätte das nicht durchgelassen: die 30 px sind der Abstand des Titels in der Frage | `scroll-margin-top: calc(68svh - 9svh - var(--kopf) - 8px)`; B5 prüft zusätzlich Lücke höchstens 40 px (gegen `670f2b2` rot mit 126 px) |

Neue Prüfungen in `pruefen/responsiv.mjs` (damit Seiten, B5 und A7): Paarprüfung zusätzlich in den Zuständen „Hoch“
(Kopfleiste zurück) und auf den Bauzeiten „Legende offen“; Treffbarkeit aller Kartenknöpfe (Mitte trifft den Knopf,
nicht abgeschnitten; unter dem offenen Blatt erlaubt, R5) in allen Zuständen, weil die Paarprüfung ganz verdeckte Knöpfe
nicht sieht; Bühne beim Laden bei y 0, wo nebeneinander; Kopfzahlen der Startseite einzeilig; Karte und Planer „erst
Liste, dann Blatt“ mit Kopfleiste eingeklappt und gleicher Blatthöhe. Gegen `670f2b2` (`--wurzel`): Seiten 13 Befunde,
A7 4, B5 10 (darunter die Lücke von 126 px, Knöpfe unter dem „i“, „Legende offen“ mit vier verdeckten Knöpfen, Bühne bei
y 88 bzw. 92). Nachher: siehe Zählung unten.

Die Messtabelle oben („Zählungen vorher und nachher“) bleibt gültig: `node pruefen/responsiv.mjs` nach der Gegenprobe
ergibt dieselben Werte für „Karte beim Lesen“, Legende bzw. Leiste und Kopfleiste in allen 32 Zeilen.

Zählung nach der Gegenprobe: `./pruefen.sh` vollständig auf `286f781` (Arbeitsstand sauber): 18 Prüfungen, 17 grün,
0 mit Befund, 1 übersprungen (Prüfsummen Kerndaten, `rohdaten/` fehlt im Worktree, wie bisher); darin Seiten grün,
A7 grün, B5 grün mit 251 Punkten, 900 Einzelpunkte „ok“. `pruefen/p1_gleich.mjs` `main` gegen `286f781`: gleich,
0 Abweichungen (Desktop der Startseite und der Karte unverändert). Bildschirmfotos der Gegenprobe liegen außerhalb des
Repos (Prüfordner der Sitzung), MD5 wie in der Tabelle.
