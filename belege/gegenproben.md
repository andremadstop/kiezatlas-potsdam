# Gegenproben und fremde Vergleichszahlen (Nachweis, 06.11.2026)

Audit K20 (`berichte/audit_20261106.md`): Zahlen, die nicht aus den eigenen Dateien gerechnet, sondern von Hand
übernommen sind, mit Fundstelle und Ablesestand.

## Gegenproben im Steckbrief (`skripte/02_auswerten.py`, `GEGENPROBE`)

| Wert | Stichtag | Fundstelle | abgelesen |
|---|---|---|---|
| 185.137 Einwohner, Potsdam | 31.12.2025 (Fortschreibung) | Regionaldatenbank, Tabelle 12411-01-01-5-B, Potsdam (12054000), https://www.regionalstatistik.de/genesis/online?operation=table&code=12411-01-01-5-B | spätestens 04.11.2026; der Wert steht seit dem ersten Commit `e737b50` (04.11.2026, 15:49) im Skript, das genaue Ablesedatum ist nicht protokolliert |
| 8.221 Einwohner, Stadtteil 32 | 31.12.2022 (Melderegister) | Landeshauptstadt Potsdam, Statistischer Informationsdienst 1/2023, „Stadtteile im Blick 2022“, S. 26, https://www.potsdam.de/system/files/document/Statistischer_Infodienst_1_2023_Stadtteile_im_Blick_2022_online.pdf | wie oben |

Die Regionaldatenbank ist nur von Hand abrufbar (keine freigegebene automatische Abfrage); beide Werte sind
deshalb nicht maschinell nachgeprüft. Sie dienen nur als Gegenprobe mit anderem Stichtag und anderer Zählweise,
keine Rechengröße. Der Abgleich am selben Stichtag (Zensus-Gemeindeergebnis, −0,07 %) steht in
`belege/A1_gemeindeabgleich_20261105.md`.

## Vergleichszahl Berlin (visinage)

| Wert | Fundstelle | gelesen |
|---|---|---|
| 61,4 % der Gebäude im Rücktest mit richtiger Bauzeit, im Median 11 Jahre daneben (alle Schätzungen, Berlin) | Methodenseite von visinage, https://berlin.visinage.com/de/methods/ | 05.11.2026, Erkundung für den Bauplan (Notiz im Vault der UG, nicht öffentlich) |

Übernommen ist nur diese Zahl als Fakt mit Fundstelle, in `berichte/B4_holdout.md` und `pruefen/B4_protokoll.md`
als Vergleich. Keine Daten, Texte oder Code von visinage. Auf den Seiten wird visinage nur einmal als
Methodenvorbild genannt (`jahre-methode.html`), ohne die Zahl.
