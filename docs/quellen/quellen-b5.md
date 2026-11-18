# Quellenbeitrag Paket B5 Zweig 2 (für QUELLEN.md, daten/LIZENZ.md und daten/schema/, Zusammenführung in I2)

B5 Zweig 2 bringt keine neue Quelle und ruft nichts aus dem Netz ab. Neu ist eine abgeleitete Datei:

| Datei | erzeugt von | Inhalt | Lizenz und Vermerk |
|---|---|---|---|
| `daten/jahre_methode.js` (`KIEZ_JAHRE_METHODE`) | `skripte/26_jahre_methode.py` aus `daten/jahre/<nr>.js` und `berichte/B4_holdout.md` (B4) | Zahl der Gebäude je Stufe und Status, Rücktest-Quoten mit n, Gegenprobe, Vergleich Gebäudekarte gegen Zensus (Zensuswerte gerundet) | wie `daten/jahre/<nr>.js`: dl-de/by-2-0, „© Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung); © GeoBasis-DE/LGB, dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), Daten verändert (eigene Berechnung)“. Rücktest-Prüfsätze (Wikipedia-Denkmalliste, Sichtprüfung Luftbilder) gehen nur als Zählung ein, keine Einträge, keine Jahre. Die Berliner Vergleichswerte stammen aus dem Bericht B4 (Methodenvorbild, nur Zahlen). |

Für `daten/schema/`: Schema als Zulieferung in `pruefen/B5_schema/jahre_methode.json` (Tabelle 0.4: `daten/schema/` gehört P0).
Bis zur Übernahme meldet `pruefen/daten.py` für `jahre_methode.js` „kein Schema“; `pruefen/B5_methode.py` prüft den
Vertrag mit derselben Prüfmaschine.
