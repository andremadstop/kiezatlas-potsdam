# N4: Lage der Grundschule Hanna von Pestalozza (MBJS 103512), Entscheidung 05.11.2026

Nur mit lokalen Daten geprüft, kein Netzabruf. Abfragen mit der Leserolle `mosidi_lesen` (nur SELECT).

## Befund

| Quelle | Lizenz | Was sie sagt |
|---|---|---|
| MBJS-Schulstandorte (`public.mbjs_schule`) | dl-de/by-2-0 | Ort „Potsdam/OT Groß Glienicke“, PLZ 14476, 281 Schüler (Stand 2022). Der Punkt (EPSG:25833 x 367319, y 5814072) liegt im Stadtteil 84 Fahrland, Planungsraum 103 Krampnitz. Rund 56 m daneben liegen mit gemeinsamer Koordinate die Grundschule Krampnitz Potsdam (107013) und das Nord-Gymnasium (121423). Die Straße speichert der Atlas bewusst nicht (`config/potsdam.yaml`, Datenschutz), ein Adressabgleich ist deshalb nicht möglich. |
| ALKIS vereinfacht, Gebäude (`public.gebaeude`) | dl-de/by-2-0 | Der MBJS-Punkt liegt auf einem Gebäude „Allgemein bildende Schule“ (`DEBBAL01000cKXAyBL`, 3.757 m², 2 Geschosse, Objekt aktualisiert 11.08.2025). In Groß Glienicke gibt es zwei Gebäude „Allgemein bildende Schule“ (`DEBBAL5400024rHABL` 2.467 m², `DEBBAL010008zRAJBL` 193 m², aktualisiert 09.02.2021), rund 3,8 km vom MBJS-Punkt entfernt. Dort liegt kein MBJS-Standort. |
| ALKIS NAS (`auswertung.alkis_nas_gebaeude`) | dl-de/by-2-0 | Alle genannten Gebäude mit Funktion 3021 (allgemeinbildende Schule), ohne Baujahr. |
| ALKIS tatsächliche Nutzung (`public.alkis_nutzung`) | dl-de/by-2-0 | An beiden Orten „Fläche besonderer funktionaler Prägung, Bildung und Wissenschaft“, ohne Namen. |
| OpenStreetMap (nur Hinweis, nicht übernommen) | ODbL 1.0, © OpenStreetMap-Mitwirkende | Ein Objekt `amenity=school` mit dem Namen der Schule liegt am ALKIS-Schulgebäude in Groß Glienicke. Am Krampnitzer Standort führt der Auszug (Stand 31.10.2026) keine Schule. Keine Koordinate aus OSM in einer Datei ohne `_odbl`. |
| Grundschuleinzugsgebiete der LHP (nur intern) | Nutzungsbedingungen der LHP, ungeprüft | Intern gegengeprüft mit `pruefen/n4_einzugsgebiete.py`. Das Ergebnis liegt nur unter `$KIEZ_DATEN/intern/N4_einzugsgebiete_20261105.md` und wird nicht veröffentlicht. Es entscheidet die Frage ebenfalls nicht. |

## Entscheidung: Lage nicht eindeutig

Zwei Lesarten passen zu den amtlichen Daten:
1. **Falsch verortet:** Die Schule steht in Groß Glienicke, wo ALKIS Schulgebäude ohne MBJS-Standort führt. Der Punkt
   ist dann eine fehlerhafte Geokodierung.
2. **Ausweichstandort:** Die Schule unterrichtet derzeit auf dem Krampnitzer Schulcampus. Dafür spricht, dass der Punkt
   auf einem 2025 aktualisierten Schulgebäude liegt und eine eigene Koordinate neben der Grundschule Krampnitz hat.

Welche Lesart stimmt, lässt sich ohne Rückfrage bei MBJS bzw. Stadt nicht entscheiden. OSM spricht für Lesart 1, darf
die Entscheidung aber nicht tragen (nur Hinweis, Lizenzgrenze). Deshalb gibt es **keinen korrigierten Punkt**.

## Umsetzung (skripte/15_planer.py, A6)

- `daten/einrichtungen.js`: Der Punkt bleibt so, wie das MBJS ihn liefert, mit dem Feld `hinweis`
  („Lage strittig …“). Die Oberfläche (`planer.js`) zeigt den Hinweis im Popup des Punkts und in der Legende der
  Entfernungskarte, solange die Grundschule gewählt ist. Die Versorgungstabelle zeigt ihn an jedem gesperrten Wert.
- **Entfernungskarte ohne den strittigen Punkt:** Für die Zellen, deren nächste Grundschule in
  `auswertung.zelle_erreichbar` der strittige Punkt ist (67 Zellen Luftlinie, 295 Zellen Fußweg), rechnet
  `15_planer.py` das nächste andere Ziel nur lesend neu. Die Luftlinie wird wie in A5a berechnet, der Fußweg mit den Funktionen von A5b
  (`skripte/14b_fussweg.py`). `zelle_erreichbar` bleibt unverändert. Größte Änderung: +60 m Luftlinie, +180 m Fußweg.
- **Grundschulwerte in 101 Groß Glienicke, Sacrow und 103 Krampnitz bleiben leer.** Betroffen sind 8 Werte Luftlinie und
  4 Werte Fußweg. Der Grund steht in `unsicherheit`.
- Export (A8): Spalte `hinweis` in der Ebene `einrichtung`, Erklärung in `daten/export/README.md`.

## Gegenproben (pruefen/A6_planer.py, A6-12)

- Das nächste Ziel ohne den strittigen Standort, ganz in SQL berechnet, ist in den 3.376 nicht betroffenen Zellen gleich der
  Tabelle (0 Abweichungen). Die Methode von A5a ist also getroffen.
- Der Fußweg-Nachbau mit allen Zielen ergibt genau `auswertung.zelle_erreichbar` (3.443 Zellen, 0 Abweichungen). Die
  neuen Fußwege liegen nie unter der neuen Luftlinie.
- `erreichbar.js`: 44.343 Werte, 0 Abweichungen. `erreichbar_fuss_odbl.js`: 64.771 Werte, 0 Abweichungen.

## Was die Sperre aufhebt

Eine schriftliche Auskunft von MBJS oder Landeshauptstadt dazu, wo die Schule unterrichtet:
- **Groß Glienicke:** Punkt auf das ALKIS-Gebäude `DEBBAL5400024rHABL` setzen, Quelle © GeoBasis-DE/LGB, dl-de/by-2-0, mit Vermerk.
- **Krampnitz:** Punkt bleibt. Die Ortsangabe ist dann veraltet, und die Sperre fällt.

Die Ausnahme steht in `skripte/15_planer.py` und greift für jede Schule, deren Ortsangabe „Potsdam/OT …“ der Lage
widerspricht (`ort_abweichung`).
