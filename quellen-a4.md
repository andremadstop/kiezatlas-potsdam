# Zulieferung A4 zu QUELLEN.md (ÖPNV nach NVP 2019)

Paket A4, 05.11.2026. Führt die Integration (I1) in `QUELLEN.md` zusammen (Zeilen 10 und 17 dort).

## VBB-Fahrplandaten (Zeile 10)

| Feld | Wert |
|---|---|
| Daten | GTFS des VBB, Fahrplan ab 03.11.2026 (Dateien vom 03.11.2026 23:43) |
| Abruf | `https://www.vbb.de/gtfs`, 05.11.2026 09:37 UTC (Paket P0, Freigabe H6), sha256 `78870d01…6fdbf`, 84.657.543 B. A4 hat nichts nachgeladen. |
| Rohdaten | `$KIEZ_DATEN/vbb_gtfs/2026-11-05/GTFS.zip`, nicht entpackt (gestreamt) |
| Lizenz | Creative Commons Namensnennung 4.0 International |
| Vermerk | VBB Verkehrsverbund Berlin-Brandenburg GmbH, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), Daten verändert (eigene Berechnung) |
| Ziel | `auswertung.haltestelle`, 315 Haltestellen (283 in Potsdam, 32 im Brandenburger Umland bis 1 km), Stichtag 10.11.2026 |
| Skript | `skripte/13_oepnv.py`, Lauf 05.11.2026 (`belege/a4_lauf_20261105.txt`) |
| Personenbezug | keiner (Haltestellennamen, Fahrzeiten) |

## Nahverkehrsplan 2019 (Zeile 17)

| Feld | Wert |
|---|---|
| Dokument | Nahverkehrsplan 2019 für die Landeshauptstadt Potsdam, VerkehrsConsult Dresden-Berlin GmbH, PDF vom 29.09.2020 mit Anlagen |
| Abruf | `https://www.potsdam.de/system/files/documents/2020-09-29_nvp_potsdam_mit_anlagen.pdf`, 05.11.2026 10:09 UTC, robots.txt vorher gelesen (`/system/files/` frei), Abstand ≥ 5 s, sha256 `3e9a83e1…cbc1bf` |
| Rohdaten | `$KIEZ_DATEN/nvp_potsdam/2019/` (nicht ins Repo, keine Lizenzangabe) |
| Übernommen | nur Fakten mit Seitenangabe: Tab. 4.1 (S. 55–56), Abb. 4.1 (S. 57–58), Kap. 4.1.3 und Tab. 4.2/4.3 (S. 58–59), Bewertungsfenster aus Anlage 4 → `config/richtwerte.yaml`, Abschnitt `oepnv` |
| Vermerk im Atlas | Richtwerte: Nahverkehrsplan 2019 der Landeshauptstadt Potsdam, Kap. 4.1 (Geltung 2019–2023; kein Nachfolger gefunden, Stand 05.11.2026) |
| geprüft | 05.11.2026, Protokoll `pruefen/a4_nvp_lesung.md` |

Hinweis für I1: In Zeile 17 von `QUELLEN.md` steht „Erkundung 05.11.2026“. Richtig ist jetzt „gelesen 05.11.2026 (A4),
Geltung 2019–2023, Nachfolger ungeprüft“.
