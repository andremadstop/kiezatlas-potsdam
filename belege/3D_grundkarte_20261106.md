# 3D-Gebäude mit Katasterhöhe und Vektor-Grundkarte (06.11.2026)

Anlass: Andre fragte, warum die Karte so anders aussieht als die Berliner Gebäudealterskarte (visinage) und wo
Details und 3D-Gebäude sind. Auftrag: „ja mach a und b, alles was geht“ (a = 3D-Gebäude auf der Bauzeiten-Seite,
b = detailreichere Grundkarte). Zweig `ausbau/3d-grundkarte`.

## Entscheidungen

| Nr. | Entscheidung | Begründung | Verworfen |
|---|---|---|---|
| G1 | Gebäudehöhe = ALKIS-Objekthöhe aus dem NAS-Auszug (`auswertung.alkis_nas_gebaeude.objekthoehe`), ganze Meter | liegt für 96,3 % der Gebäude vor, amtlich, gleiche Lizenz wie die Umrisse (dl-de/by-2-0) | LoD2 aus den Lottenhof-/Winzerberg-Projekten: nur 5 Kacheln à 1 km² (Andres Zwischenruf); Dachformen kann MapLibre mit `fill-extrusion` ohnehin nicht zeigen |
| G2 | Rückfall: Geschosse × 3 m, sonst 3 m; Werte ≤ 0,5 m (Tiefbauten, negative Angaben) gelten als fehlend | eine Höhe je Gebäude, kein Loch in der 3D-Ansicht; Rückfall offen gezählt (unten) | Gebäude ohne Höhe weglassen (sähe aus wie unbebaut) |
| G3 | Höhe auch für die Stadtteilkarte (`daten/gebaeude/*.js`), vorher immer Geschosse × 3 m | eine Höhenquelle für alle Seiten | — |
| G4 | 3D-Körper erst ab Zoom 14 und nur bei eingeschaltetem 3D; geschätzte Bauzeit heller statt durchscheinend | `fill-extrusion` kennt keine Deckkraft je Objekt; dieselbe Lesart wie in 2D (kräftig = belegt) | — |
| G5 | Grundkarte = basemap.de Web Vektor, Auszug aus dem Stil `bm_web_gry`, statt Web Raster grau | Straßen, Gewässer, Grün und Namen lesbar; Beschriftung über den eigenen Ebenen; amtlich, CC BY 4.0 | OSM-Vektorkacheln (ODbL, fremder Dienst); Raster mit mehr Deckkraft (Namen bleiben unter den Zellen) |
| G6 | Aus dem Stil entfernt: Gebäude, Adressen, Gebäudesymbole, alle Ebenen mit Sprite-Bildern, Themen ohne Potsdam-Bezug (Meer, Watt, Fels, Bergbau, Flughafen, Staats-/Landesgrenzen u. a.), Hintergrundfläche | eigene Gebäude ohne Doppelung; kein Sprite-Abruf; 16 KB gz statt 500 KB | den Stil zur Laufzeit von sgx laden (ein Abruf mehr je Besuch, kein Rückfall offline) |
| G7 | Fehlt `daten/grundkarte.js`, bleibt die Rasterkarte (Rückfall in `themen.js`) | Seiten bleiben benutzbar | — |
| G8 | Quellenvermerk nach den Nutzungsbedingungen des BKG: „© GeoBasis-DE / BKG (2026) CC BY 4.0“, BKG und Lizenz verlinkt, „Kartenstil verändert“ | wörtlich verlangt (PDF unter `kiezatlas-daten/eingang/basemapde/`); der alte Vermerk „© basemap.de / BKG“ entsprach dem schon beim Raster nicht | — |

## Zählungen

Höhenherkunft der 52.309 Gebäude in Potsdam (Snapshot `auswertung.gebaeude_stand_20261105`, Zuordnung zum
Stadtteil über einen Punkt im Umriss):

| Herkunft | Gebäude | Anteil |
|---|---:|---:|
| ALKIS-Objekthöhe > 0,5 m | 50.356 | 96,3 % |
| keine bzw. ≤ 0,5 m Objekthöhe, Geschosszahl vorhanden (NAS, sonst ALKIS vereinfacht) → Geschosse × 3 m | 73 | 0,1 % |
| weder Objekthöhe noch Geschosse → 3 m | 1.880 | 3,6 % |

Nachtrag nach dem Audit (K1): Jedes Gebäude trägt jetzt die Herkunft seiner Höhe (`hq`: kataster, geschosse,
ersatz), das Fenster zum Gebäude nennt sie. Dabei vereinheitlicht: Die Geschosszahl kommt auf beiden Seiten erst aus
dem NAS-Auszug, sonst aus ALKIS vereinfacht (vorher Bauzeiten nur NAS: 38 / 1.915; Stadtteilkarte nur WFS). Abgleich:
0 von 52.305 Umrissen haben auf Bauzeiten-Seite und Stadtteilkarte verschiedene Höhen.

Plausibilität der Objekthöhe (alle 50.409 NAS-Gebäude mit Wert): Minimum −9,1 m, 5 % 2,2 m, Median 5,5 m,
95 % 16,2 m, Maximum 89 m. Median je Geschosszahl: 1 → 3,1 m, 2 → 8,6 m, 3 → 11 m, 4 → 14,2 m, 5 → 17,3 m,
6 → 19,6 m. Die Werte sind relativ zum Gelände, nicht über NHN (Potsdam liegt 30 bis 100 m über NHN).

Stadtteilkarte (`daten/gebaeude/*.js`, 52.309 Gebäude in Potsdam in 32 Dateien): Abgleich je Umriss gegen den
vorigen Stand (52.305 verschiedene Umrisse, vier Umrisse kommen doppelt vor): Höhe bei 12.461 gleich geblieben
(denselben Wert ergab schon Geschosse × 3 m), bei den übrigen 39.844 geändert; Funktion, Geschosszahl und Umrisse
unverändert. Die Merkmale je Datei sind jetzt nach oid sortiert (vorher ohne feste Reihenfolge).

Bauzeit-Schätzung unverändert: Die 32 Dateien `daten/jahre/<nr>.js` sind ohne das neue Feld `h` und ohne `stand`
inhaltsgleich mit dem Stand vor der Änderung (Abgleich aller Features). Die Kaskade lief vollständig neu
(`skripte/24_jahre_kaskade.py rechnen`): je Stufe 106 / 815 / 17.294 / 8.501 / 25.593 Gebäude (Stufen 1, 3, 4, 5, 6),
wie vorher.

Gewicht: `daten/grundkarte.js` 16,1 KB gz (261 Ebenen unten, 89 Beschriftungen; 350 von 572 Ebenen des
Originalstils). Größte Gebäudedatei `daten/jahre/52.js` 188 KB gz statt 182 KB gz (+3 %). Die Grenze für das
Startgewicht des Planers (`pruefen/A7_planer.mjs`) steigt deshalb von 300 auf 320 KB gz JS.

## Prüfungen

| Prüfung | Ergebnis |
|---|---|
| `python -I pruefen/daten.py` (Verträge, neu `grundkarte.json`, `h` in `jahre_gebaeude.json` und `gebaeude.json`) | 0 Abweichungen |
| `node pruefen/B5_jahre.mjs` (Bauzeiten, neu: `h` ganzzahlig 1–200) | grün, 203 Punkte |
| `node pruefen/seiten.mjs` (Startseite, Karte, axe) | grün |
| `node pruefen/A7_planer.mjs` (Planer, Download-Liste mit `grundkarte.json`) | grün |
| `node pruefen/p1_themen.mjs` (Vertrag `KIEZ_THEMEN`, neu `grundkarte`, `grundLuft`, `GRUNDKARTE`) | grün |
| `node pruefen/p1_gleich.mjs` | grün |
| ruff (E, F, W) auf den geänderten Python-Skripten | keine Befunde |
| Gegenprobe mit frischem Blick (Code-Review) | kein Fund ab Sicherheit 80; drei Hinweise darunter, siehe Grenzen |

Die Prüfskripte laufen ohne Netz: Fremde Anfragen beantwortet der Prüfbrowser selbst, Vektorkacheln und
Schriften (`.pbf`) neu mit einer leeren Protobuf-Antwort.

Sichtprüfung mit echten Kacheln: ein einziger Lauf am 06.11.2026 über einen lokalen Server, sieben Ansichten
(Bauzeiten Überblick, 3D Babelsberg, 2D Innenstadt, Handy 3D, Stadtteilkarte 3D, Planer, Startseite), dabei
0 Konsolenfehler. Kacheln und Schriften von sgx.geodatenzentrum.de (robots.txt erlaubt `/gdz_basemapde_vektor/`,
gesperrt sind nur `/gdz_geoviewserver/` und `/gdz_geoviewserv/`).

## Netzabrufe für diese Änderung

| Was | Wie oft |
|---|---|
| robots.txt sgx.geodatenzentrum.de, basemap.de | je 1 |
| Stil `bm_web_gry.json`, TileJSON, Nutzungsbedingungen (PDF) | je 1, abgelegt mit Prüfsumme in `kiezatlas-daten/eingang/basemapde/` (HERKUNFT.md) |
| Produktseite basemap.de Web Vektor (Lizenzangabe gesucht) | 4 Statusabfragen, 2 Seitenabrufe |
| Kacheln und Schriften im Sichtlauf | ein Lauf, sieben Ansichten |

## Grenzen

- Dächer: jedes Gebäude ist ein Block mit flachem Dach in Objekthöhe. LoD2 mit Dachformen gibt es für Potsdam
  nur kachelweise lokal (5 km²); stadtweit nicht geprüft.
- 1.880 Gebäude (3,6 %) haben den Ersatzwert 3 m, meist Nebengebäude ohne Eintrag im NAS-Auszug.
- Die Stadtteilkarte verknüpft `public.gebaeude` über die oid mit dem NAS-Auszug, der sich auf den Snapshot vom
  05.11. bezieht. Heute sind beide gleich; nach einem neuen ALKIS-Import fielen geänderte Gebäude still auf
  Geschosse × 3 m zurück (Hinweis der Gegenprobe, nicht behoben).
- Die Grundkarte lädt Kacheln und Kartenschrift bei sgx.geodatenzentrum.de; dieser Server sieht die IP-Adresse
  (Datenschutzhinweise angepasst). Fällt der Dienst aus, bleibt die Papierfarbe ohne Grundkarte.
- Die Auswahl der entfernten Ebenen beruht auf Ebenennamen (regulärer Ausdruck in `skripte/27_grundkarte.py`).
  Ändert basemap.de seine Namen, kann eine Ebene still wegfallen; das Skript bricht nur ab, wenn eine der
  beiden Gruppen leer wird.
- Nicht geprüft: Darstellung auf echten Mobilgeräten (nur Browser im Handyformat), Ladezeit über langsame Netze.
