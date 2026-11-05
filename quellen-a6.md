# Zulieferung A6 zu QUELLEN.md und für I1 (Versorgungsaussagen, Datendateien)

Paket A6, 05.11.2026. Führt die Integration (I1) in `QUELLEN.md` und `daten/LIZENZ.md` zusammen.

## Neues Dokument: Potsdamer Baulandmodell 2019

| Feld | Wert |
|---|---|
| Dokument | Richtlinie zur sozialgerechten Baulandentwicklung in der Landeshauptstadt Potsdam (Potsdamer Baulandmodell 2019), Stand 20.11.2019 |
| Abruf | `https://www.potsdam.de/system/files/documents/anlage1potsdamerbaulandmodell-fortschreibung2019.pdf` (dazu zum Abgleich die Fassung 2016 als `anlage2-…`), 05.11.2026 10:40 UTC, robots.txt vorher gelesen, Abstand ≥ 5 s, zwei Anfragen. Herkunft: `$KIEZ_DATEN/baulandmodell/2019/HERKUNFT.md` |
| Lizenz | keine Angabe (Impressum ohne Nutzungsbedingungen) |
| Übernommen | nur Fakten mit Fundstelle: Versorgungsquoten Anlage C, S. 38 (Krippe 0 bis unter 3 Jahre 75 %, Kindergarten 3 bis unter 6 Jahre 100 %, Hort 6 bis unter 12 Jahre 70 %, Grundschule 6 bis unter 12 Jahre 100 %) → `config/richtwerte.yaml`, Abschnitt `baulandmodell` |
| Vermerk im Atlas | Quoten: Richtlinie zur sozialgerechten Baulandentwicklung der Landeshauptstadt Potsdam, Stand 20.11.2019, Anlage C |
| geprüft | 05.11.2026 von A6 am PDF selbst gelesen (Text der Anlage C, S. 38) |

## Dateien von A6 und ihre Lizenz (für `daten/LIZENZ.md`)

| Datei | Lizenz | Hinweis für I1 |
|---|---|---|
| `planer.js` | dl-de/by-2-0 **und CC BY 4.0** | Die ÖPNV-Werte stammen aus dem VBB-GTFS (CC BY 4.0). In `LIZENZ.md` steht für `planer.js` bisher nur dl-de; Vermerk VBB ergänzen. Beide Lizenzen fordern nur Namensnennung und sind zusammen nutzbar. |
| `erreichbar.js`, `einrichtungen.js` | dl-de/by-2-0 | Vermerke je Quelle mit Link und „Daten verändert (eigene Berechnung)“ in `quellen` der Datei |
| `*_odbl.js` | ODbL 1.0 | Noch nicht erzeugt (A3/A5b leer). Kopfkommentar steht in `skripte/15_planer.py` (`ODBL_KOPF`) |

Dokumente ohne Lizenz (NVP, Baulandmodell, Schülerfahrtkostensatzung, EHK, Umweltatlas Berlin) stehen in `quellen` der
Datei `planer.js` nur mit Titel und Fundstelle. Übernommen sind daraus nur Zahlen.

## Für A7 und I1: neue Kennzahlen in `planer.js`

A7 (`planer.js`, `KENNZAHL`) kennt `anteil_in_radius`, `ew_je_einrichtung`, `plaetze_je_kind`, `oepnv_erschliessung`,
`gruen_m2_je_ew`. A6 liefert zusätzlich:

| kennzahl | Bedeutung | Vorschlag für den Text |
|---|---|---|
| `plaetze_je_bedarf` | alle Plätze in Krippe, Kindergarten und Hort gegen den rechnerischen Bedarf nach Baulandmodell, Anlage C | „Plätze je Bedarfsplatz (Baulandmodell)“ |
| `schueler_je_kind` | Schüler der Grundschulen gegen Kinder 6 bis unter 12 (geschätzt), vorläufig | „Grundschüler je Kind im Grundschulalter“ |
| `oepnv_takt` | wie `oepnv_erschliessung`, aber nur Haltestellen mit dem Soll-Takt der Gebietsklasse | „ÖPNV-Erschließung mit Soll-Takt nach Nahverkehrsplan“ |
| `entfernung_median` | nur in `planer_fuss_odbl.js`: Median der Entfernung (Ärzte, Apotheken, Pflege, Märkte, Spielplätze), keine Versorgungsaussage | „mittlere Entfernung zu …“ |

Ohne Eintrag zeigt A7 den Schlüssel mit Leerzeichen („plaetze je bedarf, Kita“). Das ist lesbar, aber unschön.

Weitere Felder je Wert, die A7 nutzen kann: `zielgruppe` (unterscheidet etwa die zwei Kita-Relationen), `vorlaeufig`
(alle Grundschulwerte), `unsicherheit` (Hinweistext je Wert). `wert: null` heißt immer, dass kein Wert ausgewiesen wird.
Der Grund steht in `unsicherheit`, etwa Geheimhaltung, zu kleine Zielgruppe, gemischte Gebietsklasse oder kein Standort.

## Für I1: Methodenseite, sinngemäß

- **Raumeinheit:** Stadtteil, bis die Planungsräume (H1) vorliegen. Zellen gehören über ihren Mittelpunkt zu einer Raumeinheit.
- **Kita-Plätze:** Kapazität laut Betriebserlaubnis, nicht Belegung. Kindertagespflege fehlt. Kinder vom 15.05.2022,
  Plätze vom 05.11.2026. In Brandenburg gilt das Wunsch- und Wahlrecht, eine Relation je Raumeinheit ist deshalb ein
  Anhaltspunkt und keine Versorgungsquote einzelner Familien.
- **Baulandmodell-Quoten:** Sie sind um Kapazitätsreserven vermindert. Ein Wert von 1,0 heißt also rechnerisch gedeckt,
  ohne Reserve.
- **ÖPNV:** Einzugsradius nach Gebietsklasse des NVP 2019. Der NVP bewertet Teilflächen mit mehr als 200 EW, der Atlas
  ganze Raumeinheiten.
- **Grün:** vereinfachte Berliner Methode. Es zählen Grünanlagen und Parks aus ALKIS, ohne Mindestgröße, Schlossparks
  zählen mit. Festlegung in `richtwerte.yaml`, `gruen_definition` (`status: festgelegt`).
