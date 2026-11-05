# Quellenbeitrag Paket B4 (für QUELLEN.md und daten/LIZENZ.md, Zusammenführung in I2)

| Quelle | Datei / Stand | Lizenz und Vermerk | Verwendung |
|---|---|---|---|
| Zensus 2022, Gebäude mit Wohnraum nach Baujahr (Mikrozensus-Klassen), 100 m und 1 km | über B1 (`auswertung.zensus_gebaeude_jahr`), Stichtag 15.05.2022 | „© Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)“ | Stufe 4: je Zelle auf die Wohngebäude verteilt |
| ALKIS vereinfacht, Gebäude (Snapshot) und ALKIS NAS (Dachform, Bauweise, Objekthöhe) | `auswertung.gebaeude_stand_20261105`, `auswertung.alkis_nas_gebaeude` (B0, Stichtag 01.10.2026) | „© GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)“ | Umrisse in `daten/jahre/<nr>.js`, Gebäudeform für Stufe 3 und 4, Gebietsgrenzen in `config/blocktypen.geojson` |
| Landeshauptstadt Potsdam, Broschüre „Potsdamer Platte“ (Juli 2008, Bearbeitung Stadtkontor) | `$KIEZ_DATEN/potsdamer_platte/2026-11-05/` (HERKUNFT.md, SHA256 `99778123…0f53`) | keine offene Lizenz; nur Fakten übernommen (Bauzeiträume, Flächen), kein Text, keine Bilder. Nennung: „Bauzeiten: Landeshauptstadt Potsdam, „Potsdamer Platte“, Juli 2008“ | Stufe 3: Bauzeit je Großsiedlung, Beleg je Gebiet mit Seite |

Nicht verwendet (nur Prüfwerte im Rücktest, nie in `auswertung.gebaeude_jahr` oder `daten/`):
- Wikipedia „Liste der Baudenkmale in Potsdam“ (CC BY-SA 4.0), Prüfspalte aus B2 (Korrektur 5)
- BLDAM-Denkmalliste (Lizenz ungeklärt, E8): auch kein Denkmal-Kennzeichen `d` in `daten/jahre/`
- B3-Referenz Bornstedt (Sichtprüfung, außerhalb des Repos)
- OpenStreetMap (E1: Gebäudejahre ohne OSM)

Für `daten/LIZENZ.md`: `jahre/<nr>.js` steht unter dl-de/by-2-0 (Zensus, LGB) mit den Vermerken aus `quellen` in
jeder Datei; Bauzeiten der Großsiedlungen als Fakten mit Nennung der Broschüre.
