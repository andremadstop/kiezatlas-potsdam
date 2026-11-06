# Quellen B3 (Luftbild-Pilot), Zulieferung für QUELLEN.md

Zusammenführung in `QUELLEN.md` erst in der Integration (I1/I2); diese Datei gehört Paket B3.

| # | Quelle | Wofür | Abrufweg | Lizenz | Vermerk |
|---|---|---|---|---|---|
| 23 | LGB-Luftbilder als WMS (mapproxy): `dop100g_1953`, `dop50g_1992_1997`, `dop40g_2001_2009`, `dop20_2009_2012`, `dop20_2013_2015`, `dop20_2016_2018`, `dop20_2019_2021`, `dop20c`, jeweils mit dem `*_info`-Layer für das Flugdatum je Blatt | B3, Klammer „erstmals im Luftbild“, nur Pilot Bornstedt | `https://isk.geobasis-bb.de/mapproxy/<dienst>/service/wms`, 4 GetMap je Befliegung (0,4 m, JPEG) und GetFeatureInfo je 1-km-Blatt, ≥ 10 s zwischen allen Anfragen an isk.geobasis-bb.de, Protokoll `kiezatlas-daten/abrufprotokoll.tsv` | dl-de/by-2-0 (AccessConstraints der Capabilities) | © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) |
| 24 | Messtischblätter DR25 (WMS der LGB) | vorgesehen für „stand schon vor 1912“ | – | dl-de/by-2-0 | **nicht abgerufen, nicht genutzt** (der Pilot prüft nur die DOP-Zeitreihe) |
| – | Zensus 2022, Gebäude nach Baujahr in Jahrzehnten, 100-m-Gitter (`zensus/2022/Gebaeude_nach_Baujahr_Jahrzehnte.zip`, liegt seit P0 vor) | B3, Gegenprobe in der Summe (nur Bericht, kein Wert in `jahr_klammer`) | offline, kein Abruf | dl-de/by-2-0 | © Statistisches Bundesamt (Destatis), Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung) |

Rohdaten: `kiezatlas-daten/luftbild_lgb/2026-11-05/` mit `HERKUNFT.md`. Die Bilder, die Stichprobe und die Referenz bleiben dort;
ins öffentliche Repo kommen nur Zählungen (`berichte/B3_pilot.md`) und das Protokoll (`pruefen/B3_protokoll.md`).
