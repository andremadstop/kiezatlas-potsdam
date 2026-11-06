"""Prüfung Paket A1 (Bevölkerungsstruktur, Zensus 2022 im 100-m-Gitter).

Liest die Datenbank nur (psql als Leserolle), die Rohdaten-Zips nur zum Hash, kein Netz. Prüft:
  1. Rohdaten: SHA256 jeder A1-Datei wie in $KIEZ_DATEN/zensus/2022/HERKUNFT.md, dort ein robots-Befund;
     im Abrufprotokoll liegen zwischen zwei Anfragen an www.destatis.de mindestens 30 s.
  2. Schlüssel (Bauplan A1 mit Korrektur 25): jede gitter_id aus public.zensus_struktur steht in
     public.zensus_zelle. Ausnahme, einzeln ausgewiesen: Zellen mit Haushalten, aber ohne Personen
     (i_ges = st_ges = 0). Die gibt es durch die Cell-Key-Methode; zensus_zelle kennt sie nicht, weil
     Destatis dort keine Bevölkerung ausweist.
  3. Abdeckung je Thema in Potsdam (Zellmittelpunkt in einem der 32 Stadtteile, wie die Seite): Zellen
     mit Wert und Anteil der Einwohner (zensus_zelle.ew), die in diesen Zellen wohnen.
  4. Summen je Thema in Potsdam, je Thema mit eigenem Bezugswert:
       Personen (Altersgruppen, Staatsangehörigkeit): Einwohner aus dem Bevölkerungsgitter (182.673)
       Haushalte (Größe, Typ, Seniorenstatus): die drei Haushaltsdateien gegeneinander
       Familien (Kernfamilie): Haushalte mit Kernfamilie (Paare ohne/mit Kind + Alleinerziehende)
     Grenze 3 % (Cell-Key-Effekt). Dazu je Thema Summe der Klassen gegen „Insgesamt“.
     Liegt das Zensus-Gemeindeergebnis als Handdownload vor ($KIEZ_DATEN/eingang/zensus2022_gemeinde_potsdam.csv,
     Spalten merkmal;wert;quelle mit merkmal = i_ges, hh_ges, kf_ges, …), wird zusätzlich dagegen geprüft.
  5. Geheimhaltung: keine Datei unter daten/ enthält ein Feld aus zensus_struktur (feine Klassen je Zelle).
  6. Paketgrenze: git diff gegen die Basis berührt nur Dateien von A1 (siehe Aufruf: drei Lesarten).
  7. Planungsräume: Abdeckung je Planungsraum, sobald public.planungsraum gefüllt ist (H1), sonst Hinweis.

Aufruf (Passwort nur aus der Umgebung, nie auf der Kommandozeile):
  set -a; . ../kiezatlas-potsdam/.env; set +a
  PGPASSWORD="$LESE_PASSWORD" python3 -I pruefen/A1_zensus.py [--basis BASIS]
  BASIS (Nachlauf N2, 05.11.2026; vorher Standard ausbau/p0, auf dem Integrationsstand dauerhaft rot):
    ausbau/integration (Standard)  Nachlauf: geprüft wird, was seit dem Integrationsstand dazukam, eingecheckt
                                   und offen. Erlaubt sind die Dateien von A1 und die in NACHLAUF_PFADE
                                   freigegebenen Dateien der Nachlauf-Pakete (je Eintrag mit Paket).
    ausbau/p0                      Paketzweig ausbau/a1 selbst, eingecheckt und offen, nur Dateien von A1.
    ausbau/p0...ausbau/a1          Bereich (drei Punkte = ab dem gemeinsamen Vorfahren): nur die Commits von A1,
                                   ohne offenen Stand und ohne ungetrackte Dateien. So lässt sich auf jedem Zweig
                                   belegen, dass A1 seine Grenze gehalten hat. Zwei Punkte gelten wie drei.
Rückgabe 0 = alle Prüfungen bestanden, 1 = Befund.
"""
from __future__ import annotations

import csv
import hashlib
import os
import re
import subprocess  # nosec B404
import sys
from datetime import datetime
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
KIEZ_DATEN = Path(os.environ.get("KIEZ_DATEN") or WURZEL.parent / "kiezatlas-daten")
ZENSUS = KIEZ_DATEN / "zensus" / "2022"
GEMEINDE = KIEZ_DATEN / "eingang" / "zensus2022_gemeinde_potsdam.csv"
GRENZE = 3.0  # Prozent

A1_DATEIEN = [
    "Alter_in_infrastrukturellen_Altersgruppen.zip",
    "Zensus2022_Groesse_des_privaten_Haushalts_in_Gitterzellen.zip",
    "Typ_des_privaten_Haushalts_Familien.zip",
    "Typ_der_Kernfamilie_nach_Kindern.zip",
    "Seniorenstatus_eines_privaten_Haushalts.zip",
    "Zensus2022_Staatsangehoerigkeit_Gruppen_in_Gitterzellen.zip",
    "Zensus2022_Durchschn_Nettokaltmiete.zip",
    "Leerstandsquote_in_Gitterzellen.zip",
    "Durchschnittliche_Wohnflaeche_je_Bewohner_in_Gitterzellen.zip",
]
# Thema: (Einheit, Insgesamt-Feld, Klassen)
THEMEN = {
    "Altersgruppen": ("Personen", "i_ges", ["i_u3", "i_3_5", "i_6_9", "i_10_15", "i_16_18", "i_19_24", "i_25_39",
                                            "i_40_59", "i_60_66", "i_67_74", "i_75p"]),
    "Staatsangehörigkeit": ("Personen", "st_ges", ["st_de", "st_ausland"]),
    "Haushaltsgröße": ("Haushalte", "hh_ges", ["hh_1", "hh_2", "hh_3", "hh_4", "hh_5", "hh_6p"]),
    "Haushaltstyp": ("Haushalte", "ht_ges", ["ht_single", "ht_paar_ohne", "ht_paar_mit", "ht_alleinerz",
                                             "ht_mehrpers"]),
    "Seniorenstatus": ("Haushalte", "sen_ges", ["sen_nur", "sen_mit", "sen_ohne"]),
    "Kernfamilie": ("Familien", "kf_ges", ["kf_ehe_ohne", "kf_ehe_u18", "kf_ehe_ab18", "kf_lp_ohne", "kf_lp_u18",
                                           "kf_lp_ab18", "kf_nel_ohne", "kf_nel_u18", "kf_nel_ab18",
                                           "kf_vater_u18", "kf_vater_ab18", "kf_mutter_u18", "kf_mutter_ab18"]),
}
MITTEL = {"Nettokaltmiete (€/m²)": "miete_qm", "Leerstandsquote (%)": "leer_quote",
          "Wohnfläche je Bewohner (m²)": "wfl_je_bew"}
# Dateien, die A1 laut Bauplan 0.4 (mit Korrekturen) ändern oder anlegen darf
A1_PFADE = [r"skripte/01_vorbereiten\.py", r"skripte/10_zensus_struktur\.py", r"pruefen/A1_[^/]+",
            r"quellen-a1\.md", r"belege/A1_[^/]+", r"belege/20261105T\d{6}Z[^/]*"]
# Nur bei Basis ausbau/integration (Nachlauf): Dateien, die ein Nachlauf-Paket neben A1 laut Auftrag anfassen darf.
# Jeder Eintrag nennt sein Paket; ein neues Nachlauf-Paket trägt hier seine Dateien ein, statt die Prüfung zu lockern.
NACHLAUF_PFADE = {
    # N2 (05.11.2026): Zensus-Gegenprobe A1, Paketgrenze B1, Gebietsklassen A4 (richtwerte.yaml nur Abschnitt oepnv)
    "N2": [r"pruefen/b1_jahre\.py", r"pruefen/a4_[^/]+", r"belege/a4_[^/]+", r"quellen-a4\.md",
           r"config/richtwerte\.yaml", r"belege/N2_[^/]+"],
}
NACHLAUF_BASIS = "ausbau/integration"

befunde: list[str] = []
hinweise: list[str] = []


def pruef(ok: bool, text: str) -> bool:
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        befunde.append(text)
    return ok


def zahl(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def sql(abfrage: str) -> list[list[str]]:
    umg = {**os.environ, "PGHOST": os.environ.get("PGHOST", "127.0.0.1"),
           "PGPORT": os.environ.get("PGPORT", "55461"), "PGDATABASE": os.environ.get("PGDATABASE", "kiezatlas"),
           "PGUSER": os.environ.get("PGUSER", "mosidi_lesen")}
    aus = subprocess.run(["psql", "-X", "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1", "-c", abfrage],  # noqa: S603,S607
                         env=umg, capture_output=True, text=True, check=True)
    return [z.split("\t") for z in aus.stdout.splitlines() if z]


def rohdaten() -> None:
    print("1. Rohdaten und Abruf")
    herkunft = (ZENSUS / "HERKUNFT.md").read_text(encoding="utf-8")
    pruef("robots" in herkunft and "Crawl-delay: 30" in herkunft,
          "HERKUNFT.md nennt den robots-Befund (Crawl-delay 30)")
    for datei in A1_DATEIEN:
        h = hashlib.sha256((ZENSUS / datei).read_bytes()).hexdigest()
        pruef(re.search(rf"\|\s*{re.escape(datei)}\s*\|[^|]*\|\s*{h}\s*\|", herkunft) is not None,
              f"{datei}: SHA256 wie in HERKUNFT.md ({h[:12]}…)")
    zeiten = []
    with (KIEZ_DATEN / "abrufprotokoll.tsv").open(encoding="utf-8") as f:
        for z in csv.DictReader(f, delimiter="\t"):
            if z["rechner"] == "www.destatis.de":
                zeiten.append(datetime.fromisoformat(z["zeit_utc"]))
    abstaende = [(b - a).total_seconds() for a, b in zip(zeiten, zeiten[1:], strict=False)]
    pruef(bool(zeiten) and all(s >= 30 for s in abstaende),
          f"Abrufprotokoll: {len(zeiten)} Anfragen an www.destatis.de, kleinster Abstand "
          f"{min(abstaende) if abstaende else '–'} s (Mindestwert 30 s)")


POTSDAM = """(SELECT s.*, z.ew FROM zensus_struktur s JOIN zensus_zelle z USING (gitter_id)
              WHERE EXISTS (SELECT 1 FROM stadtteil t WHERE ST_Contains(t.geom, s.geom)))"""


def schluessel() -> None:
    print("2. Schlüssel gegen zensus_zelle")
    n, = sql("SELECT count(*) FROM zensus_struktur")[0]
    pruef(int(n) > 0, f"public.zensus_struktur hat {zahl(int(n))} Zellen")
    fremd = sql("""SELECT s.gitter_id, s.i_ges, s.st_ges, s.hh_ges,
                          EXISTS (SELECT 1 FROM stadtteil t WHERE ST_Contains(t.geom, s.geom))
                   FROM zensus_struktur s LEFT JOIN zensus_zelle z USING (gitter_id)
                   WHERE z.gitter_id IS NULL ORDER BY 1""")
    erklaert = [f for f in fremd if f[1] == "0" and f[2] == "0"]
    pruef(len(fremd) == len(erklaert),
          f"{zahl(int(n) - len(fremd))} von {zahl(int(n))} gitter_id stehen in zensus_zelle; "
          f"{len(erklaert)} Ausnahme(n) nur mit Haushalten, ohne Personen (Cell-Key), "
          f"{len(fremd) - len(erklaert)} unerklärt")
    for f in erklaert:
        print(f"        Ausnahme {f[0]}: {f[3]} Haushalte, 0 Personen, in Potsdam: {'ja' if f[4] == 't' else 'nein'}")
    dop, = sql("SELECT count(*) - count(DISTINCT gitter_id) FROM zensus_struktur")[0]
    pruef(dop == "0", "keine doppelte gitter_id")


def abdeckung() -> dict[str, float]:
    print("3. Abdeckung in Potsdam (Mittelpunkt im Stadtteil, bewohnte Zellen aus zensus_zelle)")
    zellen, ew = map(int, sql("""SELECT count(*), sum(ew) FROM zensus_zelle z WHERE ew > 0 AND EXISTS
                                 (SELECT 1 FROM stadtteil t WHERE ST_Contains(t.geom, z.geom))""")[0])
    print(f"        Bezug: {zahl(zellen)} bewohnte Zellen, {zahl(ew)} Einwohner")
    felder = {t: g for t, (_, g, _) in THEMEN.items()} | MITTEL
    teile = ", ".join(f"count(*) FILTER (WHERE s.{f} {'IS NOT NULL' if f in MITTEL.values() else '> 0'}), "
                      f"coalesce(sum(z.ew) FILTER (WHERE s.{f} {'IS NOT NULL' if f in MITTEL.values() else '> 0'}), 0)"
                      for f in felder.values())
    r = sql(f"""SELECT {teile} FROM zensus_zelle z JOIN zensus_struktur s USING (gitter_id)
                WHERE z.ew > 0 AND EXISTS (SELECT 1 FROM stadtteil t WHERE ST_Contains(t.geom, z.geom))""")[0]
    anteil = {}
    for i, (thema, feld) in enumerate(felder.items()):
        c, e = int(r[2 * i]), int(r[2 * i + 1])
        anteil[thema] = 100 * e / ew
        print(f"        {thema:<28} {feld:<11} {zahl(c):>6} Zellen ({100 * c / zellen:5.1f} %), "
              f"{zahl(e):>8} EW ({100 * e / ew:5.1f} %)")
    pruef(all(a >= 95 for t, a in anteil.items() if t in THEMEN),
          "Zählthemen erreichen je mindestens 95 % der Einwohner (Rest: Zellen ohne Haushalte/Familien)")
    return anteil


def summen() -> None:
    print("4. Summen je Thema in Potsdam, je Thema eigener Bezugswert")
    alle = [g for _, g, _ in THEMEN.values()] + [k for _, _, ks in THEMEN.values() for k in ks]
    r = sql(f"SELECT sum(ew), {', '.join(f'sum({f})' for f in alle)} FROM {POTSDAM} p")[0]
    ew = int(r[0])
    s = {f: int(v) for f, v in zip(alle, r[1:], strict=True)}
    hh_kern = s["ht_paar_ohne"] + s["ht_paar_mit"] + s["ht_alleinerz"]
    bezug = {
        "Altersgruppen": (ew, "Einwohner im Bevölkerungsgitter (zensus_zelle.ew)"),
        "Staatsangehörigkeit": (ew, "Einwohner im Bevölkerungsgitter (zensus_zelle.ew)"),
        # Destatis weist das Insgesamt je Zelle in allen Haushaltsdateien gleich aus: das ist eine
        # Stimmigkeitsprüfung, kein unabhängiger Bezug (der wäre das Gemeindeergebnis, siehe GEMEINDE)
        "Haushaltsgröße": (s["ht_ges"], "Haushalte laut Haushaltstyp-Datei"),
        "Haushaltstyp": (s["sen_ges"], "Haushalte laut Seniorenstatus-Datei"),
        "Seniorenstatus": (s["hh_ges"], "Haushalte laut Haushaltsgrößen-Datei"),
        "Kernfamilie": (hh_kern, "Haushalte mit Kernfamilie (Paare ohne/mit Kind + Alleinerziehende)"),
    }
    gemeinde = {}
    if GEMEINDE.exists():
        with GEMEINDE.open(encoding="utf-8") as f:
            gemeinde = {z["merkmal"]: (int(z["wert"]), z["quelle"]) for z in csv.DictReader(f, delimiter=";")}
    for thema, (einheit, ges, klassen) in THEMEN.items():
        summe, kl = s[ges], sum(s[k] for k in klassen)
        ref, text = bezug[thema]
        abw = 100 * (summe - ref) / ref
        kl_abw = 100 * (kl - summe) / summe
        print(f"        {thema}: Insgesamt {zahl(summe)} {einheit}, Summe der Klassen {zahl(kl)} ({kl_abw:+.1f} %)")
        if abs(kl_abw) >= GRENZE:
            # Eigenschaft der Daten (Cell-Key, „–“ in kleinen Klassen), kein Ladefehler: für A6 festhalten
            hinweise.append(f"{thema}: Summe der Klassen {kl_abw:+.1f} % gegen Insgesamt; Klassensummen "
                            "unterschätzen auf Stadtebene, Anteile nur mit Unsicherheitshinweis zeigen")
        pruef(abs(abw) < GRENZE, f"{thema}: {zahl(summe)} gegen {zahl(ref)} ({text}), Abweichung {abw:+.2f} %")
        if ges in gemeinde:
            g, q = gemeinde[ges]
            pruef(abs(100 * (summe - g) / g) < GRENZE,
                  f"{thema}: gegen Gemeindeergebnis {zahl(g)} ({q}), Abweichung {100 * (summe - g) / g:+.2f} %")
            # Klassen gegen die Gemeindetabelle nur zur Information: Cell-Key und „–“ in kleinen Klassen
            # drücken die Gittersummen je Klasse (Kernfamilie −6,4 % schon gegen das eigene Insgesamt)
            for k in klassen:
                if k in gemeinde and gemeinde[k][0]:
                    gk = gemeinde[k][0]
                    print(f"          Klasse {k:<12} Gitter {zahl(s[k]):>8}  Gemeinde {zahl(gk):>8}  "
                          f"({100 * (s[k] - gk) / gk:+.1f} %)")
    if gemeinde:
        fehlen = [ges for _, ges, _ in THEMEN.values() if ges not in gemeinde]
        pruef(not fehlen, "Gemeindeergebnis deckt alle sechs Zählthemen ab"
              + (f" (fehlt: {', '.join(fehlen)})" if fehlen else ""))
        h = hashlib.sha256(GEMEINDE.read_bytes()).hexdigest()
        herkunft = GEMEINDE.with_name("HERKUNFT.md")
        pruef(herkunft.exists() and h in herkunft.read_text(encoding="utf-8"),
              f"{GEMEINDE.name}: SHA256 wie in eingang/HERKUNFT.md ({h[:12]}…)")
    else:
        print("        Hinweis: Zensus-Gemeindeergebnis Potsdam fehlt "
              "($KIEZ_DATEN/eingang/zensus2022_gemeinde_potsdam.csv nicht vorhanden). "
              "Bezugswerte oben stammen aus demselben Zensus (Gitter), nicht aus der Gemeindetabelle.")
    m = sql(f"""SELECT round(sum(miete_qm * ew) / nullif(sum(ew) FILTER (WHERE miete_qm IS NOT NULL), 0), 2),
                       round(sum(wfl_je_bew * ew) / nullif(sum(ew) FILTER (WHERE wfl_je_bew IS NOT NULL), 0), 1),
                       count(*) FILTER (WHERE geaendert LIKE '%miete_qm:unsicher%'),
                       count(*) FILTER (WHERE geaendert LIKE '%leer_quote:unsicher%'),
                       count(*) FILTER (WHERE leer_quote IS NOT NULL),
                       count(*) FILTER (WHERE miete_qm IS NOT NULL)
                FROM {POTSDAM} p""")[0]
    print(f"        Mittelwerte (nach Einwohnern gewichtet, nur Orientierung): Nettokaltmiete {m[0]} €/m² "
          f"({m[5]} Zellen, davon {m[2]} „unsicher“), Wohnfläche {m[1]} m² je Bewohner; "
          f"Leerstandsquote in {m[4]} Zellen, davon {m[3]} „unsicher“")


def geheimhaltung() -> None:
    print("5. Geheimhaltung: keine Strukturfelder in daten/")
    felder = [f for _, g, ks in THEMEN.values() for f in [g, *ks]] + list(MITTEL.values()) + \
        ["st_eu27", "st_europa", "st_welt", "st_sonst", "geaendert"]
    muster = re.compile(r"[\"']?\b(" + "|".join(sorted(set(felder) - {"geaendert"})) + r")\b[\"']?\s*:")
    treffer = [str(p.relative_to(WURZEL)) for p in (WURZEL / "daten").rglob("*")
               if p.is_file() and p.suffix in {".js", ".json", ".csv", ".geojson", ".gpkg"}
               and "schema" not in p.parts and "fixtures" not in p.parts
               and muster.search(p.read_text(encoding="utf-8", errors="replace"))]
    pruef(not treffer, f"keine daten/-Datei mit Feldern aus zensus_struktur ({', '.join(treffer) or 'keine Treffer'})")


def git(*args: str) -> list[str]:
    # -z: Dateinamen mit Leerzeichen oder Umlauten kommen roh, nicht in Anführungszeichen
    aus = subprocess.run(["git", "-C", str(WURZEL), *args, "-z"],  # noqa: S603,S607
                         capture_output=True, text=True, check=True).stdout
    return [n for n in aus.split("\0") if n]


def paketgrenze(basis: str) -> None:
    bereich = ".." in basis
    if bereich:
        # „a..b“ wäre bei git diff Spitze gegen Spitze; gemeint ist ab dem gemeinsamen Vorfahren („a...b“)
        von, bis = basis.replace("...", "..").split("..", 1)
        rng = f"{von}...{bis}"
        print(f"6. Paketgrenze (git diff {rng}: nur die Commits von {bis}, ohne offenen Stand)")
        namen = git("diff", "--name-only", rng)
        neu: list[str] = []
    else:
        print(f"6. Paketgrenze (git diff gegen {basis}, eingecheckt und offen)")
        namen = git("diff", "--name-only", basis)
        neu = git("ls-files", "--others", "--exclude-standard")
    erlaubt = list(A1_PFADE)
    if basis == NACHLAUF_BASIS:
        erlaubt += [p for ps in NACHLAUF_PFADE.values() for p in ps]
        print(f"        Nachlauf: erlaubt sind A1 und {', '.join(NACHLAUF_PFADE)} (NACHLAUF_PFADE)")
    alle = sorted(set(namen) | set(neu))
    fremd = [n for n in alle if not any(re.fullmatch(p, n) for p in erlaubt)]
    print(f"        geändert/neu: {', '.join(alle) or '–'}")
    pruef(not fremd, f"nur erlaubte Dateien berührt ({', '.join(fremd) or 'keine fremden'})")


def planungsraeume() -> None:
    print("7. Planungsräume")
    n, = sql("SELECT count(*) FROM planungsraum")[0]
    if n == "0":
        print("        public.planungsraum ist leer (H1 fehlt); A6 aggregiert bis dahin auf die 32 Stadtteile.")
        return
    for nr, name, zellen, ew, i_ges, hh in sql("""
            SELECT p.nr, p.name, count(s.*), coalesce(sum(z.ew), 0), coalesce(sum(s.i_ges), 0),
                   coalesce(sum(s.hh_ges), 0)
            FROM planungsraum p LEFT JOIN zensus_struktur s ON ST_Contains(p.geom, s.geom)
            LEFT JOIN zensus_zelle z USING (gitter_id) GROUP BY 1, 2 ORDER BY 1"""):
        print(f"        PR {nr} {name}: {zellen} Zellen, {zahl(int(ew))} EW, "
              f"{zahl(int(i_ges))} Personen (Altersgruppen), {zahl(int(hh))} Haushalte")


def main() -> int:
    basis = sys.argv[sys.argv.index("--basis") + 1] if "--basis" in sys.argv else NACHLAUF_BASIS
    rohdaten()
    schluessel()
    abdeckung()
    summen()
    geheimhaltung()
    paketgrenze(basis)
    planungsraeume()
    if hinweise:
        print("\nHinweise (kein Befund):\n  - " + "\n  - ".join(hinweise))
    print(f"\n{len(befunde)} Befund(e)" + ("" if not befunde else ":\n  - " + "\n  - ".join(befunde)))
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
