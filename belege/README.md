# Belege: Import mit der Geodaten-Import-Pipeline (04.11.2026)

Laufberichte der Pipeline (Text und JSON) für die drei Quellen in `config/potsdam.yaml`, gegen eine frische
PostGIS-Datenbank (`docker-compose.yml`, PostgreSQL 16, PostGIS 3.6) mit den Tabellen aus `sql/`.

| Lauf | Quelle | Ergebnis |
|---|---|---|
| `20261104T132324Z` | `stadtteile` (lokale CSV aus dem Handdownload) | 32 Stadtteile neu |
| `20261104T132325Z` | `zensus_gitter` (lokale CSV aus den Destatis-Dateien) | 6 348 Zellen im Rechteck um Potsdam |
| `20261104T132333Z` | `gebaeude_alkis` (WFS der LGB, 1-km-Kacheln, 1 s Pause) | 85 046 Gebäude im Rechteck, vollständig (jede Kachel unter der Höchstzahl), 519 s |

Die Auswertung (`skripte/02_auswerten.py`) ordnet davon 52 309 Gebäude und 3 443 bewohnte Zellen den
32 Stadtteilen zu. Geprüft in der Datenbank: Die Stadtteile sind gültig, überlappen sich nicht und haben
keine Lücken; jede Zelle zählt genau einmal.

## Ausbau (05.11.2026, Paket P0)

Je Lauf genau eine Quelle (`skripte/lauf.sh laden --nur …`), Ziele in `sql/002_ausbau.sql`.

| Lauf | Quelle | Ergebnis |
|---|---|---|
| `20261105T093628Z` | `mbjs_kita` (WFS MBJS, eine Seite, 2 s Pause) | 220 Kitas (je `id_kita` ein Standort); „unvollständig“, weil der Dienst 240 Einträge meldet: 17 Kitas stehen mit mehreren Häusern und gleicher Kapazität darin. Nichts gelöscht |
| `20261105T093707Z` | `mbjs_schule` (WFS MBJS) | 106 Schulen im Rechteck, 78 in Potsdam |
| `20261105T093727Z` | `alkis_nutzung` (WFS der LGB, 2-km-Kacheln, 1 s Pause) | 28 121 Nutzungsflächen, vollständig, 150 s |

Das Quellenverzeichnis oben schreibt die Pipeline nur im eigenen Berichtsordner neu; es ist hier noch der Stand
vom 04.11. Die neuen Quellen stehen in `QUELLEN.md`.

## 3D-Gebäude und Vektor-Grundkarte (06.11.2026)

`3D_grundkarte_20261106.md`: Entscheidungen G1 bis G8, Herkunft der Gebäudehöhen (50.356 von 52.309 aus der
ALKIS-Objekthöhe), Nachweis, dass die Bauzeit-Schätzung unverändert blieb, Prüfungen, Netzabrufe und Grenzen.
