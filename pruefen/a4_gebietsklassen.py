"""Gegenprobe A4 (Nachlauf N2): NVP-Gebietsklasse je statistischem Bezirk und Stadtteil, Soll-Ist je Haltestelle.

Liest config/richtwerte.yaml (oepnv.gebietsklassen) und $KIEZ_DATEN/eingang/statistische-bezirke-in-potsdam.geojson
(Handdownload H1, LHP, Stand 31.12.2021, dl-de/by-2-0). Rechnet nur mit SELECT (Leserolle, keine Tabelle, kein DDL):
die Bezirksgrenzen gehen als Parameter in die Abfrage. Kein Netz, schreibt nichts.

Prüft (jede Zeile ein Befund, Rückgabe 1 bei mindestens einem):
  1. SHA256 der GeoJSON wie in eingang/HERKUNFT.md; 86 Bezirke
  2. jeder Bezirk liegt zu ≥ 99 % seiner Fläche in genau einem Stadtteil, und das ist der mit seinen ersten zwei Ziffern
  3. jeder Bezirk der Stadtteile mit `bezirke_geprueft` hat einen Eintrag in statistische_bezirke, und jeder Eintrag
     gehört zu einem solchen Stadtteil
  4. Klasse je Eintrag passt zu Tab. 4.1: klasse = Klasse des NVP-Ortsteils; bei klasse null steht die Klasse aus
     Tab. 4.1 in `moeglich` (Waldstadt I) bzw. der Ortsteil hat keine Klasse (Wildpark)
  5. jede Anker-Haltestelle liegt in ihrem Bezirk (auswertung.haltestelle, Name ohne „Potsdam, “)
  6. Stadtteil: klasse gesetzt genau dann, wenn alle bewohnten Bezirke (Zensus 2022, Zellmittelpunkt) dieselbe Klasse
     haben, und dann diese; anteil_ew_prozent = Einwohneranteile je Klasse (± 1 Prozentpunkt)
Berichtet ohne Befund:
  - Einwohner ohne Klasse je Stadtteil, wenn die Klasse aus dem Stadtteil (A6 heute) bzw. aus dem Bezirk käme
  - Soll-Ist je Potsdamer Haltestelle in diesen Stadtteilen: Fahrten HVZ (A4, Stichtag) gegen die Untergrenze der
    Tab. 4.3 für die Gebietsklasse des Bezirks. Die Taktklasse je Haltestelle hängt nicht von der Gebietsklasse ab.

Einwohnerzahlen je Bezirk erscheinen nur auf 10 gerundet und erst ab 100 (sonst „< 100“).

Aufruf (Rolle mosidi_lesen oder kiezatlas_rechnen, psycopg und PyYAML aus der Pipeline-Umgebung):
    set -a; . ../kiezatlas-potsdam/.env; set +a
    PGHOST=127.0.0.1 PGPORT=55461 PGDATABASE=kiezatlas PGUSER=mosidi_lesen PGPASSWORD="$LESE_PASSWORD" \
    uv run -q --no-project --offline --with-requirements ../geodaten-import-pipeline/requirements.txt \
        python -I pruefen/a4_gebietsklassen.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import psycopg
import yaml

WURZEL = Path(__file__).resolve().parent.parent
DATEN = Path(os.environ.get("KIEZ_DATEN") or WURZEL.parent / "kiezatlas-daten")
GEOJSON = DATEN / "eingang" / "statistische-bezirke-in-potsdam.geojson"
RANG = {"I": 3, "II": 2, "III": 1}
befunde: list[str] = []


def pruef(ok: bool, text: str) -> None:
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        befunde.append(text)


def ew_text(n: int) -> str:
    return "0" if not n else "< 100" if n < 100 else f"{round(n, -1):,}".replace(",", ".")


def main() -> int:
    gk = yaml.safe_load((WURZEL / "config" / "richtwerte.yaml").read_text(encoding="utf-8"))["oepnv"]
    gkl = gk["gebietsklassen"]
    tab = {o: k for k, os_ in gkl["nvp_ortsteile"].items() if k in RANG for o in os_}
    ohne_klasse = set(gkl["nvp_ortsteile"].get("ohne_klasse") or [])
    sb = {str(k): v for k, v in gkl["statistische_bezirke"].items()}
    st_yaml = {str(k): v for k, v in gkl["stadtteile"].items()}
    geprueft = {nr for nr, v in st_yaml.items() if v.get("bezirke_geprueft")}

    print("1. Eingang")
    print("        Statistische Bezirke © Landeshauptstadt Potsdam, Stand 31.12.2021; Einwohner © Statistische Ämter "
          "des Bundes und der Länder, Zensus 2022; beide dl-de/by-2-0 (https://www.govdata.de/dl-de/by-2-0), "
          "Daten verändert (eigene Berechnung). Haltestellen: VBB, CC BY 4.0.")
    roh = GEOJSON.read_bytes()
    h = hashlib.sha256(roh).hexdigest()
    herkunft = (GEOJSON.parent / "HERKUNFT.md").read_text(encoding="utf-8")
    pruef(h in herkunft, f"{GEOJSON.name}: SHA256 wie in eingang/HERKUNFT.md ({h[:12]}…)")
    feat = json.loads(roh)["features"]
    pruef(len(feat) == 86, f"{len(feat)} statistische Bezirke (Erwartung 86)")
    nrs = [str(f["properties"]["stb"]) for f in feat]
    namen = {str(f["properties"]["stb"]): f["properties"]["bezeichnun"] for f in feat}
    geoms = [json.dumps(f["geometry"]) for f in feat]

    with psycopg.connect() as db:
        b_cte = ("WITH b AS (SELECT stb, ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(g), 4326), 25833) geom "
                 "FROM unnest(%s::text[], %s::text[]) AS t(stb, g))")
        lage = {stb: (st, float(anteil)) for stb, st, anteil in db.execute(
            b_cte + """, s AS (SELECT nr::text nr, ST_Transform(geom, 25833) geom FROM public.stadtteil)
                SELECT DISTINCT ON (b.stb) b.stb, s.nr, ST_Area(ST_Intersection(b.geom, s.geom)) / ST_Area(b.geom)
                FROM b JOIN s ON ST_Intersects(b.geom, s.geom) ORDER BY b.stb, 3 DESC""", (nrs, geoms))}
        ew = defaultdict(int, {stb: int(n) for stb, n in db.execute(
            b_cte + """ SELECT b.stb, sum(z.ew) FROM b JOIN public.zensus_zelle z
                ON z.ew > 0 AND ST_Contains(b.geom, ST_Centroid(ST_Transform(z.geom, 25833))) GROUP BY 1""",
            (nrs, geoms))})
        hs_in = defaultdict(list)
        for stb, sid, name, vm, f, in_p in db.execute(
                b_cte + """ SELECT b.stb, h.stop_id, h.name, h.verkehrsmittel, h.fahrten_hvz_je_richtung, h.in_potsdam
                FROM b JOIN auswertung.haltestelle h ON ST_Contains(b.geom, h.geom) ORDER BY h.name""",
                (nrs, geoms)):
            hs_in[stb].append((sid, name.removeprefix("Potsdam, "), vm, float(f), in_p))
        ew_ohne_bezirk = db.execute(
            b_cte + """ SELECT coalesce(sum(z.ew), 0) FROM public.zensus_zelle z WHERE z.ew > 0
                AND EXISTS (SELECT 1 FROM public.stadtteil s WHERE ST_Contains(s.geom, z.geom))
                AND NOT EXISTS (SELECT 1 FROM b WHERE ST_Contains(b.geom, ST_Centroid(ST_Transform(z.geom, 25833))))""",
            (nrs, geoms)).fetchone()[0]

    print("2. Bezirke liegen in Stadtteilen")
    schlecht = [f"{n} ({lage.get(n)})" for n in nrs if n not in lage or lage[n][1] < 0.99 or lage[n][0] != n[:2]]
    pruef(not schlecht, "alle 86 Bezirke zu ≥ 99 % in dem Stadtteil ihrer ersten zwei Ziffern"
          + (f" ({', '.join(schlecht)})" if schlecht else ""))
    print(f"        Einwohner (Zensus 2022) in Potsdam außerhalb jedes Bezirks: {ew_ohne_bezirk}")

    print(f"3. Einträge für die Stadtteile {', '.join(sorted(geprueft))}")
    soll = {n for n in nrs if n[:2] in geprueft}
    pruef(soll == set(sb), "statistische_bezirke deckt genau deren Bezirke ab"
          + (f" (fehlen {sorted(soll - set(sb))}, zu viel {sorted(set(sb) - soll)})" if soll != set(sb) else ""))
    falsch_name = [n for n in sb if n in namen and sb[n].get("name") != namen[n]]
    pruef(not falsch_name, f"Bezirksnamen wie in der GeoJSON ({', '.join(falsch_name) or 'ja'})")

    print("4. Klasse je Bezirk gegen Tab. 4.1")
    for n, e in sorted(sb.items()):
        ots = e["nvp"] if isinstance(e["nvp"], list) else [e["nvp"]]
        unbekannt = [o for o in ots if o not in tab and o not in ohne_klasse]
        tab_kl = {tab[o] for o in ots if o in tab}
        if unbekannt:
            pruef(False, f"{n}: NVP-Ortsteil {unbekannt} nicht in Tab. 4.1")
        elif e.get("klasse"):
            pruef(tab_kl == {e["klasse"]},
                  f"{n} {e['name']}: {e['klasse']} = Tab. 4.1 {sorted(tab_kl)} ({'/'.join(ots)})")
        elif e.get("moeglich"):
            pruef(tab_kl <= set(e["moeglich"]) and len(e["moeglich"]) > 1,
                  f"{n} {e['name']}: nicht eindeutig, möglich {e['moeglich']} (Tab. 4.1: {sorted(tab_kl)})")
        else:
            pruef(all(o in ohne_klasse for o in ots), f"{n} {e['name']}: ohne Klasse ({'/'.join(ots)} laut Tab. 4.1)")

    print("5. Anker-Haltestellen")
    for n, e in sorted(sb.items()):
        for a in e.get("anker") or []:
            treffer = [x for x in hs_in[n] if x[1] == a]
            pruef(bool(treffer), f"{n} {e['name']}: Haltestelle „{a}“ liegt im Bezirk")

    print("6. Stadtteile")
    for st in sorted(geprueft):
        teile = sorted(n for n in sb if n[:2] == st)
        bewohnt = [n for n in teile if ew[n] > 0]
        klassen = {sb[n].get("klasse") for n in bewohnt}
        eindeutig = next(iter(klassen)) if len(klassen) == 1 and None not in klassen else None
        e = st_yaml[st]
        gesamt = sum(ew[n] for n in teile)
        je = defaultdict(int)
        for n in teile:
            k = sb[n].get("klasse") or ("/".join(sb[n]["moeglich"]) if sb[n].get("moeglich") else "ohne")
            je[k] += ew[n]
        anteil = {k: round(100 * v / gesamt) for k, v in je.items() if v} if gesamt else {}
        zeilen = [f"{n} {sb[n]['name']} → {sb[n].get('klasse') or sb[n].get('moeglich') or '–'} ({ew_text(ew[n])} EW)"
                  for n in teile]
        print(f"        {st}: " + "; ".join(zeilen))
        pruef(e.get("klasse") == eindeutig,
              f"Stadtteil {st}: klasse {e.get('klasse')} (aus den Bezirken: {eindeutig or 'nicht eindeutig'})")
        ya = {str(k): v for k, v in (e.get("anteil_ew_prozent") or {}).items()}
        pruef(set(ya) == set(anteil) and all(abs(ya[k] - anteil[k]) <= 1 for k in anteil),
              f"Stadtteil {st}: anteil_ew_prozent {ya} = berechnet {anteil}")

    print("\nEinwohner ohne eindeutige Gebietsklasse (Information für A6, oepnv_je_zelle):")
    ges_st = ges_bz = 0
    for st in sorted(geprueft):
        teile = [n for n in sb if n[:2] == st]
        alle = sum(ew[n] for n in teile)
        ohne_st = 0 if st_yaml[st].get("klasse") else alle
        ohne_bz = sum(ew[n] for n in teile if not sb[n].get("klasse"))
        ges_st, ges_bz = ges_st + ohne_st, ges_bz + ohne_bz
        print(f"        {st}: Klasse je Stadtteil {ew_text(ohne_st)}, je Bezirk {ew_text(ohne_bz)} von {ew_text(alle)}")
    print(f"        zusammen: je Stadtteil {ew_text(ges_st)}, je Bezirk {ew_text(ges_bz)}")

    print("\nSoll-Ist je Potsdamer Haltestelle (Fahrten je Stunde und Richtung, HVZ, Stichtag "
          f"{gk['messung']['stichtag']}, gegen die Untergrenze der Tab. 4.3 für die Klasse des Bezirks):")
    unter = gesamt_hs = 0

    def soll_min(klasse: str) -> float:
        return float(gk["taktklassen"][klasse]["fahrten_hvz_je_richtung_min"])

    for n, e in sorted(sb.items()):
        k = e.get("klasse")
        for _sid, name, vm, f, in_p in hs_in[n]:
            if not in_p:
                continue
            if not k:
                moegl = e.get("moeglich") or []
                txt = ", ".join(f"Soll {m} ≥ {soll_min(m):g} " + ("erfüllt" if f >= soll_min(m) else "unter")
                                for m in moegl)
                print(f"        {n} {name:<42} {vm:<14} {f:5.1f}  Klasse offen{': ' + txt if txt else ''}")
                continue
            soll_f = soll_min(k)
            gesamt_hs += 1
            ok = f >= soll_f
            unter += not ok
            urteil = "erfüllt" if ok else "UNTER SOLL"
            print(f"        {n} {name:<42} {vm:<14} {f:5.1f}  Soll {k} ≥ {soll_f:g}  {urteil}")
    print(f"        {gesamt_hs} Haltestellen mit Klasse, davon {unter} unter dem Soll")

    print(f"\n{len(befunde)} Befund(e)" + ("" if not befunde else ":\n  - " + "\n  - ".join(befunde)))
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
