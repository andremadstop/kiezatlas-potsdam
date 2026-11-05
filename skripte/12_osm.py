"""A3: OSM-Einrichtungen und Fußwegnetz aus einer Hand-PBF (offline) nach auswertung.*.

Eingang: eine OpenStreetMap-PBF, von Andre von Hand geladen (H5: BBBike-Auszug Potsdam oder Geofabrik
Brandenburg), abgelegt unter $KIEZ_DATEN/osm/<stand>/ oder $KIEZ_DATEN/eingang/. Kein Netzabruf:
kein Overpass, kein osmnx-Download, kein Abruf bei Geofabrik oder BBBike.

Ausgang (Rolle kiezatlas_rechnen, nur eigene Tabellen laut Bauplan 0.4):
- auswertung.osm_poi    Ärzte, Apotheken, Supermärkte, Pflege, Spielplätze. Ohne Namen.
- auswertung.netz_knoten, auswertung.netz_kante   Fußwegnetz (jeder OSM-Knoten eines begehbaren Wegs
                        ist ein Netzknoten, jede Kante ein gerades Stück zwischen zwei Knoten, ungerichtet)
- berichte/A3_vollstaendigkeit.md   OSM-Kitas und -Schulen gegen MBJS, dazu die Netzkennzahlen

Lizenz: alles Abgeleitete steht unter ODbL 1.0, © OpenStreetMap-Mitwirkende. Veröffentlicht wird es nur in
Dateien mit _odbl im Namen (A6), nie in den dl-de-Dateien und nie in den Gebäudejahren (E1).

Ausschnitt: Umring der 32 Stadtteile plus 2 km (EPSG:25833). Gelesen wird ein Rechteck darum (plus Rand),
behalten werden Kanten und Einrichtungen, die den Puffer berühren.

Aufruf über skripte/12_osm.sh (Umgebung und Rolle wie skripte/lauf.sh):
    skripte/12_osm.sh laden --pbf $KIEZ_DATEN/osm/2026-11-xx/potsdam.osm.pbf
    skripte/12_osm.sh laden --pbf … --trockenlauf     (alles in einer Transaktion, am Ende ROLLBACK)
    skripte/12_osm.sh pruefen                          (Abnahme A3, pruefen/a3_pruefen.py)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import sys
import time
from pathlib import Path

import numpy as np

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "skripte"))   # eigener Code; python -I lässt das Skriptverzeichnis weg
import osm_pbf

PUFFER_M = 2000
RAND_GRAD = 0.01            # Leserechteck um den Puffer, damit Wege am Rand ihre Knoten behalten
DUBLETTE_M = 25             # Fläche und Punkt derselben Art näher als das: nur der Punkt bleibt
TREFFER_M = 150             # Vollständigkeitsbericht: MBJS-Standort hat OSM-Gegenstück in diesem Abstand
ODBL = "ODbL 1.0, © OpenStreetMap-Mitwirkende (https://opendatacommons.org/licenses/odbl/1-0/)"

# ------------------------------------------------------------------------------- Regeln (rein)

FUSS_JA = {"yes", "designated", "permissive", "official"}
# Nicht begehbar oder kein Weg. Wie das Netz „walk“ von osmnx, aber mit deutscher Lesart für Radwege
# (Zeichen 237: Fußgänger nur mit foot=yes/designated).
HIGHWAY_AUS = {
    "motorway", "motorway_link", "bus_guideway", "busway", "raceway", "construction", "proposed",
    "planned", "abandoned", "razed", "disused", "no", "platform", "corridor", "escape",
    "emergency_bay", "rest_area", "services",
}


def ist_fussweg(t: dict[str, str]) -> bool:
    """Ist ein OSM-Weg für Fußgänger begehbar?"""
    hw = t.get("highway")
    if not hw or hw in HIGHWAY_AUS:
        return False
    foot = t.get("foot")
    if foot in ("no", "use_sidepath", "private"):
        return False
    erlaubt = foot in FUSS_JA
    if hw == "cycleway" and not erlaubt:
        return False
    if t.get("motorroad") == "yes" and not erlaubt:
        return False
    if t.get("access") in ("no", "private") and not erlaubt:
        return False
    return not (t.get("service") == "private" and not erlaubt)


def poi_art(t: dict[str, str]) -> tuple[str, str | None] | None:
    """(art, unterart) für die Einrichtungen aus OSM, sonst None. Namen werden nie gelesen."""
    a = t.get("amenity")
    hc = t.get("healthcare")
    if a == "doctors" or (a is None and hc == "doctor"):
        sp = t.get("healthcare:speciality")
        return "arzt", (sp[:120] if sp else None)
    if a == "pharmacy" or (a is None and hc == "pharmacy"):
        return "apotheke", None
    shop = t.get("shop")
    if shop in ("supermarket", "convenience"):
        return "supermarkt", shop
    if a == "nursing_home":
        return "pflege", "nursing_home"
    if a == "social_facility":
        sf = t.get("social_facility")
        fuer = t.get("social_facility:for", "")
        if sf in ("nursing_home", "assisted_living") or (sf == "group_home" and "senior" in fuer):
            return "pflege", sf
        return None
    if t.get("leisure") == "playground":
        if t.get("access") in ("private", "no"):
            return None   # Spielplätze auf Kita- oder Hausgrundstücken
        return "spielplatz", None
    return None


def bildung_art(t: dict[str, str]) -> str | None:
    """Nur für den Vollständigkeitsbericht (nicht in osm_poi)."""
    a = t.get("amenity")
    if a == "kindergarten":
        return "kita"
    if a == "school":
        return "schule"
    return None


def ist_flaeche_relation(t: dict[str, str]) -> bool:
    return t.get("type") == "multipolygon" and (poi_art(t) is not None or bildung_art(t) is not None)


def netz_bauen(wege: list[tuple[int, dict, np.ndarray]], erg: osm_pbf.Ergebnis
               ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Kanten (von, nach) und Knoten (id, lon, lat) aus begehbaren Wegen.

    Jede Folge zweier Knoten eines Wegs wird eine ungerichtete Kante. Fehlt einem Knoten die Koordinate
    (außerhalb des Leserechtecks), entfallen die Kanten daran; der Weg zerfällt an der Stelle. Doppelte
    Kanten (zwei Wege über dieselben Knoten) und Schleifen (gleicher Knoten zweimal) entfallen.
    """
    teile_a, teile_b = [], []
    for _wid, _t, refs in wege:
        if refs.size < 2:
            continue
        _lon, _lat, ok = erg.koordinaten(refs)
        beide = ok[:-1] & ok[1:]
        a, b = refs[:-1][beide], refs[1:][beide]
        teile_a.append(a)
        teile_b.append(b)
    if not teile_a:
        leer = np.zeros(0, dtype=np.int64)
        return leer, leer.copy(), leer.copy(), np.zeros(0)
    a = np.concatenate(teile_a)
    b = np.concatenate(teile_b)
    keine_schleife = a != b
    a, b = a[keine_schleife], b[keine_schleife]
    von = np.minimum(a, b)
    nach = np.maximum(a, b)
    paare = np.unique(np.stack([von, nach], axis=1), axis=0)
    knoten = np.unique(paare.ravel())
    lon, lat, ok = erg.koordinaten(knoten)
    assert ok.all()
    return paare[:, 0], paare[:, 1], knoten, np.stack([lon, lat], axis=1)


def flaeche_wkt(lon: np.ndarray, lat: np.ndarray) -> str | None:
    """WKT für einen Weg: Polygon, wenn geschlossen und ≥ 4 Punkte, sonst Linie bzw. Punkt."""
    if lon.size == 0:
        return None
    pts = ", ".join(f"{x:.7f} {y:.7f}" for x, y in zip(lon, lat))
    if lon.size >= 4 and lon[0] == lon[-1] and lat[0] == lat[-1]:
        return f"POLYGON(({pts}))"
    if lon.size >= 2:
        return f"LINESTRING({pts})"
    return f"POINT({lon[0]:.7f} {lat[0]:.7f})"


def objekte_sammeln(erg: osm_pbf.Ergebnis) -> tuple[list[tuple], list[tuple]]:
    """(pois, bildung) als Zeilen (osm_id, art, unterart, wkt) bzw. (osm_id, art, wkt) in EPSG:4326."""
    pois: list[tuple] = []
    bildung: list[tuple] = []
    wege_nach_id = {wid: refs for wid, _t, refs in erg.wege}

    def ablegen(osm_id: str, t: dict, wkt: str | None) -> None:
        if not wkt:
            return
        p = poi_art(t)
        if p:
            pois.append((osm_id, p[0], p[1], wkt))
        b = bildung_art(t)
        if b:
            bildung.append((osm_id, b, wkt))

    for nid, lon, lat, t in erg.getaggte_knoten:
        ablegen(f"n{nid}", t, f"POINT({lon:.7f} {lat:.7f})")
    for wid, t, refs in erg.wege:
        if poi_art(t) is None and bildung_art(t) is None:
            continue
        lon, lat, ok = erg.koordinaten(refs)
        if not ok.any():
            continue
        if ok.all():
            ablegen(f"w{wid}", t, flaeche_wkt(lon, lat))
        else:   # am Rand abgeschnitten: Punktwolke der vorhandenen Knoten
            ablegen(f"w{wid}", t, "MULTIPOINT(" + ", ".join(
                f"({x:.7f} {y:.7f})" for x, y in zip(lon[ok], lat[ok])) + ")")
    for rid, t, mitglieder in erg.relationen:
        if not ist_flaeche_relation(t):
            continue
        punkte = []
        for typ, ref, rolle in mitglieder:
            if typ == "w" and rolle in ("outer", "") and ref in wege_nach_id:
                lon, lat, ok = erg.koordinaten(wege_nach_id[ref])
                punkte.extend(zip(lon[ok], lat[ok]))
        punkte = list(dict.fromkeys(punkte))   # Ringe schließen mit dem Anfangsknoten: doppelt nur einmal
        if punkte:
            ablegen(f"r{rid}", t, "MULTIPOINT(" + ", ".join(f"({x:.7f} {y:.7f})" for x, y in punkte) + ")")
    return pois, bildung


def lies_osm(pfad: Path, rechteck: tuple[float, float, float, float] | None) -> osm_pbf.Ergebnis:
    """Zwei Durchgänge: erst alles Nötige, dann (falls nötig) die Mitgliedswege der Flächenrelationen."""
    def weg_wahl(t: dict) -> bool:
        return ist_fussweg(t) or poi_art(t) is not None or bildung_art(t) is not None

    def knoten_wahl(t: dict) -> bool:
        return poi_art(t) is not None or bildung_art(t) is not None

    erg = osm_pbf.lies(pfad, rechteck=rechteck, knoten_wahl=knoten_wahl, weg_wahl=weg_wahl,
                       relation_wahl=ist_flaeche_relation)
    vorhanden = {wid for wid, _t, _r in erg.wege}
    fehlend = {ref for _rid, _t, m in erg.relationen for typ, ref, _ro in m if typ == "w"} - vorhanden
    if fehlend:
        zweit = osm_pbf.lies(pfad, rechteck=None, knoten_wahl=lambda t: False,
                             weg_wahl=lambda t: False, relation_wahl=lambda t: False,
                             knoten_lesen=False, weg_ids=fehlend)
        # Diese Wege gehören nicht ins Netz: mit Kennzeichen anhängen, netz_bauen filtert per ist_fussweg
        erg.wege.extend((wid, {"_nur_relation": "1"}, refs) for wid, _t, refs in zweit.wege)
    return erg


# ------------------------------------------------------------------------------- Herkunft

def sha256(pfad: Path) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for stueck in iter(lambda: f.read(1 << 20), b""):
            h.update(stueck)
    return h.hexdigest()


def herkunft_pruefen(pfad: Path, kopf: osm_pbf.Kopf | None, summe: str) -> str:
    """Legt HERKUNFT.md neben der PBF an, wenn sie fehlt (Felder zum Ergänzen markiert)."""
    hk = pfad.parent / "HERKUNFT.md"
    if hk.exists():
        if summe not in hk.read_text(encoding="utf-8"):
            print(f"Hinweis: SHA256 {summe} steht nicht in {hk}; bitte nachtragen.", file=sys.stderr)
        return "vorhanden"
    zeit = (dt.datetime.fromtimestamp(kopf.zeitstempel, dt.UTC).strftime("%Y-%m-%d %H:%M UTC")
            if kopf and kopf.zeitstempel else "nicht im Dateikopf")
    hk.write_text(
        f"# Herkunft: {pfad.name}\n\n"
        "- Quelle: OpenStreetMap, Handdownload durch Andre (H5). Bezugsadresse: **bitte eintragen** "
        "(BBBike-Auszug Potsdam oder Geofabrik Brandenburg)\n"
        "- Abrufdatum: **bitte eintragen**\n"
        "- Lizenz: Open Database License 1.0 (https://opendatacommons.org/licenses/odbl/1-0/), "
        "© OpenStreetMap-Mitwirkende\n"
        "- robots/Bedingungen: kein Agentenabruf (Bauplan 0.3: Geofabrik- und BBBike-Downloads automatisiert "
        "verboten); Handdownload im Browser\n"
        f"- Größe: {pfad.stat().st_size} Byte\n"
        f"- SHA256: {summe}\n"
        f"- Dateikopf: Programm {kopf.programm if kopf else '?'}, Datenstand (Replikation) {zeit}, "
        f"Rechteck {[kopf.links, kopf.unten, kopf.rechts, kopf.oben] if kopf else '?'}\n"
        f"- angelegt von skripte/12_osm.py am {dt.date.today().isoformat()}\n",
        encoding="utf-8")
    print(f"HERKUNFT.md angelegt: {hk} (Bezugsadresse und Abrufdatum ergänzen)", file=sys.stderr)
    return "angelegt"


# ------------------------------------------------------------------------------- Datenbank

def verbinden():
    import psycopg
    if os.environ.get("PGUSER") != "kiezatlas_rechnen":
        raise SystemExit("PGUSER muss kiezatlas_rechnen sein (skripte/12_osm.sh setzt das)")
    return psycopg.connect("")


PUFFER_SQL = f"""
CREATE TEMP TABLE a3_puffer ON COMMIT DROP AS
  SELECT ST_Subdivide(ST_Buffer(ST_Transform(ST_Union(geom), 25833), {PUFFER_M}), 128) AS geom FROM public.stadtteil;
CREATE INDEX ON a3_puffer USING gist (geom);
CREATE TEMP TABLE a3_stadt ON COMMIT DROP AS
  SELECT ST_Subdivide(ST_Transform(geom, 25833), 128) AS geom FROM public.stadtteil;
CREATE INDEX ON a3_stadt USING gist (geom);
"""


def leserechteck(cur) -> tuple[float, float, float, float]:
    cur.execute("SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) FROM ("
                "SELECT ST_Extent(ST_Transform(geom, 4326)) e FROM a3_puffer) x")
    w, s, o, n = cur.fetchone()
    return w - RAND_GRAD, s - RAND_GRAD, o + RAND_GRAD, n + RAND_GRAD


def schreiben(cur, kanten_von, kanten_nach, knoten, koords, pois, bildung) -> dict:
    cur.execute("CREATE TEMP TABLE a3_k (id bigint, lon float8, lat float8) ON COMMIT DROP")
    with cur.copy("COPY a3_k (id, lon, lat) FROM STDIN") as cp:
        for i, (x, y) in zip(knoten.tolist(), koords.tolist()):
            cp.write_row((i, x, y))
    cur.execute("CREATE TEMP TABLE a3_e (von bigint, nach bigint) ON COMMIT DROP")
    with cur.copy("COPY a3_e (von, nach) FROM STDIN") as cp:
        for a, b in zip(kanten_von.tolist(), kanten_nach.tolist()):
            cp.write_row((a, b))
    cur.execute("CREATE TEMP TABLE a3_p (osm_id text, art text, unterart text, wkt text) ON COMMIT DROP")
    with cur.copy("COPY a3_p (osm_id, art, unterart, wkt) FROM STDIN") as cp:
        for r in pois:
            cp.write_row(r)
    cur.execute("CREATE TEMP TABLE a3_b (osm_id text, art text, wkt text) ON COMMIT DROP")
    with cur.copy("COPY a3_b (osm_id, art, wkt) FROM STDIN") as cp:
        for r in bildung:
            cp.write_row(r)
    cur.execute("""
        ALTER TABLE a3_k ADD COLUMN geom geometry(Point, 25833);
        UPDATE a3_k SET geom = ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 25833);
        CREATE UNIQUE INDEX ON a3_k (id);
        CREATE TEMP TABLE a3_kante ON COMMIT DROP AS
          SELECT e.von, e.nach, ST_MakeLine(a.geom, b.geom)::geometry(LineString, 25833) AS geom
          FROM a3_e e JOIN a3_k a ON a.id = e.von JOIN a3_k b ON b.id = e.nach;
        CREATE INDEX ON a3_kante USING gist (geom);
        DELETE FROM a3_kante k WHERE NOT EXISTS (SELECT 1 FROM a3_puffer p WHERE ST_Intersects(p.geom, k.geom));
    """)
    cur.execute("TRUNCATE auswertung.netz_kante, auswertung.netz_knoten, auswertung.osm_poi")
    cur.execute("""
        INSERT INTO auswertung.netz_knoten (id, geom)
          SELECT k.id, k.geom FROM a3_k k
          WHERE k.id IN (SELECT von FROM a3_kante UNION SELECT nach FROM a3_kante);
        INSERT INTO auswertung.netz_kante (id, von, nach, laenge_m, geom)
          SELECT row_number() OVER (ORDER BY von, nach), von, nach, round(ST_Length(geom)::numeric, 2), geom
          FROM a3_kante;
    """)
    # Einrichtungen: Fläche -> Punkt auf der Fläche; Punktwolke (Relation, Randstück) -> Schwerpunkt
    cur.execute(f"""
        CREATE TEMP TABLE a3_poi ON COMMIT DROP AS
          SELECT osm_id, art, unterart,
                 ST_Transform(CASE WHEN GeometryType(g) = 'MULTIPOINT' THEN ST_Centroid(g)
                                   ELSE ST_PointOnSurface(ST_MakeValid(g)) END, 25833) AS geom
          FROM (SELECT osm_id, art, unterart, ST_SetSRID(ST_GeomFromText(wkt), 4326) g FROM a3_p) x;
        DELETE FROM a3_poi q WHERE NOT EXISTS (SELECT 1 FROM a3_puffer p WHERE ST_Intersects(p.geom, q.geom));
        -- Dublette: dieselbe Einrichtung als Punkt und als Fläche; der Punkt bleibt
        DELETE FROM a3_poi f WHERE left(f.osm_id, 1) IN ('w', 'r') AND EXISTS (
          SELECT 1 FROM a3_poi n WHERE left(n.osm_id, 1) = 'n' AND n.art = f.art
            AND ST_DWithin(n.geom, f.geom, {DUBLETTE_M}));
        INSERT INTO auswertung.osm_poi (osm_id, art, unterart, geom) SELECT osm_id, art, unterart, geom FROM a3_poi;
    """)
    cur.execute("""
        CREATE TEMP TABLE a3_bildung ON COMMIT DROP AS
          SELECT osm_id, art, ST_Transform(ST_MakeValid(ST_SetSRID(ST_GeomFromText(wkt), 4326)), 25833) AS geom
          FROM a3_b;
    """)
    cur.execute("SELECT art, count(*) FROM auswertung.osm_poi GROUP BY art ORDER BY art")
    je_art = dict(cur.fetchall())
    cur.execute("SELECT (SELECT count(*) FROM auswertung.netz_knoten), (SELECT count(*) FROM auswertung.netz_kante),"
                " (SELECT round(sum(laenge_m) / 1000) FROM auswertung.netz_kante)")
    nk, ne, km = cur.fetchone()
    return {"poi_je_art": je_art, "knoten": nk, "kanten": ne, "netz_km": km}


def vollstaendigkeit(cur) -> dict:
    """OSM-Kitas und -Schulen gegen MBJS im Stadtgebiet (Trefferquote je Richtung)."""
    erg = {}
    for art, tabelle, schluessel in (("kita", "public.mbjs_kita", "id_kita"),
                                     ("schule", "public.mbjs_schule", "schul_nr")):
        cur.execute(f"""
            WITH m AS (
              SELECT t.{schluessel} id, ST_Transform(t.geom, 25833) g FROM {tabelle} t
              WHERE EXISTS (SELECT 1 FROM a3_stadt s WHERE ST_Intersects(s.geom, ST_Transform(t.geom, 25833)))),
            o AS (
              SELECT b.osm_id, b.geom g FROM a3_bildung b
              WHERE b.art = %s AND EXISTS (SELECT 1 FROM a3_stadt s WHERE ST_Intersects(s.geom, b.geom)))
            SELECT (SELECT count(*) FROM m),
                   (SELECT count(*) FROM m WHERE EXISTS (SELECT 1 FROM o WHERE ST_DWithin(o.g, m.g, %s))),
                   (SELECT count(*) FROM o),
                   (SELECT count(*) FROM o WHERE EXISTS (SELECT 1 FROM m WHERE ST_DWithin(o.g, m.g, %s)))
        """, (art, TREFFER_M, TREFFER_M))
        m_n, m_treffer, o_n, o_treffer = cur.fetchone()
        erg[art] = {"mbjs": m_n, "mbjs_mit_osm": m_treffer, "osm": o_n, "osm_mit_mbjs": o_treffer,
                    "quote": (round(100 * m_treffer / m_n, 1) if m_n else None)}
    return erg


# ------------------------------------------------------------------------------- Kennzahlen

def kennzahlen(cur) -> dict:
    """Netzkennzahlen für die Abnahme (auch von pruefen/a3_pruefen.py genutzt). Braucht a3_stadt."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree

    cur.execute("SELECT id, ST_X(geom), ST_Y(geom) FROM auswertung.netz_knoten ORDER BY id")
    zeilen = cur.fetchall()
    if not zeilen:
        return {"knoten": 0}
    ids = np.array([z[0] for z in zeilen], dtype=np.int64)
    xy = np.array([(z[1], z[2]) for z in zeilen])
    cur.execute("SELECT von, nach FROM auswertung.netz_kante")
    e = np.array(cur.fetchall(), dtype=np.int64).reshape(-1, 2)
    ia = np.searchsorted(ids, e[:, 0])
    ib = np.searchsorted(ids, e[:, 1])
    n = ids.size
    g = coo_matrix((np.ones(ia.size), (ia, ib)), shape=(n, n))
    _anz, label = connected_components(g, directed=False)
    cur.execute("""SELECT k.id FROM auswertung.netz_knoten k
                   WHERE EXISTS (SELECT 1 FROM a3_stadt s WHERE ST_Intersects(s.geom, k.geom))""")
    in_stadt = np.searchsorted(ids, np.array([r[0] for r in cur.fetchall()], dtype=np.int64))
    if in_stadt.size:
        groesse = np.bincount(label[in_stadt])
        groesste = int(groesse.max())
        anteil_komp = groesste / in_stadt.size
    else:
        groesste, anteil_komp = 0, 0.0
    cur.execute("""SELECT ST_X(g), ST_Y(g) FROM (
                     SELECT ST_Transform(z.geom, 25833) g FROM public.zensus_zelle z WHERE z.ew > 0) x
                   WHERE EXISTS (SELECT 1 FROM a3_stadt s WHERE ST_Intersects(s.geom, x.g))""")
    zellen = np.array(cur.fetchall()).reshape(-1, 2)
    d, _ = cKDTree(xy).query(zellen) if zellen.size else (np.zeros(0), None)
    return {
        "knoten": int(n), "kanten": int(e.shape[0]), "knoten_im_stadtgebiet": int(in_stadt.size),
        "groesste_komponente_im_stadtgebiet": groesste, "anteil_groesste_komponente": round(anteil_komp, 4),
        "komponenten": int(_anz),
        "bewohnte_zellen": int(zellen.shape[0]), "zellen_le_150m": int((d <= 150).sum()),
        "anteil_zellen_le_150m": round(float((d <= 150).mean()) if d.size else 0.0, 4),
        "zelle_knoten_median_m": round(float(np.median(d)) if d.size else 0.0, 1),
        "zelle_knoten_max_m": round(float(d.max()) if d.size else 0.0, 1),
    }


def bericht_schreiben(pfad: Path, *, pbf: Path, summe: str, erg: osm_pbf.Ergebnis, stand: str,
                      geschrieben: dict, voll: dict, kz: dict, trocken: bool) -> None:
    def zeile(art: str) -> str:
        v = voll[art]
        q = "–" if v["quote"] is None else f"{v['quote']:.1f} %".replace(".", ",")
        return (f"| {art} | {v['mbjs']} | {v['mbjs_mit_osm']} | **{q}** | {v['osm']} | {v['osm_mit_mbjs']} |")

    deckt = "ja"
    if erg.ausdehnung is not None and kz.get("leserechteck"):
        w, s, o, n = kz["leserechteck"]
        ew, es, eo, en = erg.ausdehnung
        if ew > w + RAND_GRAD or es > s + RAND_GRAD or eo < o - RAND_GRAD or en < n - RAND_GRAD:
            deckt = "**nein**: die Datei endet innerhalb des Puffers, Randwerte sind unvollständig"
    def pz(anteil: float) -> str:
        return f"{100 * anteil:.1f} %".replace(".", ",")

    pfad.parent.mkdir(exist_ok=True)
    pfad.write_text("\n".join([
        "# A3 Vollständigkeit: OpenStreetMap gegen MBJS" + (" (TROCKENLAUF, nichts gespeichert)" if trocken else ""),
        "",
        f"Erzeugt von `skripte/12_osm.py` am {dt.date.today().isoformat()}. Daten: {ODBL}.",
        f"PBF: `{pbf.name}` (SHA256 `{summe[:16]}…`), Datenstand {stand}. Deckt den Puffer (Stadtgebiet + 2 km) ab: {deckt}.",
        "",
        f"## Kitas und Schulen im Stadtgebiet (Treffer: OSM-Objekt höchstens {TREFFER_M} m entfernt, bei Flächen vom Rand)",
        "",
        "| Art | MBJS-Standorte | davon mit OSM-Gegenstück | Trefferquote | OSM-Objekte | davon mit MBJS-Gegenstück |",
        "|---|---|---|---|---|---|",
        zeile("kita"), zeile("schule"),
        "",
        ("MBJS-Kitas: ein Standort je `id_kita` (public.mbjs_kita). OSM-Kitas: `amenity=kindergarten`, Schulen: "
        "`amenity=school` (Punkte und Flächen). Die Trefferquote misst, wie vollständig OSM gegenüber der amtlichen "
        "Liste ist; sie ist ein Hinweis auf die Güte der OSM-Kategorien ohne amtliche Liste (Ärzte, Apotheken, "
        "Märkte, Pflege, Spielplätze), kein Beleg dafür."),
        "",
        "## Einrichtungen aus OSM (auswertung.osm_poi, ohne Namen)",
        "",
        "| Art | Anzahl |", "|---|---|",
        *[f"| {a} | {n} |" for a, n in sorted(geschrieben["poi_je_art"].items())],
        "",
        "## Fußwegnetz (auswertung.netz_knoten, auswertung.netz_kante)",
        "",
        f"- Knoten {kz.get('knoten', 0)}, Kanten {kz.get('kanten', 0)}, Netzlänge rund {geschrieben['netz_km']} km",
        (f"- Knoten im Stadtgebiet {kz.get('knoten_im_stadtgebiet', 0)}, davon in der größten Komponente "
        f"{kz.get('groesste_komponente_im_stadtgebiet', 0)} ({pz(kz.get('anteil_groesste_komponente', 0))}); "
        f"Komponenten insgesamt {kz.get('komponenten', 0)}"),
        (f"- Bewohnte Zellen im Stadtgebiet {kz.get('bewohnte_zellen', 0)}, davon mit Netzknoten in ≤ 150 m "
        f"{kz.get('zellen_le_150m', 0)} ({pz(kz.get('anteil_zellen_le_150m', 0))}); "
        f"Abstand Median {kz.get('zelle_knoten_median_m', 0)} m, größter {kz.get('zelle_knoten_max_m', 0)} m"),
        "",
        ("Regeln: begehbar sind `highway`-Wege außer Autobahn, Bau, geplant, Bahnsteig, Rennstrecke; Radwege nur mit "
        "`foot=yes/designated`; `foot=no`, `access=private/no` ohne Fußfreigabe und Kraftfahrstraßen entfallen. "
        "Jeder OSM-Knoten eines solchen Wegs ist Netzknoten; Kanten sind ungerichtet."),
        "",
    ]), encoding="utf-8")


# ------------------------------------------------------------------------------- Hauptlauf

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pbf", required=True, type=Path)
    ap.add_argument("--trockenlauf", action="store_true", help="alles rechnen, am Ende ROLLBACK")
    ap.add_argument("--bericht", type=Path, default=WURZEL / "berichte" / "A3_vollstaendigkeit.md")
    a = ap.parse_args()
    pbf = a.pbf.resolve()
    if not pbf.is_file():
        raise SystemExit(f"PBF fehlt: {pbf} (Handdownload H5 nach $KIEZ_DATEN/osm/<stand>/)")
    t0 = time.time()
    summe = sha256(pbf)
    with verbinden() as conn:
        with conn.cursor() as cur:
            cur.execute(PUFFER_SQL)
            rechteck = leserechteck(cur)
            print(f"Leserechteck {tuple(round(v, 4) for v in rechteck)}", flush=True)
            erg = lies_osm(pbf, rechteck)
            print(f"PBF gelesen in {time.time() - t0:.0f} s: {erg.knoten_gesamt} Knoten, {erg.wege_gesamt} Wege, "
                  f"{erg.relationen_gesamt} Relationen; im Rechteck {erg.knoten_id.size} Knoten", flush=True)
            if not a.trockenlauf:
                herkunft_pruefen(pbf, erg.kopf, summe)
            fusswege = [w for w in erg.wege if "_nur_relation" not in w[1] and ist_fussweg(w[1])]
            von, nach, knoten, koords = netz_bauen(fusswege, erg)
            pois, bildung = objekte_sammeln(erg)
            geschrieben = schreiben(cur, von, nach, knoten, koords, pois, bildung)
            voll = vollstaendigkeit(cur)
            kz = kennzahlen(cur)
            kz["leserechteck"] = rechteck
            stand = (dt.datetime.fromtimestamp(erg.kopf.zeitstempel, dt.UTC).date().isoformat()
                     if erg.kopf and erg.kopf.zeitstempel
                     else dt.date.fromtimestamp(pbf.stat().st_mtime).isoformat() + " (Dateidatum)")
            bericht_schreiben(a.bericht, pbf=pbf, summe=summe, erg=erg, stand=stand, geschrieben=geschrieben,
                              voll=voll, kz=kz, trocken=a.trockenlauf)
            print(f"Einrichtungen {geschrieben['poi_je_art']}; Netz {geschrieben['knoten']} Knoten, "
                  f"{geschrieben['kanten']} Kanten; Vollständigkeit Kita {voll['kita']['quote']} %, "
                  f"Schule {voll['schule']['quote']} %; Bericht {a.bericht}")
        if a.trockenlauf:
            conn.rollback()
            print("Trockenlauf: ROLLBACK, in auswertung ist nichts geändert.")
        else:
            conn.commit()
    print(f"fertig in {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
