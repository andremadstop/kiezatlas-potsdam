# Änderungen

Jeder veröffentlichte Stand bekommt einen Tag `stand-JJJJ-MM-TT` (bei mehreren am Tag mit Buchstabe) und steht hier.
Die Seiten nennen den Stand im Fuß. Entscheidungen: `docs/entscheidungen.md`; Prüfstände: `belege/pruefstand-*`.

## 2026-11-08 (kommender Stand, noch ohne Tag)

- Drei Belegfilme unter `docs/filme/` (Übersicht `docs/filme/README.md`): „Potsdam wächst aus den Daten“ (Karte,
  Blender, 47,0 s), „Der Lauf im Terminal“ (pycairo, 44,8 s) und „Was der Kiezatlas beantwortet“ (Manim, 74,2 s). Jede Zahl
  im Bild liest das Skript beim Rendern aus einer Datei im Repository und gleicht sie ab (168 Prüfstellen); jeder Film
  endet mit einem Befund über Potsdam (Altbau, Fernwärme). Entscheidung A20, Beleg `belege/filme_20261108.md`.
- README: Standbild der Karte als Aufmacher, GIF des Terminalfilms bei „Prüfen“.
- Prüfprotokoll von `./pruefen.sh` am Stand `a057522` (18 von 18 grün) als `docs/filme/terminal/pruefen.log`.
- Pre-existing: Die Übersicht in `docs/entscheidungen.md` endete bei A18 (Zeile A19 nachgetragen), das README nannte
  „A1 bis A17“.

## 2026-11-07 (kommender Stand, noch ohne Tag)

- 3D heißt Häuser: keine Zellsäulen mehr auf Startseite, freier Karte und Bauzeiten; die Zellen liegen flach, die
  Farbe trägt den Wert. Der Schalter „3D-Häuser“ führt mit einem Klick zu Gebäuden als Körper, auf den Bauzeiten
  dazu der Knopf „Häuser in 3D ansehen“. Zellmosaik leiser, Fragen der Startseite von oben (Entscheidung A18,
  Beleg `belege/3D_haeuser_20261107.md`).
- Gegenprobe 2 (Beleg G11 bis G23): Startseite mit 3D-Häusern zeigt die Zellen flach darunter, „3D-Häuser“ steht vorn
  in der Leiste und fliegt wie auf Karte und Bauzeiten nah heran (Zoom 16,2, Handy 15,6); selbst eingeschaltet bleibt
  3D beim Weiterlesen; Doppelklick ohne Zellfenster; Chip-Klick scrollt die Seite nicht mehr; Links der freien Karte
  behalten die Kopplung von 3D und Gebäuden; zwei Texte berichtigt.
- Voll responsive (Andre 07.11., Entscheidung A19, Beleg `belege/responsive_20261107.md`): Kopfleiste klappt beim
  Lesen ein und kommt beim Hochscrollen wieder; Handy quer und Tablet zeigen Karte und Text nebeneinander; Legende der
  Bauzeiten einklappbar; Kartenknöpfe nicht mehr unter dem Quellen-„i“; Tippziele auf Touch ab 44 px; Prüfung über
  acht Breiten in `seiten.mjs`, `B5_jahre.mjs` und `A7_planer.mjs`. Sichtbare Karte beim Lesen am Handy (390 × 844):
  Bauzeiten 250 → 424 px, Startseite 438 → 506 px.
- Startseite mit 3D-Häusern: Wahl aus Liste oder Register fliegt zu den Häusern, ein Klick in den gewählten Stadtteil
  wählt ihn nicht ab, „Luftbild einblenden“ lässt die Häuser stehen.
- Neues Vorschaubild `og.png` aus der Bauzeiten-Seite mit 3D-Häusern (`skripte/28_vorschaubild.mjs`).
- Pre-existing: Methode der Startseite stand bei 360 px um 29 px seitlich über (langer Belegpfad).

## stand-2026-11-06

- Gebäudehöhe in 3D aus der ALKIS-Objekthöhe statt Geschosse × 3 m, Herkunft je Gebäude im Fenster; 3D-Gebäude in
  Bauzeit-Farbe auf der Bauzeiten-Seite (Beleg `belege/3D_grundkarte_20261106.md`).
- Grundkarte basemap.de Web Vektor statt Raster, Beschriftung über den eigenen Ebenen; Quellenvermerk nach den
  Nutzungsbedingungen des BKG.
- Audit nach Nutzergruppen und gegen den Standard der Geodaten-Import-Pipeline (`berichte/audit_20261106.md`):
  Texte zu Höhe, Wikidata-Zuordnung, Stichtag und Rundung korrigiert; Datenschutzvertrag der Bauzeiten
  verschärft; Rücktest mit 95-%-Bereich; gleiche Kopfzeile auf allen Seiten; Steckbrief aus dem Planer;
  README mit „Zur Prüfung“, Rundgang, Entscheidungsprotokoll, Prüfkette `pruefen.sh`, Rohdaten-Prüfsummen,
  festgeschriebene Python-Umgebung; Zitiervorschlag und Meldeweg für Fehler.
- Code-Karte (`docs/codekarte/`).

## 2026-11-05

- Planer-Ebene (Bevölkerung, Gemeinbedarf, Erreichbarkeit Luftlinie und Fußweg, ÖPNV nach Gebietsklassen,
  Planungsräume, GIS-Export) und Bauzeiten-Seite (Zellen und Schätzung je Gebäude, Rücktest).

## 2026-11-04

- Erste Fassung: 32 Stadtteile aus Zensus 2022, amtlichen Stadtteilen und ALKIS-Gebäuden.
