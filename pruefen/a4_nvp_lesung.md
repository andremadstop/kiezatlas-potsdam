# A4: Lese-Protokoll Nahverkehrsplan 2019 und Stichprobe Taktklasse

Paket A4, 05.11.2026. Erfüllt Korrektur 11 des Prüfberichts („Tab. 4.2/4.3 und die zugehörige Gebietskarte vor A4 noch
einmal lesen und das Ergebnis protokollieren; Aktualität prüfen“). Seitenangaben sind Druckseiten des NVP
(PDF-Seite = Druckseite + 1).

Quelle: `$KIEZ_DATEN/nvp_potsdam/2019/2020-09-29_nvp_potsdam_mit_anlagen.pdf`, sha256 `3e9a83e1…cbc1bf`, abgerufen
05.11.2026 10:09 UTC über `skripte/abruf.py` (robots vorher gelesen, siehe `HERKUNFT.md` dort).

## 1. Was der NVP sagt

| Stelle | Inhalt | Folge für den Atlas |
|---|---|---|
| Kap. 4.1, S. 54 | Das Anforderungsprofil gilt „im Zeitraum von 2019 bis 2023“. | Plan formal abgelaufen; siehe Abschnitt 3. |
| Kap. 4.1.1, S. 54–55 | Gebietskategorien auf Basis der Ortsteile, eingeteilt nach Nutzungsdichte (potenzielle ÖPNV-Nutzende je bebauter Fläche, Prognose 2023 und FNP): Klasse I hoch, II mittel, III niedrig. | **Die Klasse gehört zum Gebiet, nicht zur Haltestelle.** |
| Tab. 4.1, S. 55–56 | 15 Ortsteile in Klasse I, 15 in II, 16 in III; Forst Potsdam Süd und Wildpark ohne Klasse; am Wochenende eine Klasse tiefer: Bornstedter Feld, Babelsberg Süd, Am Stern (→ II), Golm Ost/West, Industriegelände (→ III). | wörtlich in `config/richtwerte.yaml` → `oepnv.gebietsklassen.nvp_ortsteile` |
| Text S. 56 | Klasse I = Korridor Innenstadt, westliche/südliche Vorstädte, südliches Babelsberg, Stern-Drewitz-Kirchsteigfeld „und zur Waldstadt I“, Bornstedter Feld, Golm. | **Widerspruch:** Tab. 4.1 führt Waldstadt I unter Klasse II, Text und Anlage 4 unter Klasse I. Nicht aufgelöst, in der YAML vermerkt. |
| Abb. 4.1, S. 57–58 | Verkehrszeiten Mo–Fr: HVZ Klasse I 6–9 und 13–18 Uhr, Klasse II ebenso mit Übergangszeiten, Klasse III 7–9 und etwa 13/14–18 Uhr. | Messfenster 06:00–09:00 (morgendliche HVZ Klasse I/II) |
| Kap. 4.1.3, S. 58 | Teilflächen mit mehr als 200 EW sollen erschlossen sein; erschlossen, wenn 80 % der EW in den fußläufigen Einzugsbereichen liegen. | `oepnv.erschliessung`; „Teilfläche“ ist nicht als Geometrie definiert. |
| Tab. 4.2, S. 59 | Einzugsbereich (Luftlinie) nach Verkehrsmittel und Klasse: Straßenbahn 350 / 450 / – m, Bus 300 / 400 / 500 m (I / II / III). | `oepnv.einzugsradius_m`; Schlüssel ist die **Gebietsklasse**. |
| Tab. 4.3, S. 59 | Soll-Fahrten je Stunde und Richtung: HVZ I 6–12, II 2–3, III 1; NVZ I 3–6, II 2–3, III 0,5–1; SVZ I 3, II 1, III 0,5–1; NaVZ I 1 (WE 2), II 1 (WE), III –. Abfahrten „möglichst gleichmäßig auf eine Stunde verteilt“. | `oepnv.taktklassen` (HVZ-Untergrenzen) |
| S. 59 unten | Erschließung gegeben, wenn für den überwiegenden Teil des Gebiets (bzw. die maßgeblichen Haltestellen) die Kriterien erfüllt sind. In die Bewertung gehen alle ÖPNV-Angebote einschließlich einfahrender Regionalverkehre ein. | Regionalbus und SPNV zählen mit. |
| Abb. 4.2, S. 61 (Gebietskarte) | Karte der Einzugsgebiete: Klasse I Bus 300 m, Klasse I Tram 350 m, Klasse II Bus 400 m, Klasse II Tram 450 m, Klasse III 500 m, SPNV als eigene Signatur **ohne Radiusangabe**; Erschließungslücken markiert (Liste S. 60). | Bestätigt: Radius nach Gebietsklasse × Verkehrsmittel. SPNV-Radius bleibt `null`. |
| S. 61 | HVZ-Unterschreitungen 2019 u. a. an Falkenhorst, Am Fenn, Drewitzer Str./E.-Weinert-Str., Unter den Eichen, Spindelstr., Theodor-Fontane-Str.; zu allen Zeiten in Golm, Schloss Sanssouci, Telegrafenberg, Karl-Liebknecht-Stadion. | Plausibilitätsprüfung der Stichprobe (Abschnitt 4) |
| Anlage 2 | Einwohner 31.12.2017 je **statistischem Bezirk** (dreistellige Nummern, z. B. 131 Das Kurze Feld, 132 Bornstedter Feld, 133 Bornstedter Ortslage). | Die NVP-Ortsteile entsprechen den statistischen Bezirken bzw. deren Gruppen. Genaue Geometrie → H1 (statistische-bezirke-in-potsdam). |
| Anlage 4 | Bewertung der Bedienungshäufigkeit je Haltestelle; Fenster: Klasse I HVZ 6–8 Uhr, Klasse II/III HVZ 7–9 Uhr (Fußnoten 1 und 2). | Bewertungsfenster des NVP; in der YAML als `hvz_fenster_nvp_anlage4` vermerkt. |

## 2. Was das für A4 heißt (Entscheidungen)

1. **Zwei Klassen, nicht eine.** Die Spalte `auswertung.haltestelle.klasse` (DDL von P0, CHECK auf I/II/III/„unter III“) trägt die
   **Taktklasse**: den gemessenen HVZ-Takt der Haltestelle, eingeordnet an den Untergrenzen der Tab. 4.3 (≥ 6 → I, ≥ 2 → II,
   ≥ 1 → III, sonst „unter III“). Werte über 3 und unter 6 ordnet der NVP keiner Klasse zu; hier gelten sie als II (eigene
   Festlegung, in der YAML). Die **Gebietsklasse** (Tab. 4.1) steht in `config/richtwerte.yaml` → `oepnv.gebietsklassen`.
   Einzugsradius und Soll-Takt folgen aus der Gebietsklasse. A5 nimmt den Radius nie aus `klasse`.
2. **Gebietsklasse auf Stadtteile:** eindeutig bzw. zusammengesetzt bei 23 der 32 Stadtteile; gemischt bei 7
   (11 Bornim, 13 Bornstedt, 32 Potsdam West, 64 Waldstadt I/Industriegelände, 72 Drewitz, 84 Fahrland, 86 Groß Glienicke),
   offen bei 2 (43 Zentrum Ost/Nuthepark, 44 Hauptbahnhof/Brauhausberg Nord, kein gleichnamiger NVP-Ortsteil).
   Die genaue Zuordnung braucht die Geometrie der statistischen Bezirke (H1). Bis dahin: blockiert für die 9 Stadtteile.
   **Nachlauf N2 (05.11.2026): mit den statistischen Bezirken bestimmt, siehe Abschnitt 6.**
3. **Messung:** Stichtag Dienstag 10.11.2026 (Schultag; Herbstferien Brandenburg 19.–30.10.2026), Fenster 06:00–09:00,
   Mittel je Stunde. Gezählt werden Abfahrten (ohne Endhalt der Fahrt, ohne pickup_type 1), alle Linien zusammen, getrennt
   nach `direction_id`; es zählt die stärkere Richtung. Fahrten des Vortags nach Mitternacht (Zeiten ≥ 24:00) werden
   berücksichtigt.
4. **Bekannte Grenze der Richtungszählung:** `direction_id` ist je Linie festgelegt, nicht je Straßenseite. Beispiel
   Theodor-Fontane-Str.: Linie 638 mit direction_id 1 hält am Steig ::1 zusammen mit Linie 604 direction_id 0. An Knoten mit
   mehreren Linien kann der Wert deshalb von einer Zählung je Straßenseite abweichen. Für die Stichprobe ändert das nichts
   (Steig ::1: 5 Abfahrten, ::2: 4; Wert 5/3 = 1,7 in beiden Lesarten).
5. **Haltestelle** = DHID-Stamm (z. B. `de:12054:900230014`). Platz der Einheit besteht so aus drei Haltestellen (West,
   Nord, Bildungsforum), wie im VBB. Bahnhöfe fassen Bahnsteige und Bus-/Tramsteige zusammen, wenn sie denselben Stamm haben
   (z. B. Pirschheide Bhf: bus+spnv+tram). Für A5: bei mehreren Verkehrsmitteln den größten Radius der vorhandenen Mittel nehmen.
6. **Umland:** Haltestellen bis 1.000 m außerhalb der Stadtgrenze bleiben drin (`in_potsdam = false`), Berlin nicht (E7).

## 3. Aktualität

- NVP 2019: Geltung 2019–2023 (Kap. 4.1). Zwei Websuchen am 05.11.2026 („Nahverkehrsplan Potsdam Fortschreibung 2025 2026“,
  „Potsdam Nahverkehrsplan 2024 OR 2025 … Beschluss“) fanden keinen Nachfolger; Treffer nur bis 2020 (Beschluss SVV 16.09.2020,
  DS 20/SVV/0222). Bei der Stadt nicht nachgefragt, Ratsinfo nicht durchsucht.
- **Befund: formal abgelaufen, Nachfolger ungeprüft.** Die Werte gelten im Atlas als „NVP 2019 (Geltung bis 2023, kein
  Nachfolger gefunden)“. Keine Aussage, der Plan sei aktuell.
- Nicht geprüft (Prüfbericht 11, Rest): EHK/STEK Einzelhandel und Schülerfahrtkostensatzung, nicht A4.

## 4. Stichprobe: fünf Haltestellen von Hand gegen den Fahrplan

Liste der einzelnen Abfahrten: `belege/a4_stichprobe_20261110.txt`, erzeugt mit `pruefen/a4_stichprobe.py` (eigene,
von `skripte/13_oepnv.py` unabhängige Auswahl von Diensten und Fahrten). Gezählt von Hand am 05.11.2026, Stichtag 10.11.2026,
06:00–09:00 (3 h). Endhalte nicht gezählt.

| Haltestelle | Richtung 0 | Richtung 1 | von Hand: max/3 h | Tabelle | Taktklasse | NVP 2019 (Gebietsklasse, Soll HVZ) | Anlage 4 / S. 61 |
|---|---|---|---|---|---|---|---|
| Spindelstr. (694, 616) | 17 | 17 | 17/3 = 5,7 | 5,7 | II | Babelsberg Zentrum, I, ≥ 6 | HVZ-Defizit 2019; 2026 weiter knapp unter 6 |
| Falkenhorst (693, 602) | 10 | 11 | 11/3 = 3,7 | 3,7 | II | Schlaatz, I, ≥ 6 | HVZ-Defizit 2019; weiter |
| Theodor-Fontane-Str. (604, 638) | 4 | 5 | 5/3 = 1,7 | 1,7 | III | Groß Glienicke, II, ≥ 2 | HVZ-Defizit 2019; weiter |
| Kienheide (609) | 1 | 1 | 1/3 = 0,3 | 0,3 | unter III | Satzkorn, III, ≥ 1 | HVZ-Defizit 2019; weiter |
| Platz der Einheit/Nord (Tram 93, 96, 98, 99) | 5 | 6 | 6/3 = 2,0 | 2,0 | II | Nördliche Innenstadt, I | Wendestelle; der Platz insgesamt: West 38,7 (I), Bildungsforum 13,3 (I) |

Ergebnis: 5 von 5 Tabellenwerten stimmen mit der Handzählung überein. Die vier Haltestellen, die der NVP 2019 als
HVZ-Defizit führt, liegen auch im Fahrplan ab 03.11.2026 unter dem Soll ihrer Gebietsklasse. Der Abgleich mit Anlage 4 ist
eine Plausibilitätsprüfung (anderer Fahrplan), keine Abnahme.

## 5. Gegenproben der Abnahme

- `pruefen/a4_haltestelle.py` (Ausgabe `belege/a4_pruefung_20261105.txt`): 283 Potsdamer Haltestellen, 0 ohne Klasse,
  stop_id eindeutig, jede Klasse folgt aus `fahrten_hvz_je_richtung` und den YAML-Grenzen, keine Berliner Haltestelle,
  keine Taktgrenze und kein Radius aus Tab. 4.2 im Code. Ergebnis „ok“.
- Negativprobe: Grenze für Klasse I in einer Kopie der YAML auf 10 gesetzt → `13_oepnv.py --trocken` liefert 52 statt 112
  Haltestellen der Klasse I; `a4_haltestelle.py` gegen die geänderte YAML meldet 63 Verstöße. Die Grenzen wirken also aus
  der YAML, nicht aus dem Code. YAML danach zurückgesetzt (byte-gleich geprüft).
- Ohne Abfahrt am Stichtag und deshalb nicht in der Tabelle (DHID-Stamm de:12054): Hiroshima-Nagasaki-Platz, Freiligrathstr.,
  Otto-Erich-Str. (alle Rudolf-Breitscheid-Straße), Am Küssel, Wublitzstr./Am Bahnhof, Hauptbahnhof/Friedrich-Engels-Str.
  (Tramsteig), die Fähranleger Auf dem Kiewitt und Hermannswerder. Ursache (Baustelle, Saison) nicht geprüft.

## 6. Nachlauf N2: Gebietsklasse je statistischem Bezirk (05.11.2026)

Eingang: `$KIEZ_DATEN/eingang/statistische-bezirke-in-potsdam.geojson` (H1, LHP, Stand 31.12.2021, 86 Bezirke,
dl-de/by-2-0, sha256 `e5949434…`). Nur intern gerechnet; in `daten/` und im Export steht nichts daraus.
Ergebnis in `config/richtwerte.yaml` → `oepnv.gebietsklassen.statistische_bezirke` (29 Bezirke) und in den 9
Stadtteil-Einträgen (`bezirke_geprueft`, `anteil_ew_prozent`). Gegenprobe: `pruefen/a4_gebietsklassen.py`, Ausgabe
`belege/a4_gebietsklassen_20261105.txt` (0 Befunde).

**Wie zugeordnet wird.** Der NVP hat keine Ortsteilgrenzen als Datei. Anlage 2 listet die Einwohner je statistischem
Bezirk (Nummern von 2017); die ersten zwei Ziffern bilden die Ortsteilgruppe, Tab. 4.1 teilt einige Gruppen weiter.
Alle 86 Bezirke liegen zu ≥ 99 % in dem Stadtteil ihrer ersten zwei Ziffern. Je Bezirk eine Grundlage:
- **name:** Bezirksname = NVP-Ortsteil (z. B. 131 Das Kurze Feld, 323 Forststraße, 843 Kartzow).
- **anker:** Haltestellen, die Anlage 3 oder 4 unter dem Ortsteil bzw. der Klasse führt, liegen im Bezirk
  (z. B. 844 mit sechs Fahrländer Haltestellen der Klasse II, 845 Fahrländer See, 842 Rotkehlchenweg; 111 mit der
  Haltestelle Institut für Agrartechnik als Anker für „Institut Bornim“).
- **nummer:** Ortsteil aus der Nummerngruppe der Anlage 2. 43 und 44 bestehen aus den Bezirken der Gruppe 42 von 2017
  (421 Brauhausberg Nord, 422 Hauptbahnhof, 423 Zentrum Ost), also Südliche Innenstadt, Klasse I. Anlage 4 führt
  Am Havelblick (441) und Schlaatzstr. (442) unter Klasse I (Zeile Teltower Vorstadt, ebenfalls I).
- **ausschluss:** einziger übrig bleibender Ortsteil der Gruppe (113 Katharinenholz → Bornim, 322 Luftschiffhafen →
  Potsdam West, 722/725 → Drewitz).

**Umnummerierung 2017 → 2021 (nach Namen):** 330 → 324 Wildpark, 421/422 → 441/442, 423 → 431 (+ 432 Nuthepark),
660 → 644 Industriegelände, 670 → 613 Forst Potsdam Süd, 841 → 844 Fahrland Ortslage, 842 → 845 Krampnitz.

**Ergebnis für die 9 Stadtteile** (Einwohneranteile Zensus 2022, Zellmittelpunkt im Bezirk):

| Stadtteil | Bezirke → Klasse | Stadtteilklasse |
|---|---|---|
| 11 Bornim | 112, 113 → II; 111, 114 → III | gemischt: II 83 %, III 17 % |
| 13 Bornstedt | 132 → I; 133 → II; 131 → III | gemischt: I 73 %, II 13 %, III 15 % |
| 32 Potsdam West | 321, 322 → I; 323 → III; 324 Wildpark ohne Klasse | gemischt: I 85 %, III 14 %, ohne 1 % |
| 43 Zentrum Ost und Nuthepark | 431, 432 → I | **I** (vorher offen) |
| 44 Hauptbahnhof und Brauhausberg Nord | 441, 442 → I | **I** (vorher offen) |
| 64 Waldstadt I und Industriegelände | 641–643 Waldstadt I → I oder II; 644 → II | nicht eindeutig: nach Tab. 4.1 ganz II, nach Text/Anlage 4 zu 98 % I |
| 72 Drewitz | 722–725 → I; 721 Drewitz Ortslage (Alt Drewitz) → III | gemischt: I 83 %, III 17 % |
| 84 Fahrland | 844, 845 → II; 842, 843 → III | gemischt: II 96 %, III 4 % |
| 86 Groß Glienicke | 860 → II oder III | nicht trennbar: ein Bezirk mit Groß Glienicke (II) und Waldsiedlung (III) |

Genau bestimmt ist damit die Klasse **je Bezirk** in 7 der 9 Stadtteile vollständig; eine einzige Stadtteilklasse gibt es
nur in 43 und 44. In 11, 13, 32, 72 und 84 ist der Stadtteil tatsächlich gemischt. Offen bleiben Waldstadt I (Widerspruch
im NVP) und Groß Glienicke (keine feinere Grenze). Eine Mehrheitsklasse je Stadtteil wird bewusst nicht gesetzt.

**Folge für A6 (nicht in N2 geändert):** `15_planer.py` nimmt die Klasse je Zelle aus dem Stadtteil. Mit der Klasse je
Bezirk hätten in diesen 9 Stadtteilen statt rund 50.340 nur noch rund 11.050 Einwohner keine eindeutige Klasse
(Waldstadt I und Groß Glienicke). Die neue Klasse I für 43 und 44 macht `daten/planer.js` veraltet: `pruefen/A6_planer.py`
meldet mit der neuen YAML Abweichungen in den Planungsräumen 401 und 601 (ÖPNV-Erschließung und -Takt). Neu rechnen ist
Sache von A6 (`15_planer.py`) und danach A8 (Export).

**Soll-Ist je Haltestelle** (Fahrten HVZ am Stichtag gegen die Untergrenze der Tab. 4.3 für die Klasse des Bezirks):
75 Potsdamer Haltestellen in Bezirken mit Klasse, davon 14 unter dem Soll, u. a. Bornstedter Feld (Am Pfingstberg,
Hannes-Meyer-Str., Wiesenpark, Schlegelstr./Pappelallee), Zentrum Ost (Humboldtring, Wiesenstr.), Am Havelblick und
Finkenweg, Fahrländer See. Am Havelblick und Fahrländer See führt auch Anlage 4 als Defizit. Liste im Beleg. Die
Taktklasse je Haltestelle (`auswertung.haltestelle.klasse`) hängt nicht von der Gebietsklasse ab und bleibt unverändert;
`a4_haltestelle.py` ist mit der neuen YAML grün. `13_oepnv.py --trocken` lief nicht: Er legt eine TEMP-Tabelle an, das
darf die Leserolle nicht, und `RECHNEN_PASSWORD` steht nicht in der `.env`.

