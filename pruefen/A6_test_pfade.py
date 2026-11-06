"""Test der Codepfade von skripte/15_planer.py, die mit dem heutigen Datenstand nicht laufen (Paket A6).

Ohne Datenbank und ohne Netz: kleine erfundene Eingaben (klar unecht) für
  - Fußweg-Dateien (planer_fuss_odbl.js, erreichbar_fuss_odbl.js) und einrichtungen_odbl.js (wartet auf A3/A5b)
  - Geheimhaltung (Raumeinheit unter 100 EW), Mindestgröße der Zielgruppe
  - Prognose-Spalte aus $KIEZ_DATEN/eingang/prognose_planungsraum.csv (H11)
  - Raumebene planungsraum (H1)
  - strittige Lage einer Schule (N4), Vermerk statistische Bezirke (N2), VBB-Quelle im Fußweg (N1)
Die erzeugten Dateien landen in einem Temp-Ordner und laufen durch die Prüfregeln von pruefen/daten.py
(Vertrag, ODbL-Kopf, keine OSM-Spur außerhalb _odbl, keine Adressen, keine feinen Klassen).

Aufruf: python -I pruefen/A6_test_pfade.py   Rückgabe 0 = alle Tests bestanden.
"""

from __future__ import annotations

import copy
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
        # Seit Nachlauf N1/N4 (05.11.) hat der Fußweg einen eigenen Randhinweis (nach der Luftlinie gezählt, beim
        # Fußweg können es mehr sein); verboten bleibt der Luftlinien-Wortlaut am Fußweg
        ok("die Entfernung nur eine Obergrenze" not in kf["unsicherheit"]
           and "der Fußweg nur eine Obergrenze" in kf["unsicherheit"] and "gezählt nach der Luftlinie" in kf["unsicherheit"],
           "kein Luftlinien-Randhinweis am Fußweg, sondern der eigene Fußweg-Hinweis")

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

        # Strittige Lage (N4, Pestalozza-Fall): Ortsangabe widerspricht den Koordinaten
        ds = beispiel()
        ds["ort_abweichung"] = [{"id": "s1", "name": "Beispiel-Schule (unecht)", "ot": "Ort X", "stadtteil": "Ort Y",
                                 "raum": "A", "raum_ot": "B"}]
        ds["ziel"] = {"luftlinie": defaultdict(dict), "fussweg": defaultdict(dict)}
        for m_ in ("luftlinie", "fussweg"):
            for g in ids:
                ds["ziel"][m_]["grundschule"][g] = "s1" if g in ids[:2] else "s9"
                ds["ziel"][m_]["kita"][g] = "k1"

        class CurS:
            def execute(self, sql, par=None):
                self.par = par

            def fetchall(self):
                return [(g, 900.0) for g in self.par[2]]   # neue Luftlinie ohne s1

        alt_fuss = p.fussweg_ohne
        try:
            p.fussweg_ohne = lambda cur, art, aus: {g: 1000.0 for g in ids}
            ms: list[str] = []
            p.strittig_neu_rechnen(CurS(), ds, ms)
            ok(
                [ds["erreichbar"]["luftlinie"]["grundschule"][g] for g in ids] == [900.0, 900.0, 1100.0, 1350.0]
                and [ds["erreichbar"]["fussweg"]["grundschule"][g] for g in ids] == [1000.0, 1000.0, 1400.0, 1700.0]
                and ds["erreichbar"]["luftlinie"]["kita"][ids[0]] == 200,
                "strittige Lage: nur Zellen mit dem strittigen Ziel neu, andere Arten und Zellen unverändert",
            )
            ok(ds["strittig"]["grundschule"]["luftlinie"] == 2 and ms, "strittige Lage: Zahl der Zellen gemeldet")
            p.fussweg_ohne = lambda cur, art, aus: {g: 100.0 for g in ids}
            try:
                p.strittig_neu_rechnen(CurS(), ds, [])
                abbruch = ""
            except SystemExit as e:
                abbruch = str(e)
            ok("Fußweg < Luftlinie" in abbruch, "strittige Lage: Fußweg unter der Luftlinie bricht ab")
        finally:
            p.fussweg_ohne = alt_fuss
        ES = p.einrichtungen_datei(ds)
        hin = {f["properties"]["id"]: f["properties"].get("hinweis") for f in ES["features"]}
        ok(hin["s1"] and "strittig" in hin["s1"] and not hin["k1"], "einrichtungen.js: Hinweis nur am strittigen Punkt")
        ER = p.erreichbar_datei(ds, rw, "luftlinie", ids)
        ok("Beispiel-Schule (unecht) (MBJS s1) zählt nicht als Ziel" in ER["hinweis"], "erreichbar.js nennt den Punkt")
        PS = p.planer_datei(ds, rw, "luftlinie", {}, {}, [])
        gs = [w for nr in ("A", "B") for w in PS["raeume"][nr]["werte"] if (w["kennzahl"], w["art"]) in p.GS_KENNZAHLEN]
        ok(gs and all(w["wert"] is None and "ohne diesen Standort" in w["unsicherheit"] for w in gs),
           "Grundschulwerte in beiden betroffenen Raumeinheiten gesperrt, mit Hinweis")
        # Vermerk statistische Bezirke (N2): Stadtteilklasse über die Bezirke bestimmt
        rw_b = copy.deepcopy(rw)
        rw_b["oepnv"]["gebietsklassen"]["stadtteile"]["A"] = {"klasse": "II", "zuordnung": "bezirke"}
        PB = p.planer_datei(beispiel(), rw_b, "luftlinie", {}, {}, [])
        ub = next(w for w in PB["raeume"]["A"]["werte"] if w["kennzahl"] == "oepnv_erschliessung")
        ok("statbezirk" in PB["quellen"] and "statistischen Bezirke" in ub["unsicherheit"]
           and "statbezirk" not in PL["quellen"], "Vermerk statistische Bezirke nur, wenn eine Klasse daraus stammt")
        dh = beispiel()
        dh["erreichbar"]["fussweg"]["haltestelle"] = {g: 300.0 for g in ids}
        ok("vbb" in p.erreichbar_datei(dh, rw, "fussweg", ids)["quellen"] and "vbb" not in EF["quellen"],
           "Fußweg mit Haltestellen nennt die VBB-Quelle (N1)")

        # Audit 06.11.2026 (K4, K14, K24, K27, K28, K32)
        dk = beispiel()
        dk["einrichtungen"].append({**dk["einrichtungen"][2], "id": "p1", "art": "sek1", "unterart": "G/S",
                                    "name": "Beispiel-Oberschule mit Primarstufe (unecht)", "schueler": 400})
        dk["einrichtungen"].append({**dk["einrichtungen"][0], "id": "k1#haus2", "plaetze": None, "raum": "B"})
        dk["ziel"] = {"luftlinie": defaultdict(dict), "fussweg": defaultdict(dict)}

        class CurP:
            def execute(self, sql, par=None):
                self.par = par

            def fetchall(self):
                return [(g, 100.0, "p1") for g in self.par[1]]   # Schule mit Primarstufe 100 m von jeder Zelle

        alt_zu = p.fussweg_zu
        try:
            p.fussweg_zu = lambda cur, wo, par, art: {g: 150.0 for g in ids}
            mp: list[str] = []
            p.primarstufe_einrechnen(CurP(), dk, rw, mp)
        finally:
            p.fussweg_zu = alt_zu
        ok([dk["erreichbar"]["luftlinie"]["grundschule"][g] for g in ids] == [100.0] * 4
           and [dk["erreichbar"]["fussweg"]["grundschule"][g] for g in ids] == [150.0] * 4
           and dk["erreichbar"]["luftlinie"]["kita"][ids[0]] == 200 and mp and "p1" in mp[0],
           "K4: Schule mit Primarstufe als Grundschulziel, je Zelle das nähere Ziel, andere Arten unverändert")
        PK = p.planer_datei(dk, rw, "luftlinie", {}, {}, [])
        AK = {(w["kennzahl"], w["art"]): w for w in PK["raeume"]["A"]["werte"]}
        sk = AK[("schueler_je_kind", "grundschule")]
        ok(sk["wert"] is None and sk["zaehler"] is None
           and sk["unsicherheit"].startswith("Schule mit Primarstufe im Raum, Schülerzahl nicht nach Stufe teilbar")
           and "Betriebserlaubnis" not in sk["unsicherheit"] and "wie oben" not in sk["unsicherheit"]
           and sk["status"] == "orientierung",
           "K4: Grundschüler je Kind ohne Wert mit Grund im ersten Satz, ohne Kita-Bausteine, Status Orientierung")
        ok(AK[("ew_je_einrichtung", "grundschule")]["nenner"] == 2
           and "mit Primarstufe" in AK[("ew_je_einrichtung", "grundschule")]["unsicherheit"],
           "K4: Einwohner je Grundschulstandort zählt die Schule mit Primarstufe mit")
        pb = AK[("plaetze_je_bedarf", "kita")]
        ok(pb["status"] == "orientierung" and "Abweichend von Nr. 3.4.4" in pb["unsicherheit"],
           "K7: Plätze je Bedarfsplatz Orientierung mit Satz zu Nr. 3.4.4")
        ok("wie viele frei sind, steht nicht in den Daten" in pb["unsicherheit"]
           and "nicht belegte" not in json.dumps(PK, ensure_ascii=False), "K8: Wortlaut genehmigte Plätze")
        pk_ = AK[("plaetze_je_kind", "kita")]
        ok(pk_["zaehler"] == 30 and pk_["nenner"] == 30 and pk_["zaehler_text"] and pk_["nenner_text"]
           and pb["differenz"] == p.rund(70 - bedarf, 10) and pb["zaehler"] == 70 and pb["nenner"] == p.rund(bedarf, 10),
           "K14: Zähler, Nenner und Differenz (Plätze genau, Personen und Bedarf auf 10)")
        fein_Bk = [w for w in PK["raeume"]["B"]["werte"]
                   if "zaehler" in w and w["wert"] is None and w["kennzahl"] != "ew_je_einrichtung"]
        ok(fein_Bk and all(w["zaehler"] is None and w["nenner"] is None for w in fein_Bk)
           and PK["raeume"]["B"]["kinder"] is None and PK["raeume"]["A"]["kinder"] == {"u3": 20, "3_bis_5": 20,
                                                                                      "6_bis_unter_12": 30},
           "K14: ohne Wert keine Zähler und Nenner, Kinder je Raum nur ab der Mindestgröße")
        G = PK["gesamt"]
        gk = {(w["kennzahl"], w["art"]): w for w in G["werte"]}
        gp = gk[("plaetze_je_kind", "kita")]
        ok(G["name"] == "Potsdam" and gp["zaehler"] == 30 and "1 von 2 Raumeinheiten, ohne B" in gp["unsicherheit"]
           and gk[("schueler_je_kind", "grundschule")]["wert"] is None and G["kinder"] is None,
           "K24: gesamt aus veröffentlichten Zählern und Nennern, Raumeinheiten ohne Wert genannt")
        ok("Häuser in den Raumeinheiten A und B" in pb["unsicherheit"]
           and "Häuser in den Raumeinheiten A und B" in
           next(w for w in PK["raeume"]["B"]["werte"] if w["kennzahl"] == "plaetze_je_bedarf")["unsicherheit"],
           "K27: Kita mit Häusern in zwei Raumeinheiten in beiden genannt")
        ok(set(PK["pruefwerte"]) == set(p.PRUEFWERTE) and PK["pruefwerte"]["osm_kita_vollstaendig"]["wert"] == 78.1,
           "K28: Prüfwerte aus den Belegen gelesen")
        ok(p.fahrplan_text(rw) == "Fahrplan für Dienstag, 10.11.2026 (Schultag), 6 bis 9 Uhr (GTFS gültig ab "
           "3.11.2026)", "K32: Fahrplantext aus config/richtwerte.yaml")

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
            ("einrichtungen.js", "KIEZ_EINRICHTUNGEN", ES, ""),
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
            (tmp / "h1" / "eingang" / p.H1_DATEI).write_text('{"features":[{"properties":{"pr":"101"}}]}')
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
            p.PR_CSV.write_text("nr;name;wkt\n999;Alt;POLYGON((13 52.4,13.1 52.4,13.1 52.5,13 52.4))\n")
            try:
                p.raumquelle(Cur())
                abbruch = ""
            except SystemExit as e:
                abbruch = str(e)
            ok("passt nicht" in abbruch, "CSV mit anderen Nummern als H1: Abbruch statt alter Grenzen")
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
