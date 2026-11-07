# Änderungen

Jeder veröffentlichte Stand bekommt einen Tag `stand-JJJJ-MM-TT` (bei mehreren am Tag mit Buchstabe) und steht hier.
Die Seiten nennen den Stand im Fuß. Entscheidungen: `docs/entscheidungen.md`; Prüfstände: `belege/pruefstand-*`.

## 2026-11-07 (kommender Stand, noch ohne Tag)

- 3D heißt Häuser: keine Zellsäulen mehr auf Startseite, freier Karte und Bauzeiten; die Zellen liegen flach, die
  Farbe trägt den Wert. Der Schalter „3D-Häuser“ führt mit einem Klick zu Gebäuden als Körper, auf den Bauzeiten
  dazu der Knopf „Häuser in 3D ansehen“. Zellmosaik leiser, Fragen der Startseite von oben (Entscheidung A18,
  Beleg `belege/3D_haeuser_20261107.md`).

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
