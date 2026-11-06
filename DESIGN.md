# Kiezatlas Potsdam: Gestaltung

## Brief

- **Gegenstand:** Alle 32 Stadtteile Potsdams in Zahlen und Karte, aus Zensus 2022 (100-m-Gitter), amtlichen Stadtteilen und ALKIS-Gebäuden. Prototyp der Stiebitz Souverain Systems UG.
- **Publikum:** Stadtplanung, Wohnungsunternehmen, Quartiersarbeit, Verwaltung, Fachpublikum. Sachlich, präzise, ruhig.
- **Aufgabe der Seite:** In einem Durchgang zeigen, was das Werkzeug kann (Fragen als Einstieg), dann frei erkunden, vergleichen, die Methode nachvollziehen. Sorgfalt sichtbar machen (Grenzfall, Quellen bei jeder Zahl).
- **Wünsche des Besitzers:** Einstieg über Alltagsfragen, die die Karte an die richtige Stelle führen und nebenbei je eine Funktion erklären. Zensus-Gitter als echte 3D-Säulen mit Tiefenwirkung, Höhe nach Wert, schräger Blick.
- **Grenzen:** Statisch, ohne Build, läuft per Doppelklick und über einen statischen Server. Daten nur aus `daten/*.js` (nie von Hand eingesetzte Zahlen). Kein Orange, keine Gedankenstrich-Ketten, keine Buzzwords.
- **Annahmen:** Keine Bilder außer Karte und Luftbild. Kein Loader. One-Pager plus `404.html`.

## Drei Konzepte

| | Idee | Anker | Signatur | O / F / Fe / P |
|---|---|---|---|---|
| A. Material: das Gitter | Potsdam besteht aus 100-m-Zellen, und auf jede Frage hin richtet sich die Stadt in Säulen auf | Zensus-Gitter EPSG:3035, 100 m, bewohnte Zellen; die Havelseen bleiben als Leerstellen | Die flache Stadtteilkarte kippt beim ersten Scroll und die Zellen wachsen zu Säulen; jede Frage baut das Gitter um | 4 / 5 / 4 / 1 |
| B. Ort: die Stadtteilnummern | Die Ordnung 11 bis 86 (Bezirk = erste Ziffer) trägt Register, Farben und Navigation | amtliche Nummerierung der Stadt | Ein Nummernregister, das Flächen auf der Karte aufleuchten lässt | 3 / 4 / 5 / 2 |
| C. Formal: die Grenzlinie | Die violette Verwaltungsgrenze der topografischen Karte ist der rote Faden; alles dreht sich um Zuordnung | Signatur der Verwaltungsgrenzen in der TK, Grenzfall-Methode | Eine Zelle, die von der Grenze geteilt wird, wechselt zwischen „ganz“ und „anteilig“ | 4 / 4 / 4 / 2 |

**Gewählt: A.** Es trägt beide Wünsche des Besitzers (Fragen führen die Karte, 3D-Gitter) und lässt sich aus keinem anderen Projekt übertragen. Aus C kommen die Akzentfarbe (Grenzviolett) und die Grenzfall-Grafik, aus B das Stadtteil-Register (gruppiert nach Bezirk).

## Concept Card

```
Idea:        Potsdam als Gitter aus 100-m-Zellen, das sich auf Alltagsfragen hin aufrichtet und Antworten in Höhe und Farbe zeigt.
Metaphor:    Das Kartenblatt der Landesvermessung: Gitter, Rahmen, violette Verwaltungsgrenzen, DIN-Schrift.
Signature:   Beim ersten Scroll kippt die flache Stadtteilkarte in den Schrägblick und die Zellen wachsen zu Säulen
             (MapLibre fill-extrusion, ein Höhenfaktor über den GSAP-Ticker); jede weitere Frage baut das Gitter um.
Emotion:     ruhig, genau, „ach so funktioniert das“.
Motion verb: aufrichten und einrasten (Dinge wachsen aus der Grundlinie und rasten auf das Raster).
Screenshot:  Die schräg gestellte Stadt aus Säulen, die Havel als Leerstelle, daneben die Frage „Wie viele Menschen wohnen in meiner Nachbarschaft?“.
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

**Bewegung:** ein Ease `cubic-bezier(.2,.8,.2,1)` (expo-artig) für alles, Kamera 1,4 s, Säulen 0,9 s, Hover 0,35 s. Aufrichten: Knöpfe füllen sich von der Grundlinie aufwärts; Registerzeilen lassen einen violetten Block einrasten; Textlinks haben eine Linie, die dicker wird.

**Ruhezustand:** Nach 2 s ohne Scroll und ohne Zeiger dreht sich die schräg gestellte Stadt sehr langsam (±4° Peilung) um ihren Mittelpunkt, nur wenn die Bühne sichtbar ist, nie unter reduzierter Bewegung. Auf dem Handy aus (Akku, Rechenlast).

**Entscheidung Ruhezustand im Auftakt:** Der erste Bildschirm (flache Stadtteilkarte) steht bewusst still; Leben kommt über die Hover-Zustände und das Aufrichten bei der ersten Frage. Gedreht wird erst im Schrägblick. `idleMotion: false` im Auftakt ist damit gewollt.

**Reduzierte Bewegung:** Kamera springt (`jumpTo`), Säulen stehen sofort, keine Einblendungen, kein Drehen. Der Schrägblick bleibt, damit die Säulen lesbar bleiben.

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

- GSAP 3.15.1 + ScrollTrigger lokal unter `vendor/` (Fragen-Auslöser, Säulen-Höhenfaktor, Titel). **Kein Lenis:** Weichscrollen streitet mit dem Mausrad der Karte.
- MapLibre 4.7.1 lokal unter `vendor/` (gleiche Version wie bisher), `cooperativeGestures`: Mausrad scrollt die Seite, Strg+Mausrad bzw. zwei Finger bewegen die Karte.
- Alle Datenskripte `defer`, damit der Titel (LCP) sofort steht. `zellen.js` (1,1 MB) und die Gebäudedateien zählen im Audit als JS; das ist Daten, keine Logik, und bewusst so (file://-tauglich).
- Gebäude werden nur auf ausdrücklichen Wunsch geladen (Schalter „Gebäude in 3D“ oder ab Zoom 14 bei gewähltem Stadtteil). Gebäude in 3D und Zellsäulen erscheinen nie gleichzeitig.
- Säulenhöhe: Einwohner über die Wurzel (sonst wenige Nadeln), Durchschnittsalter ab dem Minimum, Anteile bei 100 % gekappt; Zellen mit weniger als 10 Personen bzw. Wohnungen liegen flach und grau (Wert zu unscharf), so steht es in der Legende.

## Nachträge (Besitzerwünsche während des Baus)

- **Schaugrafik:** Export im Browser als SVG (Schriften eingebettet), PNG mit 300 dpi und PDF über die Druckansicht (`@page` in Formatgröße). Formate A4 hoch, A4 quer, halbe Seite quer, Spalte 85 mm, Quadrat. Karte nur aus eigenen Daten (Gitter, Stadtteile), keine Kacheln. Passt der Inhalt nicht, wird höchstens auf 85 % verkleinert und danach werden Rubriken von hinten weggelassen und benannt.
- **Datenschutz und Veröffentlichung:** alle Bibliotheken und Schriften lokal (`vendor/`, `fonts/`), fremd sind nur Kartenkacheln und Kartenschrift (basemap.de) und Luftbild (LGB); Hinweis im Fuß, Links auf Impressum und Datenschutz.
- **Desktop-Mausrad:** scrollt immer die Seite (kein Strg-Hinweis über der Karte); gezoomt wird per Doppelklick oder Knopf. Auf Touch bleibt die Zwei-Finger-Bedienung.
