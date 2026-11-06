# Prüfsummen der Rohdaten (Stand 06.11.2026)

Die Rohdaten liegen nicht im Repository (Lizenz je Datei, Größe). Damit sich trotzdem prüfen lässt, ob eine
eigene Kopie dieselbe Datei ist, stehen hier die SHA256-Prüfsummen. Herkunft, Lizenz, Abrufzeit und
robots-Befund je Datei stehen in der `HERKUNFT.md` des jeweiligen Ordners unter `$KIEZ_DATEN`
(Standard `../kiezatlas-daten`), die Zuordnung zu den Skripten in [`docs/rundgang.md`](../docs/rundgang.md).

| Datei | Bezug | Einträge |
|---|---|---:|
| [`rohdaten.sha256`](rohdaten.sha256) | Repo-Wurzel (`rohdaten/` ist ein Verweis auf `../kiezatlas-potsdam-west/rohdaten`) | 7 |
| [`rohdaten.kiez_daten.sha256`](rohdaten.kiez_daten.sha256) | `$KIEZ_DATEN` | 78 |

Nachprüfen (ohne Netz):

```
sha256sum -c --strict belege/rohdaten.sha256
(cd "$KIEZ_DATEN" && sha256sum -c --strict "$OLDPWD/belege/rohdaten.kiez_daten.sha256")
```

`./pruefen.sh` macht beides, wenn die Ordner da sind, und überspringt es sonst mit Hinweis.

## Kerndaten des Grundatlas: nachträglich gehasht am 06.11.2026

Diese sieben Dateien liest `skripte/01_vorbereiten.py` (Stadtteile Zeile 189, Zensus-Themen Zeilen 51 bis 66).
Für sie gab es bisher nirgends eine Prüfsumme. Sie sind am 06.11.2026 lokal gehasht worden, also nach der
Auswertung vom 04.11.2026. Dass es dieselben Dateien sind wie beim Lauf, belegt der Hash deshalb nicht; belegt
ist, dass `01_vorbereiten.py` am 06.11.2026 aus ihnen byte-gleiche `vorbereitet/stadtteile.csv` und
`vorbereitet/zensus_potsdam.csv` erzeugt wie die Dateien vom 04.11.2026 im Haupt-Repo (Vergleich mit `cmp`).

| Datei | Bytes | SHA256 |
|---|---:|---|
| `rohdaten/stadtteile.geojson` | 352379 | `866fa80e32cb9cb43116b0906c64d11c64845b23357dcfdce87275ae7e2eb605` |
| `rohdaten/zensus/Zensus2022_Bevoelkerungszahl.zip` | 18501524 | `1a8428d31eab264c8717bfdcbf40fbd66c217edb2e2a98d0e67741bd8a1a941a` |
| `rohdaten/zensus/Alter_in_5_Altersklassen.zip` | 32352246 | `88965e23852b901c2eeb27502688777934ef2d1a4ed20f0e6544b773b35005c5` |
| `rohdaten/zensus/Durchschnittsalter_in_Gitterzellen.zip` | 22856466 | `d733805a1a147123e083593dc9c981778210e4b8e943f31b8b70c820157a0d6d` |
| `rohdaten/zensus/Zensus2022_Heizungsart.zip` | 21524746 | `e4df997077903c9932deb1ac8d92e2224cc4dc13c4d6b1f676975516ed0539e2` |
| `rohdaten/zensus/Zensus2022_Energietraeger.zip` | 24318600 | `e0eaad323c03892b9447ab27e1aed496543f7ca667d88ae0e5291a1598f2de40` |
| `rohdaten/zensus/Wohnungen_mod_MZ_Baujahresklassen_in_Gitterzellen.zip` | 15364464 | `f8e80783abdc4c111d94c930c2a4b50f615bce8f76a9a260f41ae198614f380d` |

Herkunft: Stadtteile Handdownload vom Open-Data-Portal der Landeshauptstadt (dl-zero-de/2.0), Zensus-Gitter von
Destatis (dl-de/by-2-0), beides laut `QUELLEN.md` Nr. 1 und 2. Eine `HERKUNFT.md` mit Abrufzeit gibt es für diese
Dateien nicht.

## Dateien unter `$KIEZ_DATEN`: aus den HERKUNFT.md übernommen und nachgeprüft

Für jede Datei wurde die Prüfsumme am 06.11.2026 neu berechnet und in der `HERKUNFT.md` ihres Ordners gesucht.
Ergebnis: 74 von 80 stehen dort mit genau diesem Wert, 3 weitere dort gekürzt (Anfang und Ende stimmen),
3 hatten keinen. Keine Datei weicht von einer dokumentierten Prüfsumme ab, und jede Prüfsumme in diesen
`HERKUNFT.md` gehört zu einer vorhandenen Datei.

Nicht in der Liste (seit 06.11.2026): die zwei Eingangsdateien, die unter den Nutzungsbedingungen der
Landeshauptstadt Potsdam stehen und nur intern genutzt werden (Grundschuleinzugsgebiete, Grünflächen-Portal);
ihre Prüfsummen stehen nur in `$KIEZ_DATEN/eingang/HERKUNFT.md`. Die Liste hat deshalb 78 Einträge.

| Ordner | Dateien | wie in HERKUNFT.md | Anmerkung |
|---|---:|---:|---|
| `eingang/` | 25 | 24 | Handdownloads H1, H4, H9, Zensus-Gemeindeergebnis, basemap.de-Stil. `wikidata_potsdam_aussortiert.md` (Liste der aussortierten Zeilen) nachträglich gehasht. `grundschuleinzugsgebiete.geojson` und `grunflachen-in-potsdam.geojson` stehen unter den Nutzungsbedingungen der LHP und werden nur intern genutzt |
| `zensus/2022/` | 12 | 12 | Strukturmerkmale (A1) und Gebäude nach Baujahr (B1) |
| `alkis_nas/2026-10-01/` | 1 | 1 | NAS-Auszug ohne Eigentümer (B0) |
| `alkis_nutzung/2026-11-05/` | 1 | 1 | Feldbeschreibung (XSD) des Dienstes |
| `baulandmodell/2019/` | 2 | 2 | Potsdamer Baulandmodell (A6, nur Fakten) |
| `bldam/2026-01-01/` | 1 | 1 | Denkmalliste, nur intern (B2) |
| `mbjs/2026-11-05/` | 1 | 1 | Kita-Standorte (A2) |
| `nvp_potsdam/2019/` | 1 | 1 | Nahverkehrsplan (A4, nur Fakten) |
| `osm/2026-11-05/` | 1 | 1 | OSM-PBF, ODbL; Prüfsumme in `eingang/HERKUNFT.md` |
| `potsdamer_platte/2026-11-05/` | 1 | 1 | Broschüre (B4, nur Bauzeiträume) |
| `vbb_gtfs/2026-11-05/` | 1 | 1 | VBB-Fahrplan (A4, A5b) |
| `_robots/2026-11-05/` | 5 | 0 | gelesene robots.txt; 3 gekürzt in anderen HERKUNFT.md, 2 nachträglich gehasht |
| `wikipedia_denkmale/2026-11-05/` | 28 | 28 | Übersicht und 27 Teillisten, nur Prüfspalte (B2) |

Nicht aufgenommen, mit Grund:

- `luftbild_lgb/2026-11-05/` (152 Dateien): Pilot B3. Die Bilder haben ihre Prüfsummen in der eigenen
  `HERKUNFT.md`; der Unterordner `referenz/` enthält Stichproben je Gebäude, die über ALKIS auf Adressen
  rückführbar sind, und bleibt deshalb ganz außerhalb des Repos.
- `wikidata_zuordnung/2026-11-05/` (7): Zuordnung und Stichproben von `pruefen/N3_wd_stichprobe.py`, deren
  Bezeichnungen Adressen enthalten können; keine Eingangsdaten.
- `wikipedia_denkmale/2026-11-05/stichproben/` (5): Arbeitsdateien, keine Eingangsdaten.
- `intern/` (2) und `entwuerfe/` (4): interne Notizen und nicht verschickte Mailentwürfe.
- `abrufprotokoll.tsv`: wird bei jedem Abruf fortgeschrieben, eine Prüfsumme wäre sofort alt.

## Offen: Gebäudestand ohne Sicherung

Die Gebäude kommen nicht aus einer Datei, sondern aus dem WFS der LGB (Lauf `20261104T132333Z`, 85 046 Gebäude).
Teil B und die 3D-Ansicht beziehen sich auf die Kopie `auswertung.gebaeude_stand_20261105` in der Datenbank
(`sql/002_ausbau.sql`). Diese Kopie liegt nur im Docker-Volume des Containers `kiezatlas-potsdam-db-1`; ein
Neuabruf des WFS liefert einen anderen Stand. Eine Sicherung (zum Beispiel `pg_dump` der Tabelle oder ein
GeoPackage mit SHA256 unter `$KIEZ_DATEN`) ist nicht angelegt. Das entscheidet André; sie gehört nicht ins
Repository, weil die Gebäudekennungen über ALKIS auf Adressen rückführbar sind.
