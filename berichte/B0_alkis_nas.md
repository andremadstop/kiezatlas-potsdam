# B0 ALKIS-NAS: Gebäudeform und Zuordnung

Erzeugt von `skripte/20_alkis_nas.py` am 05.11.2026. Quelle: `alkis_p.zip` (LGB, Bestandsdatenauszug ohne Eigentümer, Stichtag 01.10.2026, SHA256 geprüft). Bezug: `auswertung.gebaeude_stand_20261105` (Snapshot 05.11.2026), nie `public.gebaeude`.

Vermerk: © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung).

## Abnahme

| Kriterium | Ergebnis |
|---|---|
| ≥ 98 % der 52.309 Gebäude in Potsdam zugeordnet | 52.269 von 52.309 = **99,9 %** |
| Füllgrad `baujahr` stadtweit | **0 von 50.795 AX_Gebaeude (0,0 %)**; das Element `baujahr` kommt im Auszug nicht vor (Stichprobe der Erkundung: 0 von 600) |
| Kein Eigentümerfeld importiert | siehe `pruefen/B0_nas.py` (Schemaprüfung, Objektarten) |

## Eingelesen

- Teildateien im Zip: 40 (Kopfteil 00 und 39 NAS-Kacheln); Objekte außerhalb von `wfs:Insert`: 0; doppelte gml:id über Kacheln: 0
- Bauwerke mit Fläche je Objektart (gelesen / ohne Fläche verworfen):
  - `AX_Gebaeude`: 50.795 (gelesen 50.795, ohne Fläche 0)
  - `AX_Bauteil`: 1.052 (gelesen 1.052, ohne Fläche 0)
  - `AX_Turm`: 83 (gelesen 83, ohne Fläche 0)
  - `AX_VorratsbehaelterSpeicherbauwerk`: 37 (gelesen 37, ohne Fläche 0)
  - `AX_BauwerkOderAnlageFuerIndustrieUndGewerbe`: 109 (gelesen 126, ohne Fläche 17)
  - `AX_BauwerkOderAnlageFuerSportFreizeitUndErholung`: 5 (gelesen 5, ohne Fläche 0)
  - `AX_SonstigesBauwerkOderSonstigeEinrichtung`: 270 (gelesen 5.198, ohne Fläche 4.928)

## Zuordnung zum Snapshot

Regel: größte Schnittfläche in EPSG:25833 innerhalb derselben Objektart; gültig ab Schnitt ≥ 50 % der kleineren Fläche. `ueberlappung` = Schnitt / Vereinigung (IoU).

- Snapshot gesamt (Rechteck): 52.272 von 85.046 zugeordnet (61,5 %); außerhalb der Stadt liefert der Potsdam-Auszug nichts.
- In Potsdam: 52.269 von 52.309 (99,9 %)

| Objektart (Snapshot in Potsdam) | Gebäude | zugeordnet | Anteil |
|---|---:|---:|---:|
| AX_Gebaeude | 50.760 | 50.722 | 99,9 % |
| AX_Bauteil | 1.053 | 1.051 | 99,8 % |
| AX_SonstigesBauwerkOderSonstigeEinrichtung | 269 | 269 | 100,0 % |
| AX_BauwerkOderAnlageFuerIndustrieUndGewerbe | 104 | 104 | 100,0 % |
| AX_Turm | 82 | 82 | 100,0 % |
| AX_VorratsbehaelterSpeicherbauwerk | 37 | 37 | 100,0 % |
| AX_BauwerkOderAnlageFuerSportFreizeitUndErholung | 4 | 4 | 100,0 % |

- NAS-Bauwerke mit Zuordnung: 52.278 von 52.351; ohne: 73
- Gegenprobe Kennung (`oid = gml_id || 'BL'`): 52.256 der 52.278 Zuordnungen treffen dasselbe Gebäude, 22 weichen ab; ohne Zuordnung, obwohl die Kennung im Snapshot steht: 0
- Snapshot-Gebäude mit mehr als einem NAS-Bauwerk: 6
- IoU Median: 1,000
- IoU-Verteilung (Zehntel): 0,0–0,1: 1, 0,1–0,2: 3, 0,2–0,3: 5, 0,3–0,4: 5, 0,4–0,5: 3, 0,5–0,6: 6, 0,6–0,7: 6, 0,7–0,8: 3, 0,8–0,9: 18, 0,9–1,0: 52,228

## Füllgrad der Merkmale (AX_Gebaeude)

| Merkmal | gefüllt | Anteil |
|---|---:|---:|
| `dachform` | 50.269 | 99,0 % |
| `bauweise` | 9.490 | 18,7 % |
| `geschosse` | 15.395 | 30,3 % |
| `objekthoehe` | 50.206 | 98,8 % |
| `baujahr` | 0 | 0,0 % |
| `wohnungen` | 0 | 0,0 % |

`wohnungen`: Der NAS-Auszug führt kein Attribut zur Zahl der Wohnungen. Die Regel „unter 3 Wohneinheiten nur Klasse, kein Jahr“ (Prüfbericht, Korrektur 6) lässt sich daher nicht aus B0 ableiten; B4 braucht eine andere Grundlage (z. B. Gebäudefunktion und Bauweise oder Zensus-Gebäudetyp).

Kodierung: `funktion` = `<Objektart ohne AX_>:<Kennung>`, z. B. `Gebaeude:1010` (Wohnhaus) oder `Bauteil:<bauart>`; die Kennungen bleiben unübersetzt (Beschriftung steht im Snapshot). `dachform` und `bauweise` sind nach den Wertearten der GeoInfoDok 7.1 beschriftet. Gegenprobe Bauweise gegen den Funktionstext des Snapshots: Garagenbauweisen 1.914 von 1.916 auf „Garage“, Doppelhaushälfte/Reihenhaus/Haus in Reihe 1.730 von 1.730 auf „Wohn…“. Die Dachform-Beschriftung ist nicht gegen eine Primärquelle geprüft (keine Gegenprobe im Bestand möglich).

Dachform: Satteldach 20.971, Flachdach 16.356, Pultdach 6.070, Walmdach 3.916, Krüppelwalmdach 1.358, Zeltdach 816, Mansardendach 442, Bogendach 84, Mischform 80, Sheddach 63, Versetztes Pultdach 43, Turmdach 38, Kuppeldach 27, Kegeldach 5.

Bauweise: Freistehendes Einzelgebäude 4.193, Einzelgarage 1.389, Doppelhaushälfte 1.076, Freistehender Gebäudeblock 834, Gebäudeblock in geschlossener Bauweise 475, Reihenhaus 433, Doppelgarage 353, Haus in Reihe 221, Sammelgarage 174, Sonstiges 174, Gruppenhaus 168.

## Adressen (nur intern)

`auswertung.gebaeude_adresse`: 26.775 Zeilen an 22.030 Gebäuden. Verweise `zeigtAuf`: 26.781, davon ohne Hausnummernobjekt 0, ohne Straßenkatalog 0, am nicht zugeordneten Bauwerk 6. Pseudonummern (Nebengebäude) werden nicht übernommen. Die Tabelle ist für `mosidi_lesen` gesperrt und darf nie in `daten/` oder einen Export; dieser Bericht enthält nur Zählungen.

## Nicht übernommen

Buchungs- und Flurstücksangaben (`AX_Buchungsblatt`, `AX_Buchungsstelle`, `AX_Flurstueck`), Namen an Bauwerken, `lebenszeitintervall` (Fortführungsdatum, kein Baujahr) und alle übrigen Objektarten. Personen- und Anschriftenobjekte enthält der Auszug nicht.
