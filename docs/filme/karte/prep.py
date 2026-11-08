# Film „Potsdam wächst aus den Daten“: Daten lesen, gegen die Belege prüfen, Geometrie für Blender und Overlay bauen.
# Aufruf aus der Repo-Wurzel (Python mit numpy, shapely, mapbox_earcut, pyproj):
#   python docs/filme/karte/prep.py --daten berichte/filme-2026-11-08/karte/daten --aus berichte/filme-2026-11-08/karte/prep [--fakten <fakten.json>]
# --daten: Ausgabe von holen.py. Alle Zahlen, die der Film zeigt, liest dieses Skript aus Dateien des Repos
# (belege/, daten/, config/) und schreibt sie nach <aus>/meta.json; jede Doppelquelle wird per assert abgeglichen.
# --fakten (optional): Faktenblatt der Filmarbeit; dann werden auch Befund-Sätze und Werte dagegen geprüft.
import argparse
import csv
import glob
import json
import math
import os
import re

import mapbox_earcut as earcut
import numpy as np
from pyproj import Transformer
from shapely import wkt as shp_wkt
from shapely.geometry import Point, Polygon, shape
from shapely.ops import unary_union

csv.field_size_limit(1 << 30)
ap = argparse.ArgumentParser()
ap.add_argument("--daten", required=True)
ap.add_argument("--aus", required=True)
ap.add_argument("--repo", default=".")
ap.add_argument("--fakten", default="")
args = ap.parse_args()
R = args.repo
os.makedirs(args.aus, exist_ok=True)


def pfad(*p):
    return os.path.join(R, *p)


def lade_js(p):
    t = open(p, encoding="utf-8").read()
    t = re.sub(r"^\s*/\*.*?\*/\s*", "", t, flags=re.S)
    return json.loads(t[t.index("=") + 1:].rstrip().rstrip(";"))


def lies_csv(name):
    with open(os.path.join(args.daten, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def srgb_hex(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


# ------------------------------------------------------------ Importläufe (belege/)
laeufe = []
for p in sorted(glob.glob(pfad("belege", "2026110*Z.json"))):
    d = json.load(open(p, encoding="utf-8"))
    assert len(d["quellen"]) == 1, p
    q = d["quellen"][0]
    txt = open(p[:-5] + ".txt", encoding="utf-8").read().splitlines()
    # Gegenprobe gegen die Konsolenausgabe (.txt): Kopfzeile und Zählerzeile
    m = re.match(r"Importlauf (\S+) · ([\d.]+) s$", txt[0])
    assert m and m.group(1) == d["lauf_id"] and float(m.group(2)) == d["laufzeit_s"], (p, txt[0])
    m = re.match(r"\s+(\S+)\s+(\S+)\s+neu\s+(\d+)\s+geändert\s+(\d+)\s+gelöscht\s+(\d+)\s+unverändert\s+(\d+)", txt[1])
    z = q["zaehler"]
    assert m and m.group(1) == q["quelle"] and m.group(2) == q["status"], (p, txt[1])
    assert [int(m.group(i)) for i in (3, 4, 5, 6)] == [z["neu"], z["geaendert"], z["geloescht"], z["unveraendert"]], p
    warn = [l.strip()[len("Warnung: "):] for l in txt if l.strip().startswith("Warnung: ")]
    assert warn == q["warnungen"], p
    laeufe.append({"lauf_id": d["lauf_id"], "start": d["start"], "quelle": q["quelle"], "status": q["status"],
                   "neu": z["neu"], "geaendert": z["geaendert"], "geloescht": z["geloescht"],
                   "unveraendert": z["unveraendert"], "laufzeit_s": d["laufzeit_s"],
                   "laufzeit_quelle_s": q["laufzeit_s"], "warnungen": q["warnungen"], "hinweise": q["hinweise"],
                   "unvollstaendig": bool(q.get("unvollstaendig")), "lauf_unvollstaendig": d.get("unvollstaendig", []),
                   "datei": os.path.relpath(p, R)})
laeufe.sort(key=lambda x: x["start"])
assert len(laeufe) == 7
REIHE = [l["quelle"] for l in laeufe]
assert REIHE == ["stadtteile", "zensus_gitter", "gebaeude_alkis", "mbjs_kita", "mbjs_schule", "alkis_nutzung",
                 "zensus_struktur"], REIHE
L = {l["quelle"]: l for l in laeufe}

# Kita: Erklärung aus belege/README.md (Zeile mit der Lauf-ID), wörtlich
kita_readme = None
for nr, zeile in enumerate(open(pfad("belege", "README.md"), encoding="utf-8").read().splitlines(), 1):
    if L["mbjs_kita"]["lauf_id"] in zeile and "id_kita" in zeile:
        zellen_ = [c.strip() for c in zeile.strip().strip("|").split("|")]
        kita_readme = {"zeile": nr, "text": zellen_[-1]}
assert kita_readme, "Kita-Zeile in belege/README.md fehlt"
m = re.search(r"(\d+) Kitas \(je `id_kita` ein Standort\); „unvollständig“, weil der Dienst (\d+) Einträge meldet: "
              r"(\d+) Kitas stehen mit mehreren Häusern", kita_readme["text"])
assert m, kita_readme
kita_readme["kitas"], kita_readme["eintraege"], kita_readme["mehrere"] = (int(m.group(i)) for i in (1, 2, 3))
assert kita_readme["kitas"] == L["mbjs_kita"]["neu"]
mw = re.match(r"Nur (\d+) von (\d+) gemeldeten Objekten erhalten", L["mbjs_kita"]["warnungen"][0])
assert mw and int(mw.group(1)) == kita_readme["kitas"] and int(mw.group(2)) == kita_readme["eintraege"]

# ------------------------------------------------------------ Konfiguration: Rechteck und Kacheln
cfg = open(pfad("config", "potsdam.yaml"), encoding="utf-8").read()


def block(name):
    i = cfg.index("\n  " + name + ":")
    j = re.search(r"\n  \S", cfg[i + 3:])
    return cfg[i:i + 3 + (j.start() if j else len(cfg))]


def bbox_kachel(name):
    b = block(name)
    bb = [float(x) for x in re.search(r"bbox: \[([^\]]+)\]", b).group(1).split(",")]
    km = float(re.search(r"kachel_m: (\d+)", b).group(1))
    return bb, km


BB_G, K_G = bbox_kachel("gebaeude_alkis")
BB_N, K_N = bbox_kachel("alkis_nutzung")
assert BB_G == BB_N


def kacheln(bb, km):
    nx = math.ceil((bb[2] - bb[0]) / km)
    ny = math.ceil((bb[3] - bb[1]) / km)
    return nx, ny


NXG, NYG = kacheln(BB_G, K_G)
NXN, NYN = kacheln(BB_N, K_N)
# Letzte Kachel wie im Bericht (letzte_abfrage): oben rechts
lb = json.load(open(pfad(L["gebaeude_alkis"]["datei"]), encoding="utf-8"))["quellen"][0]["letzte_abfrage"]
bx = [float(x) for x in re.search(r"BBOX=([\d.%C]+)", lb).group(1).split("%2C")[:4]]
assert bx == [BB_G[2] - K_G, BB_G[3] - K_G, BB_G[2], BB_G[3]], bx

OX, OY = (BB_G[0] + BB_G[2]) / 2, (BB_G[1] + BB_G[3]) / 2  # Ursprung = Mitte des Abrufrechtecks


def kachel_index(xmin, ymin, bb, km, nx, ny):
    c = min(max(int((xmin - bb[0]) // km), 0), nx - 1)
    r = min(max(int((ymin - bb[1]) // km), 0), ny - 1)
    return r * nx + c


# ------------------------------------------------------------ Kennzahlen
KZ = json.load(open(pfad("daten", "kennzahlen.json"), encoding="utf-8"))
assert KZ["kontrolle"]["gebaeude_im_rechteck"] == L["gebaeude_alkis"]["neu"]
N_GEB_P = KZ["stadt"]["gebaeude"]["anzahl"]
assert KZ["kontrolle"]["gebaeude_in_potsdam"] == N_GEB_P


def kachel(G, id_):
    return [k for k in G["kacheln"] if k["id"] == id_][0]


# ------------------------------------------------------------ Stadtteile
tr = Transformer.from_crs(4326, 25833, always_xy=True)
ST_JS = lade_js(pfad("daten", "stadtteile.js"))
st_rows = lies_csv("stadtteile.csv")
assert len(ST_JS["features"]) == len(st_rows) == L["stadtteile"]["neu"] == len(KZ["stadtteile"]) == 32
names_js = {f["properties"]["nr"]: f["properties"]["name"] for f in ST_JS["features"]}
stadtteile = []
polys = []
for r in st_rows:
    assert names_js[r["nr"]] == r["name"] == KZ["stadtteile"][r["nr"]]["name"], r["nr"]
    g = shape(json.loads(r["geo"]))
    polys.append(g)
    ringe = []
    for pg in getattr(g, "geoms", [g]):
        for ring in [pg.exterior, *pg.interiors]:
            ringe.append([[round(x - OX, 1), round(y - OY, 1)] for x, y in ring.coords])
    stadtteile.append({"nr": r["nr"], "name": r["name"], "lx": float(r["lx"]) - OX, "ly": float(r["ly"]) - OY,
                       "ringe": ringe})
stadt = unary_union(polys)
stadt_ringe = []
for pg in getattr(stadt, "geoms", [stadt]):
    for ring in [pg.exterior, *pg.interiors]:
        stadt_ringe.append([[round(x - OX, 1), round(y - OY, 1)] for x, y in ring.simplify(4).coords])


# ------------------------------------------------------------ Gebäude
def tri_polygon(rings):
    """rings: [aussen, loch...] als Listen (x, y); gibt (verts2d, tris) zurück."""
    flat = []
    ends = []
    for r in rings:
        r = r[:-1] if len(r) > 1 and r[0] == r[-1] else r
        flat.extend(r)
        ends.append(len(flat))
    if len(flat) < 3:
        return flat, []
    v = np.asarray(flat, dtype=np.float64)
    t = earcut.triangulate_float64(v, np.asarray(ends, dtype=np.uint32))
    return flat, t.reshape(-1, 3).tolist()


def flaeche(r):
    a = 0.0
    for i in range(len(r)):
        x1, y1 = r[i]
        x2, y2 = r[(i + 1) % len(r)]
        a += x1 * y2 - x2 * y1
    return a / 2


JAHR_KLASSEN = None
PAL = lade_js(pfad("daten", "jahre", "11.js"))  # Kopf mit klassen
JAHR_KLASSEN = PAL["klassen"]
jsq = open(pfad("jahre.js"), encoding="utf-8").read()
PALETTE = re.findall(r"#[0-9a-fA-F]{6}", re.search(r"var PALETTE = \[([^\]]+)\]", jsq).group(1))
GEB_ND = re.search(r'GEB_ND = "(#[0-9a-fA-F]{6})"', jsq).group(1)
assert len(PALETTE) == len(JAHR_KLASSEN) == 8

geb_rows = lies_csv("gebaeude.csv")
assert len(geb_rows) == L["gebaeude_alkis"]["neu"]
innen = {}
aussen = []
for r in geb_rows:
    if r["nr"]:
        innen.setdefault(r["nr"], []).append(r)
    else:
        aussen.append(r)
assert sum(len(v) for v in innen.values()) == N_GEB_P
assert len(aussen) == L["gebaeude_alkis"]["neu"] - N_GEB_P

V, T, A_T0, A_AUS, A_KCOL, A_NR, A_NEB = [], [], [], [], [], [], []
KACHEL_GEB = [0] * (NXG * NYG)  # Gebäude je Kachel (Zähler im Film)
zahl = {"hq": {}, "g": {}, "k": [0] * 8, "nd": 0, "j_gesehen": 0}
nr_index = {s["nr"]: i for i, s in enumerate(stadtteile)}
# je Stadtteil (Reihenfolge wie stadtteile, also wie die Umfärbung): Klassen, nicht datiert, Herkunft der Bauzeit,
# dazu der Schwerpunkt der Gebäude (Anker der Befund-Fahnen; lx/ly liegt in der Teltower Vorstadt im Wald)
je_teil = [{"k": [0] * 8, "nd": 0, "g": {}, "sx": 0.0, "sy": 0.0, "n": 0} for _ in stadtteile]
max_abw = 0.0
for nr in sorted(innen):
    J = lade_js(pfad("daten", "jahre", nr + ".js"))
    G = lade_js(pfad("daten", "gebaeude", nr + ".js"))
    assert J["klassen"] == JAHR_KLASSEN
    fj, fg = J["features"], G["features"]
    rows = sorted(innen[nr], key=lambda r: int(r["rang"]))
    assert len(fj) == len(fg) == len(rows) == KZ["stadtteile"][nr]["gebaeude"]["anzahl"], nr
    for a, b, row in zip(fj, fg, rows):
        assert a["geometry"] == b["geometry"]
        pa, pb = a["properties"], b["properties"]
        assert pa["h"] == pb["h"] and pa["hq"] == pb["hq"]
        # j (Einzeljahr) wird bewusst nicht gelesen
        zahl["hq"][pa["hq"]] = zahl["hq"].get(pa["hq"], 0) + 1
        zahl["g"][pa["g"]] = zahl["g"].get(pa["g"], 0) + 1
        k = pa["k"]
        jt = je_teil[nr_index[nr]]
        jt["g"][pa["g"]] = jt["g"].get(pa["g"], 0) + 1
        if k is None:
            zahl["nd"] += 1
            jt["nd"] += 1
        else:
            zahl["k"][k] += 1
            jt["k"][k] += 1
        coords = a["geometry"]["coordinates"]
        ringe = []
        for ring in coords:
            xs, ys = tr.transform([c[0] for c in ring], [c[1] for c in ring])
            ringe.append([(x - OX, y - OY) for x, y in zip(xs, ys)])
        # Abgleich mit der Datenbank: Lagepunkt der DB-Zeile liegt im Umriss (Toleranz 1,5 m)
        pg = Polygon(ringe[0], ringe[1:])
        jt["sx"] += pg.centroid.x
        jt["sy"] += pg.centroid.y
        jt["n"] += 1
        pp = Point(float(row["px"]) - OX, float(row["py"]) - OY)
        dd = pg.distance(pp)
        max_abw = max(max_abw, dd)
        assert dd < 1.5, (nr, row["rang"], dd)
        ti = kachel_index(float(row["xmin"]), float(row["ymin"]), BB_G, K_G, NXG, NYG)
        KACHEL_GEB[ti] += 1
        h = float(pa["h"])
        col = srgb_hex(PALETTE[k]) if k is not None else srgb_hex(GEB_ND)
        neb = 1.0 if k is None else 0.0
        flat, tris = tri_polygon(ringe)
        off = len(V)
        V.extend((x, y, h) for x, y in flat)
        T.extend((a_ + off, b_ + off, c_ + off) for a_, b_, c_ in tris)
        for ri, rr in enumerate(ringe):
            rr = rr[:-1] if rr[0] == rr[-1] else rr
            ccw = flaeche(rr) > 0
            if ccw != (ri == 0):
                rr = rr[::-1]
            o2 = len(V)
            for x, y in rr:
                V.append((x, y, 0.0))
                V.append((x, y, h))
            n = len(rr)
            for i in range(n):
                j = (i + 1) % n
                T.append((o2 + 2 * i, o2 + 2 * j, o2 + 2 * j + 1))
                T.append((o2 + 2 * i, o2 + 2 * j + 1, o2 + 2 * i + 1))
        nv = len(V) - off
        A_T0.extend([ti] * nv)
        A_AUS.extend([0.0] * nv)
        A_KCOL.extend([col] * nv)
        A_NR.extend([nr_index[nr]] * nv)  # Reihenfolge der Umfärbung
        A_NEB.extend([neb] * nv)
JM = lade_js(pfad("daten", "jahre_methode.js"))
assert zahl["hq"] == {k: JM["hoehe"][k] for k in zahl["hq"]}, (zahl["hq"], JM["hoehe"])
assert zahl["g"] == JM["je_g"], (zahl["g"], JM["je_g"])
# Summen je Stadtteil gleich den Gesamtzahlen (der Film zählt sie Stadtteil für Stadtteil hoch)
assert [sum(j["k"][i] for j in je_teil) for i in range(8)] == zahl["k"]
assert sum(j["nd"] for j in je_teil) == zahl["nd"]
assert {g: sum(j["g"].get(g, 0) for j in je_teil) for g in zahl["g"]} == zahl["g"]
assert sum(j["n"] for j in je_teil) == N_GEB_P
for s_, j in zip(stadtteile, je_teil):
    s_["gx"], s_["gy"] = (round(j["sx"] / j["n"], 1), round(j["sy"] / j["n"], 1)) if j["n"] else (s_["lx"], s_["ly"])
    del j["sx"], j["sy"]
print("Gebäude in Potsdam:", N_GEB_P, "größter Abstand Lagepunkt/Umriss", round(max_abw, 2), "m", flush=True)

# außerhalb Potsdams: nur Grundriss, flach (keine Höhe aus dem NAS-Bestand)
H_AUSSEN = 1.2
for r in aussen:
    g = shape(json.loads(r["geo"]))
    ti = kachel_index(float(r["xmin"]), float(r["ymin"]), BB_G, K_G, NXG, NYG)
    KACHEL_GEB[ti] += 1
    for pg in getattr(g, "geoms", [g]):
        ringe = [[(x - OX, y - OY) for x, y in ring.coords] for ring in [pg.exterior, *pg.interiors]]
        flat, tris = tri_polygon(ringe)
        off = len(V)
        V.extend((x, y, H_AUSSEN) for x, y in flat)
        T.extend((a_ + off, b_ + off, c_ + off) for a_, b_, c_ in tris)
        nv = len(V) - off
        A_T0.extend([ti] * nv)
        A_AUS.extend([1.0] * nv)
        A_KCOL.extend([srgb_hex("#e5e7e2")] * nv)
        A_NR.extend([-1] * nv)
        A_NEB.extend([0.0] * nv)
np.savez_compressed(os.path.join(args.aus, "gebaeude.npz"), v=np.asarray(V, np.float32), t=np.asarray(T, np.int32),
                    t0=np.asarray(A_T0, np.float32), aus=np.asarray(A_AUS, np.float32),
                    kcol=np.asarray(A_KCOL, np.float32), nr=np.asarray(A_NR, np.float32),
                    neb=np.asarray(A_NEB, np.float32))
print("Gebäude-Mesh:", len(V), "Ecken,", len(T), "Dreiecke", flush=True)
V = T = None

# ------------------------------------------------------------ Zensus-Zellen
z_rows = lies_csv("zellen.csv")
assert len(z_rows) == L["zensus_gitter"]["neu"]
ZJS = lade_js(pfad("daten", "zellen.js"))
assert len(ZJS["features"]) == KZ["stadt"]["zellen"]
ew_js = sorted(f["properties"]["ew"] for f in ZJS["features"])
innen_z = [r for r in z_rows if r["in_potsdam"] == "t"]
assert len(innen_z) == KZ["stadt"]["zellen"]
assert sorted(int(r["ew"]) for r in innen_z) == ew_js
assert sum(ew_js) == kachel(KZ["stadt"], "einwohner")["wert"]
n_grenz = sum(1 for r in z_rows if r["grenz"] == "t")
assert n_grenz == KZ["grenzfall"]["stadt"]["grenzzellen"], n_grenz
n_struktur = sum(1 for r in z_rows if r["struktur"] == "t")
# zensus_struktur: 6.334 Zeilen (Lauf = Tabelle); im Bild leuchten die Zellen des Gitters auf, die eine
# Strukturzeile haben (n_struktur). Der Rest hat keine Zelle im Gitterlauf; die Zahl steht in meta.json.
n_struktur_tab = int(lies_csv("struktur_anzahl.csv")[0]["n"])
assert n_struktur_tab == L["zensus_struktur"]["neu"], n_struktur_tab
assert n_struktur <= n_struktur_tab
# Klassen wie themen.js (klassen): Quintile über die Werte von zellen.js, doppelte Grenzen entfallen
w = [v for v in ew_js if v is not None]
grenzen = []
for p_ in (0.2, 0.4, 0.6, 0.8):
    v = w[min(len(w) - 1, math.floor(p_ * len(w)))]
    if not grenzen or v > grenzen[-1]:
        grenzen.append(v)
css = open(pfad("atlas.css"), encoding="utf-8").read()
STUFEN = [re.search(r"--k%d:(#[0-9a-fA-F]{6})" % i, css).group(1) for i in range(1, 6)]
GRAU_UNSCHARF = re.search(r'var GRAU = "(#[0-9a-fA-F]{6})"', open(pfad("themen.js"), encoding="utf-8").read()).group(1)


def stufe(v):
    i = 0
    while i < len(grenzen) and v >= grenzen[i]:
        i += 1
    return min(i, 4)


V, T, Z_T, Z_IN, Z_COL, Z_ST = [], [], [], [], [], []
klassen_anz = [0] * 5
grenz_quad = []
for i, r in enumerate(z_rows):
    g = shp_wkt.loads(r["wkt"])
    ring = [(x - OX, y - OY) for x, y in list(g.exterior.coords)[:-1]]
    ew = int(r["ew"]) if r["ew"] not in ("", None) else None
    if ew is None:
        col = srgb_hex(GRAU_UNSCHARF)
    else:
        s = stufe(ew)
        col = srgb_hex(STUFEN[s])
        if r["in_potsdam"] == "t":
            klassen_anz[s] += 1
    if r["grenz"] == "t":
        grenz_quad.append([[round(x, 1), round(y, 1)] for x, y in ring])
    off = len(V)
    V.extend((x, y, 0.0) for x, y in ring)
    T.extend([(off, off + 1, off + 2), (off, off + 2, off + 3)])
    Z_T.extend([i / len(z_rows)] * 4)
    Z_IN.extend([1.0 if r["in_potsdam"] == "t" else 0.0] * 4)
    Z_COL.extend([col] * 4)
    Z_ST.extend([1.0 if r["struktur"] == "t" else 0.0] * 4)
np.savez_compressed(os.path.join(args.aus, "zellen.npz"), v=np.asarray(V, np.float32), t=np.asarray(T, np.int32),
                    tz=np.asarray(Z_T, np.float32), innen=np.asarray(Z_IN, np.float32),
                    kcol=np.asarray(Z_COL, np.float32), struktur=np.asarray(Z_ST, np.float32))

# ------------------------------------------------------------ Nutzung
GK = json.loads(re.sub(r"^\s*/\*.*?\*/\s*", "", open(pfad("daten", "grundkarte.js"), encoding="utf-8").read(),
                       flags=re.S).split("=", 1)[1].rstrip().rstrip(";"))
gk_farbe = {}
for l in GK["unten"] + GK["oben"]:
    if l.get("type") == "fill":
        c = l.get("paint", {}).get("fill-color")
        if isinstance(c, dict):
            c = c["stops"][-1][1]
        gk_farbe[l["id"]] = c


def rgbtxt(c):
    m = re.match(r"rgb\((\d+),(\d+),(\d+)\)", c.replace(" ", ""))
    return [int(m.group(i)) / 255 for i in (1, 2, 3)]


# nutzart -> (Gruppe für die Legende, Ebene der Grundkarte des Kiezatlas, deren Grauton der Film übernimmt)
GRUPPEN = {
    "Gewässer": ("bm-Gewaesser_F_See_Hafenbecken", ["Fließgewässer", "Stehendes Gewässer", "Hafenbecken", "Schiffsverkehr"]),
    "Wald, Gehölz, Heide, Moor": ("bm-VegetationsF_Wald", ["Wald", "Gehölz", "Heide", "Sumpf", "Moor"]),
    "Landwirtschaft, Unland": ("bm-VegetationsF_Gruenland", ["Landwirtschaft", "Unland/Vegetationslose Fläche"]),
    "Siedlung, Gewerbe, Erholung": ("bm-SiedlungF_Siedlung", ["Wohnbaufläche", "Industrie- und Gewerbefläche",
                                    "Fläche gemischter Nutzung", "Fläche besonderer funktionaler Prägung",
                                    "Sport-, Freizeit- und Erholungsfläche", "Friedhof", "Halde",
                                    "Tagebau, Grube, Steinbruch"]),
    "Verkehr": ("bm-Verkehrsflaeche_Bahnverkehr_Schiffsverkehr", ["Straßenverkehr", "Weg", "Platz", "Bahnverkehr"]),
}
art_gruppe = {a: g for g, (_, arten) in GRUPPEN.items() for a in arten}
n_rows = lies_csv("nutzung.csv")
assert len(n_rows) == L["alkis_nutzung"]["neu"]
V, T, N_T, N_COL = [], [], [], []
KACHEL_NUTZ = [0] * (NXN * NYN)
gruppen_anz = {g: 0 for g in GRUPPEN}
for r in n_rows:
    gname = art_gruppe[r["nutzart"]]
    gruppen_anz[gname] += 1
    col = rgbtxt(gk_farbe[GRUPPEN[gname][0]])
    ti = kachel_index(float(r["xmin"]), float(r["ymin"]), BB_N, K_N, NXN, NYN)
    KACHEL_NUTZ[ti] += 1
    g = shape(json.loads(r["geo"]))
    for pg in getattr(g, "geoms", [g]):
        if pg.is_empty:
            continue
        ringe = [[(x - OX, y - OY) for x, y in ring.coords] for ring in [pg.exterior, *pg.interiors]]
        flat, tris = tri_polygon(ringe)
        off = len(V)
        V.extend((x, y, 0.0) for x, y in flat)
        T.extend((a_ + off, b_ + off, c_ + off) for a_, b_, c_ in tris)
        N_T.extend([ti] * len(flat))
        N_COL.extend([col] * len(flat))
assert sum(gruppen_anz.values()) == sum(KACHEL_NUTZ) == L["alkis_nutzung"]["neu"]
assert sum(KACHEL_GEB) == L["gebaeude_alkis"]["neu"]
np.savez_compressed(os.path.join(args.aus, "nutzung.npz"), v=np.asarray(V, np.float32), t=np.asarray(T, np.int32),
                    t0=np.asarray(N_T, np.float32), kcol=np.asarray(N_COL, np.float32))
print("Nutzung:", len(V), "Ecken", flush=True)

# ------------------------------------------------------------ Einrichtungen (Lage)
kita = [(float(r["x"]) - OX, float(r["y"]) - OY, r["in_potsdam"] == "t") for r in lies_csv("kita.csv")]
schule = [(float(r["x"]) - OX, float(r["y"]) - OY, r["in_potsdam"] == "t") for r in lies_csv("schule.csv")]
assert len(kita) == L["mbjs_kita"]["neu"] and len(schule) == L["mbjs_schule"]["neu"]

# ------------------------------------------------------------ Befunde über Potsdam (kennzahlen.json)
def anteil(nr, id_):
    return kachel(KZ["stadtteile"][nr], id_)["wert"]


gross = [nr for nr in KZ["stadtteile"] if kachel(KZ["stadtteile"][nr], "einwohner")["wert"] >= 1000]
assert len(gross) == 26
alt_max = max(gross, key=lambda n: anteil(n, "altbau"))
alt_min = min(gross, key=lambda n: anteil(n, "altbau"))
fw_max = max(gross, key=lambda n: anteil(n, "fernwaerme"))
fw_min = min(gross, key=lambda n: anteil(n, "fernwaerme"))


def de1(x):
    return f"{x:.1f}".replace(".", ",")


s_alt = kachel(KZ["stadt"], "altbau")
s_fw = kachel(KZ["stadt"], "fernwaerme")
befunde = {
    "altbau": {"stadt": s_alt["wert"], "max": [alt_max, KZ["stadtteile"][alt_max]["name"], anteil(alt_max, "altbau")],
               "min": [alt_min, KZ["stadtteile"][alt_min]["name"], anteil(alt_min, "altbau")],
               "zaehler": s_alt["zaehler"], "nenner": s_alt["nenner"], "titel": s_alt["titel"]},
    "fernwaerme": {"stadt": s_fw["wert"], "max": [fw_max, KZ["stadtteile"][fw_max]["name"], anteil(fw_max, "fernwaerme")],
                   "min": [fw_min, KZ["stadtteile"][fw_min]["name"], anteil(fw_min, "fernwaerme")],
                   "titel": s_fw["titel"]},
}
befunde["altbau"]["satz"] = (f"Ein Viertel der Wohnungen ({de1(s_alt['wert'])} %) liegt in Häusern von vor 1949. "
                             f"In der {befunde['altbau']['max'][1]} sind es {de1(befunde['altbau']['max'][2])} %, "
                             f"in {befunde['altbau']['min'][1]} {de1(befunde['altbau']['min'][2])} %.")
befunde["fernwaerme"]["satz"] = (f"Sechs von zehn Wohnungen in Potsdam heizen mit Fernwärme ({de1(s_fw['wert'])} %). "
                                 f"Im Stadtteil {befunde['fernwaerme']['max'][1]} sind es {de1(befunde['fernwaerme']['max'][2])} %, "
                                 f"in {befunde['fernwaerme']['min'][1]} {de1(befunde['fernwaerme']['min'][2])} %.")
assert 0.24 <= s_alt["wert"] / 100 <= 0.26 and 0.55 <= s_fw["wert"] / 100 <= 0.65  # „ein Viertel“, „sechs von zehn“
# Rangfolge aller Stadtteile ab 1.000 Einwohnern (Balken im Befund), absteigend
befunde["altbau"]["rang"] = sorted(([nr, KZ["stadtteile"][nr]["name"], anteil(nr, "altbau")] for nr in gross),
                                   key=lambda x: -x[2])
assert befunde["altbau"]["rang"][0][0] == alt_max and befunde["altbau"]["rang"][-1][0] == alt_min
if args.fakten:
    F = json.load(open(args.fakten, encoding="utf-8"))
    saetze = [b["satz"] for b in F["befunde"]["wert"]]
    assert befunde["altbau"]["satz"] in saetze, befunde["altbau"]["satz"]
    assert befunde["fernwaerme"]["satz"] in saetze, befunde["fernwaerme"]["satz"]
    assert F["befund_altbau_max"]["wert"]["nr"] == alt_max and F["befund_altbau_min"]["wert"]["nr"] == alt_min
    assert F["gebaeude_im_rechteck"]["wert"] == L["gebaeude_alkis"]["neu"]
    assert F["zellen_zugeordnet"]["wert"] == KZ["stadt"]["zellen"]
    assert F["importlaeufe_summe_laufzeit_s"]["wert"] == round(sum(l["laufzeit_s"] for l in laeufe), 2)
    print("Faktenblatt abgeglichen", flush=True)

# ------------------------------------------------------------ Namensnennung (daten/LIZENZ.md, Dateiköpfe)
lz = open(pfad("daten", "LIZENZ.md"), encoding="utf-8").read()


def lizenz_zeile(dateiname):
    for zeile in lz.splitlines():
        if zeile.startswith("| `" + dateiname):
            return zeile.strip().strip("|").split("|")[-1].strip()
    raise KeyError(dateiname)


def kurz(s):
    return re.sub(r" \(https?://[^)]+\)", "", s)


EIN = lade_js(pfad("daten", "einrichtungen.js"))
JQ = lade_js(pfad("daten", "jahre", "11.js"))["quellen"]
namens = {
    "stadtteile": kurz(lizenz_zeile("stadtteile.js")) + ", dl-de/zero-2-0",
    "zensus": kurz(lizenz_zeile("zellen.js")),
    "gebaeude": kurz(lizenz_zeile("gebaeude/<nr>.js")),
    "lgb": kurz(EIN["quellen"]["lgb"]["vermerk"]),
    "mbjs": kurz(EIN["quellen"]["mbjs"]["vermerk"]),
    "jahre_zensus": kurz(JQ["zensus"]["vermerk"]),
    "wikidata": "belegte Bauzeiten: Wikidata, CC0 1.0",
}
assert "dl-de/zero-2-0" in lizenz_zeile("stadtteile.js") or "dl-de/zero-2-0" in lz
assert any(z.startswith("| `jahre_zellen.js`") and "Wikidata (CC0 1.0" in z for z in lz.splitlines())

meta = {
    "ursprung": [OX, OY], "bbox": [BB_G[0] - OX, BB_G[1] - OY, BB_G[2] - OX, BB_G[3] - OY],
    "bbox_utm": BB_G, "kachel_geb": [K_G, NXG, NYG], "kachel_nutz": [K_N, NXN, NYN],
    "je_kachel_geb": KACHEL_GEB, "je_kachel_nutz": KACHEL_NUTZ,
    "laeufe": laeufe, "kita_readme": kita_readme,
    "stadtteile": stadtteile, "stadt_ringe": stadt_ringe,
    "kita": kita, "schule": schule, "grenz_zellen": grenz_quad,
    "zahlen": {
        "geb_rechteck": L["gebaeude_alkis"]["neu"], "geb_potsdam": N_GEB_P, "geb_aussen": len(aussen),
        "zellen_rechteck": L["zensus_gitter"]["neu"], "zellen_potsdam": KZ["stadt"]["zellen"],
        "zellen_struktur": n_struktur_tab, "zellen_struktur_im_gitter": n_struktur, "grenzzellen": n_grenz,
        "grenz_ew": KZ["grenzfall"]["stadt"]["ew_in_grenzzellen"],
        "einwohner": kachel(KZ["stadt"], "einwohner")["wert"],
        "kita_potsdam": sum(1 for k in kita if k[2]), "schule_potsdam": sum(1 for s in schule if s[2]),
        "hq": zahl["hq"], "je_g": zahl["g"], "k": zahl["k"], "nd": zahl["nd"],
        "summe_laufzeit": round(sum(l["laufzeit_s"] for l in laeufe), 2),
        "summe_neu": sum(l["neu"] for l in laeufe),
        "summe_geaendert": sum(l["geaendert"] for l in laeufe), "summe_geloescht": sum(l["geloescht"] for l in laeufe),
        "stand_auswertung": KZ["stand_auswertung"],
    },
    "ew_grenzen": grenzen, "ew_klassen_anz": klassen_anz, "stufen": STUFEN,
    "nutzung_gruppen": {g: [gk_farbe[GRUPPEN[g][0]], gruppen_anz[g]] for g in GRUPPEN},
    "je_teil": je_teil, "jahr_klassen": JAHR_KLASSEN, "palette": PALETTE, "geb_nd": GEB_ND,
    "befunde": befunde, "namens": namens, "h_aussen": H_AUSSEN,
}
json.dump(meta, open(os.path.join(args.aus, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("meta.json geschrieben; Zellen", len(z_rows), "Grenzzellen", n_grenz, "Klassen", grenzen, klassen_anz)
