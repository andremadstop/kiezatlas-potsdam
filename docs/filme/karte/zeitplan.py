# Gemeinsamer Zeitplan für Blender-Szene (szene.py) und Beschriftung (overlay.py), Film „Potsdam wächst aus den Daten“.
# Zeiten in Sekunden Film, 30 fps. Koordinaten lokal in Metern: EPSG:25833 minus Mitte des Abrufrechtecks
# (meta.json „ursprung“). Kamera perspektivisch; overlay.py projiziert mit derselben Rechnung wie Blender.
import json
import math
import os

FPS = 30
W, H = 1920, 1080
LENS, SENSOR = 35.0, 36.0          # mm, Sensor horizontal eingepasst
MAP_CX = 718                       # Bild-x der Kartenmitte (links vom Schriftfeld)
SHIFT_X = (W / 2 - MAP_CX) / W

# Phasen: je Importlauf ein Abschnitt, in der Reihenfolge der Läufe (Startzeit im Bericht)
PHASEN = [  # quelle, Beginn, Ende (s Film)
    ("stadtteile", 2.4, 4.8),
    ("zensus_gitter", 4.8, 8.0),
    ("gebaeude_alkis", 8.0, 19.0),
    ("mbjs_kita", 19.0, 22.2),
    ("mbjs_schule", 22.2, 24.2),
    ("alkis_nutzung", 24.2, 28.0),
    ("zensus_struktur", 28.0, 30.4),
]
P = {q: (a, b) for q, a, b in PHASEN}
LAEUFE_FERTIG = PHASEN[-1][2]      # erst danach Summen und Zuordnung
ZU0, ZU1 = 30.8, 35.6              # Zuordnung zu Potsdam
AW0, AW1 = 35.6, 38.8              # Auswertung: Bauzeit-Klasse je Gebäude (Stadtteil für Stadtteil)
BF0, BF1 = 38.8, 44.0              # Befund über Potsdam
ENDE = 47.0
N = int(round(ENDE * FPS))
GROW = 0.45                        # s, Wachsen eines Gebäudes
NEU_FADE = 0.8                     # s, „neu“ (dunkel) -> Grundfarbe
ZELL_IN = 0.35                     # s, Einblenden einer Zelle
FARB_DAUER = 0.7                   # s, Umfärben eines Gebäudes


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease2(x):
    x = clamp(x)
    return x * x * x * (x * (6 * x - 15) + 10)


def seg(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= a)


def lerp(a, b, x):
    return a + (b - a) * x


META = None


def lade(prep):
    global META
    META = json.load(open(os.path.join(prep, "meta.json"), encoding="utf-8"))
    return META


def phase_jetzt(t):
    for i, (q, a, b) in enumerate(PHASEN):
        if a <= t < b:
            return i
    return None


def faktor(q):
    """Lauf-Laufzeit (Bericht, laufzeit_s) geteilt durch die Filmdauer der Phase."""
    lz = [l for l in META["laeufe"] if l["quelle"] == q][0]["laufzeit_s"]
    a, b = P[q]
    return lz, b - a, lz / (b - a)


# ---------------- Kamera: Zielpunkt, Abstand, Neigung (0 = senkrecht), Blickrichtung (0 = nach Norden)
# Werte zwischen den Stützstellen kubisch (Hermite, Tangenten aus den Nachbarn), Abstand logarithmisch.
KEYS = [
    # t,    tx,    ty,     D,     tilt, az
    (0.0,    0.0,   600.0, 30500.0, 30.0, -8.0),
    (4.8,    0.0,   100.0, 27500.0, 33.0, -5.0),
    (8.0,  300.0,  -900.0, 24500.0, 38.0, -2.0),
    (10.9, 1900.0, -4300.0, 7200.0, 52.0,  4.0),
    (13.4, 2500.0, -3300.0, 4300.0, 58.0, 12.0),
    (15.9, 1300.0, -1600.0, 9500.0, 50.0,  8.0),
    (19.0,  400.0,  -500.0, 22500.0, 40.0,  2.0),
    (24.2,  400.0,  -700.0, 21500.0, 40.0, -2.0),
    (30.4,  400.0,  -700.0, 21800.0, 38.0, -4.0),
    (35.6,  450.0,  -800.0, 20800.0, 40.0, -3.0),
    (39.0, 3000.0, -5900.0, 7400.0, 50.0,  6.0),
    (44.0, 3500.0, -6500.0, 5600.0, 54.0, 12.0),
    (47.0, 3200.0, -6100.0, 7600.0, 50.0, 14.0),
]


def _hermite(t, i):
    """Wert aller Parameter zwischen KEYS[i] und KEYS[i+1]."""
    k0, k1 = KEYS[i], KEYS[i + 1]
    km = KEYS[i - 1] if i > 0 else k0
    kp = KEYS[i + 2] if i + 2 < len(KEYS) else k1
    h = k1[0] - k0[0]
    s = (t - k0[0]) / h
    h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
    out = []
    for j in range(1, 6):
        f = (lambda v: math.log(v)) if j == 3 else (lambda v: v)
        p0, p1 = f(k0[j]), f(k1[j])
        m0 = (p1 - f(km[j])) / (k1[0] - km[0]) if km is not k0 else (p1 - p0) / h
        m1 = (f(kp[j]) - p0) / (kp[0] - k0[0]) if kp is not k1 else (p1 - p0) / h
        v = h00 * p0 + h10 * h * m0 + h01 * p1 + h11 * h * m1
        out.append(math.exp(v) if j == 3 else v)
    return out


def kamera_param(t):
    t = clamp(t, 0.0, KEYS[-1][0] - 1e-6)
    for i in range(len(KEYS) - 1):
        if KEYS[i][0] <= t < KEYS[i + 1][0]:
            return _hermite(t, i)
    return list(KEYS[-1][1:])


def kamera(t):
    """pos, (r, u, f): Lage und Achsen (rechts, oben, vorwärts) der Kamera."""
    tx, ty, D, tilt, az = kamera_param(t)
    th, ph = math.radians(tilt), math.radians(az)
    f = (math.sin(th) * math.sin(ph), math.sin(th) * math.cos(ph), -math.cos(th))
    r = (math.cos(ph), -math.sin(ph), 0.0)
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    pos = (tx - f[0] * D, ty - f[1] * D, -f[2] * D)
    return pos, (r, u, f), D, tilt


def projektion(t):
    """(x, y, z) lokal -> (px, py) im Bild, oder None hinter der Kamera. Wie Blender: Lochkamera,
    Sensor 36 mm horizontal eingepasst, Brennweite LENS, Verschiebung SHIFT_X."""
    pos, (r, u, f), D, tilt = kamera(t)
    k = LENS / SENSOR

    def p(x, y, z=0.0):
        dx, dy, dz = x - pos[0], y - pos[1], z - pos[2]
        xc = dx * r[0] + dy * r[1] + dz * r[2]
        yc = dx * u[0] + dy * u[1] + dz * u[2]
        zc = dx * f[0] + dy * f[1] + dz * f[2]
        if zc <= 1.0:
            return None
        return (W / 2 + (k * xc / zc - SHIFT_X) * W, H / 2 - (k * yc / zc) * W)
    return p, D, tilt


def sonne(t):
    """Höhe (Grad), Azimut (woher, 0 = N, 90 = O), Stärke."""
    x = ease(seg(t, 8.5, 11.0)) * (1 - ease(seg(t, 16.0, 19.0)))
    x2 = ease(seg(t, BF0 - 1.0, BF0 + 0.5))
    return lerp(42.0, 30.0, max(x, x2)), 215.0, lerp(3.2, 4.2, max(x, x2))


# ---------------- Werte für die Materialien (je Bild gesetzt)
def zell_mix(t):
    """Wie kräftig die Zellen ihre Klassenfarbe zeigen (Rest Papierfarbe, deckend, ohne Transparenz):
    voll im Gitterlauf, unter den Gebäuden leiser, ab dem Strukturlauf wieder kräftig."""
    g0 = P["gebaeude_alkis"][0]
    if t < P["zensus_struktur"][0]:
        return lerp(1.0, 0.5, ease(seg(t, g0 + 0.6, g0 + 2.6)))
    return lerp(0.5, 0.9, ease(seg(t, P["zensus_struktur"][0], P["zensus_struktur"][0] + 0.6)))


def zell_sicht(t):
    """Sichtbarkeit der Zellen insgesamt; zur Auswertung ausgeblendet (dann sieht man die Nutzung)."""
    return 1.0 - ease(seg(t, AW0, AW0 + 1.0))


def zell_hoch(t):
    """z der Zellen: unter der Nutzung (0,3 m), ab dem Strukturlauf darüber (0,9 m)."""
    return 0.9 if t >= P["zensus_struktur"][0] else 0.3


def struktur_puls(t):
    a, b = P["zensus_struktur"]
    return math.sin(math.pi * seg(t, a + 0.1, b - 0.2)) if a <= t <= b else 0.0
