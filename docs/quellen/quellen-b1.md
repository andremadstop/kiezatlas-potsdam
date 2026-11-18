# Quellen aus Paket B1 (zur Zusammenführung in QUELLEN.md durch I2)

Paket B1 nutzt nur Quelle 4 aus `QUELLEN.md` (Zensus 2022, Gebäude nach Baujahr), keine neue Quelle und keinen
neuen Abruf. Die Zips lagen schon unter `$KIEZ_DATEN/zensus/2022/` (HERKUNFT.md dort, SHA256 je Datei).

| Ausgabe | Quelle | Lizenz | Vermerk |
|---|---|---|---|
| `daten/jahre_zellen.js` (Mikrozensus-Klassen, 100 m) | `Gebaeude_nach_Baujahr_in_Mikrozensus_Klassen.zip` | dl-de/by-2-0 | © Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) |
| `auswertung.zensus_gebaeude_jahr` (Jahrzehnte und Mikrozensus-Klassen, 100 m und 1 km) | dazu `Gebaeude_nach_Baujahr_Jahrzehnte.zip` | dl-de/by-2-0 | wie oben |

`Gebaeude_mit_Wohnraum_nach_Gebaeudetyp_Groesse.zip` (ebenfalls Quelle 4) liest B1 nicht; sie ist für B4.

Bearbeitung: Zellen im Rahmen um Potsdam ausgewählt, „–“ als 0 mit Merker `geaendert`, Anteile der Klassen an der
Klassensumme in Prozent, vorherrschende Klasse. Bericht: `belege/B1_zensus_jahre.md`.
