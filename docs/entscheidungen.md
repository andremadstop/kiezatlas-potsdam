# Entscheidungen

Festgelegte Regeln des Kiezatlas mit Anlass, Begründung und dem, was verworfen wurde. Nummern mit dem Präfix **A**
(Atlas), damit sie nicht mit dem Entscheidungsprotokoll der Geodaten-Import-Pipeline (E1 bis E48) verwechselt werden.
Angelegt am 06.11.2026 nach dem Audit (`berichte/audit_20261106.md`, Fund K10). Die Begründungen stammen aus dem
Bauplan vom 05.11.2026, seinem Prüfbericht und den Nachläufen; beide Dokumente liegen im internen Vault der UG und
sind nicht öffentlich. Was dort steht und hier gebraucht wird, steht unten ausgeschrieben.

Entschieden hat jeweils André Stiebitz; Vorschläge, Prüfberichte und Umsetzung kamen überwiegend von KI-Agenten (Claude).

## Übersicht

| Nr. | Entscheidung | Stand | alte Kennung |
|---|---|---|---|
| A1 | OpenStreetMap nur in eigenen `_odbl`-Dateien | 05.11.2026 | E1, Prüfbericht Korrektur 4 |
| A2 | Wikipedia-Listen und OSM-Baujahre nur zur Prüfung, nie in den Daten | 05.11.2026 | Korrektur 5 |
| A3 | Bauzeiten ohne Einzeljahr bei Wohnraum, ohne Adressen und ohne Gebäudekennung | 05.11., verschärft 06.11.2026 | Korrektur 6, Nachlauf N3, Audit K3 |
| A4 | Daten unter den Nutzungsbedingungen der Landeshauptstadt nur intern | 05.11.2026 | Nachlauf N4 |
| A5 | Nebengebäude bleiben „nicht datiert“ | 05.11.2026 | E5 |
| A6 | Maßstäbe ohne Primärbeleg nur als „Orientierung“ | 05.11., ergänzt 06.11.2026 | E6, Audit K7 |
| A7 | Einrichtungen in Brandenburg außerhalb der Stadt zählen mit, Berlin nicht | 05.11.2026 | E7 |
| A8 | Denkmalliste des Landesamts erst nach schriftlicher Klärung | 05.11.2026, offen | E8 |
| A9 | Regeln des Rücktests vor dem Lauf festgelegt; Belege der Reihenfolge | 05.11., belegt 06.11.2026 | Prüfprotokoll B4, Nachtrag N3, Audit K9 |
| A10 | Daten als Dateien je Stadtteil, keine Vektorkacheln | 05.11.2026 | E2 |
| A11 | Planungsräume als Hauptebene des Planers | 05.11.2026 | Korrektur 2 |
| A12 | Luftlinie als Grundeinstellung, Fußweg zusätzlich | 05.11., ergänzt 06.11.2026 | Nachlauf N1, Audit K26 |
| A13 | Grundschule Pestalozza bis zur Klärung gesperrt | 05.11.2026, offen | Nachlauf N4 |
| A14 | Gebäudehöhe aus dem Kataster, Grundkarte basemap.de Vektor | 06.11.2026 | Beleg G1 bis G8 |
| A15 | Schulen mit Primarstufe zählen als Grundschulstandort | 06.11.2026 | Audit K4 |
| A16 | Schaugrafik unter CC BY 4.0 | 06.11.2026 | Audit K19 |
| A17 | Zitierfähige Stände: Version, Tag, Änderungsprotokoll, Meldeweg | 06.11.2026 | Audit K13 |
| A18 | 3D heißt Häuser: keine Zellsäulen auf Karte und Bauzeiten, ein Klick zu den Häusern | 07.11.2026 | Beleg H1 bis H9 |

## A1: OpenStreetMap nur in eigenen `_odbl`-Dateien

- **Anlass:** Fußwege, Ärzte, Apotheken, Supermärkte und Spielplätze gibt es offen nur aus OpenStreetMap (ODbL 1.0,
  Share-Alike für abgeleitete Datenbanken).
- **Entscheidung:** OSM-Anteile stehen nur in Dateien mit `_odbl` im Namen und ODbL-Vermerk im Kopf (`daten/*_odbl.js`,
  `daten/export/csv_odbl/`, `kiezatlas_potsdam_odbl.gpkg`). Alle anderen Dateien bleiben OSM-frei und unter den
  amtlichen Lizenzen. `pruefen/daten.py` bricht ab, wenn eine OSM-Spur in einer Datei ohne `_odbl` steht.
- **Verworfen:** OSM-Werte in `planer.js` mischen (machte die ganze Datei zur ODbL-Datenbank).
- **Neu prüfen, wenn:** amtliche Daten für Wege oder Nahversorgung offen verfügbar werden.

## A2: Wikipedia-Listen und OSM-Baujahre nur zur Prüfung

- **Anlass:** Die Denkmallisten der Wikipedia stehen unter CC BY-SA 4.0, das auch das Datenbankrecht lizenziert; eine
  systematische Übernahme der Jahre wäre eine wesentliche Entnahme mit Share-Alike.
- **Entscheidung:** Wikipedia- und OSM-Jahre dienen nur als Prüfspalte im Rücktest, nie als Wert in `daten/`.
  Genaue Jahre kommen nur aus Wikidata (CC0), zugeordnet über die Koordinate des Wikidata-Objekts.
- **Verworfen:** eine dritte Lizenzgrenze `_bysa`.

## A3: Bauzeiten ohne Einzeljahr bei Wohnraum, ohne Adressen und ohne Kennung

- **Anlass:** Ein Baujahr je Wohnhaus mit Adressbezug kann auf die Eigentümer verweisen, vor allem bei Ein- und
  Zweifamilienhäusern. ALKIS führt keine Zahl der Wohneinheiten, „mindestens drei Wohnungen“ ist nicht entscheidbar.
- **Entscheidung:** Gebäude mit Wohnraum tragen nur die Bauzeitklasse, auch Denkmale. Ein Einzeljahr nur bei
  belegten Gebäuden ohne Wohnraum. In `daten/jahre/` keine Adresse und keine Gebäudekennung (oid, gml_id);
  `pruefen/daten.py` sperrt diese Felder seit 06.11.2026, der Vertrag `daten/schema/jahre_gebaeude.json` ebenso.
  Keine Tabelle je Gebäude zum Herunterladen, nur die Kartendateien.
- **Verworfen:** Einzeljahr ab drei Wohneinheiten (nicht prüfbar).

## A4: Daten unter den Nutzungsbedingungen der Landeshauptstadt nur intern

- **Anlass:** Grundschuleinzugsgebiete und das Grünflächen-Portal stehen nicht unter einer offenen Lizenz, sondern
  unter den „Nutzungsbedingungen der LHP“.
- **Entscheidung:** Diese Dateien liegen nur unter `$KIEZ_DATEN/intern` und werden nur für Prüfungen gelesen, nie in
  `daten/`, Export oder Seite. Auch ihre Prüfsummen stehen nicht im öffentlichen Repo (`belege/rohdaten.md`).
- **Neu prüfen, wenn:** die Stadt die Daten unter dl-de/by oder dl-de/zero stellt.

## A5: Nebengebäude bleiben „nicht datiert“

Garagen, Lauben und Schuppen (über 21.000: 10.267 Garagen und 11.338 Lauben laut Bauplan, dazu Schuppen) bekommen keine geschätzte Bauzeit; der Zensus zählt sie nicht, jede
Schätzung wäre geraten. Die Karte zeigt sie grau.

## A6: Maßstäbe ohne Primärbeleg nur als „Orientierung“

- **Entscheidung:** Ein Abzeichen „amtlicher Maßstab“ trägt nur, was nach einer amtlichen Vorgabe gerechnet ist.
  Radien wie Kita 500 m oder Grundschule 1.000 m sind einstellbare „Orientierung, kein Richtwert“.
- **Ergänzt 06.11.2026 (Audit K7):** „Plätze je Bedarfsplatz“ rechnet ohne die Regel der Kita-Bedarfsplanung für
  angrenzende Planungsräume (Nr. 3.4.4) und trägt deshalb „Orientierung“. Die Kennzahl mit Nachbarräumen ist
  vorgemerkt, nicht gebaut.

## A7: Einrichtungen außerhalb der Stadt

Kitas und Schulen in Brandenburg außerhalb der Stadtgrenze zählen bei der Entfernung mit (MBJS-Daten reichen über
die Grenze), Berlin nicht. Am Stadtrand ist die Entfernung deshalb teils nur eine Obergrenze; das steht bei jedem
betroffenen Wert.

## A8: Denkmalliste des Landesamts

Die Liste des Brandenburgischen Landesamts für Denkmalpflege (BLDAM) hat keine Lizenzangabe; als Datenbank genießt
sie Schutz nach § 87a UrhG. Bis zu einer schriftlichen Antwort dient sie nur der Prüfung. Die Anfrage ist
vorbereitet, aber noch nicht gesendet (Stand 06.11.2026).

## A9: Regeln des Rücktests vor dem Lauf

- **Entscheidung:** Was als Treffer zählt, welche Gebäude Prüfgebäude sind und welche Stufen der Rücktest rechnet,
  steht in `pruefen/B4_protokoll.md` (und für die Luftbilder in `pruefen/B3_protokoll.md`), festgelegt vor dem
  jeweiligen Lauf.
- **Beleg der Reihenfolge** (Commits der Entwicklungshistorie, Uhrzeit MEZ):

| Festlegung | Commit, Zeit | Lauf mit Ergebnis | Commit, Zeit |
|---|---|---|---|
| Rücktest-Protokoll B4 | `9e962b4`, 05.11.2026 12:30 | erster Lauf der Kaskade | `be05dc8`, 12:34 |
| Nachtrag N3 (Rücktest ohne Stufe 1, Wikidata als Prüfsatz) | `1298b23`, 18:53 | Lauf 3 | `8b503ed`, 19:49 |
| Nachtrag nach der Gegenprobe (nachträglich, Regeln unverändert) | `d3b8df2`, 22:23 | Lauf nach Fix der Wikidata-Zuordnung | `f9e87ce`, 22:06 |

- **Warum diese Commits nicht öffentlich sind:** Die Entwicklungshistorie vom 05.11. enthielt zeitweise eine
  Stichprobe mit Jahr und Fläche von Wohngebäuden (Widerspruch zu A3). Sie wurde vor der Veröffentlichung zu
  einem Commit zusammengefasst; die Einzelschritte liegen nur lokal (Zweig `nachlauf/historie-20261105`). Die Tabelle
  oben ist deshalb eine Angabe des Projekts, extern nicht nachprüfbar. Künftig wird ein Nachtrag als eigener
  Commit veröffentlicht, bevor der Lauf beginnt.

## A10: Dateien je Stadtteil statt Vektorkacheln

Die Seiten laden ihre Daten als einfache Skriptdateien (auch per Doppelklick, `file://`), Gebäude je Stadtteil
nachgeladen. Folge: Gebäude erscheinen erst ab Zoom 14. Vektorkacheln (PMTiles) bleiben eine Option für später.

## A11: Planungsräume als Hauptebene des Planers

Die Stadt plant Kita und Schule auf 19 Planungsräumen, nicht auf den 32 Stadtteilen. Der Planer rechnet deshalb
auf Planungsräumen; die Stadtteile bleiben die Orientierungsebene der übrigen Seiten.

## A12: Luftlinie als Grundeinstellung, Fußweg zusätzlich

Luftlinie braucht keine OSM-Daten und bleibt die Grundeinstellung des Planers; der Fußweg über das OSM-Wegenetz ist
zuschaltbar (A1). Ausnahme seit 06.11.2026: Die Kita-Frage der Startseite öffnet den Planer gleich im Fußweg, weil
Eltern den Weg wissen wollen, nicht die Luftlinie (Audit K26).

## A13: Grundschule Pestalozza gesperrt

Die Schule (MBJS 103512) liegt nach den MBJS-Koordinaten im Planungsraum 103 Krampnitz, der Ort der MBJS-Daten und ein Schulgebäude im Kataster weisen aber auf Groß Glienicke (Befund `belege/N4_pestalozza_20261105.md`). Bis eine
schriftliche Auskunft des MBJS oder der Stadt vorliegt, ist sie für die Auswertung gesperrt, mit Hinweis in Karte,
Tabelle und Export; die Grundschulwerte für Groß Glienicke und Krampnitz bleiben leer.

## A14: Gebäudehöhe und Grundkarte

Entscheidungen G1 bis G8 mit Begründung und Zählungen: `belege/3D_grundkarte_20261106.md`. Kurz: Höhe aus der
ALKIS-Objekthöhe, Herkunft je Gebäude angegeben; Grundkarte basemap.de Web Vektor (CC BY 4.0), gekürzter Stil,
Quellenvermerk nach den Nutzungsbedingungen des BKG.

## A15: Schulen mit Primarstufe

Oberschulen, Gesamtschulen und Schulzentren mit Grundschulteil zählen für Entfernung und Einwohner je Standort als
Grundschulstandort. „Grundschüler je Kind“ bleibt in Räumen mit einer solchen Schule leer, weil die Schülerzahl
nicht nach Stufen geteilt vorliegt (Audit K4; Umsetzung und Zählung in `belege/planer_audit_20261106.md`).

## A16: Schaugrafik unter CC BY 4.0

Grafiken aus der Schaugrafik dürfen gedruckt und weitergegeben werden, mit der Bildzeile, die auf der Grafik steht
(Atlas, Adresse, Datenquellen). Die Datenquellen behalten ihre eigenen Lizenzen und Vermerke.

## A17: Zitierfähige Stände

Jeder veröffentlichte Stand bekommt einen Tag im Repository und eine Zeile in `CHANGELOG.md`; die Seiten nennen
im Fuß Stand und Version. Zitiervorschlag in `CITATION.cff`. Fehler in Daten oder Texten bitte an
kontakt@souverain-systems.de.

## A18: 3D heißt Häuser

Anlass: Andre am 07.11.2026 nach einem Sichtvergleich mit einer anderen Gebäudealterskarte: „ich komm nirgends zu
den 3d daten und find unsere kacheln oft zu unübersichtlich“ und „genau, zu viele säulen verwirren mich“.

Entscheidung: Auf der freien Karte und den Bauzeiten zeigt 3D nur noch Gebäude als Körper in Katasterhöhe, nie mehr
Zensus-Zellen als Säulen. Der Schalter heißt „3D-Häuser“ und führt mit einem Klick zu Häusern; auf den Bauzeiten
kommt der Knopf „Häuser in 3D ansehen“ dazu. Hat der Nutzer 3D selbst eingeschaltet, nimmt die Geschichte es beim
Weiterlesen nicht wieder weg. Die Zellen bleiben flach und etwas leiser (ohne Rand, geringere Deckkraft, Muster mit
halbtransparenter Tinte); Schraffur, Punkte und die acht Farben bleiben.

Begründung: „3D“ bedeutete je nach Zoom zwei Dinge (unter Zoom 14 Säulen, darüber Häuser), und zu den Häusern
führten am Desktop acht Gesten. Die Zoomschwelle selbst bleibt, weil die Gebäude nach A10 als Datei je Stadtteil
geladen werden: Bei Zoom 13 lägen 8 bis 15 Stadtteile im Bild. Statt die Schwelle zu senken, fliegt die Karte zu
den Häusern.

Verworfen: die Schwelle auf Zoom 13 senken (Flickenteppich aus geladenen und nicht geladenen Stadtteilen); 3D schon
beim Laden (1 bis 3 MB vor der ersten Geste, verstößt gegen „nichts beim Start aus `daten/jahre/`“); Zoomen mit dem
Mausrad (Nachtrag „Desktop-Mausrad“ in `DESIGN.md`); nach dem Einschalten zur letzten Frage springen; neue
Kodierungen für Geheimhaltung und Gleichstand; die Ebene `zellen-3d` löschen (Prüfskripte lesen sie). Die Startseite
behält ihre Säulen, bis Andre entscheidet. Einzelheiten, Zählungen und Prüfungen: `belege/3D_haeuser_20261107.md`.

## Nicht geprüft sind

- Ob ein neuer Nahverkehrsplan die Gebietsklassen ändert (gerechnet mit dem Nahverkehrsplan 2019, `config/richtwerte.yaml`).
- Wie vollständig OpenStreetMap für Ärzte, Apotheken, Supermärkte und Spielplätze ist (für Kitas verglichen,
  siehe `belege/N1_osm_fussweg_20261105.md`).
- Die Fundstelle der Schülerfahrtkostensatzung für die Wegegrenzen der Grundschule.
- Die Schulbezirke: Eine nahe Grundschule ist nicht die zuständige; zuständig ist der Schulbezirk der Stadt.
- Dachformen und Höhen nach LoD2 für die ganze Stadt.
- Darstellung auf echten Mobilgeräten (geprüft nur im Browser im Handyformat).

## Kürzel

| Kürzel | Bedeutung |
|---|---|
| A1 bis A8, B0 bis B5 | Bauabschnitte des Ausbaus vom 05.11.2026 (A = Planer-Ebene, B = Gebäudejahre); Berichte unter `berichte/` und Belege unter `belege/` tragen diese Kürzel |
| P0, P1, I1, I2 | Vorbereitung, Gerüst und Integration des Ausbaus |
| N1 bis N4 | Nachläufe am Abend des 05.11.2026 (Fußweg, Zensusabgleich und ÖPNV, Wikidata-Jahre, Versorgung und Export) |
| H1 bis H11 | Handdownloads und Freigaben durch André, unter anderem H1 Planungsräume, H5 OSM-Auszug, H6 VBB-Fahrplan, H7 ALKIS-NAS, H9 Wikidata-Export, H11 Prognose (Herkunft je Datei in `$KIEZ_DATEN/eingang/HERKUNFT.md`, Prüfsummen in `belege/rohdaten.md`) |
| E1 bis E8, Korrektur 1 bis 9 | Kennungen des internen Bauplans und seines Prüfberichts; Zuordnung in der Übersicht oben |
| K1 bis K32 | Funde des Audits vom 06.11.2026 (`berichte/audit_20261106.md`) |
| G1 bis G8 | Entscheidungen zu Höhe und Grundkarte (`belege/3D_grundkarte_20261106.md`) |
