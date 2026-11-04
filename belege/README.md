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
