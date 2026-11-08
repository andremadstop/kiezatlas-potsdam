# Beschriftung (pycairo) über die Blender-Bilder: Kartenrahmen, Grenzen, Einrichtungen, Schriftfeld mit Bericht,
# großer Zähler, Zeitleiste nach laufzeit_s, Legenden, Namensnennung je Szene.
# Aufruf: FONTCONFIG_FILE=<fonts.conf mit Barlow> python docs/filme/karte/overlay.py --prep <prep> --ein <frames> --aus <komp>
#         [--frames 0-1409] [--jobs 1]
# Alle Zahlen kommen aus <prep>/meta.json (prep.py liest sie aus belege/, daten/, config/ und prüft sie dort).
import argparse
import math
import os
import sys
from multiprocessing import Pool

import cairo

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import zeitplan as Z

ap = argparse.ArgumentParser()
ap.add_argument("--prep", required=True)
ap.add_argument("--ein", required=True)
ap.add_argument("--aus", required=True)
ap.add_argument("--frames", default="")
ap.add_argument("--jobs", type=int, default=1)
args = ap.parse_args()
M = Z.lade(args.prep)
FPS, W, H = Z.FPS, Z.W, Z.H
LAUF = {l["quelle"]: l for l in M["laeufe"]}
ZA = M["zahlen"]


def hexrgb(h, a=1.0):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (a,)


# DESIGN.md / atlas.css
GROUND, SURFACE, INK, MUTED, LINE, ACCENT = "#f1f2ee", "#fafbf8", "#13212a", "#4f5d64", "#cdd1cc", "#6a2c82"
PETROL = "#3b7684"  # --k4
F_TXT, F_MED, F_SEMI = "Barlow", "Barlow Medium", "Barlow SemiBold"
F_DISP, F_DISP_S = "Barlow Semi Condensed Medium", "Barlow Semi Condensed SemiBold"


def de(n):
    return f"{n:,}".replace(",", ".")


def dez(x, st=1):
    return f"{x:,.{st}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def lz_txt(x):
    """Laufzeit wie im Bericht (ohne überflüssige Nullen), deutsch."""
    s = repr(float(x))
    if s.endswith(".0"):
        s = s[:-2] + ",0"
    return s.replace(".", ",")


def datum(lauf_id):
    return f"{lauf_id[6:8]}.{lauf_id[4:6]}.{lauf_id[0:4]}"


# ---------------- Text
def font(ctx, fam, size):
    ctx.select_font_face(fam, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)


def breite(ctx, s, fam, size, track=0.0, tab=False):
    font(ctx, fam, size)
    dw = ctx.text_extents("0").x_advance
    return sum((dw if (tab and c.isdigit()) else ctx.text_extents(c).x_advance) + track for c in s) - (track if s else 0)


def text(ctx, s, x, y, fam, size, col, align="l", track=0.0, alpha=1.0, tab=True):
    """tab: Ziffern gleich breit (tabellarisch), wie DESIGN.md verlangt."""
    if alpha <= 0.002 or not s:
        return 0.0
    font(ctx, fam, size)
    ctx.set_source_rgba(*hexrgb(col, alpha))
    dw = ctx.text_extents("0").x_advance
    adv = [(dw if (tab and c.isdigit()) else ctx.text_extents(c).x_advance) for c in s]
    w = sum(adv) + track * (len(s) - 1)
    if align == "r":
        x -= w
    elif align == "c":
        x -= w / 2
    cx = x
    for c, a in zip(s, adv):
        off = (a - ctx.text_extents(c).x_advance) / 2 if (tab and c.isdigit()) else 0
        ctx.move_to(cx + off, y)
        ctx.show_text(c)
        cx += a + track
    return w


def umbruch(ctx, s, fam, size, maxw):
    zeilen, z = [], ""
    for wort in s.split(" "):
        k = (z + " " + wort).strip()
        if breite(ctx, k, fam, size, tab=False) <= maxw or not z:
            z = k
        else:
            zeilen.append(z)
            z = wort
    if z:
        zeilen.append(z)
    return zeilen


def absatz(ctx, s, x, y, fam, size, col, maxw, lh=None, alpha=1.0):
    lh = lh or size * 1.32
    for i, z in enumerate(umbruch(ctx, s, fam, size, maxw)):
        text(ctx, z, x, y + i * lh, fam, size, col, alpha=alpha, tab=False)
    return y + len(umbruch(ctx, s, fam, size, maxw)) * lh


def linie(ctx, x1, y1, x2, y2, col, w=1.0, alpha=1.0):
    ctx.set_source_rgba(*hexrgb(col, alpha))
    ctx.set_line_width(w)
    ctx.move_to(x1, y1)
    ctx.line_to(x2, y2)
    ctx.stroke()


def swatch(ctx, x, y, col, w=22, h=12, rand=INK, alpha=1.0):
    ctx.set_source_rgba(*hexrgb(col, alpha))
    ctx.rectangle(x, y - h + 2, w, h)
    ctx.fill()
    if rand:
        ctx.set_source_rgba(*hexrgb(rand, 0.45 * alpha))
        ctx.set_line_width(0.6)
        ctx.rectangle(x, y - h + 2, w, h)
        ctx.stroke()


# ---------------- Layout
RA, RI = 20, 32
PX, PR = 1404, W - RI
XT, XR = PX + 26, PR - 24          # Textspalte im Schriftfeld
MAPR = PX
TL_X0, TL_X1, TL_Y = 70, 1350, H - RI - 34   # Zeitleiste


def ring_pfad(ctx, proj, ring, z=0.0):
    erst = True
    for x, y in ring:
        p = proj(x, y, z)
        if p is None:
            continue
        if erst:
            ctx.move_to(*p)
            erst = False
        else:
            ctx.line_to(*p)
    ctx.close_path()


# Stadtteile: Länge je Ring für das Zeichnen
for s in M["stadtteile"]:
    s["len"] = sum(math.dist(r[i], r[(i + 1) % len(r)]) for r in s["ringe"] for i in range(len(r)))
ST_NR = {s["nr"]: s for s in M["stadtteile"]}
NST = len(M["stadtteile"])


def teil_ring(ctx, proj, ring, rest):
    """zeichnet vom Ring die ersten `rest` Meter; gibt den Rest zurück."""
    p = proj(*ring[0])
    if p is None:
        return rest
    ctx.move_to(*p)
    for j in range(1, len(ring) + 1):
        a, b = ring[j - 1], ring[j % len(ring)]
        d = math.dist(a, b)
        if d >= rest:
            f = rest / d if d else 0
            q = proj(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            if q:
                ctx.line_to(*q)
            return 0.0
        q = proj(*b)
        if q:
            ctx.line_to(*q)
        rest -= d
    return rest


def grenzen(ctx, t, proj):
    a0, a1 = Z.P["stadtteile"]
    if t < a0:
        return
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    dauer = (a1 - a0) / NST
    for i, s in enumerate(M["stadtteile"]):
        x = Z.clamp((t - (a0 + i * dauer * 0.7)) / (dauer * 3.0))
        if x <= 0:
            continue
        if x >= 1:
            for r in s["ringe"]:
                ring_pfad(ctx, proj, r)
        else:
            rest = s["len"] * Z.ease(x)
            for r in s["ringe"]:
                if rest <= 0:
                    break
                rest = teil_ring(ctx, proj, r, rest)
        aktiv = x < 1 or t < a1 + 0.3
        fade = Z.seg(t, a1 + 0.3, a1 + 1.4)
        if aktiv:
            ctx.set_source_rgba(*hexrgb(ACCENT, 0.95))
            ctx.set_line_width(1.7)
        else:
            ctx.set_source_rgba(*hexrgb(ACCENT, Z.lerp(0.9, 0.0, fade)))
            ctx.set_line_width(Z.lerp(1.5, 0.8, fade))
            ctx.stroke_preserve()
            ctx.set_source_rgba(*hexrgb(INK, 0.38 * fade))
        ctx.stroke()


def rechteck(ctx, t, proj):
    a = Z.seg(t, 0.6, 1.4) * (1 - Z.seg(t, Z.ZU0 + 0.6, Z.ZU0 + 1.6))
    if a <= 0:
        return
    b = M["bbox"]
    pts = [proj(b[0], b[1]), proj(b[2], b[1]), proj(b[2], b[3]), proj(b[0], b[3])]
    if any(p is None for p in pts):
        return
    ctx.set_source_rgba(*hexrgb(INK, 0.55 * a))
    ctx.set_line_width(0.9)
    ctx.set_dash([7, 5])
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.stroke()
    ctx.set_dash([])
    # Beschriftung an der unteren linken Ecke, im Kartenbereich gehalten
    lx = min(max(pts[0][0] + 8, RI + 40), MAPR - 470)
    ly = min(max(pts[0][1] - 10, RI + 140), TL_Y - 70)
    bw = (M["bbox_utm"][2] - M["bbox_utm"][0]) / 1000
    bh = (M["bbox_utm"][3] - M["bbox_utm"][1]) / 1000
    text(ctx, f"Abrufrechteck Gebäude und Nutzung {de(int(bw))} × {de(int(bh))} km (config/potsdam.yaml, bbox)", lx, ly, F_MED, 13, INK,
         alpha=0.8 * a)


def kachel_marke(ctx, t, proj):
    """aktuelle Kachel im Gebäude- und im Nutzungslauf (zeilenweise wie die Pipeline)."""
    for q, (km, nx, ny), dauer_ab in (("gebaeude_alkis", M["kachel_geb"], Z.GROW + 0.2), ("alkis_nutzung", M["kachel_nutz"], 0.4)):
        a, b = Z.P[q]
        if not (a <= t < b - dauer_ab + 0.05):
            continue
        n = nx * ny
        i = min(n - 1, int((t - a) / (b - a - dauer_ab) * n))
        r, c = divmod(i, nx)
        bb = M["bbox"]
        x0, y0 = bb[0] + c * km, bb[1] + r * km
        x1, y1 = min(x0 + km, bb[2]), min(y0 + km, bb[3])
        pts = [proj(x0, y0), proj(x1, y0), proj(x1, y1), proj(x0, y1)]
        if any(p is None for p in pts):
            continue
        ctx.set_source_rgba(*hexrgb(PETROL, 0.95))
        ctx.set_line_width(2.0)
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.stroke()
        # Zeile: dünne Linie über die ganze Breite
        pa, pb = proj(bb[0], y0), proj(bb[2], y0)
        if pa and pb:
            linie(ctx, pa[0], pa[1], pb[0], pb[1], PETROL, 0.8, 0.5)


def einrichtungen(ctx, t, proj):
    for q, pts, form in (("mbjs_kita", M["kita"], "kreis"), ("mbjs_schule", M["schule"], "quadrat")):
        a, b = Z.P[q]
        if t < a:
            continue
        aus = 1 - Z.seg(t, Z.ZU0 + 0.2, Z.ZU0 + 1.0)
        if aus <= 0:
            continue
        n = len(pts)
        for i, (x, y, _innen) in enumerate(pts):
            t_i = a + 0.15 + i / n * (b - a - 0.6)
            u = Z.seg(t, t_i, t_i + 0.25)
            if u <= 0:
                continue
            p = proj(x, y, 2.0)
            if p is None or p[0] > MAPR - 4:
                continue
            neu = 1 - Z.seg(t, t_i + 0.25, t_i + 0.9)
            r = 3.2 + 3.0 * neu * u
            ctx.set_line_width(1.1)
            if form == "kreis":
                ctx.arc(p[0], p[1], r, 0, 2 * math.pi)
            else:
                ctx.rectangle(p[0] - r, p[1] - r, 2 * r, 2 * r)
            ctx.set_source_rgba(*hexrgb(SURFACE if form == "quadrat" else INK, 0.95 * u * aus))
            ctx.fill_preserve()
            ctx.set_source_rgba(*hexrgb(INK, 0.95 * u * aus))
            ctx.stroke()


def schleier(ctx, t, proj):
    """Zuordnung: außerhalb der Stadtgrenze tritt alles zurück (Papier darüber), die Grenze wird gezogen."""
    a = Z.ease(Z.seg(t, Z.ZU0 + 0.6, Z.ZU0 + 1.8))
    if a <= 0:
        return
    ctx.save()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.rectangle(0, 0, W, H)
    for r in M["stadt_ringe"]:
        ring_pfad(ctx, proj, r)
    ctx.set_source_rgba(*hexrgb(GROUND, 0.84 * a))
    ctx.fill()
    ctx.restore()
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for r in M["stadt_ringe"]:
        ring_pfad(ctx, proj, r)
    ctx.set_source_rgba(*hexrgb(INK, 0.85 * a))
    ctx.set_line_width(1.6)
    ctx.stroke()


def grenzzellen(ctx, t, proj):
    a = Z.seg(t, Z.ZU0 + 1.6, Z.ZU0 + 2.2) * (1 - Z.seg(t, Z.AW0 + 0.2, Z.AW0 + 0.9))
    if a <= 0:
        return
    for q in M["grenz_zellen"]:
        ring_pfad(ctx, proj, q, 1.0)
    ctx.set_source_rgba(*hexrgb(ACCENT, 0.95 * a))
    ctx.set_line_width(1.5)
    ctx.stroke()


def befund_marken(ctx, t, proj):
    a = Z.seg(t, Z.BF0 + 0.3, Z.BF0 + 1.0)
    if a <= 0:
        return
    B = M["befunde"]["altbau"]
    for (nr, name, wert), seite in ((B["max"], -1), (B["min"], 1)):
        s = ST_NR[nr]
        for r in s["ringe"]:
            ring_pfad(ctx, proj, r)
        ctx.set_source_rgba(*hexrgb(ACCENT, a))
        ctx.set_line_width(2.6)
        ctx.stroke()
        p = proj(s["gx"], s["gy"], 30.0)  # Schwerpunkt der Gebäude des Stadtteils
        if p is None:
            continue
        # Fahne: Name und Wert, links bzw. rechts vom Stadtteil, im Kartenbereich gehalten
        fx = min(max(p[0] + seite * 150, RI + 30 + (230 if seite < 0 else 0)), MAPR - 30 - (0 if seite < 0 else 230))
        fy = min(max(p[1] - 110, RI + 150), TL_Y - 120)
        linie(ctx, p[0], p[1], fx, fy + 8, INK, 1.0, a)
        ctx.set_source_rgba(*hexrgb(INK, a))
        ctx.arc(p[0], p[1], 3.5, 0, 2 * math.pi)
        ctx.fill()
        al = "r" if seite < 0 else "l"
        bw = max(breite(ctx, name, F_DISP, 22), breite(ctx, dez(wert) + " %", F_DISP, 46)) + 24
        bx = fx - bw if seite < 0 else fx
        ctx.set_source_rgba(*hexrgb(SURFACE, 0.92 * a))
        ctx.rectangle(bx, fy - 60, bw, 92)
        ctx.fill()
        tx = fx - 12 if seite < 0 else fx + 12
        text(ctx, dez(wert) + " %", tx, fy - 14, F_DISP, 46, INK, al, alpha=a)
        text(ctx, name, tx, fy + 16, F_DISP_S, 20, INK, al, alpha=a)


def befund_balken(ctx, t):
    """Wohnungen in Häusern von vor 1949 je Stadtteil (ab 1.000 Einwohnern), absteigend; die beiden markierten
    Stadtteile in Lila, Linie = Potsdam. Werte aus daten/kennzahlen.json (über meta.json)."""
    a = Z.seg(t, Z.BF0 + 0.6, Z.BF0 + 1.3)
    if a <= 0:
        return
    B = M["befunde"]["altbau"]
    rang = B["rang"]
    x0, yb, bw, gap, hmax = 64, TL_Y - 84, 13, 4, 150.0
    breite_ = len(rang) * (bw + gap) - gap
    ctx.set_source_rgba(*hexrgb(GROUND, 0.92 * a))
    ctx.rectangle(x0 - 14, yb - hmax - 74, breite_ + 28, hmax + 108)
    ctx.fill()
    text(ctx, "WOHNUNGEN IN HÄUSERN VON VOR 1949, JE STADTTEIL", x0, yb - hmax - 50, F_SEMI, 11, MUTED, track=1.2,
         alpha=a, tab=False)
    text(ctx, f"{de(len(rang))} Stadtteile ab 1.000 Einwohnern, Zensus 2022, absteigend", x0, yb - hmax - 32, F_TXT,
         12.5, MUTED, alpha=a)
    vmax = rang[0][2]
    markiert = {B["max"][0], B["min"][0]}
    for i, (nr, _name, v) in enumerate(rang):
        x = x0 + i * (bw + gap)
        h = max(1.5, hmax * v / vmax * Z.ease(Z.seg(t, Z.BF0 + 0.8 + i * 0.03, Z.BF0 + 1.6 + i * 0.03)))
        ctx.set_source_rgba(*hexrgb(ACCENT if nr in markiert else "#9aa19c", a))
        ctx.rectangle(x, yb - h, bw, h)
        ctx.fill()
    linie(ctx, x0 - 4, yb, x0 + breite_ + 4, yb, INK, 0.8, a)
    ys = yb - hmax * B["stadt"] / vmax
    ctx.set_dash([4, 3])
    linie(ctx, x0 - 4, ys, x0 + breite_ + 4, ys, INK, 1.0, a)
    ctx.set_dash([])
    text(ctx, f"Potsdam {dez(B['stadt'])} %", x0 + breite_ + 4, ys - 5, F_MED, 12.5, INK, "r", alpha=a)
    text(ctx, f"{B['max'][1]} {dez(B['max'][2])} %", x0, yb + 18, F_MED, 12.5, ACCENT, alpha=a, tab=False)
    text(ctx, f"{B['min'][1]} {dez(B['min'][2])} %", x0 + breite_, yb + 18, F_MED, 12.5, ACCENT, "r", alpha=a,
         tab=False)


# ---------------- Schriftfeld
def _kacheln_gestartet(t, a, b, je):
    n = len(je)
    k = int(math.floor((t - a) / b * n)) + 1 if t >= a else 0
    return sum(je[:max(0, min(n, k))])


def zaehler(t, q):
    """Zähler „neu“ genau wie im Bild: was bis t erschienen ist (gleiche Zeitformeln wie szene.py/overlay)."""
    a, b = Z.P[q]
    n = LAUF[q]["neu"]
    if q == "stadtteile":
        d = (b - a) / NST
        return sum(1 for i in range(NST) if t >= a + i * d * 0.7 + d * 3.0)
    if q == "zensus_gitter":
        return min(n, int(math.floor((t - a) / (b - a - Z.ZELL_IN) * n)) + 1)
    if q == "gebaeude_alkis":
        return _kacheln_gestartet(t, a, b - a - Z.GROW - 0.2, M["je_kachel_geb"])
    if q == "alkis_nutzung":
        return _kacheln_gestartet(t, a, b - a - 0.4, M["je_kachel_nutz"])
    if q in ("mbjs_kita", "mbjs_schule"):
        return sum(1 for i in range(n) if t >= a + 0.15 + i / n * (b - a - 0.6))
    return int(round(n * Z.seg(t, a + 0.1, b - 0.3)))


def farb_start(i):
    """Beginn der Umfärbung des i-ten Stadtteils (gleiche Formel wie tff in szene.py)."""
    return Z.AW0 + 0.2 + i / NST * (Z.AW1 - Z.AW0 - Z.FARB_DAUER - 0.6)


def bauzeit_stand(t):
    """Zählung der Gebäude, deren Stadtteil sich bis t zu färben begonnen hat: (k[8], nd, je_g, Stadtteile)."""
    k, nd, g, n = [0] * 8, 0, {}, 0
    for i, j in enumerate(M["je_teil"]):
        if t < farb_start(i):
            continue
        n += 1
        k = [a + b for a, b in zip(k, j["k"])]
        nd += j["nd"]
        for kk, v in j["g"].items():
            g[kk] = g.get(kk, 0) + v
    return k, nd, g, n


assert bauzeit_stand(Z.BF0)[:3] == (ZA["k"], ZA["nd"], ZA["je_g"]), "Zählung je Stadtteil ungleich Summe"


def lauf_zeige(t, q):
    """(Zustand, neu angezeigt): 0 offen, 1 läuft, 2 fertig."""
    a, b = Z.P[q]
    n = LAUF[q]["neu"]
    if t < a:
        return 0, 0
    if t >= b:
        return 2, n
    z = min(n, zaehler(t, q))
    return 1, z


def kopfbox(ctx):
    ctx.set_source_rgba(*hexrgb(GROUND, 0.97))
    ctx.rectangle(PX, RI, PR - PX, H - 2 * RI)
    ctx.fill()
    linie(ctx, PX, RI, PX, H - RI, INK, 0.9)
    text(ctx, "KIEZATLAS POTSDAM", XT, 72, F_SEMI, 13, ACCENT, track=2.2)
    text(ctx, "Potsdam wächst aus den Daten", XT, 110, F_DISP, 33, INK, tab=False)
    linie(ctx, PX, 130, PR, 130, INK, 0.6)


def tabelle(ctx, t):
    text(ctx, "Sieben Importläufe, 04. und 05.11.2026", XT, 158, F_MED, 15, INK, tab=False)
    text(ctx, "Geodaten-Import-Pipeline · Berichte in belege/", XT, 179, F_TXT, 13, MUTED, tab=False)
    y = 214
    cols = (("NEU", XT + 226), ("GEÄND.", XT + 290), ("GELÖSCHT", XT + 362), ("LAUFZEIT", XR))
    text(ctx, "QUELLE", XT, y, F_SEMI, 10.5, MUTED, track=1.4)
    for lab, x in cols:
        text(ctx, lab, x, y, F_SEMI, 10.5, MUTED, "r", track=1.4)
    linie(ctx, XT, y + 9, XR, y + 9, INK, 0.5, 0.5)
    for i, l in enumerate(M["laeufe"]):
        q = l["quelle"]
        yy = y + 34 + i * 27
        z, n = lauf_zeige(t, q)
        if z == 0:
            ctx.set_source_rgba(*hexrgb(INK, 0.45))
            ctx.set_line_width(0.8)
            ctx.rectangle(XT, yy - 9, 8, 8)
            ctx.stroke()
        else:
            ctx.set_source_rgba(*hexrgb(PETROL if z == 1 else INK))
            ctx.rectangle(XT, yy - 9, 8, 8)
            ctx.fill()
        w = text(ctx, q, XT + 18, yy, F_MED, 14, INK, alpha=1.0 if z else 0.45, tab=False)
        if z == 2 and l["unvollstaendig"]:
            ctx.set_source_rgba(*hexrgb(ACCENT))
            ctx.rectangle(XT + 18 + w + 6, yy - 8, 6, 6)
            ctx.fill()
        if z:
            text(ctx, de(n), cols[0][1], yy, F_TXT, 14, PETROL if z == 1 else INK, "r")
        if z == 2:  # erst nach Abschluss der Zeile: geändert, gelöscht, Laufzeit
            text(ctx, de(l["geaendert"]), cols[1][1], yy, F_TXT, 14, INK, "r")
            text(ctx, de(l["geloescht"]), cols[2][1], yy, F_TXT, 14, INK, "r")
            text(ctx, lz_txt(l["laufzeit_s"]) + " s", cols[3][1], yy, F_TXT, 14, INK, "r")
    yb = y + 34 + 7 * 27 - 8
    linie(ctx, XT, yb, XR, yb, INK, 0.5, 0.5)
    if t >= Z.LAEUFE_FERTIG:
        a = Z.seg(t, Z.LAEUFE_FERTIG, Z.LAEUFE_FERTIG + 0.5)
        text(ctx, f"zusammen {lz_txt(ZA['summe_laufzeit'])} s · {de(ZA['summe_neu'])} neu · "
             f"{de(ZA['summe_geaendert'])} geändert · {de(ZA['summe_geloescht'])} gelöscht",
             XT, yb + 21, F_MED, 13, INK, alpha=a)
    else:
        i = Z.phase_jetzt(t)
        l = M["laeufe"][i] if i is not None else M["laeufe"][0]
        text(ctx, f"aktueller Lauf: {l['datei']}", XT, yb + 21, F_TXT, 13, MUTED, tab=False)
    unv = [l["quelle"] for l in M["laeufe"] if lauf_zeige(t, l["quelle"])[0] == 2 and l["unvollstaendig"]]
    if unv:
        ctx.set_source_rgba(*hexrgb(ACCENT))
        ctx.rectangle(XT, yb + 37, 6, 6)
        ctx.fill()
        text(ctx, f"{', '.join(unv)}: im Bericht als unvollständig markiert, Status ok", XT + 14, yb + 44, F_TXT, 13,
             MUTED, tab=False)
    linie(ctx, PX, 488, PR, 488, INK, 0.6)


def grosszahl(ctx, t):
    y = 520
    i = Z.phase_jetzt(t)
    if t < Z.P["stadtteile"][0]:
        B = M["befunde"]["altbau"]
        a = Z.seg(t, 0.1, 0.5) * (1 - Z.seg(t, Z.P["stadtteile"][0] - 0.3, Z.P["stadtteile"][0]))
        text(ctx, "VORAB, DER BEFUND", XT, y + 4, F_SEMI, 11, ACCENT, track=1.5, alpha=a, tab=False)
        tz = f"{dez(B['max'][2])} % gegen {dez(B['min'][2])} %"
        gr = 64
        while breite(ctx, tz, F_DISP, gr) > XR - XT and gr > 30:
            gr -= 2
        text(ctx, tz, XT - 3, y + 80, F_DISP, gr, INK, alpha=a)
        absatz(ctx, f"der Wohnungen in Häusern von vor 1949: {B['max'][1]} gegen {B['min'][1]} (Zensus 2022). "
               "Wie man das aus sieben Importläufen erfährt:", XT + 2, y + 112, F_TXT, 17, INK, XR - XT, alpha=a)
        return
    if i is not None:
        l = M["laeufe"][i]
        q = l["quelle"]
        z, n = lauf_zeige(t, q)
        text(ctx, f"{q.upper()} · NEU", XT, y + 4, F_SEMI, 11, MUTED, track=1.5, tab=False)
        text(ctx, de(n), XT - 4, y + 96, F_DISP, 92, PETROL if z == 1 else INK)
        lz, fd, f = Z.faktor(q)
        art = (f"Zeitraffer {dez(f, 0 if f >= 10 else 1)}×" if f >= 1.05
               else (f"gedehnt, Faktor {dez(f, 2)}" if f < 0.95 else "etwa Echtzeit"))
        text(ctx, f"Lauf {l['lauf_id']} · {datum(l['lauf_id'])}", XT, y + 124, F_MED, 13.5, INK)
        text(ctx, f"Laufzeit {lz_txt(lz)} s · im Film {dez(fd)} s · {art}", XT, y + 144, F_TXT, 13.5, INK)
        if q == "gebaeude_alkis":
            km, nx, ny = M["kachel_geb"]
            a, b = Z.P[q]
            k = min(nx * ny, int(Z.seg(t, a, b - Z.GROW - 0.2) * nx * ny) + 1)
            text(ctx, f"Kachel {de(k)} von {de(nx * ny)} · {de(int(km))} m, zeilenweise ab Südwest", XT, y + 164,
                 F_TXT, 13.5, MUTED)
        elif q == "alkis_nutzung":
            km, nx, ny = M["kachel_nutz"]
            a, b = Z.P[q]
            k = min(nx * ny, int(Z.seg(t, a, b - 0.4) * nx * ny) + 1)
            text(ctx, f"Kachel {de(k)} von {de(nx * ny)} · {de(int(km))} m, zeilenweise ab Südwest", XT, y + 164,
                 F_TXT, 13.5, MUTED)
        return
    if t < Z.ZU0:
        return
    if t < Z.AW0:
        a = Z.seg(t, Z.ZU0, Z.ZU0 + 0.5)
        text(ctx, "ZUORDNUNG ZU POTSDAM", XT, y + 4, F_SEMI, 11, MUTED, track=1.5, alpha=a)
        x = Z.ease(Z.seg(t, Z.ZU0 + 0.8, Z.ZU0 + 2.4))
        g = int(round(Z.lerp(ZA["geb_rechteck"], ZA["geb_potsdam"], x)))
        zz = int(round(Z.lerp(ZA["zellen_rechteck"], ZA["zellen_potsdam"], x)))
        text(ctx, de(g), XT - 3, y + 80, F_DISP, 70, INK, alpha=a)
        text(ctx, "Gebäude", XT + 2, y + 104, F_MED, 14, INK, alpha=a, tab=False)
        text(ctx, de(zz), XT + 236, y + 80, F_DISP, 70, INK, alpha=a)
        text(ctx, "Zensus-Zellen", XT + 240, y + 104, F_MED, 14, INK, alpha=a, tab=False)
        b = Z.seg(t, Z.ZU0 + 2.4, Z.ZU0 + 2.9)
        text(ctx, f"von {de(ZA['geb_rechteck'])} im Abrufrechteck", XT + 2, y + 124, F_TXT, 13, MUTED, alpha=b)
        text(ctx, f"von {de(ZA['zellen_rechteck'])} im Gitterlauf", XT + 240, y + 124, F_TXT, 13, MUTED, alpha=b)
        text(ctx, f"{de(ZA['einwohner'])} Einwohner (Zensus 2022) in {de(ZA['zellen_potsdam'])} Zellen", XT + 2,
             y + 150, F_MED, 13.5, INK, alpha=b)
        return
    if t < Z.BF0:
        a = Z.seg(t, Z.AW0, Z.AW0 + 0.5)
        text(ctx, "AUSWERTUNG · BAUZEIT JE GEBÄUDE", XT, y + 4, F_SEMI, 11, MUTED, track=1.5, alpha=a, tab=False)
        _k, _nd, g, nt = bauzeit_stand(t)
        fertig = nt == NST
        text(ctx, de(g.get("geschaetzt", 0)), XT - 3, y + 80, F_DISP, 70, INK if fertig else PETROL, alpha=a)
        text(ctx, "geschätzt", XT + 2, y + 104, F_MED, 14, INK, alpha=a, tab=False)
        text(ctx, de(g.get("belegt", 0)), XT + 236, y + 80, F_DISP, 70, INK if fertig else PETROL, alpha=a)
        text(ctx, "belegt", XT + 240, y + 104, F_MED, 14, INK, alpha=a, tab=False)
        text(ctx, f"Stadtteil {de(nt)} von {de(NST)}", XR, y + 4, F_SEMI, 11, MUTED, "r", track=1.0, alpha=a)
        text(ctx, f"{de(g.get('nicht_datiert', 0))} nicht datiert · Stand der Auswertung "
             f"{ZA['stand_auswertung'][8:10]}.{ZA['stand_auswertung'][5:7]}.{ZA['stand_auswertung'][0:4]}",
             XT + 2, y + 128, F_TXT, 13, MUTED, alpha=a)
        text(ctx, "Kein Lauf liefert die Bauzeit: Sie ist aus dem Zensus-Baujahr", XT + 2, y + 150, F_TXT, 13, INK,
             alpha=a, tab=False)
        text(ctx, "je Zelle nach Gebäudeform auf die Häuser verteilt.", XT + 2, y + 168, F_TXT, 13, INK, alpha=a,
             tab=False)
        return
    B = M["befunde"]["altbau"]
    a = Z.seg(t, Z.BF0, Z.BF0 + 0.6)
    text(ctx, "BEFUND ÜBER POTSDAM", XT, y + 4, F_SEMI, 11, ACCENT, track=1.5, alpha=a)
    text(ctx, dez(B["stadt"]) + " %", XT - 3, y + 80, F_DISP, 70, INK, alpha=a)
    text(ctx, "der Wohnungen in Häusern von vor 1949", XT + 2, y + 104, F_MED, 14, INK, alpha=a, tab=False)
    b = Z.seg(t, Z.BF0 + 0.8, Z.BF0 + 1.4)
    absatz(ctx, B["satz"], XT + 2, y + 134, F_TXT, 15, INK, XR - XT, alpha=b)


def legende(ctx, t):
    y = 724
    lw = XR - XT

    def gruppe(alpha):
        ctx.push_group()
        return alpha

    def ende(alpha):
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(alpha)

    g0 = Z.P["gebaeude_alkis"][0]
    if Z.P["zensus_gitter"][0] - 0.3 <= t < g0 + 1.2:
        a = Z.seg(t, Z.P["zensus_gitter"][0] - 0.3, Z.P["zensus_gitter"][0] + 0.3) * (1 - Z.seg(t, g0 + 0.6, g0 + 1.2))
        ctx.push_group()
        text(ctx, "EINWOHNER JE ZELLE (100 × 100 m)", XT, y, F_SEMI, 11, MUTED, track=1.4)
        gr = M["ew_grenzen"]
        labs = [f"unter {gr[0]}"] + [f"{gr[i]} bis {gr[i + 1] - 1}" for i in range(len(gr) - 1)] + [f"{gr[-1]} und mehr"]
        for i, lab in enumerate(labs):
            yy = y + 26 + i * 21
            swatch(ctx, XT, yy, M["stufen"][i])
            text(ctx, lab, XT + 32, yy, F_TXT, 13.5, INK)
            text(ctx, f"{de(M['ew_klassen_anz'][i])} Zellen in Potsdam", XR, yy, F_TXT, 12.5, MUTED, "r")
        yy = y + 26 + len(labs) * 21 + 6
        absatz(ctx, f"Klassen wie auf der Seite: Quintile über die {de(ZA['zellen_potsdam'])} Zellen in Potsdam. "
               "Zensus 2022, Stichtag 15.05.2022. Reihenfolge der Füllung nach Gitterkennung, schematisch.",
               XT, yy, F_TXT, 12.5, MUTED, lw)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)
    elif g0 + 0.6 <= t < Z.P["mbjs_kita"][0]:
        a = Z.seg(t, g0 + 0.6, g0 + 1.2) * (1 - Z.seg(t, Z.P["mbjs_kita"][0] - 0.4, Z.P["mbjs_kita"][0]))
        ctx.push_group()
        text(ctx, "GEBÄUDE", XT, y, F_SEMI, 11, MUTED, track=1.4)
        hq = ZA["hq"]
        swatch(ctx, XT, y + 26, INK)
        text(ctx, "dunkel: in diesem Lauf neu", XT + 32, y + 26, F_TXT, 13.5, INK, tab=False)
        swatch(ctx, XT, y + 48, M["geb_nd"])
        text(ctx, f"{de(ZA['geb_potsdam'])} in Potsdam, Höhe in Metern:", XT + 32, y + 48, F_TXT, 13.5, INK)
        for j, (k, lab) in enumerate((("kataster", "ALKIS-Objekthöhe (NAS-Bestand)"), ("geschosse", "Geschosse × 3 m"),
                                      ("ersatz", "ohne Angabe: 3 m"))):
            text(ctx, lab, XT + 44, y + 68 + j * 18, F_TXT, 12.5, INK, tab=False)
            text(ctx, de(hq[k]), XR, y + 68 + j * 18, F_TXT, 12.5, INK, "r")
        swatch(ctx, XT, y + 136, "#e5e7e2")
        text(ctx, f"{de(ZA['geb_aussen'])} außerhalb: nur Grundriss, flach", XT + 32, y + 136, F_TXT, 13.5, INK)
        absatz(ctx, "Grundrisse aus diesem Lauf; die Höhe stammt nicht aus dem Lauf, sondern aus dem ALKIS-NAS-Bestand "
               "der Auswertung.", XT, y + 162, F_TXT, 12.5, MUTED, lw)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)
    elif Z.P["mbjs_kita"][0] <= t < Z.P["alkis_nutzung"][0]:
        a = Z.seg(t, Z.P["mbjs_kita"][0], Z.P["mbjs_kita"][0] + 0.4) * (
            1 - Z.seg(t, Z.P["alkis_nutzung"][0] - 0.3, Z.P["alkis_nutzung"][0]))
        ctx.push_group()
        L = LAUF["mbjs_kita"]
        ctx.set_source_rgba(*hexrgb(INK))
        ctx.arc(XT + 6, y - 4, 4, 0, 2 * math.pi)
        ctx.fill()
        text(ctx, f"Kita ({de(L['neu'])})", XT + 18, y, F_MED, 13.5, INK)
        ctx.set_source_rgba(*hexrgb(INK))
        ctx.set_line_width(1.1)
        ctx.rectangle(XT + 150, y - 8, 8, 8)
        ctx.stroke()
        b = Z.seg(t, Z.P["mbjs_schule"][0], Z.P["mbjs_schule"][0] + 0.3)
        text(ctx, f"Schule ({de(LAUF['mbjs_schule']['neu'])})", XT + 166, y, F_MED, 13.5, INK, alpha=0.35 + 0.65 * b)
        text(ctx, "Lage ohne Namen und Adresse", XR, y, F_TXT, 12.5, MUTED, "r", tab=False)
        c = Z.seg(t, Z.P["mbjs_kita"][1] - 1.6, Z.P["mbjs_kita"][1] - 1.1)
        yy = y + 30
        ctx.set_source_rgba(*hexrgb(ACCENT, c))
        ctx.rectangle(XT, yy - 9, 6, 6)
        ctx.fill()
        text(ctx, "WARNUNG IM BERICHT DES KITA-LAUFS", XT + 14, yy - 2, F_SEMI, 11, MUTED, track=1.2, alpha=c, tab=False)
        yy = absatz(ctx, L["warnungen"][0], XT, yy + 20, F_MED, 13.5, INK, lw, alpha=c)
        yy = absatz(ctx, "Hinweis: " + L["hinweise"][0], XT, yy + 2, F_TXT, 12.5, MUTED, lw, alpha=c)
        d = Z.seg(t, Z.P["mbjs_kita"][1] - 0.3, Z.P["mbjs_kita"][1] + 0.3)
        KR = M["kita_readme"]
        text(ctx, f"ERKLÄRUNG IN BELEGE/README.MD, ZEILE {KR['zeile']}", XT, yy + 14, F_SEMI, 11, MUTED, track=1.2,
             alpha=d, tab=False)
        absatz(ctx, KR["text"].replace("`", ""), XT, yy + 34, F_TXT, 13.5, INK, lw, alpha=d)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)
    elif Z.P["alkis_nutzung"][0] <= t < Z.P["zensus_struktur"][0]:
        a = Z.seg(t, Z.P["alkis_nutzung"][0], Z.P["alkis_nutzung"][0] + 0.4) * (
            1 - Z.seg(t, Z.P["zensus_struktur"][0] - 0.3, Z.P["zensus_struktur"][0]))
        ctx.push_group()
        text(ctx, "TATSÄCHLICHE NUTZUNG (ALKIS)", XT, y, F_SEMI, 11, MUTED, track=1.4)
        zus = {}
        for gname, (farbe, n) in M["nutzung_gruppen"].items():
            zus.setdefault(farbe, []).append((gname, n))
        for j, (farbe, gl) in enumerate(zus.items()):
            yy = y + 26 + j * 21
            r, g, b_ = (int(v) for v in farbe[4:-1].split(","))
            swatch(ctx, XT, yy, f"#{r:02x}{g:02x}{b_:02x}")
            text(ctx, " · ".join(x[0] for x in gl), XT + 32, yy, F_TXT, 13.5, INK, tab=False)
            text(ctx, f"{de(sum(x[1] for x in gl))} Flächen", XR, yy, F_TXT, 12.5, MUTED, "r")
        absatz(ctx, "Grautöne der Grundkarte auf der Seite; die Gruppen sind für die Darstellung zusammengefasst.",
               XT, y + 26 + len(zus) * 21 + 6, F_TXT, 12.5, MUTED, lw)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)
    elif Z.P["zensus_struktur"][0] <= t < Z.ZU0:
        a = Z.seg(t, Z.P["zensus_struktur"][0], Z.P["zensus_struktur"][0] + 0.4) * (1 - Z.seg(t, Z.ZU0 - 0.3, Z.ZU0))
        ctx.push_group()
        text(ctx, "ZENSUS_STRUKTUR", XT, y, F_SEMI, 11, MUTED, track=1.4)
        absatz(ctx, "Weitere Merkmale je 100-m-Zelle: Haushalte, Familien, Staatsangehörigkeit, Miete, Leerstand "
               "(Zielspalten in config/potsdam.yaml).", XT, y + 26, F_TXT, 13.5, INK, lw)
        swatch(ctx, XT, y + 90, SURFACE)
        text(ctx, "leuchtet: Zelle mit Strukturdaten", XT + 32, y + 90, F_TXT, 13.5, INK, tab=False)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)
    elif Z.ZU0 <= t < Z.AW0:
        a = Z.seg(t, Z.ZU0 + 0.6, Z.ZU0 + 1.2) * (1 - Z.seg(t, Z.AW0 - 0.3, Z.AW0))
        ctx.push_group()
        text(ctx, "WIE ZUGEORDNET WIRD", XT, y, F_SEMI, 11, MUTED, track=1.4)
        linie(ctx, XT, y + 21, XT + 22, y + 21, INK, 1.6)
        text(ctx, "Stadtgrenze (32 Stadtteile)", XT + 32, y + 26, F_TXT, 13.5, INK, tab=False)
        text(ctx, "Gebäude: Punkt im Umriss liegt im Stadtteil", XT + 32, y + 48, F_TXT, 13.5, INK, tab=False)
        text(ctx, "Zelle: Mittelpunkt liegt im Stadtteil", XT + 32, y + 70, F_TXT, 13.5, INK, tab=False)
        ctx.set_source_rgba(*hexrgb(ACCENT))
        ctx.set_line_width(1.5)
        ctx.rectangle(XT + 4, y + 82, 12, 12)
        ctx.stroke()
        text(ctx, f"{de(ZA['grenzzellen'])} bewohnte Zellen schneiden die Grenze", XT + 32, y + 94, F_TXT, 13.5, INK)
        text(ctx, f"({de(ZA['grenz_ew'])} Einwohner), zugeordnet nach Mittelpunkt", XT + 32, y + 112, F_TXT, 13.5, INK)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)
    elif t >= Z.AW0:
        a = Z.seg(t, Z.AW0, Z.AW0 + 0.5) * (1 - Z.seg(t, Z.BF1 - 0.2, Z.BF1 + 0.3))
        if a <= 0:
            return
        y = 748  # unter dem Erklärtext der Auswertung bzw. dem Befund-Satz
        ctx.push_group()
        text(ctx, "FARBE = BAUZEIT-KLASSE JE GEBÄUDE, GESCHÄTZT", XT, y - 16, F_SEMI, 11, MUTED, track=1.2, tab=False)
        kz, ndz, _g, _n = bauzeit_stand(t)
        # im Befund: die beiden Klassen vor 1949 (erste Zeile) hervorheben
        hb = Z.seg(t, Z.BF0 + 0.3, Z.BF0 + 1.0)
        if hb > 0:
            ctx.set_source_rgba(*hexrgb(ACCENT, hb))
            ctx.set_line_width(1.4)
            ctx.rectangle(XT - 6, y - 7, lw + 12, 22)
            ctx.stroke()
        for i, (lab, col) in enumerate(zip(M["jahr_klassen"], M["palette"])):
            cx = XT + (i % 2) * 220
            yy = y + 8 + (i // 2) * 20
            swatch(ctx, cx, yy, col)
            text(ctx, lab, cx + 30, yy, F_TXT, 13, INK)
            text(ctx, de(kz[i]), cx + 206, yy, F_TXT, 12, MUTED, "r")
        yy = y + 8 + 4 * 20
        swatch(ctx, XT, yy, M["geb_nd"])
        text(ctx, "nicht datiert", XT + 30, yy, F_TXT, 13, INK, tab=False)
        text(ctx, de(ndz), XT + 206, yy, F_TXT, 12, MUTED, "r")
        absatz(ctx, "Zählung: Gebäude. Die Befunde zählen Wohnungen (Zensus 2022) in anderen Klassen.",
               XT, yy + 26, F_TXT, 12.5, MUTED, lw)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)


def nachweis(ctx, t):
    """Namensnennung für alles, was zur Zeit t im Bild zu sehen ist (nicht nur für den laufenden Lauf)."""
    N = M["namens"]
    P_ = Z.P
    z = []
    if t >= P_["stadtteile"][0]:
        z.append(N["stadtteile"])
    if t < P_["stadtteile"][0] or P_["zensus_gitter"][0] <= t < Z.AW0 + 1.0 or t >= Z.BF0:  # 00: Befund vorab
        z.append(N["zensus"])
    if t >= P_["gebaeude_alkis"][0] and t < Z.AW0 + 0.2:
        z.append(N["gebaeude"])
    if P_["mbjs_kita"][0] <= t < Z.ZU0 + 1.0:
        z.append(N["mbjs"])
    if t >= P_["alkis_nutzung"][0] and N["lgb"] not in z:
        z.append(N["lgb"])
    if t >= Z.AW0 + 0.2:
        z.append(N["jahre_zensus"] + "; " + N["wikidata"])
    if not z:
        z = [N["stadtteile"]]
    zeilen = []
    for s in z:
        zeilen.extend(umbruch(ctx, s, F_TXT, 11.5, XR - XT))
    y0 = H - RI - 14 - (len(zeilen) - 1) * 15
    linie(ctx, PX, y0 - 22, PR, y0 - 22, INK, 0.6)
    for j, s in enumerate(zeilen):
        text(ctx, s, XT, y0 + j * 15, F_TXT, 11.5, INK, tab=False)


def abspann(ctx, t):
    a = Z.seg(t, Z.BF1, Z.BF1 + 0.6)
    if a <= 0:
        return
    ctx.push_group()
    y = 520
    text(ctx, "WAS DIE DATEN ÜBER POTSDAM SAGEN", XT, y + 4, F_SEMI, 11, ACCENT, track=1.5, tab=False)
    yy = absatz(ctx, M["befunde"]["altbau"]["satz"], XT, y + 40, F_MED, 22, INK, XR - XT, lh=28)
    yy = absatz(ctx, M["befunde"]["fernwaerme"]["satz"], XT, yy + 14, F_MED, 22, INK, XR - XT, lh=28)
    yy = absatz(ctx, "Anteile der Wohnungen, Zensus 2022, Stadtteile ab 1.000 Einwohnern; daten/kennzahlen.json. "
                "Lizenztexte: govdata.de/dl-de/by-2-0", XT, yy + 4, F_TXT, 12.5, MUTED, XR - XT)
    absatz(ctx, "Film: André Stiebitz, Stiebitz Souverain Systems UG, mit KI-Unterstützung erstellt", XT, yy + 8,
           F_TXT, 12.5, INK, XR - XT)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)


def kopf(ctx, t):
    i = Z.phase_jetzt(t)
    if t < Z.P["stadtteile"][0] - 0.2:
        nr, tit, unt = "00", "Potsdam, bevor die Daten kommen", "Papier, Abrufrechteck, sonst nichts"
    elif i is not None:
        l = M["laeufe"][i]
        nr = f"{i + 1:02d}"
        tit = {"stadtteile": "Stadtteilgrenzen", "zensus_gitter": "Zensus-Gitter, Einwohner je Zelle",
               "gebaeude_alkis": "Gebäude aus dem Kataster", "mbjs_kita": "Kitas", "mbjs_schule": "Schulen",
               "alkis_nutzung": "Tatsächliche Nutzung", "zensus_struktur": "Zensus, weitere Merkmale"}[l["quelle"]]
        unt = f"Importlauf {l['lauf_id']} · {l['quelle']}"
    elif t < Z.ZU0:
        nr, tit, unt = "07", "Zensus, weitere Merkmale", f"Importlauf {M['laeufe'][-1]['lauf_id']} · zensus_struktur"
    elif t < Z.AW0:
        nr, tit, unt = "08", "Was davon in Potsdam liegt", "Auswertung, Zuordnung zu den Stadtteilen"
    elif t < Z.BF0:
        nr, tit, unt = "09", "Bauzeit je Gebäude", "Auswertung, Stadtteil für Stadtteil"
    else:
        nr, tit, unt = "10", "Wo Potsdam alt ist und wo nicht", "Befund aus daten/kennzahlen.json"
    w1 = breite(ctx, tit, F_DISP, 24, tab=False)
    w2 = breite(ctx, unt, F_TXT, 14)
    ctx.set_source_rgba(*hexrgb(GROUND, 0.88))
    ctx.rectangle(52, 50, 128 + max(w1, w2) + 16 - 52, 66)
    ctx.fill()
    text(ctx, nr, 62, 100, F_DISP, 52, ACCENT)
    text(ctx, tit, 128, 80, F_DISP, 24, INK, tab=False)
    text(ctx, unt, 128, 101, F_TXT, 14, MUTED)


def zeitleiste(ctx, t):
    """Balken mit den sieben Läufen, Länge je Lauf nach laufzeit_s; Marke = Stand im Lauf."""
    ges = ZA["summe_laufzeit"]
    ctx.set_source_rgba(*hexrgb(GROUND, 0.88))
    ctx.rectangle(TL_X0 - 14, TL_Y - 32, TL_X1 - TL_X0 + 28, 52)
    ctx.fill()
    text(ctx, f"ZEITLEISTE NACH LAUFZEIT_S · 7 LÄUFE · {lz_txt(ges)} s · Pausen zwischen den Läufen weggelassen",
         TL_X0, TL_Y - 14, F_SEMI, 10.5, MUTED, track=1.1, tab=False)
    x = TL_X0
    pos = None
    for i, l in enumerate(M["laeufe"]):
        w = (TL_X1 - TL_X0) * l["laufzeit_s"] / ges
        a, b = Z.P[l["quelle"]]
        z = 2 if t >= b else (1 if t >= a else 0)
        ctx.set_source_rgba(*hexrgb(INK if z == 2 else (PETROL if z == 1 else LINE)))
        ctx.rectangle(x, TL_Y - 4, max(w, 1.5), 8)
        ctx.fill()
        if z == 1:
            pos = x + w * Z.seg(t, a, b)
        if w > 80:
            text(ctx, f"{l['quelle']} {lz_txt(l['laufzeit_s'])} s", x + 4, TL_Y + 18, F_TXT, 11.5,
                 INK if z else MUTED, tab=False)
        x += w
        if i < 6:
            ctx.set_source_rgba(*hexrgb(GROUND))
            ctx.rectangle(x - 0.5, TL_Y - 5, 1.0, 10)
            ctx.fill()
    if t >= Z.LAEUFE_FERTIG:
        pos = TL_X1
    if pos is not None:
        linie(ctx, pos, TL_Y - 9, pos, TL_Y + 9, ACCENT, 2.0)


def schema_hinweis(ctx, t):
    i = Z.phase_jetzt(t)
    s = None
    if i is not None:
        q = M["laeufe"][i]["quelle"]
        s = {"stadtteile": "schematisch: Reihenfolge und Takt der Linien (geliefert in einem Lauf von 0,13 s)",
             "zensus_gitter": "schematisch: Takt der Füllung; Farbe nach Einwohnern je Zelle",
             "gebaeude_alkis": "schematisch: jede Kachel gleich lang; Höhe aus dem NAS-Bestand, nicht aus dem Lauf",
             "mbjs_kita": "schematisch: Takt der Punkte",
             "mbjs_schule": "schematisch: Takt der Punkte",
             "alkis_nutzung": "schematisch: jede Kachel gleich lang; Grautöne zusammengefasst",
             "zensus_struktur": "schematisch: das Aufleuchten steht für die zugeladenen Merkmale"}[q]
    elif Z.ZU0 <= t < Z.AW0:
        s = "Zuordnung wie skripte/02_auswerten.py; außerhalb der Stadt zurückgenommen"
    elif Z.AW0 <= t:
        s = "Farbe = Bauzeit-Klasse, geschätzt; Reihenfolge Stadtteil für Stadtteil, schematisch"
    if s:
        w = breite(ctx, s, F_TXT, 12.5)
        ctx.set_source_rgba(*hexrgb(GROUND, 0.88))
        ctx.rectangle(MAPR - 18 - w - 8, TL_Y - 62, w + 16, 22)
        ctx.fill()
        text(ctx, s, MAPR - 18, TL_Y - 46, F_TXT, 12.5, MUTED, "r", tab=False)


def nordpfeil(ctx, t):
    tx, ty, D, tilt, az = Z.kamera_param(t)
    p, _, _ = Z.projektion(t)
    a0, a1 = p(tx, ty), p(tx, ty + 200.0)
    if not a0 or not a1:
        return
    ang = math.atan2(a1[0] - a0[0], -(a1[1] - a0[1]))
    cx, cy = MAPR - 46, 92
    ctx.set_source_rgba(*hexrgb(GROUND, 0.88))
    ctx.rectangle(MAPR - 160, cy - 46, 146, 88)
    ctx.fill()
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(ang)
    ctx.set_source_rgba(*hexrgb(INK))
    ctx.move_to(0, -22)
    ctx.line_to(6, 6)
    ctx.line_to(0, 0)
    ctx.close_path()
    ctx.fill()
    ctx.set_line_width(0.8)
    ctx.move_to(0, -22)
    ctx.line_to(-6, 6)
    ctx.line_to(0, 0)
    ctx.close_path()
    ctx.stroke()
    ctx.restore()
    text(ctx, "N", cx, cy - 30, F_SEMI, 12, INK, "c")
    text(ctx, "Perspektive, ohne Maßstab", MAPR - 18, cy + 30, F_TXT, 11.5, MUTED, "r", tab=False)


def rahmen(ctx):
    ctx.set_source_rgba(*hexrgb(INK))
    ctx.set_line_width(1.6)
    ctx.rectangle(RA, RA, W - 2 * RA, H - 2 * RA)
    ctx.stroke()
    ctx.set_line_width(0.7)
    ctx.rectangle(RI, RI, W - 2 * RI, H - 2 * RI)
    ctx.stroke()
    # Ränder außerhalb des Innenrahmens: Papier
    ctx.set_source_rgba(*hexrgb(GROUND))
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.rectangle(0, 0, W, H)
    ctx.rectangle(RI, RI, W - 2 * RI, H - 2 * RI)
    ctx.fill()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    ctx.set_source_rgba(*hexrgb(INK))
    ctx.set_line_width(1.6)
    ctx.rectangle(RA, RA, W - 2 * RA, H - 2 * RA)
    ctx.stroke()
    ctx.set_line_width(0.7)
    ctx.rectangle(RI, RI, W - 2 * RI, H - 2 * RI)
    ctx.stroke()


def bild(fr):
    t = fr / FPS
    ein = os.path.join(args.ein, "b_%04d.png" % fr)
    surf = cairo.ImageSurface.create_from_png(ein)
    ctx = cairo.Context(surf)
    proj, D, tilt = Z.projektion(t)
    # Karte: alles, was zur Karte gehört, auf den Kartenbereich begrenzt
    ctx.save()
    ctx.rectangle(RI, RI, MAPR - RI, H - 2 * RI)
    ctx.clip()
    rechteck(ctx, t, proj)
    schleier(ctx, t, proj)
    grenzen(ctx, t, proj)
    grenzzellen(ctx, t, proj)
    kachel_marke(ctx, t, proj)
    einrichtungen(ctx, t, proj)
    befund_marken(ctx, t, proj)
    befund_balken(ctx, t)
    ctx.restore()
    rahmen(ctx)
    kopfbox(ctx)
    tabelle(ctx, t)
    if t < Z.BF1:
        grosszahl(ctx, t)
    legende(ctx, t)
    abspann(ctx, t)
    nachweis(ctx, t)
    kopf(ctx, t)
    zeitleiste(ctx, t)
    schema_hinweis(ctx, t)
    nordpfeil(ctx, t)
    surf.write_to_png(os.path.join(args.aus, "o_%04d.png" % fr))
    return fr


if __name__ == "__main__":
    os.makedirs(args.aus, exist_ok=True)
    if args.frames:
        a, _, b = args.frames.partition("-")
        frames = list(range(int(a), int(b or a) + 1))
    else:
        frames = sorted(int(f[2:6]) for f in os.listdir(args.ein) if f.startswith("b_") and f.endswith(".png"))
    frames = [f for f in frames if os.path.exists(os.path.join(args.ein, "b_%04d.png" % f))]
    if args.jobs > 1:
        with Pool(args.jobs) as pool:
            for i, _ in enumerate(pool.imap_unordered(bild, frames, chunksize=8)):
                if i % 60 == 0:
                    print("OVERLAY", i, flush=True)
    else:
        for i, fr in enumerate(frames):
            bild(fr)
            if i % 60 == 0:
                print("OVERLAY", i, flush=True)
