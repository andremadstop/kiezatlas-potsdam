"""Test der Codepfade von skripte/15_planer.py, die mit dem heutigen Datenstand nicht laufen (Paket A6).

Ohne Datenbank und ohne Netz: kleine erfundene Eingaben (klar unecht) für
  - Fußweg-Dateien (planer_fuss_odbl.js, erreichbar_fuss_odbl.js) und einrichtungen_odbl.js (wartet auf A3/A5b)
  - Geheimhaltung (Raumeinheit unter 100 EW), Mindestgröße der Zielgruppe
  - Prognose-Spalte aus $KIEZ_DATEN/eingang/prognose_planungsraum.csv (H11)
  - Raumebene planungsraum (H1)
Die erzeugten Dateien landen in einem Temp-Ordner und laufen durch die Prüfregeln von pruefen/daten.py
(Vertrag, ODbL-Kopf, keine OSM-Spur außerhalb _odbl, keine Adressen, keine feinen Klassen).

Aufruf: python -I pruefen/A6_test_pfade.py   Rückgabe 0 = alle Tests bestanden.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True  # kein __pycache__ beim Laden der Module per importlib
WURZEL = Path(__file__).resolve().parent.parent
fehler: list[str] = []


def laden(name: str, pfad: Path):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def ok(bed: bool, text: str) -> None:
    print(("  ok    " if bed else "  FEHLT ") + text)
    if not bed:
        fehler.append(text)


def beispiel(ebene: str = "stadtteil") -> dict:
    """Zwei Raumeinheiten: A mit 400 EW, B mit 50 EW (unter der Mindestgröße). Vier Zellen."""
    ids = [
        "CRS3035RES100mN1000000E1000000",
        "CRS3035RES100mN1000000E1000100",
        "CRS3035RES100mN1000100E1000000",
        "CRS3035RES100mN1000100E1000100",
    ]
    zellen = {
        ids[0]: {"raum": "A", "ew": 200, "x": 0.0, "y": 0.0},
        ids[1]: {"raum": "A", "ew": 200, "x": 100.0, "y": 0.0},
        ids[2]: {"raum": "B", "ew": 50, "x": 0.0, "y": 100.0},
        ids[3]: {"raum": "B", "ew": 0, "x": 100.0, "y": 100.0},
    }
    struktur = {
        ids[0]: {"raum": "A", "i_u3": 10, "i_3_5": 10, "i_6_9": 15, "i_10_15": 12},
        ids[1]: {"raum": "A", "i_u3": 5, "i_3_5": 5, "i_6_9": 10, "i_10_15": 6},
        ids[2]: {"raum": "B", "i_u3": 3, "i_3_5": 3, "i_6_9": 3, "i_10_15": 3},
    }
    err = {"luftlinie": defaultdict(dict), "fussweg": defaultdict(dict)}
    for i, g in enumerate(ids):
        for art, basis in (("kita", 300), ("grundschule", 800), ("gruen", 50), ("arzt", 400), ("supermarkt", 450)):
            err["fussweg"][art][g] = basis + 300 * i
        for art, basis in (("kita", 200), ("grundschule", 600), ("gruen", 40)):
            err["luftlinie"][art][g] = basis + 250 * i
    gruen = {
        "luftlinie": {(g, 500): 8.0 - i for i, g in enumerate(ids)},
        "fussweg": {(g, 500): 5.0 + i for i, g in enumerate(ids)},
    }
    ein = [
        {
            "id": "k1",
            "art": "kita",
            "unterart": "krippe_kindergarten",
            "name": "Beispiel-Kita (unecht)",
            "plaetze": 30,
            "schueler": None,
            "schueler_stand": None,
            "status": "kapazitaet",
            "in_potsdam": True,
            "quelle": "x",
            "lon": 13.0,
            "lat": 52.4,
            "raum": "A",
        },
        {
            "id": "k2",
            "art": "kita",
            "unterart": "krippe_kindergarten_hort",
            "name": "Beispiel-Kita 2 (unecht)",
            "plaetze": 40,
            "schueler": None,
            "schueler_stand": None,
            "status": "kapazitaet",
            "in_potsdam": True,
            "quelle": "x",
            "lon": 13.01,
            "lat": 52.4,
            "raum": "A",
        },
        {
            "id": "s1",
            "art": "grundschule",
            "unterart": "G",
            "name": "Beispiel-Schule (unecht)",
            "plaetze": None,
            "schueler": 30,
            "schueler_stand": "2022",
            "status": "kapazitaet",
            "in_potsdam": True,
            "quelle": "x",
            "lon": 13.02,
            "lat": 52.4,
            "raum": "A",
        },
    ]
    hs = [{"id": "h1", "vm": {"bus"}, "klasse": "II", "x": 0.0, "y": 50.0}]
    poi = [
        {"id": "node/1", "art": "arzt", "unterart": None, "lon": 13.0, "lat": 52.41},
        {"id": "node/2", "art": "supermarkt", "unterart": None, "lon": 13.01, "lat": 52.41},
    ]
    return {
        "raumebene": ebene,
        "raeume": {"A": "Raum A (unecht)", "B": "Raum B (unecht)"},
        "zellen": zellen,
        "zelle_stadtteil": {g: z["raum"] for g, z in zellen.items()},
        "struktur": struktur,
        "erreichbar": err,
        "gruen": gruen,
        "einrichtungen": ein,
        "haltestellen": hs,
        "osm_poi": poi,
        "_ids": ids,
    }


def main() -> int:
    import yaml

    p = laden("planer15", WURZEL / "skripte" / "15_planer.py")
    dp = laden("daten_pruefen", WURZEL / "pruefen" / "daten.py")
    rw = yaml.safe_load((WURZEL / "config" / "richtwerte.yaml").read_text(encoding="utf-8"))
    rw["oepnv"]["gebietsklassen"]["stadtteile"] = {
        "A": {"klasse": "II", "zuordnung": "eindeutig"},
        "B": {"klasse": None, "zuordnung": "gemischt", "teile": {"x": "I", "y": "III"}},
    }
    d = beispiel()
    ids = d["_ids"]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # Prognose-Datei (H11) im Format aus richtwerte.yaml
        (tmp / "eingang").mkdir()
        (tmp / "eingang" / "prognose_planungsraum.csv").write_text(
            "raum;raumebene;jahr;altersgruppe;personen;quelle\n"
            "A;stadtteil;2030;u3;12;Beispielprognose (unecht)\n"
            "A;stadtteil;2030;3_5;14;Beispielprognose (unecht)\n"
            "A;stadtteil;2035;u3;11;Beispielprognose (unecht)\n"
            "A;stadtteil;2035;3_5;13;Beispielprognose (unecht)\n"
            "A;stadtteil;2030;6_11;1.200;Beispielprognose (unecht)\n"
            "A;stadtteil;2030;6_11;34;Beispielprognose (unecht)\n"
            "A;planungsraum;2030;u3;999;Beispielprognose (unecht)\n"
            "A;stadtteil;2030;9_12;5\n",
            encoding="utf-8",
        )
        os.environ["KIEZ_DATEN"] = str(tmp)
        meld: list[str] = []
        prog = p.prognose_lesen(rw, "stadtteil", meld)
        ok(prog and prog["werte"]["A"]["u3"][2030] == 12, "Prognose gelesen, Zeile anderer Raumebene nicht addiert")
        ok(prog["werte"]["A"]["6_11"][2030] == 1234, "Tausenderpunkt gelesen, zwei Zeilen addiert (1.200 + 34)")
        ok(any("9_12" in m for m in meld), "unbekannte Altersgruppe gemeldet (Zeile ohne quelle)")
        ok(any("anderer raumebene" in m for m in meld), "Zeile mit anderer Raumebene gemeldet")
        # Randliste (A5a, nur Luftlinie): Zelle 3 von Raum A mit Kita-Wert über 500 m
        rand = {(ids[1], "kita"): "berlin"}
        dr = beispiel()
        dr["erreichbar"]["luftlinie"]["kita"][ids[1]] = 650.0  # über 500 m: Wert ist nur Obergrenze
        dr["erreichbar"]["fussweg"]["kita"][ids[1]] = 700.0
        RL = p.planer_datei(dr, rw, "luftlinie", rand, prog, meld)
        RF = p.planer_datei(dr, rw, "fussweg", rand, prog, meld)
        kl = next(w for w in RL["raeume"]["A"]["werte"] if w["kennzahl"] == "anteil_in_radius" and w["art"] == "kita")
        kf = next(w for w in RF["raeume"]["A"]["werte"] if w["kennzahl"] == "anteil_in_radius" and w["art"] == "kita")
        ok("Obergrenze" in kl["unsicherheit"], "Randhinweis an der Luftlinie")
        ok("Obergrenze" not in kf["unsicherheit"], "kein Luftlinien-Randhinweis am Fußweg")

        PL = p.planer_datei(d, rw, "luftlinie", {}, prog, meld)
        PF = p.planer_datei(d, rw, "fussweg", {}, prog, meld)
        EF = p.erreichbar_datei(d, rw, "fussweg", ids)
        EO = p.einrichtungen_odbl_datei(d)
        ok(
            PF is not None and EF is not None and EO is not None,
            "Fußweg- und OSM-Dateien entstehen, wenn Daten da sind",
        )

        # Geheimhaltung: B hat 50 EW
        fein_B = [
            w for w in PL["raeume"]["B"]["werte"] if (w.get("zielgruppe") or "").startswith(("Kinder", "rechnerischer"))
        ]
        ok(fein_B and all(w["wert"] is None for w in fein_B), f"Raum B (50 EW): {len(fein_B)} Altersklassen-Werte null")
        ok(all("Geheimhaltung" in w["unsicherheit"] for w in fein_B), "Grund der Leerstelle im Hinweis")
        ew_B = [
            w
            for w in PL["raeume"]["B"]["werte"]
            if w.get("zielgruppe") == "Einwohner" and w["kennzahl"] == "anteil_in_radius"
        ]
        ok(ew_B and ew_B[0]["wert"] is not None, "Einwohner-Anteile bleiben auch in kleinen Raumeinheiten")
        # Kita-Relationen (Prüfbericht 9)
        A = {(w["kennzahl"], w["art"]): w for w in PL["raeume"]["A"]["werte"]}
        ok(
            A[("plaetze_je_kind", "kita")]["wert"] == round(30 / 30, 2),
            "Kita ohne Hortanteil: 30 Plätze / 30 Kinder unter 6",
        )
        ok(
            "Ohne 40 Plätze in 1 Einrichtung mit" in A[("plaetze_je_kind", "kita")]["unsicherheit"],
            "kombinierte Einrichtung benannt",
        )
        ok(A[("plaetze_je_kind", "hort")]["wert"] is None, "kein reiner Hort, nur kombinierte: Hortrelation null")
        bedarf = 0.75 * 15 + 1.0 * 15 + 0.70 * (25 + 18 * 0.3333)
        ok(
            abs(A[("plaetze_je_bedarf", "kita")]["wert"] - round(70 / bedarf, 2)) < 0.005,
            f"Bedarf nach Baulandmodell: 70 Plätze / {bedarf:.2f}",
        )
        ok(A[("schueler_je_kind", "grundschule")].get("vorlaeufig") is True, "Grundschule vorläufig")
        # ÖPNV: Klasse II, Bus 400 m, Haltestelle 50 m von Zelle 0 und rund 112 m von Zelle 1 → 100 %
        ok(A[("oepnv_erschliessung", "oepnv")]["wert"] == 100, "ÖPNV Klasse II: beide Zellen im 400-m-Radius")
        ok(
            PL["raeume"]["B"]["werte"]
            and next(w for w in PL["raeume"]["B"]["werte"] if w["kennzahl"] == "oepnv_erschliessung")["wert"] is None,
            "gemischte Gebietsklasse: wert null mit Spanne",
        )
        # Prognose angehängt
        pk = [w for w in PL["raeume"]["A"]["werte"] if w.get("prognose")]
        ok(
            pk and pk[0]["prognose"]["personen"] == {"2030": 26, "2035": 24},
            "Prognose 2030/2035 an Kinder-unter-6-Werten",
        )
        pg = [w for w in PL["raeume"]["A"]["werte"] if w.get("zielgruppe", "").startswith("Kinder 6 bis unter 12")]
        ok(pg and pg[0]["prognose"]["personen"] == {"2030": 1234}, "Prognose 6 bis unter 12 an der Grundschul-Relation")
        # Fußweg: Ärzte nur Entfernung
        arten_f = {(w["kennzahl"], w["art"]) for w in PF["raeume"]["A"]["werte"]}
        ok(
            ("entfernung_median", "arzt") in arten_f
            and not any(a == "arzt" and k != "entfernung_median" for k, a in arten_f),
            "Fußweg: Arzt nur als Entfernung (Korrektur 13)",
        )
        ok(
            all(w["methode"] == "fussweg" for _, r in PF["raeume"].items() for w in r["werte"]),
            "Fußweg-Datei nur methode fussweg",
        )
        ok("osm" in PF["quellen"] and "osm" not in PL["quellen"], "OSM-Quelle nur in der Fußweg-Datei")

        # Dateien schreiben und mit den Regeln von daten.py prüfen
        (tmp / "zellen.js").write_text(
            "window.KIEZ_ZELLEN=" + json.dumps({"features": [{"properties": {"id": g}} for g in ids]}) + ";",
            encoding="utf-8",
        )
        kontext = {"erste_id": ids[0], "letzte_id": ids[-1], "anzahl": len(ids)}
        liste = dp.schemas()
        vorher = len(dp.befunde)
        for name, var, inhalt, kopf in (
            ("planer.js", "KIEZ_PLANER", PL, ""),
            ("planer_fuss_odbl.js", "KIEZ_PLANER_FUSS", PF, p.ODBL_KOPF),
            ("erreichbar_fuss_odbl.js", "KIEZ_ERREICHBAR_FUSS", EF, p.ODBL_KOPF),
            ("einrichtungen_odbl.js", "KIEZ_EINRICHTUNGEN_ODBL", EO, p.ODBL_KOPF),
            ("erreichbar.js", "KIEZ_ERREICHBAR", p.erreichbar_datei(d, rw, "luftlinie", ids), ""),
        ):
            pfad = tmp / name
            p.js_schreiben(pfad, var, inhalt, kopf)
            dp.datei_pruefen(pfad, name, liste, kontext, fixture=False)
        ok(len(dp.befunde) == vorher, "alle Testdateien bestehen Vertrag und Lizenzgrenze aus daten.py")

        # ohne Fußweg-Daten: keine Datei
        d2 = beispiel()
        d2["erreichbar"]["fussweg"] = defaultdict(dict)
        d2["osm_poi"] = []
        ok(
            p.planer_datei(d2, rw, "fussweg", {}, {}, []) is None
            and p.erreichbar_datei(d2, rw, "fussweg", ids) is None
            and p.einrichtungen_odbl_datei(d2) is None,
            "leere OSM-Quelle: keine Fußweg- und OSM-Dateien",
        )
        # Raumebene planungsraum (H1)
        d3 = beispiel("planungsraum")
        P3 = p.planer_datei(d3, rw, "luftlinie", {}, {}, [])
        ok(
            P3["raumebene"] == "planungsraum" and "Planungsraum" in P3["hinweis"],
            "Raumebene planungsraum wird übernommen",
        )
        # ÖPNV auf Planungsräumen: Gebietsklasse je Zelle aus ihrem Stadtteil
        d3["zelle_stadtteil"] = {ids[0]: "A", ids[1]: "B", ids[2]: "B", ids[3]: "A"}
        P3 = p.planer_datei(d3, rw, "luftlinie", {}, {}, [])
        oe = {nr: {w["kennzahl"]: w for w in r["werte"] if w["art"] == "oepnv"} for nr, r in P3["raeume"].items()}
        ok(
            oe["A"]["oepnv_erschliessung"]["wert"] == 100 and "50 % der Einwohner" in oe["A"]["oepnv_erschliessung"][
                "unsicherheit"],
            "Planungsraum: Klasse je Zelle aus dem Stadtteil, gemischte Zellen (50 %) zählen nicht",
        )
        ub = oe["B"]["oepnv_erschliessung"]
        ut = oe["B"]["oepnv_takt"]
        ok(
            ub["wert"] is None and "100 bis 100 %" in ub["unsicherheit"] and ut["wert"] is None
            and "0 bis 100 %" in ut["unsicherheit"],
            "Planungsraum nur mit gemischter Klasse: kein Wert, Spanne über die möglichen Klassen",
        )
        # Quelle der Planungsräume: CSV aus 03_planungsraeume.py, solange public.planungsraum leer ist

        class Cur:
            def execute(self, *a):
                pass

            def fetchone(self):
                return (0,)

        alt, alt_daten = p.PR_CSV, os.environ.get("KIEZ_DATEN")
        try:
            p.PR_CSV = tmp / "planungsraeume.csv"
            os.environ["KIEZ_DATEN"] = str(tmp / "leer")
            ok(p.raumquelle(Cur())[0] == "stadtteil", "ohne H1, Tabelle und CSV: Stadtteile")
            (tmp / "h1" / "eingang").mkdir(parents=True)
            (tmp / "h1" / "eingang" / p.H1_DATEI).write_text("{}")
            os.environ["KIEZ_DATEN"] = str(tmp / "h1")
            try:
                p.raumquelle(Cur())
                abbruch = ""
            except SystemExit as e:
                abbruch = str(e)
            ok(
                "03_planungsraeume.py" in abbruch and "--nr-feld pr" in abbruch,
                "H1 im Eingang, aber weder Tabelle noch CSV: Abbruch mit Aufruf statt stiller Stadtteile",
            )
            p.PR_CSV.write_text("nr;name;wkt\n101;Beispiel;POLYGON((13 52.4,13.1 52.4,13.1 52.5,13 52.4))\n")
            ebene, tab, par, _ = p.raumquelle(Cur())
            ok(
                ebene == "planungsraum" and "unnest" in tab and par["pr_nr"] == ["101"],
                "leere Tabelle, CSV vorhanden: Planungsräume per SELECT über unnest",
            )
        finally:
            p.PR_CSV = alt
            if alt_daten is None:
                os.environ.pop("KIEZ_DATEN", None)
            else:
                os.environ["KIEZ_DATEN"] = alt_daten
    print(f"\n{len(fehler)} Fehler" if fehler else "\nalle Tests bestanden")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
