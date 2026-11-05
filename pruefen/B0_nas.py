"""Prüfung Paket B0 (ALKIS-NAS): Abnahmekriterien direkt gegen die Datenbank und die Dateien.

  1. ≥ 98 % der 52.309 Snapshot-Gebäude in Potsdam haben ein NAS-Bauwerk (oid_bezug)
  2. Füllgrad baujahr stadtweit (Zahl, keine Schwelle)
  3. Kein Eigentümer-, Personen- oder Buchungsfeld in den B0-Tabellen (Schemaprüfung), nur Bauwerksarten
     in funktion
  4. Adressen nur intern: mosidi_lesen kann gebaeude_adresse nicht lesen; keine Datei in daten/ (und
     export/, falls vorhanden) enthält ein Adressfeld oder eine der Adressen aus gebaeude_adresse
     (Ausgabe nur Zählungen, nie Adressen)

Aufruf wie skripte/20_alkis_nas.py (PG*-Umgebung als kiezatlas_rechnen, dazu LESE_PASSWORD für Punkt 4):
    uv run -q --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \\
        python -I pruefen/B0_nas.py
Exit 0 nur, wenn alle Punkte bestehen.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import psycopg

WURZEL = Path(__file__).resolve().parent.parent
GEBAEUDE_IN_POTSDAM = 52309
VERBOTEN_SPALTE = re.compile(r"eigent|person|namensnummer|anschrift|buchung|flurst|vorname|nachname|geburt", re.I)
ERLAUBT_FUNKTION = re.compile(r"^(Gebaeude|Bauteil|Turm|VorratsbehaelterSpeicherbauwerk|"
                              r"BauwerkOderAnlageFuerIndustrieUndGewerbe|BauwerkOderAnlageFuerSportFreizeitUndErholung|"
                              r"SonstigesBauwerkOderSonstigeEinrichtung)(:\d+)?$")
ADRESSFELD = re.compile(r"""["']?\b(strasse|straße|hausnr|hausnummer|adresse|anschrift)\b["']?\s*:""", re.I)

fehler: list[str] = []


def pruefe(ok: bool, text: str) -> None:
    print(("ok    " if ok else "FEHLT ") + text)
    if not ok:
        fehler.append(text)


def adresse_in(text: str, je_strasse: dict[str, set[str]]) -> bool:
    """True, wenn im Text eine Straße aus je_strasse mit einer ihrer Hausnummern steht."""
    klein = text.lower()
    for strasse, nummern in je_strasse.items():
        if strasse not in klein:
            continue
        for n in re.findall(re.escape(strasse) + r"\s*,?\s*(\d+\s*[a-z]?)\b", klein):
            if n.replace(" ", "") in nummern:
                return True
    return False


def main() -> int:
    with psycopg.connect("") as conn, conn.cursor() as cur:
        # 1. Zuordnung
        cur.execute("""
            WITH p AS (SELECT g.oid FROM auswertung.gebaeude_stand_20261105 g
                       WHERE EXISTS (SELECT 1 FROM public.stadtteil s
                                     WHERE ST_Contains(s.geom, ST_PointOnSurface(g.geom))))
            SELECT count(*), count(*) FILTER (WHERE EXISTS (
                       SELECT 1 FROM auswertung.alkis_nas_gebaeude a WHERE a.oid_bezug = p.oid))
            FROM p""")
        n, zu = cur.fetchone()
        pruefe(n == GEBAEUDE_IN_POTSDAM, f"Snapshot-Gebäude in Potsdam: {n} (erwartet {GEBAEUDE_IN_POTSDAM})")
        pruefe(zu >= 0.98 * n, f"zugeordnet: {zu} von {n} = {100 * zu / max(n, 1):.2f} % (Schwelle 98 %)")
        cur.execute("""SELECT count(*) FROM auswertung.alkis_nas_gebaeude a
                       WHERE oid_bezug IS NOT NULL AND NOT EXISTS (
                           SELECT 1 FROM auswertung.gebaeude_stand_20261105 g WHERE g.oid = a.oid_bezug)""")
        pruefe(cur.fetchone()[0] == 0, "jedes oid_bezug steht im Snapshot gebaeude_stand_20261105")

        # 2. baujahr
        cur.execute("""SELECT count(*) FILTER (WHERE funktion LIKE 'Gebaeude%'),
                              count(*) FILTER (WHERE funktion LIKE 'Gebaeude%' AND baujahr IS NOT NULL)
                       FROM auswertung.alkis_nas_gebaeude""")
        geb, bj = cur.fetchone()
        pruefe(geb > 0, f"Füllgrad baujahr stadtweit: {bj} von {geb} AX_Gebaeude ({100 * bj / max(geb, 1):.1f} %)")

        # 3. Schema
        cur.execute("""SELECT table_name, column_name FROM information_schema.columns
                       WHERE table_schema = 'auswertung'
                         AND table_name IN ('alkis_nas_gebaeude', 'gebaeude_adresse')
                       ORDER BY 1, ordinal_position""")
        spalten = cur.fetchall()
        pruefe(len(spalten) >= 13, f"Spalten gelesen: {len(spalten)}")
        verboten = [f"{t}.{c}" for t, c in spalten if VERBOTEN_SPALTE.search(c)]
        pruefe(not verboten, f"kein Eigentümer-/Personen-/Buchungsfeld (gefunden: {verboten or 'keins'})")
        cur.execute("SELECT DISTINCT funktion FROM auswertung.alkis_nas_gebaeude")
        fremd = [f for (f,) in cur.fetchall() if not ERLAUBT_FUNKTION.match(f or "")]
        pruefe(not fremd, f"funktion enthält nur Bauwerksarten (fremd: {len(fremd)})")

        # 4a. Adressen: Anzahl und Bestand für den Dateiabgleich (bleibt im Speicher)
        cur.execute("SELECT strasse, hausnr FROM auswertung.gebaeude_adresse")
        adressen = cur.fetchall()
        pruefe(len(adressen) > 0, f"gebaeude_adresse gefüllt: {len(adressen)} Zeilen")

    # 4b. Leserolle hat keinen Zugriff
    lese = os.environ.get("LESE_PASSWORD")
    if not lese:
        pruefe(False, "LESE_PASSWORD fehlt, Zugriff von mosidi_lesen nicht prüfbar")
    else:
        try:
            with psycopg.connect("", user="mosidi_lesen", password=lese) as c2, c2.cursor() as cur2:
                cur2.execute("SELECT 1 FROM auswertung.gebaeude_adresse LIMIT 1")
                pruefe(False, "mosidi_lesen kann auswertung.gebaeude_adresse lesen")
        except psycopg.errors.InsufficientPrivilege:
            pruefe(True, "mosidi_lesen: permission denied auf auswertung.gebaeude_adresse")

    # 4c. Keine Adressen in veröffentlichten Dateien
    je_strasse: dict[str, set[str]] = {}
    for s, h in adressen:
        je_strasse.setdefault(s.lower(), set()).add(h.lower().replace(" ", ""))
    # Selbsttest der Erkennung mit erfundenen Werten (beweist, dass die Suche anschlägt)
    probe = {"testgasse": {"7b"}}
    pruefe(adresse_in("Lage: Testgasse 7 b", probe) and not adresse_in("Testgasse 8", probe)
           and ADRESSFELD.search('{"strasse": "x"}') is not None, "Selbsttest der Adresserkennung")
    dateien = [p for ordner in ("daten", "export", "downloads") if (WURZEL / ordner).is_dir()
               for p in (WURZEL / ordner).rglob("*") if p.is_file()]
    treffer_feld, treffer_adresse = [], []
    for p in dateien:
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if ADRESSFELD.search(text):
            treffer_feld.append(p.relative_to(WURZEL).as_posix())
        if adresse_in(text, je_strasse):
            treffer_adresse.append(p.relative_to(WURZEL).as_posix())
    pruefe(not treffer_feld, f"kein Adressfeld in {len(dateien)} Dateien (daten/, export/, downloads/): "
                             f"{treffer_feld or 'keins'}")
    pruefe(not treffer_adresse, f"keine Adresse aus gebaeude_adresse in diesen Dateien "
                                f"(Dateien mit Treffer: {len(treffer_adresse)})")

    print(f"\n{'BESTANDEN' if not fehler else 'NICHT BESTANDEN'}: {len(fehler)} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
