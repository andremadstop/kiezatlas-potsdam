# Kiezatlas Potsdam: Gestaltung

## Brief

- **Gegenstand:** Alle 32 Stadtteile Potsdams in Zahlen und Karte, aus Zensus 2022 (100-m-Gitter), amtlichen Stadtteilen und ALKIS-Gebäuden. Prototyp der Stiebitz Souverain Systems UG.
- **Publikum:** Stadtplanung, Wohnungsunternehmen, Quartiersarbeit, Verwaltung, Fachpublikum. Sachlich, präzise, ruhig.
- **Aufgabe der Seite:** In einem Durchgang zeigen, was das Werkzeug kann (Fragen als Einstieg), dann frei erkunden, vergleichen, die Methode nachvollziehen. Sorgfalt sichtbar machen (Grenzfall, Quellen bei jeder Zahl).
- **Wünsche des Besitzers:** Einstieg über Alltagsfragen, die die Karte an die richtige Stelle führen und nebenbei je eine Funktion erklären. Zensus-Gitter als echte 3D-Säulen mit Tiefenwirkung, Höhe nach Wert, schräger Blick (so bis 07.11.2026; seither auf Andres Wunsch keine Säulen mehr, 3D heißt Häuser, siehe Nachträge).
- **Grenzen:** Statisch, ohne Build, läuft per Doppelklick und über einen statischen Server. Daten nur aus `daten/*.js` (nie von Hand eingesetzte Zahlen). Kein Orange, keine Gedankenstrich-Ketten, keine Buzzwords.
- **Annahmen:** Keine Bilder außer Karte und Luftbild. Kein Loader. One-Pager plus `404.html`.

## Drei Konzepte

| | Idee | Anker | Signatur | O / F / Fe / P |
|---|---|---|---|---|
| A. Material: das Gitter | Potsdam besteht aus 100-m-Zellen, und auf jede Frage hin richtet sich die Stadt in Säulen auf (verworfen am 07.11.2026: keine Säulen mehr) | Zensus-Gitter EPSG:3035, 100 m, bewohnte Zellen; die Havelseen bleiben als Leerstellen | Die flache Stadtteilkarte kippt beim ersten Scroll und die Zellen wachsen zu Säulen; jede Frage baut das Gitter um | 4 / 5 / 4 / 1 |
| B. Ort: die Stadtteilnummern | Die Ordnung 11 bis 86 (Bezirk = erste Ziffer) trägt Register, Farben und Navigation | amtliche Nummerierung der Stadt | Ein Nummernregister, das Flächen auf der Karte aufleuchten lässt | 3 / 4 / 5 / 2 |
| C. Formal: die Grenzlinie | Die violette Verwaltungsgrenze der topografischen Karte ist der rote Faden; alles dreht sich um Zuordnung | Signatur der Verwaltungsgrenzen in der TK, Grenzfall-Methode | Eine Zelle, die von der Grenze geteilt wird, wechselt zwischen „ganz“ und „anteilig“ | 4 / 4 / 4 / 2 |

**Gewählt: A.** Es trägt beide Wünsche des Besitzers (Fragen führen die Karte, damals das 3D-Gitter; seit 07.11.2026 flach, 3D nur für Häuser) und lässt sich aus keinem anderen Projekt übertragen. Aus C kommen die Akzentfarbe (Grenzviolett) und die Grenzfall-Grafik, aus B das Stadtteil-Register (gruppiert nach Bezirk).

## Concept Card

```
Idea:        Potsdam als Gitter aus 100-m-Zellen, das auf Alltagsfragen hin umgebaut wird und Antworten in Farbe zeigt.
Metaphor:    Das Kartenblatt der Landesvermessung: Gitter, Rahmen, violette Verwaltungsgrenzen, DIN-Schrift.
Signature:   Beim ersten Scroll weicht die Stadtteilkarte dem farbigen Zellgitter; jede weitere Frage baut das Gitter um.
             Bis 07.11.2026 wuchsen die Zellen dabei zu Säulen; seither gibt es keine Säulen mehr, 3D zeigt nur Häuser.
Emotion:     ruhig, genau, „ach so funktioniert das“.
Motion verb: einrasten (Knöpfe füllen sich von der Grundlinie, Registerzeilen rasten auf das Raster).
Screenshot:  Die Stadt als farbiges Zellgitter von oben (bis 07.11.2026 schräg aus Säulen, seither keine Säulen mehr), die Havel als Leerstelle, daneben die Frage „Wie viele Menschen wohnen in meiner Nachbarschaft?“.
```

## System

**Palette** (Kartenpapier, nicht Creme; Grenzviolett aus der TK statt Orange)

| Rolle | Wert | Herkunft |
|---|---|---|
| ground | `#f1f2ee` | Kartenpapier, kühl |
| ink | `#13212a` | Tiefenlinie / Beschriftung |
| muted | `#4f5d64` | Nebenschrift (AA auf ground) |
| line | `#cdd1cc` | Gitterlinie |
| accent | `#6a2c82` | Verwaltungsgrenze (violett) in topografischen Karten |
| curtain | `#13212a` | Methodenteil (Kartenrückseite) |

Klassenfarben im Gitter: fünf Stufen Wasser bis Tiefe `#dce6e2 #a8c7c2 #6fa1a3 #3b7684 #1c4a5b`. Stadtteile: ein Farbton je Stadtbezirk, heller und dunkler je Stadtteil (wie bisher, leiser gesättigt).

**Schrift:** Barlow Semi Condensed 500/600 für Anzeige (Erbe der DIN 1451, der Schrift von Kartenbeschriftung und Wegweisern), Barlow 400/500/600 für Text und Bedienung. Ziffern immer tabellarisch. Keine Monospace-Etiketten.

**Raster:** 12 Spalten, Gutter `clamp(16px, 2vw, 28px)`. Drei Fluchtlinien: Spalte 1, 5, 9. Abschnittsabstände wechseln: Erzählung ohne Zwischenraum (Bühne), Register normal, Grenzfall luftig, Methode dunkel und dicht.

**Form:** Radius 0 überall (Gitterzellen sind Quadrate). Linien 1 px.

**Bewegung:** ein Ease `cubic-bezier(.2,.8,.2,1)` (expo-artig) für alles, Kamera 1,4 s, Hover 0,35 s (der Säulen-Tween von 0,9 s entfiel am 07.11.2026 mit den Säulen). Aufrichten: Knöpfe füllen sich von der Grundlinie aufwärts; Registerzeilen lassen einen violetten Block einrasten; Textlinks haben eine Linie, die dicker wird.

**Ruhezustand:** Nach 2 s ohne Scroll und ohne Zeiger dreht sich die schräg gestellte Stadt (seit 07.11.2026 nur mit 3D-Häusern, die Fragen zeigen die Karte von oben) sehr langsam (±4° Peilung) um ihren Mittelpunkt, nur wenn die Bühne sichtbar ist, nie unter reduzierter Bewegung. Auf dem Handy aus (Akku, Rechenlast).

**Entscheidung Ruhezustand im Auftakt:** Der erste Bildschirm (flache Stadtteilkarte) steht bewusst still; Leben kommt über die Hover-Zustände und den Wechsel zum Zellgitter bei der ersten Frage. Gedreht wird nur im Schrägblick. `idleMotion: false` im Auftakt ist damit gewollt.

**Reduzierte Bewegung:** Kamera springt (`jumpTo`), keine Einblendungen, kein Drehen. (Bis 07.11.2026 standen hier auch die Säulen sofort; seither gibt es keine Säulen mehr.)

## Komposition

```
ERZÄHLUNG (Desktop)                         ERZÄHLUNG (390 px)
+--------------+---------------------------+  +----------------------+
| H1 Kiezatlas | BÜHNE (sticky, 100svh)    |  | H1 / Lede / 5 Zahlen |
| Lede         | Karte, Werkzeugleiste     |  +----------------------+
| 5 Stadtzahlen| oben, Legende unten links,|  | BÜHNE sticky 56svh   |
|--------------| Statuszeile               |  | Chips, Legende       |
| Frage 1      |                           |  +----------------------+
| Frage 2 ...  |                           |  | Frage-Karte          |
| Frage 6 Grenze                           |  | Frage-Karte ...      |
| Selbst erkunden                          |  +----------------------+
+--------------+---------------------------+

REGISTER (Index-Liste + Steckbrief)
+----------------------------+-----------------------+
| Sortierung: Nr Ew <18 65+ … | Steckbrief (sticky)   |
| 1 Nord   11 Bornim   ▬▬▬   | Gebiet-Auswahl        |
|          12 Nedlitz  ▬     | 5 Kennzahlen + Quelle |
| 2 …                        | Gegenprobe, Fußnote   |
+----------------------------+ Verteilungen (4)      |

GRENZFALL (asymmetrisches Paar, luftig)
+--------------------+-----------------------------+
| Zelle als Grafik   | Frage, Erklärung, Schalter  |
| (SVG aus Daten)    | Stadt-Zahlen                 |
+--------------------+-----------------------------+
| Tabelle: Mittelpunkt / Fläche / Abw. % / Personen / Grenzzellen |

METHODE (dunkel): Pipeline als Abfolge 1–5, darunter vier Absätze
QUELLEN (Liste, zwei Spalten)    FUSS (Impressumszeile, Stand)
```

## Genericness-Test

- Erste Idee war ein Kennzahlen-Hero mit fünf gleichen Kacheln: Template. Ersetzt durch die Karte als Bühne, die Stadtzahlen sind eine Zeile im Hero.
- Fade-up auf jedem Abschnitt gestrichen; Bewegung gibt es nur an der Karte, an Bedienelementen und einmal am Titel.
- Akzent nicht Orange/Grün, sondern das Violett der Verwaltungsgrenze, eingesetzt nur für Grenzen, Auswahl und Fokus.

## Technische Entscheidungen

- GSAP 3.15.1 + ScrollTrigger lokal unter `vendor/` (Fragen-Auslöser, Titel; den Säulen-Höhenfaktor gibt es seit 07.11.2026 nicht mehr, keine Säulen). **Kein Lenis:** Weichscrollen streitet mit dem Mausrad der Karte.
- MapLibre 4.7.1 lokal unter `vendor/` (gleiche Version wie bisher), `cooperativeGestures`: Mausrad scrollt die Seite, Strg+Mausrad bzw. zwei Finger bewegen die Karte.
- Alle Datenskripte `defer`, damit der Titel (LCP) sofort steht. `zellen.js` (1,1 MB) und die Gebäudedateien zählen im Audit als JS; das ist Daten, keine Logik, und bewusst so (file://-tauglich).
- Gebäude werden nur auf ausdrücklichen Wunsch geladen (Schalter „3D-Häuser“, Knopf in Frage 4 oder ab Zoom 14 bei gewähltem Stadtteil). Zellsäulen gibt es seit 07.11.2026 nicht mehr; mit 3D-Häusern bleibt das Zellgitter flach und heller (Deckkraft 0,55 wie auf der freien Karte) unter den Gebäuden. Hat der Nutzer 3D selbst eingeschaltet (Schalter oder Knopf in Frage 4), stellen die Fragen beim Weiterlesen nur noch das Thema ein (wie auf den Bauzeiten).
- Zellfarbe: fünf Stufen, Anteile zu 20 Prozentpunkten, Einwohner und Durchschnittsalter in Fünfteln aller Zellen; Zellen mit weniger als 10 Personen bzw. Wohnungen sind grau (Wert zu unscharf), so steht es in der Legende. Die Säulenhöhe (Einwohner über die Wurzel) entfiel am 07.11.2026, keine Säulen mehr; `T.hoehe` in `themen.js` bleibt als geprüfter Vertrag stehen, keine Seite nutzt es.

## Nachträge (Besitzerwünsche während des Baus)

- **Schaugrafik:** Export im Browser als SVG (Schriften eingebettet), PNG mit 300 dpi und PDF über die Druckansicht (`@page` in Formatgröße). Formate A4 hoch, A4 quer, halbe Seite quer, Spalte 85 mm, Quadrat. Karte nur aus eigenen Daten (Gitter, Stadtteile), keine Kacheln. Passt der Inhalt nicht, wird höchstens auf 85 % verkleinert und danach werden Rubriken von hinten weggelassen und benannt.
- **Datenschutz und Veröffentlichung:** alle Bibliotheken und Schriften lokal (`vendor/`, `fonts/`), fremd sind nur Kartenkacheln und Kartenschrift (basemap.de) und Luftbild (LGB); Hinweis im Fuß, Links auf Impressum und Datenschutz.
- **Desktop-Mausrad:** scrollt immer die Seite (kein Strg-Hinweis über der Karte); gezoomt wird per Doppelklick oder Knopf. Auf Touch bleibt die Zwei-Finger-Bedienung.
- **3D = Häuser, keine Säulen (Andre 07.11.):** „ich komm nirgends zu den 3d daten“, „zu viele säulen verwirren mich“. Auf der freien Karte (`karte.html`) und den Bauzeiten (`jahre.html`) heißt 3D nur noch: Häuser als Körper in Katasterhöhe. Der Schalter heißt „3D-Häuser“ und bringt mit einem Klick hin (Bauzeiten: gewählter Stadtteil, sonst die Kartenmitte ab Zoom 13, sonst die Innenstadt; Karte: wählt bei Bedarf einen Stadtteil und fliegt hin). Auf den Bauzeiten steht dazu im Auftakt der Knopf „Häuser in 3D ansehen“. Hat der Nutzer 3D selbst eingeschaltet, stellt die Geschichte beim Weiterlesen nur noch Ansicht und Bauzeit ein, nicht Kamera und 3D. Die Ebene `zellen-3d` bleibt, ist aber immer aus. Das Mausrad bleibt wie im Nachtrag davor. Seit dem Nachtrag am selben Tag („1 weg“, auf die Frage, ob die Säulen auch von der Startseite sollen) gilt das auch für die Startseite: keine Säulen mehr, die Zellen liegen flach (Farbe trägt den Wert), die Fragen zeigen die Karte von oben, schräg nur mit 3D-Häusern; dort heißt der Schalter ebenfalls „3D-Häuser“. Beleg: `belege/3D_haeuser_20261107.md`.
- **Responsive (Andre 07.11.):** Anlass „Handy-Karte auf der Bauzeiten-Seite zeigt nur 223 px“, Antwort „ja mach lieber voll responsive“. Regeln für alle vier Kartenseiten (Beleg `belege/responsive_20261107.md`, Entscheidung A19):
  - *Kopfleiste* klappt beim Lesen nach oben weg (Scrollen nach unten, Schwelle 12 px, oben unter 60 px immer sichtbar) und kommt beim Hochscrollen oder bei Tastaturfokus wieder (`kopf.js`). Startseite und Bauzeiten immer, Karte und Planer nur schmal (bis 860 px) oder niedrig (bis 500 px Höhe), dort beim Lesen im Blatt. Sie liegt über der Karte; die Bühne ändert ihre Größe dabei nicht (kein Neuzeichnen der Karte), Chips und Kartenknöpfe rücken mit nach oben. Reduzierte Bewegung: ohne Übergang.
  - *Gestapelt oder nebeneinander:* Karte oben und Text darunter nur am Handy hoch, Abfrage `(max-width:599px),(max-width:699px) and (orientation:portrait)` wörtlich gleich in `kopf.js` (`window.KIEZ_GESTAPELT`) und den Stylesheets. Handy quer und Tablet stehen Karte und Text nebeneinander wie am Desktop; Karte und Planer zeigen dort die Seitenleiste (320 px) statt des Blatts von unten.
  - *Höhen:* Bühne der Startseite am Handy 60svh (vorher 52), Bauzeiten 68svh ab Oberkante (vorher 68svh minus Kopfleiste); Blatt auf Karte und Planer offen 72svh (vorher 78dvh). svh statt dvh, damit die Karte beim Ein- und Ausfahren der Adressleiste nicht springt.
  - *Leiste der Bauzeiten:* Legende einklappbar (Knopf „Legende“), am Handy hoch und quer eingeklappt; niedrig wird die Leiste so knapp wie am Handy.
  - *Kartenknöpfe:* über dem Quellen-„i“ (vorher lag „Meinen Standort zeigen“ halb darunter), bei niedriger Höhe nebeneinander statt übereinander.
  - *Tippziele* auf Touch (`pointer:coarse`) mindestens 44 × 44 px: Chips, Kartenknöpfe, Quellen-„i“, Hauptnavigation, Marke, „Legende“ und „Nacheinander“. Desktop mit Maus bleibt bei 34 px.
  - *Chipzeile* auf Touch und schmal in einer Zeile, seitlich wischbar.
  - *Aussparungen:* `viewport-fit=cover`, Abstände aus `env(safe-area-inset-*)` an Kopfleiste, Rand (`--gut`), Kartenknöpfen, Blatt und Leiste.
  - Das Mausrad scrollt am Desktop weiter die Seite.
