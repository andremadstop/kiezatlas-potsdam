#!/usr/bin/env python3
"""Der Lauf im Terminal: Film aus den echten Laufberichten und dem Prüfprotokoll des Kiezatlas Potsdam.

Alle Texte und Zahlen im Bild werden zur Renderzeit aus Dateien gelesen und per assert abgeglichen:
  belege/2026110*Z.txt / .json   die sieben Importläufe (je Lauf eine Quelle)
  belege/README.md               Befehl je Lauf, was jeder Lauf belegt, Erklärung zum Kita-Lauf
  QUELLEN.md, daten/LIZENZ.md     Namensnennung je Quelle
  daten/kennzahlen.json          Zahlenkarte (Einwohner, Gebäude, Fernwärme, Altbau)
  README.md                      Tabelle „Zur Prüfung“ (Gegenprobe der Kernzahlen)
  pruefen.log (--pruefen-log)    ./pruefen.sh mit Zeitstempel je Zeile, neben diesem Skript (siehe README.md)

Aufruf (aus der Repo-Wurzel):
  python3 docs/filme/terminal/film.py                 # film.mp4 neben dem Skript
  python3 docs/filme/terminal/film.py --check         # Beschriftung: Rand, Überlappung
  python3 docs/filme/terminal/film.py --still 9.5,30  # Probebilder probe-<t>.png in --probe-dir
  python3 docs/filme/terminal/film.py --standbild     # standbild.png
  python3 docs/filme/terminal/film.py --gif           # film.gif aus film.mp4
  python3 docs/filme/terminal/film.py --manifest      # jede Zahl mit Quelle als JSON
Optionen: --repo, --pruefen-log, --schriften, --probe-dir, --jobs.
"""
import argparse, glob, hashlib, json, math, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_ap0 = argparse.ArgumentParser(add_help=False)
_ap0.add_argument("--repo", default=os.path.join(HERE, "..", "..", ".."))
_ap0.add_argument("--pruefen-log", default=None)
_ap0.add_argument("--schriften", default=None)
_a0 = _ap0.parse_known_args()[0]
ROOT = os.path.normpath(_a0.repo)
LOG = os.path.normpath(_a0.pruefen_log or os.path.join(HERE, "pruefen.log"))
LOG_REL = os.path.relpath(LOG, ROOT)

# ---------------------------------------------------------------- Schriften (vor import cairo)
def schriften_vorbereiten(ordner):
    """Barlow aus fonts/*.woff2 als ttf mit eigener fonts.conf. Ohne vorhandenen Ordner wird umgewandelt
    (braucht fontTools und brotli)."""
    conf = os.path.join(ordner, "fonts.conf")
    if not os.path.exists(conf):
        from fontTools.ttLib import TTFont
        os.makedirs(ordner, exist_ok=True)
        for w in sorted(glob.glob(os.path.join(ROOT, "fonts", "*.woff2"))):
            f = TTFont(w); f.flavor = None
            f.save(os.path.join(ordner, os.path.basename(w)[:-6] + ".ttf"))
        with open(conf, "w", encoding="utf-8") as fh:
            fh.write('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>\n'
                     '  <dir prefix="relative">.</dir>\n  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
                     '</fontconfig>\n')
    os.environ["FONTCONFIG_FILE"] = os.path.abspath(conf)

_SCHRIFTEN = _a0.schriften
if not _SCHRIFTEN:
    _w = os.path.join(ROOT, "berichte", "filme-werkzeug", "fonts")
    _SCHRIFTEN = _w if os.path.exists(os.path.join(_w, "fonts.conf")) else os.path.join(ROOT, "berichte", "filme-schriften")
schriften_vorbereiten(_SCHRIFTEN)

import cairo
import numpy as np
from PIL import Image, ImageFilter

MONO = "Noto Sans Mono"                 # Terminal (fonts/ des Kiezatlas hat keine Monospace-Schrift)
TXT, TXT_M, TXT_SB = "Barlow", "Barlow Medium", "Barlow SemiBold"
DISP = "Barlow Semi Condensed SemiBold"  # große Zahlen
SCHRIFT_DATEI = {TXT: "barlow-400", TXT_M: "barlow-500", TXT_SB: "barlow-600", DISP: "barlow-semi-condensed-600",
                 MONO: "NotoSansMono"}

def schriften_pruefen():
    """Kein stiller Rückfall auf eine andere Schrift: fc-match muss die erwartete Datei liefern."""
    for fam, teil in SCHRIFT_DATEI.items():
        f = subprocess.run(["fc-match", "-f", "%{file}", fam], capture_output=True, text=True, check=True).stdout
        assert teil in os.path.basename(f), (fam, f)
schriften_pruefen()

W, H, FPS = 1920, 1080, 30
FS, LH = 20.5, 27.5          # Terminalschrift, Zeilenhöhe
KOPF_H = 64
TX0, TY0 = 72, 104           # linker Rand, erste Grundlinie
TROWS = 19                   # sichtbare Terminalzeilen (letzte Grundlinie y 599)
KARTE_Y0, KARTE_Y1 = 632, 818
ZL_Y = 858                   # Balken der Zeitleiste
GR_KOPF, GR_NOTIZ, GR_QUELLE, GR_DATEN = 19, 17, 16, 16

def hx(s):
    s = s.lstrip("#"); return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))
# Farben aus atlas.css / DESIGN.md des Kiezatlas: --tief #13212a, --tief-ink #e9ece8, --tief-muted #a9b5b9,
# Klassenstufen #dce6e2 #a8c7c2 #6fa1a3 #3b7684 #1c4a5b, Akzent #6a2c82 (hell #c9a6d8), Papier #f1f2ee
C = dict(
    bg_in=hx("#13212a"), bg_out=hx("#0a1318"),
    txt=hx("#a8c7c2"), dim=hx("#6fa1a3"), faint=hx("#3b7684"), bright=hx("#dce6e2"),
    name=hx("#e9ece8"), num=hx("#f1f2ee"), ok=hx("#dce6e2"), warn=hx("#c9a6d8"),
    petrol=hx("#1c4a5b"), petrol_l=hx("#6fa1a3"), ink=hx("#e9ece8"), muted=hx("#a9b5b9"),
    paper=hx("#f1f2ee"), accent=hx("#6a2c82"), violett=hx("#c9a6d8"), tief=hx("#13212a"),
)

# ---------------------------------------------------------------- Daten aus dem Repo
def lies(p):
    with open(os.path.join(ROOT, p) if not os.path.isabs(p) else p, encoding="utf-8") as f:
        return f.read()

def de(x, n=1):
    return f"{x:.{n}f}".replace(".", ",")

def punkt(n):
    return f"{n:,}".replace(",", ".")

def sek_txt(s):
    """Sekunden genau mit den Stellen aus dem Berichtskopf (149.75 bleibt 149,75)."""
    return s.replace(".", ",")

def lauf_lesen(txt):
    lid = os.path.basename(txt)[:-4]
    zeilen = lies(txt).rstrip("\n").split("\n")
    d = json.loads(lies(txt[:-4] + ".json"))
    assert d["lauf_id"] == lid and len(d["quellen"]) == 1, lid
    q = d["quellen"][0]
    m = re.match(r"^Importlauf (\S+) · ([\d.]+) s$", zeilen[0]); assert m and m.group(1) == lid
    assert abs(float(m.group(2)) - d["laufzeit_s"]) < 1e-9, lid
    mq = re.match(r"^  (\S+)\s+(ok)\s+neu\s+(\d+)\s+geändert\s+(\d+)\s+gelöscht\s+(\d+)\s+unverändert\s+(\d+)$", zeilen[1])
    assert mq and mq.group(1) == q["quelle"] and q["status"] == "ok", lid
    z = q["zaehler"]
    assert [int(mq.group(i)) for i in (3, 4, 5, 6)] == [z["neu"], z["geaendert"], z["geloescht"], z["unveraendert"]], lid
    # Warnungen/Hinweise der Konsole = JSON, in derselben Reihenfolge
    wh = [re.sub(r"^\s+(Warnung|Hinweis): ", "", x) for x in zeilen[2:] if re.match(r"^\s+(Warnung|Hinweis):", x)]
    assert wh == q["warnungen"] + q["hinweise"], lid
    assert zeilen[-1] == f"  Änderungskarte: {lid}-karte.html", lid
    return dict(id=lid, zeilen=zeilen, kopf_sek=m.group(2), sek=d["laufzeit_s"], quelle=q["quelle"], typ=q["typ"],
                start=d["start"], zaehler=z, warnungen=q["warnungen"], unvollstaendig=q["unvollstaendig"],
                lauf_unvollstaendig=d["unvollstaendig"], q_sek=q["laufzeit_s"], info=q.get("info") or {}, json=d)

LAEUFE = [lauf_lesen(os.path.join("belege", os.path.basename(p)))
          for p in sorted(glob.glob(os.path.join(ROOT, "belege", "2026110*Z.txt")))]
assert len(LAEUFE) == 7, len(LAEUFE)
QUELLEN_REIHE = [L["quelle"] for L in LAEUFE]
assert QUELLEN_REIHE == ["stadtteile", "zensus_gitter", "gebaeude_alkis", "mbjs_kita", "mbjs_schule",
                         "alkis_nutzung", "zensus_struktur"], QUELLEN_REIHE
SUMME_SEK = sum(L["sek"] for L in LAEUFE)
KITA = next(L for L in LAEUFE if L["quelle"] == "mbjs_kita")
# Die Lücke steht als Warnung in der Konsole und als unvollstaendig im JSON; Status bleibt ok
assert KITA["unvollstaendig"] is True and KITA["lauf_unvollstaendig"] == ["mbjs_kita"]
assert all(L["unvollstaendig"] is False for L in LAEUFE if L is not KITA)
m = re.match(r"Nur (\d+) von (\d+) gemeldeten Objekten erhalten", KITA["warnungen"][0])
KITA_ERH, KITA_GEM = int(m.group(1)), int(m.group(2))
assert KITA_ERH == KITA["zaehler"]["neu"] == 220 and KITA_GEM == 240

# belege/README.md: Befehl (Spalte „erzeugt von“), was der Lauf belegt, Kita-Erklärung
_breadme = lies("belege/README.md")
BELEGT, CMD = {}, {}
for L in LAEUFE:
    mm = re.search(rf"^\| `{L['id']}\.txt/\.json` \| (.+?) \| `(?:skripte/lauf\.sh laden|…) --nur (\S+)` \|$", _breadme, re.M)
    assert mm and mm.group(2) == L["quelle"], L["id"]
    BELEGT[L["id"]] = mm.group(1)
    CMD[L["id"]] = f"skripte/lauf.sh laden --nur {L['quelle']}"
assert re.search(r"`skripte/lauf\.sh laden --nur stadtteile`", _breadme)
assert "skripte/lauf.sh laden --nur QUELLE" in lies("skripte/lauf.sh")
mm = re.search(rf"^\| `{KITA['id']}` \| `mbjs_kita` \([^)]*\) \| (.+?) \|$", _breadme, re.M)
KITA_GRUND = mm.group(1).replace("`", "")
KITA_GRUND_Z = _breadme[:mm.start()].count("\n") + 1
assert "240 Einträge" in KITA_GRUND and "17 Kitas" in KITA_GRUND and "Nichts gelöscht" in KITA_GRUND

# Namensnennung je Quelle: Spalte „Namensnennung“ in QUELLEN.md (Nr. der Zeile, „wie N“ aufgelöst)
_q = {}
for z in lies("QUELLEN.md").split("\n"):
    t = [c.strip() for c in z.split("|")]
    if len(t) > 8 and t[1].isdigit():
        _q[int(t[1])] = t
def _vermerk(nr):
    v = _q[nr][6]
    mw = re.fullmatch(r"wie (\d+)", v)
    return _vermerk(int(mw.group(1))) if mw else v
QUELLE_NR = dict(stadtteile=(1, "Stadtteile der Landeshauptstadt Potsdam"), zensus_gitter=(2, "Zensus 2022, 100-m-Gitter: Bevölkerung"),
                 zensus_struktur=(3, "--nur zensus_struktur"), gebaeude_alkis=(5, "Pipeline `gebaeude_alkis`"),
                 alkis_nutzung=(6, "Pipeline `alkis_nutzung`"), mbjs_kita=(7, "Pipeline `mbjs_kita`"),
                 mbjs_schule=(8, "Pipeline `mbjs_schule`"))
def kurz(v):
    """Vermerk ohne die URL in Klammern (im Bild zu lang; voller Wortlaut in QUELLEN.md und README.md)."""
    return re.sub(r" \(https?://[^)]*\)", "", v)
VERMERK = {}
for qn, (nr, kenn) in QUELLE_NR.items():
    assert kenn in " | ".join(_q[nr]), (qn, nr)
    VERMERK[qn] = kurz(_vermerk(nr))
# Kennzahlen: Zeile für kennzahlen.json in daten/LIZENZ.md
_liz = next(z for z in lies("daten/LIZENZ.md").split("\n") if z.startswith("| `zellen.js`, `kennzahlen.js`, `kennzahlen.json`"))
VERMERK_KENNZ = kurz([c.strip() for c in _liz.split("|")][3])

# Prüfprotokoll: Zeitstempel-Wrapper um ./pruefen.sh (Wrapper-Zeilen beginnen mit „# “)
_logtxt = lies(LOG)
LOG_SHA = hashlib.sha256(_logtxt.encode("utf-8")).hexdigest()
PLOG = []
for z in _logtxt.rstrip("\n").split("\n"):
    mm = re.match(r"^(\d\d:\d\d:\d\d\.\d{3}) \+\s*([\d.]+)s \| ?(.*)$", z)
    assert mm, z
    PLOG.append((float(mm.group(2)), mm.group(3)))
assert PLOG[0][1].startswith("# Wrapper:") and "./pruefen.sh" in PLOG[0][1]
P_RUECK = next(t for _, t in PLOG if t.startswith("# Rückgabe pruefen.sh:"))
assert P_RUECK == "# Rückgabe pruefen.sh: 0"
P_ENDE = PLOG[-1][0]
P_KOPF = []
for s, t in PLOG[1:]:
    if t.startswith("== ") or not t: break
    P_KOPF.append((s, t))
assert P_KOPF[0][1].startswith("Kiezatlas Potsdam, Prüflauf ") and P_KOPF[1][1].startswith("Commit: ")
P_COMMIT = P_KOPF[1][1].split()[1][:7]
P_DATUM = re.search(r"Prüflauf (\d\d\.\d\d\.\d{4}) (\d\d:\d\d):\d\d (\S+)$", P_KOPF[0][1]).groups()
ABSCHNITTE = []   # (name, s_start, s_ende, zeile_start, zeile_ende)
_offen = None
for s, t in PLOG:
    if t.startswith("== Zählung:"):
        P_ZAEHL = (s, t); break
    if t.startswith("== "):
        _offen = (t[3:], s, t)
    elif t.startswith("-- ") and _offen:
        assert t.startswith(f"-- {_offen[0]}: "), t
        ABSCHNITTE.append(dict(name=_offen[0], s0=_offen[1], s1=s, z0=_offen[2], z1=t,
                               gruen=bool(re.search(r": grün, \d+ s$", t)))); _offen = None
mz = re.fullmatch(r"== Zählung: (\d+) Prüfungen, (\d+) grün, (\d+) mit Befund, (\d+) übersprungen", P_ZAEHL[1])
P_N, P_GRUEN, P_BEFUND, P_UEBER = map(int, mz.groups())
assert P_N == len(ABSCHNITTE) and P_GRUEN == sum(a["gruen"] for a in ABSCHNITTE), (P_N, len(ABSCHNITTE))
# Zählung danach als Liste „  grün  <Name>“, gleiche Namen in gleicher Reihenfolge
_liste = [t for s, t in PLOG if re.match(r"^  (grün|Befund|übersprungen)\s{2}", t)]
assert [re.sub(r"^  \S+\s+", "", t) for t in _liste] == [a["name"] for a in ABSCHNITTE]
# drei Zeilen aus pruefen/daten.py, die die Zahlen der Zahlenkarte prüfen
P_AUSZUG_MUSTER = [r"^  ok    Σ ew über zellen\.js = Kachel Einwohner Stadt \((\d+) = (\d+)\)$",
                   r"^  ok    Σ Gebäude = kontrolle\.gebaeude_in_potsdam = stadt\.gebaeude\.anzahl \((\d+)\)$",
                   r"^  ok    kontrolle: Gebäude im Rechteck \((\d+)\) ≥ in Potsdam$"]
P_AUSZUG = []
for mu in P_AUSZUG_MUSTER:
    hit = [(s, t, re.match(mu, t)) for s, t in PLOG if re.match(mu, t)]
    assert len(hit) == 1, mu
    P_AUSZUG.append(hit[0])
P_BROWSER0 = next(a["s0"] for a in ABSCHNITTE if a["name"].startswith("Browser:"))

# Kennzahlen (Auswertung) und Gegenproben
KZ = json.loads(lies("daten/kennzahlen.json"))
assert json.loads(re.sub(r"^.*?=", "", lies("daten/kennzahlen.js").strip(), count=1, flags=re.S).rstrip(";")) == KZ
def kachel(obj, k): return next(x for x in obj["kacheln"] if x["id"] == k)
EW = kachel(KZ["stadt"], "einwohner")["wert"]
ZELLEN = KZ["stadt"]["zellen"]
GEB = KZ["stadt"]["gebaeude"]["anzahl"]
GEB_RECHT = KZ["kontrolle"]["gebaeude_im_rechteck"]
FERN = kachel(KZ["stadt"], "fernwaerme"); ALT = kachel(KZ["stadt"], "altbau")
STICHTAG = re.search(r"Stichtag (\d\d\.\d\d\.\d{4})", kachel(KZ["stadt"], "einwohner")["quelle"]).group(1)
assert all(f"Stichtag {STICHTAG}" in k["quelle"] for k in (FERN, ALT))
assert "100-m-Gitter" in FERN["quelle"] and FERN["titel"] == "Wohnungen mit Fernwärme" and ALT["titel"] == "Wohnungen in Gebäuden von vor 1949"
def datum_de(iso):
    j, m, t = iso.split("-"); return f"{t}.{m}.{j}"
assert FERN["nenner"] == ALT["nenner"]
assert abs(round(100 * FERN["zaehler"] / FERN["nenner"], 1) - FERN["wert"]) < 1e-9
assert abs(round(100 * ALT["zaehler"] / ALT["nenner"], 1) - ALT["wert"]) < 1e-9
N_ST = len(KZ["stadtteile"])
assert N_ST == 32
G = {L["quelle"]: L for L in LAEUFE}
assert G["gebaeude_alkis"]["zaehler"]["neu"] == GEB_RECHT, "Lauf gebaeude_alkis = kontrolle.gebaeude_im_rechteck"
assert G["stadtteile"]["zaehler"]["neu"] == N_ST
ZELLEN_GELADEN = G["zensus_gitter"]["zaehler"]["neu"]
assert (int(P_AUSZUG[0][2].group(1)), int(P_AUSZUG[0][2].group(2))) == (EW, EW)
assert int(P_AUSZUG[1][2].group(1)) == GEB and int(P_AUSZUG[2][2].group(1)) == GEB_RECHT
_readme = lies("README.md")
_rz = re.search(r"^\| ([\d.]+) Einwohner in ([\d.]+) Gitterzellen mit Mittelpunkt in Potsdam und Einwohnerwert, (\d+) Stadtteile", _readme, re.M)
assert (int(_rz.group(1).replace(".", "")), int(_rz.group(2).replace(".", "")), int(_rz.group(3))) == (EW, ZELLEN, N_ST)
_rg = re.search(r"^\| ([\d.]+) Gebäude in den (\d+) Stadtteilen, ([\d.]+) im Abrufrechteck", _readme, re.M)
assert (int(_rg.group(1).replace(".", "")), int(_rg.group(2)), int(_rg.group(3).replace(".", ""))) == (GEB, N_ST, GEB_RECHT)
# Befund: Stadtteile ab 1.000 Einwohnern (kleinere Gebiete sind durch die Cell-Key-Geheimhaltung unscharf)
MIN_EW = 1000
ST = []
for nr, t in sorted(KZ["stadtteile"].items()):
    ew = kachel(t, "einwohner")["wert"]
    if ew >= MIN_EW:
        ST.append(dict(nr=nr, name=t["name"], ew=ew, fern=kachel(t, "fernwaerme")["wert"], alt=kachel(t, "altbau")["wert"]))
FERN_S = sorted(ST, key=lambda x: -x["fern"]); ALT_S = sorted(ST, key=lambda x: -x["alt"])
F_MAX, F_MIN, A_MAX, A_MIN = FERN_S[0], FERN_S[-1], ALT_S[0], ALT_S[-1]
assert FERN_S[0]["fern"] > FERN_S[1]["fern"] and FERN_S[-1]["fern"] < FERN_S[-2]["fern"]
assert ALT_S[0]["alt"] > ALT_S[1]["alt"] and ALT_S[-1]["alt"] < ALT_S[-2]["alt"]
# Zusammenhang Fernwärme / Altbau über dieselben Stadtteile: Rangkorrelation nach Spearman (Bindungen gemittelt)
def raenge(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
        for m_ in range(i, j + 1): r[o[m_]] = (i + j) / 2 + 1
        i = j + 1
    return r
def pearson(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return sab / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
RHO = pearson(raenge([x["fern"] for x in ST]), raenge([x["alt"] for x in ST]))
assert RHO <= -0.5, RHO          # die Merkzeile „Tendenz: je mehr Fernwärme, desto weniger Altbau“ gilt nur dann
# drei Stadtteile nach Regel, in beiden Balkenreihen gleich hervorgehoben
B_FERN = A_MIN                                         # kein Altbau (bei hoher Fernwärme)
B_ALT = max(ST, key=lambda x: x["alt"] - x["fern"])     # viel Altbau, kaum Fernwärme
B_BEIDES = max(ST, key=lambda x: x["alt"] + x["fern"])  # viel von beidem (Ausnahme der Tendenz)
BEISPIELE = [B_FERN, B_BEIDES, B_ALT]
assert len({x["nr"] for x in BEISPIELE}) == 3
assert B_FERN["fern"] > 75 and B_ALT["fern"] < 25 and B_ALT["alt"] > 50 and B_BEIDES["fern"] > 50 and B_BEIDES["alt"] > 40
MERKZEILE = "Tendenz: Je mehr Fernwärme, desto weniger Wohnungen von vor 1949."
MERK_AUSNAHME = (f"Ausnahme mit viel von beidem: {B_BEIDES['name']} ({de(B_BEIDES['fern'])} % Fernwärme, "
                 f"{de(B_BEIDES['alt'])} % vor 1949). Rangkorrelation nach Spearman {de(RHO, 2).replace('-', '−')} "
                 f"über die {len(ST)} Stadtteile, eigene Rechnung.")
# optional: Faktenblatt der Vorbereitung (nicht im Repo)
_fb = os.path.join(ROOT, "berichte", "filme-2026-11-08", "fakten.json")
FAKTEN_GEPRUEFT = False
if os.path.exists(_fb):
    fb = json.loads(lies(_fb))
    assert fb["einwohner_zensus"]["wert"] == EW and fb["gebaeude_in_potsdam"]["wert"] == GEB
    assert fb["gebaeude_im_rechteck"]["wert"] == GEB_RECHT and fb["zellen_zugeordnet"]["wert"] == ZELLEN
    assert fb["stadt_fernwaerme"]["wert"]["prozent"] == FERN["wert"] and fb["stadt_altbau"]["wert"]["prozent"] == ALT["wert"]
    assert (fb["befund_fernwaerme_max"]["wert"]["name"], fb["befund_fernwaerme_max"]["wert"]["wert"]) == (F_MAX["name"], F_MAX["fern"])
    assert (fb["befund_fernwaerme_min"]["wert"]["name"], fb["befund_fernwaerme_min"]["wert"]["wert"]) == (F_MIN["name"], F_MIN["fern"])
    assert (fb["befund_altbau_max"]["wert"]["name"], fb["befund_altbau_max"]["wert"]["wert"]) == (A_MAX["name"], A_MAX["alt"])
    assert (fb["befund_altbau_min"]["wert"]["name"], fb["befund_altbau_min"]["wert"]["wert"]) == (A_MIN["name"], A_MIN["alt"])
    # Kita-Lesart: nicht nur Zahlen, auch Flag und Wortlaut gegen den Laufbericht
    _kl = fb["kita_lauf_lesart"]
    assert _kl["wert"]["unvollstaendig_flag"] is KITA["unvollstaendig"] and _kl["wert"]["status"] == "ok"
    assert (_kl["wert"]["erhalten"], _kl["wert"]["gemeldet"]) == (KITA_ERH, KITA_GEM)
    for _t in (_kl["hinweis"], _kl["aufloesung"]["lesart"]):
        assert "unvollstaendig false" not in _t and "unvollstaendig true" in _t.replace(" = ", " "), _t
    FAKTEN_GEPRUEFT = True

def utc(start):
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)", start)
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}, {m.group(4)}:{m.group(5)} UTC"

# ---------------------------------------------------------------- Zeilen mit Stil je Zeichen
class Z:
    def __init__(self, text, stil="txt"):
        self.t = text; self.s = [stil] * len(text)
    def mal(self, a, b, stil):
        for i in range(max(0, a), min(len(self.t), b)): self.s[i] = stil
        return self
    def plus(self, text, stil):
        self.t += text; self.s += [stil] * len(text); return self

def stil_bericht(z):
    L = Z(z, "txt")
    if z.startswith("Importlauf"):
        return L.mal(0, len(z), "bright")
    m = re.match(r"^  (\S+)(\s+)(ok)\b", z)
    if m:
        L.mal(0, len(z), "dim").mal(m.start(1), m.end(1), "name").mal(m.start(3), m.end(3), "ok")
        for mm in re.finditer(r"(neu|geändert|gelöscht|unverändert)(\s+)(\d+)", z):
            L.mal(mm.start(3), mm.end(3), "num" if mm.group(3) != "0" else "faint")
        return L
    m = re.match(r"^(\s+)(Hinweis:|Warnung:)", z)
    if m:
        if m.group(2) == "Warnung:": L.mal(m.start(2), len(z), "warn")
        else: L.mal(m.start(2), len(z), "dim")
        return L
    if z.startswith("  Änderungskarte:"):
        return L.mal(0, len(z), "faint")
    return L

def stil_pruef(z):
    L = Z(z, "dim")
    if z.startswith("== Zählung"):
        return L.mal(0, len(z), "bright")
    if z.startswith("== "):
        return L.mal(0, 2, "faint").mal(3, len(z), "txt")
    m = re.match(r"^-- (.+): (grün)(, \d+ s)$", z)
    if m:
        return L.mal(0, 2, "faint").mal(3, m.end(1), "dim").mal(m.start(2), m.end(2), "ok").mal(m.start(3), len(z), "dim")
    if z.startswith("  ok "):
        L.mal(2, 4, "ok")
        for mm in re.finditer(r"\d{3,}", z): L.mal(mm.start(), mm.end(), "num")
        return L
    return L.mal(0, len(z), "txt")

# ---------------------------------------------------------------- Drehbuch
T_TITEL = 3.0
F_KURZ, F_LANG = 4, 200                     # Zeitraffer: kurze Läufe 4×, gebaeude_alkis und alkis_nutzung 200×
FAKTOR = {L["id"]: (F_LANG if L["sek"] > 60 else F_KURZ) for L in LAEUFE}
assert [FAKTOR[L["id"]] for L in LAEUFE] == [F_KURZ, F_KURZ, F_LANG, F_KURZ, F_KURZ, F_LANG, F_KURZ]
TYP_ERST, TYP = 0.95, 0.36                 # Tippen des Befehls
VOR = 0.14                                 # Enter bis Beginn
HALT = 0.45
HALT_KITA = 4.4
HALT_LETZT = 1.0

IMPORT = []   # je Lauf: Beginn (Film), Tippdauer, Laufdauer (Film), Halt
_t = 0.0
for k, L in enumerate(LAEUFE):
    typ = TYP_ERST if k == 0 else TYP
    d = L["sek"] / FAKTOR[L["id"]]
    h = HALT_KITA if L is KITA else (HALT_LETZT if k == len(LAEUFE) - 1 else HALT)
    IMPORT.append(dict(L=L, t0=_t, typ=typ, t_lauf=_t + typ + VOR, d=d, t_fertig=_t + typ + VOR + d, halt=h))
    _t = _t + typ + VOR + d + h
T_IMPORT = _t

P_F1, P_F2 = 8, 120                         # pruefen.sh: 8× bis zum ersten Browser-Test, danach 120×
P_TYP = 0.6
def p_film(s):
    """Filmsekunden ab Start von pruefen.sh für Protokollsekunde s."""
    return s / P_F1 if s <= P_BROWSER0 else P_BROWSER0 / P_F1 + (s - P_BROWSER0) / P_F2
P_HALT = 2.0
T_PRUEF = 0.25 + P_TYP + VOR + p_film(P_ENDE) + P_HALT
T_SCHLUSS = 12.6

SZENEN = [("titel", T_TITEL), ("import", T_IMPORT), ("pruefen", T_PRUEF), ("schluss", T_SCHLUSS)]
GESAMT = sum(d for _, d in SZENEN)
NFRAMES = int(round(GESAMT * FPS))

def szene_bei(t):
    a = 0.0
    for n, d in SZENEN:
        if t < a + d: return n, t - a, d
        a += d
    return SZENEN[-1][0], SZENEN[-1][1], SZENEN[-1][1]

def szene_start(n):
    a = 0.0
    for name, d in SZENEN:
        if name == n: return a
        a += d
    raise KeyError(n)

SPIN = "|/-\\"

def import_zeilen(lt):
    """Terminal der Importläufe zur lokalen Zeit lt; dazu aktueller Lauf, Echtzeit im Lauf, Phase."""
    rows, akt, r, phase = [], None, 0.0, "vor"
    cur = (int(lt * 2.2) % 2 == 0)
    for k, E in enumerate(IMPORT):
        if lt < E["t0"]:
            break
        akt = k
        L = E["L"]; cmd = CMD[L["id"]]
        x = lt - E["t0"]
        n = len(cmd) if x >= E["typ"] else int(len(cmd) * max(0.0, x) / E["typ"])
        p = Z("$ ", "ok").plus(cmd[:n], "bright")
        tippt = x < E["typ"] + VOR
        rows.append((p, tippt and cur))
        if lt < E["t_lauf"]:
            phase = "tippt"; r = 0.0; break
        if lt < E["t_fertig"]:
            phase = "laeuft"
            r = (lt - E["t_lauf"]) * FAKTOR[L["id"]]
            sp = SPIN[int(lt * 14) % 4]
            live = Z(f"  {L['quelle']:<24} {sp} läuft  {de(r, 2):>7} s", "dim")
            live.mal(2, 2 + len(L["quelle"]), "name").mal(27, 28, "bright")
            rows.append((live, False)); break
        phase = "fertig"; r = L["sek"]
        for z in L["zeilen"]: rows.append((stil_bericht(z), False))
    if phase == "fertig" and akt == len(IMPORT) - 1:
        rows.append((Z("$ ", "ok"), cur))
    return rows, akt, r, phase

def import_summe(akt, r):
    return sum(IMPORT[k]["L"]["sek"] for k in range(akt)) + r if akt is not None else 0.0

P_ZEILEN = []   # (Protokollsekunde, Zeile)
for s, t in P_KOPF: P_ZEILEN.append((s, t))
for a in ABSCHNITTE:
    P_ZEILEN.append((a["s0"], a["z0"]))
    if a["name"].startswith("Datenverträge und Summen"):
        for s, t, _ in P_AUSZUG: P_ZEILEN.append((s, t))
    P_ZEILEN.append((a["s1"], a["z1"]))
P_ZEILEN.append(P_ZAEHL)
assert [s for s, _ in P_ZEILEN] == sorted(s for s, _ in P_ZEILEN)

def pruef_zeilen(lt):
    rows = []
    cur = (int(lt * 2.2) % 2 == 0)
    cmd = "./pruefen.sh"
    x = lt - 0.25
    n = len(cmd) if x >= P_TYP else int(len(cmd) * max(0.0, x) / P_TYP)
    rows.append((Z("$ ", "ok").plus(cmd[:n], "bright"), x < P_TYP + VOR and cur))
    if x < P_TYP + VOR:
        return rows, 0.0, False
    fx = x - P_TYP - VOR
    # Protokollsekunde zur Filmzeit (Umkehrung von p_film)
    s = fx * P_F1 if fx * P_F1 <= P_BROWSER0 else P_BROWSER0 + (fx - P_BROWSER0 / P_F1) * P_F2
    s = min(s, P_ENDE)
    fertig = s >= P_ENDE
    for ps, t in P_ZEILEN:
        if ps <= s: rows.append((stil_pruef(t), False))
    offen = next((a for a in ABSCHNITTE if a["s0"] <= s < a["s1"]), None)
    if offen and not fertig:
        sp = SPIN[int(lt * 14) % 4]
        live = Z(f"   {sp} läuft  {de(s - offen['s0'], 1):>6} s", "dim").mal(3, 4, "bright")
        rows.append((live, False))
    if fertig:
        rows.append((Z("$ ", "ok"), cur))
    return rows, s, fertig

# ---------------------------------------------------------------- Zeichnen
def font(cr, fam=MONO, size=FS, bold=False):
    # Barlow-Schnitte tragen das Gewicht im Namen; nur die Monospace-Schrift hat einen echten Bold-Schnitt
    cr.select_font_face(fam, cairo.FONT_SLANT_NORMAL,
                        cairo.FONT_WEIGHT_BOLD if (bold and fam == MONO) else cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)

STILE = {"txt": ("txt", False), "dim": ("dim", False), "faint": ("faint", False), "bright": ("bright", True),
         "name": ("name", True), "num": ("num", True), "ok": ("ok", True), "warn": ("warn", False)}

def fopts():
    fo = cairo.FontOptions(); fo.set_antialias(cairo.ANTIALIAS_GRAY); fo.set_hint_style(cairo.HINT_STYLE_SLIGHT)
    fo.set_hint_metrics(cairo.HINT_METRICS_OFF); return fo

def zeichen_breite(size=FS):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10); cr = cairo.Context(s); cr.set_font_options(fopts()); font(cr, MONO, size)
    return cr.text_extents("M" * 100).x_advance / 100
CW = zeichen_breite()
COLS = int((W - TX0 - 56) / CW)

def zeile_malen(cr, L, x, y, cw, cursor=False, alpha=1.0, size=FS):
    i = 0; t = L.t
    while i < len(t):
        j = i
        while j < len(t) and L.s[j] == L.s[i]: j += 1
        farbe, bold = STILE[L.s[i]]
        font(cr, MONO, size, bold); cr.set_source_rgba(*C[farbe], alpha)
        cr.move_to(x + i * cw, y); cr.show_text(t[i:j])
        i = j
    if cursor:
        cr.set_source_rgba(*C["txt"], alpha)
        cr.rectangle(x + len(t) * cw + 2, y - size * 0.82, cw - 2, size * 1.05); cr.fill()

def terminal_malen(cr, rows, alpha=1.0):
    flach = []
    for L, cur in rows:
        assert len(L.t) <= COLS, (len(L.t), L.t)   # kein Umbruch nötig, nichts abgeschnitten
        flach.append((L, cur))
    sichtbar = flach[-TROWS:]
    for n, (L, cur) in enumerate(sichtbar):
        zeile_malen(cr, L, TX0, TY0 + n * LH, CW, cur, alpha)
    return [L.t for L, _ in sichtbar]

BOXEN = []   # (Kontext, x0, y0, x1, y1, Text) für --check

def text(cr, s, x, y, size, farbe, fam=TXT, alpha=1.0, anker="l", bold=False):
    font(cr, fam, size, bold)
    e = cr.text_extents(s); w = e.x_advance
    if anker == "r": x -= w
    elif anker == "c": x -= w / 2
    cr.set_source_rgba(*farbe, alpha); cr.move_to(x, y); cr.show_text(s)
    if s.strip() and alpha > 0.02:
        BOXEN.append((id(cr), x, y + e.y_bearing, x + max(w, e.x_bearing + e.width), y + e.y_bearing + e.height, s))
    return w

def umbrechen(cr, s, breite, fam, size):
    font(cr, fam, size)
    zeilen, akt = [], ""
    for wort in s.split(" "):
        probe = (akt + " " + wort).strip()
        if akt and cr.text_extents(probe).x_advance > breite:
            zeilen.append(akt); akt = wort
        else:
            akt = probe
    if akt: zeilen.append(akt)
    return zeilen

def absatz(cr, s, x, y_erste, size, farbe, breite, lh, fam=TXT, alpha=1.0):
    zeilen = umbrechen(cr, s, breite, fam, size)
    for k, z in enumerate(zeilen):
        text(cr, z, x, y_erste + k * lh, size, farbe, fam, alpha)
    return len(zeilen)

def absatz_unten(cr, s, x, y_letzte, size, farbe, breite, lh, fam=TXT, alpha=1.0):
    zeilen = umbrechen(cr, s, breite, fam, size)
    y0 = y_letzte - (len(zeilen) - 1) * lh
    for k, z in enumerate(zeilen):
        text(cr, z, x, y0 + k * lh, size, farbe, fam, alpha)
    return y0

def mischen(a, b, u):
    return tuple(a[k] * (1 - u) + b[k] * u for k in range(3))

def kopfleiste(cr, mitte, faktor_txt, uhr_txt, alpha=1.0, blitz=0.0):
    cr.set_source_rgba(*C["petrol"], 0.94 * alpha); cr.rectangle(0, 0, W, KOPF_H); cr.fill()
    cr.set_source_rgba(*C["petrol_l"], 0.55 * alpha); cr.rectangle(0, KOPF_H, W, 1); cr.fill()
    # Marke wie auf den Seiten des Kiezatlas: Quadrat halb Akzent, halb Tinte
    cr.set_source_rgba(*C["ink"], alpha); cr.rectangle(32, 25, 14, 14); cr.fill()
    cr.set_source_rgba(*C["accent"], alpha); cr.rectangle(32, 25, 7, 7); cr.fill()
    cr.set_source_rgba(*C["tief"], alpha); cr.rectangle(39, 32, 7, 7); cr.fill()
    yb = 41
    lw = text(cr, "Kiezatlas Potsdam · Der Lauf im Terminal", 58, yb, GR_KOPF + 1, C["ink"], TXT_SB, alpha)
    if mitte: text(cr, mitte, 58 + lw + 40, yb, GR_KOPF - 1, C["ink"], TXT, 0.92 * alpha)
    if faktor_txt:
        font(cr, TXT_SB, GR_KOPF); w = cr.text_extents(faktor_txt).x_advance + 28
        x = W - 32 - w
        if uhr_txt:
            uw = text(cr, uhr_txt, W - 32, yb, GR_KOPF, C["ink"], TXT, alpha, "r")
            x = W - 32 - uw - 20 - w
        if blitz > 0:   # Wechsel des Zeitraffers: Plakette blitzt auf
            g = 6 + 10 * blitz
            cr.set_source_rgba(*C["txt"], 0.5 * blitz * alpha); cr.rectangle(x - g, 15 - g, w + 2 * g, 34 + 2 * g); cr.fill()
        cr.set_source_rgba(*mischen(C["paper"], C["txt"], blitz), alpha); cr.rectangle(x, 15, w, 34); cr.fill()
        text(cr, faktor_txt, x + 14, yb, GR_KOPF, C["tief"], TXT_SB, alpha)
    elif uhr_txt:
        text(cr, uhr_txt, W - 32, yb, GR_KOPF, C["ink"], TXT, alpha, "r")

def zeitleiste(cr, segs, r, titel, alpha=1.0, klein_gruppe=None, titel_fertig=None):
    """segs: [(etikett, dauer)]; r: verstrichene Echtzeit. Maßstäblich nach dauer (Wiedergabe eines Protokolls).
    Etiketten mit Dauer erscheinen erst, wenn ihr Segment abgelaufen ist; titel_fertig ersetzt titel am Ende.
    klein_gruppe: Text für ein gemeinsames Etikett aller kleinen Segmente (statt je eines)."""
    x0, x1, y = 72, W - 72, ZL_Y
    tot = sum(d for _, d in segs)
    fertig = r >= tot - 1e-6
    tw = text(cr, titel_fertig if (fertig and titel_fertig) else titel, x0, y - 13, 16, C["muted"], TXT_M, alpha)
    if titel_fertig:   # Platz für den längeren Titel freihalten, damit die Etiketten nicht springen
        font(cr, TXT_M, 16); tw = max(tw, cr.text_extents(titel_fertig).x_advance)
    cx, mittel, acc = x0, [], 0.0
    for lab, d in segs:
        w = (x1 - x0) * d / tot
        cr.set_source_rgba(*C["petrol"], 0.75 * alpha); cr.rectangle(cx, y, max(w - 2, 1), 14); cr.fill()
        anteil = max(0.0, min(1.0, (r - acc) / d)) if d else 1.0
        if anteil > 0:
            cr.set_source_rgba(*C["txt"], 0.95 * alpha); cr.rectangle(cx, y, max((w - 2) * anteil, 1), 14); cr.fill()
        mittel.append((cx, max(w - 2, 1), lab, d, r >= acc + d - 1e-6))
        cx += w; acc += d
    klein = []
    for sx, w, lab, d, da in mittel:
        if not da and w >= 300:
            continue
        if w >= 300:
            font(cr, MONO, 16, True); lw = cr.text_extents(lab).x_advance
            lx = min(max(sx + w / 2 - lw / 2, x0 + tw + 36), x1 - lw)
            text(cr, lab, lx, y - 12, 16, C["txt"], MONO, alpha, bold=True)
        else:
            klein.append([sx, w, lab])
    gruppe, gruppe_da = [], True
    if klein_gruppe:
        for sx_, w_, lab_, _, da_ in mittel:
            if w_ >= 300: break
            gruppe.append([sx_, w_, lab_]); gruppe_da = gruppe_da and da_
        klein = [k for k in klein if k not in gruppe]
    # kleine Einzeletiketten: Position aus allen (kein Springen), sichtbar erst nach Ablauf
    sichtbar_klein = {id(k): next(m[4] for m in mittel if m[0] == k[0]) for k in klein}
    if gruppe and gruppe_da:
        sx = gruppe[0][0]; ex = gruppe[-1][0] + gruppe[-1][1]
        cr.set_source_rgba(*C["muted"], 0.8 * alpha); cr.rectangle(sx, y + 20, ex - sx, 1.5); cr.fill()
        text(cr, klein_gruppe, sx, y + 40, 16, C["txt"], MONO, 0.9 * alpha)
    if klein:
        for k in klein:
            font(cr, MONO, 15); k.append(cr.text_extents(k[2]).x_advance)
        pos = []
        for k in range(len(klein)):
            p = klein[k][0]
            if k: p = max(p, pos[-1] + klein[k - 1][3] + 22)
            pos.append(max(p, x0))
        for k in range(len(klein) - 1, -1, -1):
            grenze = x1 if k == len(klein) - 1 else pos[k + 1] - 22
            pos[k] = min(pos[k], grenze - klein[k][3])
        for kk, ((sx, w, lab, lw), lx) in enumerate(zip(klein, pos)):
            if not sichtbar_klein[id(klein[kk])]: continue
            # feiner Strich vom Segment zum Etikett
            cr.set_source_rgba(*C["muted"], 0.7 * alpha); cr.set_line_width(1)
            cr.move_to(sx + w / 2, y + 16); cr.line_to(sx + w / 2, y + 22); cr.line_to(lx + 4, y + 22); cr.line_to(lx + 4, y + 25); cr.stroke()
            text(cr, lab, lx, y + 40, 15, C["txt"], MONO, 0.9 * alpha)
    px = x0 + (x1 - x0) * min(r / tot, 1.0) if tot else x0
    cr.set_source_rgba(*C["bright"], alpha); cr.rectangle(px - 1, y - 6, 2, 26); cr.fill()

def fuss(cr, notiz, quelle, vermerke, alpha=1.0):
    if notiz:
        absatz_unten(cr, notiz, 72, 946, GR_NOTIZ, C["muted"], W - 144, 22, TXT, 0.95 * alpha)
    cr.set_source_rgba(*C["petrol_l"], 0.45 * alpha); cr.rectangle(72, 962, W - 144, 1); cr.fill()
    if quelle: text(cr, quelle, 72, 986, GR_QUELLE, C["muted"], TXT, alpha)
    if vermerke:
        absatz(cr, "Daten: " + "\u00a0· ".join(v.replace("© ", "©\u00a0") for v in vermerke), 72, 1012, GR_DATEN, C["ink"], W - 144, 22, TXT, 0.95 * alpha)

def json_auszug(L):
    z = L["zaehler"]
    zaehl = ", ".join(f'"{k}": {v}' for k, v in list(z.items())[:5])   # Reihenfolge der Datei, Rest gekürzt
    q = L["json"]["quellen"][0]
    assert list(q)[:3] == ["quelle", "typ", "status"], list(q)
    return [f'"quelle": "{q["quelle"]}", "typ": "{q["typ"]}", "status": "{q["status"]}"',
            '"zaehler": {' + zaehl + ', …}',
            f'"unvollstaendig": {"true" if L["unvollstaendig"] else "false"}, "laufzeit_s": {L["q_sek"]}']

def laufkarte(cr, L, a, kita_u=0.0):
    """Karte unter dem Terminal: Auszug aus dem JSON-Bericht links, was belege/README.md belegt rechts."""
    y0, y1 = KARTE_Y0, KARTE_Y1
    cr.set_source_rgba(*C["bg_out"], 0.55 * a); cr.rectangle(72, y0, W - 144, y1 - y0); cr.fill()
    cr.set_source_rgba(*C["petrol_l"], 0.5 * a); cr.set_line_width(1); cr.rectangle(72.5, y0 + 0.5, W - 145, y1 - y0 - 1); cr.stroke()
    xm = 1010
    cr.rectangle(xm, y0 + 16, 1, y1 - y0 - 32); cr.fill()
    text(cr, f"belege/{L['id']}.json (Auszug)", 96, y0 + 34, 16, C["muted"], TXT_M, a)
    for k, z in enumerate(json_auszug(L)):
        yy = y0 + 68 + k * 28
        if k == 2 and L["unvollstaendig"] and kita_u > 0:
            font(cr, MONO, 16); w = cr.text_extents(z.split(",")[0]).x_advance
            cr.set_source_rgba(*C["accent"], 0.85 * kita_u * a); cr.rectangle(90, yy - 19, w + 12, 26); cr.fill()
        text(cr, z, 96, yy, 16, C["ink"] if k != 2 or not L["unvollstaendig"] else C["violett"], MONO, a)
    if L["info"].get("titel"):
        absatz(cr, f"Dienst: {L['info']['titel']} · {L['info']['kontakt']['anbieter']}", 96, y0 + 154, 15, C["muted"], xm - 130, 20, TXT, a)
    else:
        text(cr, f"typ {L['typ']}: lokale Datei, kein Netzabruf im Lauf", 96, y0 + 154, 15, C["muted"], TXT, a)
    xr = xm + 28; br = W - 72 - 24 - xr
    if L is KITA and kita_u > 0:
        text(cr, f"Warum {KITA_ERH} von {KITA_GEM}? belege/README.md, Zeile {KITA_GRUND_Z}:", xr, y0 + 34, 16, C["violett"], TXT_M, a * kita_u)
        absatz(cr, KITA_GRUND, xr, y0 + 68, 21, C["ink"], br, 27, TXT_M, a * kita_u)
    else:
        text(cr, "Was der Lauf belegt (belege/README.md):", xr, y0 + 34, 16, C["muted"], TXT_M, a)
        absatz(cr, BELEGT[L["id"]].replace("`", ""), xr, y0 + 76, 26, C["ink"], br, 32, TXT_M, a)

def pruefgitter(cr, s, a=1.0):
    """18 Felder, je Prüfung eines (Radius 0 wie die Gitterzellen); füllt sich, wenn die Zeile „grün“ erscheint."""
    y0, y1 = KARTE_Y0, KARTE_Y1
    cr.set_source_rgba(*C["bg_out"], 0.55 * a); cr.rectangle(72, y0, W - 144, y1 - y0); cr.fill()
    cr.set_source_rgba(*C["petrol_l"], 0.5 * a); cr.set_line_width(1); cr.rectangle(72.5, y0 + 0.5, W - 145, y1 - y0 - 1); cr.stroke()
    text(cr, f"Je Prüfung ein Feld, gefüllt sobald ihre Zeile „grün“ meldet ({P_N} Prüfungen in pruefen.sh)", 96, y0 + 34, 16, C["muted"], TXT_M, a)
    n = len(ABSCHNITTE); gap = 8; fw = (W - 144 - 48 - (n - 1) * gap) / n; fy = y0 + 56; fh = 58
    for k, ab in enumerate(ABSCHNITTE):
        fx = 96 + k * (fw + gap)
        if s >= ab["s1"]:
            cr.set_source_rgba(*C["txt"], a); cr.rectangle(fx, fy, fw, fh); cr.fill()
        elif s >= ab["s0"]:
            u = 0.30 + 0.25 * math.sin(s * 0.9 + k)
            cr.set_source_rgba(*C["faint"], u * a); cr.rectangle(fx, fy, fw, fh); cr.fill()
            cr.set_source_rgba(*C["dim"], a); cr.set_line_width(3); cr.rectangle(fx + 1.5, fy + 1.5, fw - 3, fh - 3); cr.stroke()
            cr.set_line_width(1)
        cr.set_source_rgba(*C["petrol_l"], 0.7 * a); cr.rectangle(fx + 0.5, fy + 0.5, fw - 1, fh - 1); cr.stroke()
    fertig = s >= P_ENDE
    if fertig:
        text(cr, P_ZAEHL[1][3:], 96, y0 + 158, 30, C["ink"], TXT_SB, a)
        text(cr, P_RUECK[2:], W - 96, y0 + 158, 22, C["txt"], MONO, a, "r")
    else:
        g = sum(s >= ab["s1"] for ab in ABSCHNITTE)
        text(cr, f"{g} von {P_N} gemeldet", 96, y0 + 158, 24, C["muted"], TXT_M, a)

def balken(cr, x, y, w, h, ziel, feld, maxv, u, hervor, etik, a=1.0, von=None, mix=1.0):
    """Je Stadtteil ein Balken; wachsen von der Grundlinie ein (Darstellung). ziel: Reihenfolge am Ende; von/mix:
    Umsortieren aus einer anderen Reihenfolge (mix 0 = von, 1 = ziel). hervor: {nr: Gewicht 0..1} (Papierfarbe).
    etik: [(Stadtteil, anker l|r, alpha)], Beschriftung unter der Grundlinie mit feinem Strich zum Balken."""
    n = len(ziel); gap = 4; bw = (w - (n - 1) * gap) / n
    pos = {}
    for k, st in enumerate(ziel):   # gestaffelt umsortieren, damit nicht alle Balken zugleich in der Mitte stehen
        mk = max(0.0, min(1.0, mix * 1.6 - k / n * 0.6)); e = mk * mk * (3 - 2 * mk)
        pos[st["nr"]] = (von.index(st) if von else k) * (1 - e) + k * e
    cr.set_source_rgba(*C["petrol_l"], 0.6 * a); cr.rectangle(x, y + h, w, 1); cr.fill()
    rang = {st["nr"]: k for k, st in enumerate(von or ziel)}   # Einwachsen in der Reihenfolge, die zuerst steht
    for st in sorted(ziel, key=lambda x: hervor.get(x["nr"], 0.0)):   # hervorgehobene obenauf
        uu = max(0.0, min(1.0, u * 1.6 - rang[st["nr"]] / n * 0.6))
        uu = 1 - (1 - uu) ** 3
        bh = max(h * st[feld] / maxv * uu, 1.5 if uu > 0 else 0)
        g = hervor.get(st["nr"], 0.0)
        # deckend (gegen den Grund gemischt), damit sich kreuzende Balken beim Umsortieren nicht verschmieren
        cr.set_source_rgba(*mischen(mischen(C["bg_in"], C["txt"], 0.74), C["paper"], g), a)
        cr.rectangle(x + pos[st["nr"]] * (bw + gap), y + h - bh, bw, bh); cr.fill()
    for st, anker, al in etik:
        if al <= 0: continue
        bx = x + pos[st["nr"]] * (bw + gap)
        lab = f"{st['name']} {de(st[feld])} %"
        cr.set_source_rgba(*C["paper"], 0.8 * al * a); cr.set_line_width(1.5)
        xs = bx + bw / 2; cr.move_to(xs, y + h + 4); cr.line_to(xs, y + h + 9); cr.stroke(); cr.set_line_width(1)
        if anker == "l":
            text(cr, lab, bx, y + h + 30, 19, C["paper"], TXT_SB, al * a)
        else:
            text(cr, lab, bx + bw, y + h + 30, 19, C["paper"], TXT_SB, al * a, "r")

# ---------------------------------------------------------------- Bildaufbau
_STATIC = {}
def statik(clean):
    if clean in _STATIC: return _STATIC[clean]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    v = np.clip(d, 0, 1) ** 1.6
    bg = (np.array(C["bg_in"], np.float32)[None, None] * (1 - v[..., None]) +
          np.array(C["bg_out"], np.float32)[None, None] * v[..., None])
    vign = (1 - 0.35 * np.clip(d - 0.55, 0, 1) ** 1.2)[..., None]
    scan = np.ones((H, 1, 1), np.float32)
    if not clean:
        scan[2::3] = 0.86
    rng = np.random.default_rng(7)
    grain = None if clean else rng.normal(0, 0.010, (H, W, 1)).astype(np.float32)   # feste Körnung (Dateigröße)
    _STATIC[clean] = (bg, vign, scan, grain)
    return _STATIC[clean]

def surf_np(s):
    a = np.ndarray((H, W, 4), np.uint8, s.get_data()).astype(np.float32) / 255
    return a[..., [2, 1, 0]], a[..., 3:4]

def blur(rgb, r):
    im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    im = im.resize((W // 2, H // 2), Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / 2)).resize((W, H), Image.BILINEAR)
    return np.asarray(im).astype(np.float32) / 255

NOTIZ_IMPORT = (f"schematisch: Die Zeile „läuft … s“ ist Darstellung, die Pipeline gibt den Bericht am Ende des Laufs aus; "
                f"er erscheint hier nach der gemessenen Laufzeit (laufzeit_s). Zeitraffer {F_KURZ}× bei kurzen Läufen, "
                f"{F_LANG}× bei gebaeude_alkis und alkis_nutzung; Pausen zwischen den Läufen ausgelassen. Befehl laut belege/README.md.")
NOTIZ_PRUEF = (f"gekürzt: nur Kopf, Abschnittszeilen (== / --), drei Zeilen aus pruefen/daten.py und die Zählung, "
               f"{len(PLOG)} Zeilen im Protokoll; Zeitstempel des Protokolls entfernt. Zeitraffer {P_F1}× bis zum ersten Browser-Test, "
               f"danach {P_F2}×. „läuft … s“ ist Darstellung.")

def frame(i, clean=False):
    t = i / FPS
    name, lt, sd = szene_bei(t)
    term = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ct = cairo.Context(term)
    ui = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); cu = cairo.Context(ui)
    fo = fopts()
    for c in (ct, cu): c.set_antialias(cairo.ANTIALIAS_GRAY); c.set_font_options(fo)
    hell = 1.0

    if name == "titel":
        on = min(1.0, lt / 0.35)
        s = "Der Lauf im Terminal"
        k = min(len(s), int(len(s) * max(0, lt - 0.3) / 0.7))
        text(ct, s[:k], 160, 470, 76, C["bright"], MONO, bold=True)
        if (int(lt * 3) % 2 == 0) or k < len(s):
            font(ct, MONO, 76, True); w = ct.text_extents(s[:k]).x_advance
            ct.set_source_rgba(*C["txt"], 1); ct.rectangle(166 + w, 410, 40, 70); ct.fill()
        if lt > 0.75:
            a = min(1, (lt - 0.75) / 0.3)
            d1, d2 = utc(LAEUFE[0]["start"])[:6], utc(LAEUFE[-1]["start"])[:10]
            text(ct, f"Kiezatlas Potsdam. Sieben Importläufe vom {d1} und {d2}, Prüflauf vom {P_DATUM[0]}.",
                 164, 545, 26, C["txt"], MONO, a)
            text(cu, "André Stiebitz · Stiebitz Souverain Systems UG", 164, 604, 22, C["muted"], TXT_SB, a)
        if lt > 1.3:
            a = min(1, (lt - 1.3) / 0.4)
            text(cu, "Was die Läufe über Potsdam zeigen: Fernwärme und Altbau, Stadtteil für Stadtteil", 164, 330, 34,
                 C["paper"], TXT_SB, a)
        if on < 1: hell = on

    elif name == "import":
        rows, akt, r, phase = import_zeilen(lt)
        terminal_malen(ct, rows)
        E = IMPORT[akt] if akt is not None else IMPORT[0]
        L = E["L"]
        f = FAKTOR[L["id"]]
        vorher = FAKTOR[IMPORT[akt - 1]["L"]["id"]] if akt else f
        blitz = max(0.0, 1 - (lt - E["t0"]) / 0.7) if (f != vorher and lt >= E["t0"]) else 0.0
        uhr = (f"Laufzeit {de(r, 2)} s" if phase != "fertig" else f"Laufzeit {sek_txt(L['kopf_sek'])} s")
        kopfleiste(cu, f"Lauf {akt + 1} von {len(LAEUFE)} · {L['quelle']} · {utc(L['start'])}", f"Zeitraffer {f}×", uhr, blitz=blitz)
        # Karte zum Lauf erst, wenn sein Bericht da ist (nicht vorher)
        if phase == "fertig":
            a = min(1.0, (lt - E["t_fertig"]) / 0.25)
            ku = max(0.0, min(1.0, (lt - E["t_fertig"] - 0.6) / 0.5)) if L is KITA else 0.0
            laufkarte(cu, L, a, ku)
            if L is KITA and ku > 0:
                # Marker an der Warnzeile im Terminal
                n_vor = len(rows)
                idx = next(j for j, (Lz, _) in enumerate(rows) if Lz.t.lstrip().startswith("Warnung:"))
                pos = idx - max(0, n_vor - TROWS)
                yy = TY0 + pos * LH
                cu.set_source_rgba(*C["violett"], ku); cu.rectangle(TX0 - 26, yy - 19, 6, 26); cu.fill()
        segs = [(f"{Lx['quelle']} {sek_txt(Lx['kopf_sek'])} s", Lx["sek"]) for Lx in LAEUFE]
        zeitleiste(cu, segs, import_summe(akt, r), "laufzeit_s je Lauf, maßstäblich",
                   titel_fertig=f"laufzeit_s je Lauf, maßstäblich (Summe {de(SUMME_SEK, 2)} s)")
        verm = []
        for k in range(akt + 1):
            v = VERMERK[IMPORT[k]["L"]["quelle"]]
            if v not in verm: verm.append(v)
        fuss(cu, NOTIZ_IMPORT, f"Quelle: belege/{L['id']}.txt, .json · belege/README.md · Namensnennung QUELLEN.md", verm)

    elif name == "pruefen":
        rows, s, fertig = pruef_zeilen(lt)
        terminal_malen(ct, rows)
        f = P_F1 if s < P_BROWSER0 else P_F2
        sw = 0.25 + P_TYP + VOR + p_film(P_BROWSER0)
        blitz = max(0.0, 1 - (lt - sw) / 0.7) if sw <= lt < sw + 0.7 else 0.0
        uhr = f"+ {de(s, 1)} s" if not fertig else f"{de(P_ENDE, 1)} s"
        kopfleiste(cu, f"./pruefen.sh · Prüflauf {P_DATUM[0]}, {P_DATUM[1]} {P_DATUM[2]} · Commit {P_COMMIT}", f"Zeitraffer {f}×", uhr, blitz=blitz)
        pruefgitter(cu, s)
        segs = [(a["name"].replace("Browser: pruefen/", "").replace(".mjs", "") + f" {de(a['s1'] - a['s0'], 0)} s", a["s1"] - a["s0"])
                for a in ABSCHNITTE]
        vor = [a for a in ABSCHNITTE if a["s1"] <= P_BROWSER0]
        assert all(not a["name"].startswith("Browser:") for a in vor) and len(vor) == ABSCHNITTE.index(next(a for a in ABSCHNITTE if a["name"].startswith("Browser:")))
        zeitleiste(cu, segs, s - ABSCHNITTE[0]["s0"], "Dauer je Prüfung aus den Zeitstempeln, maßstäblich",
                   klein_gruppe=f"{len(vor)} Prüfungen ohne Browser zusammen {de(sum(a['s1'] - a['s0'] for a in vor), 1)} s")
        fuss(cu, NOTIZ_PRUEF, f"Quelle: {LOG_REL} (./pruefen.sh vom {P_DATUM[0]} mit Zeitstempel je Zeile, ein lokaler Pfad ersetzt)",
             [VERMERK_KENNZ])
        if lt < 0.12: hell = 0.35 + lt / 0.12 * 0.65

    elif name == "schluss":
        kopfleiste(cu, f"Was die Daten über Potsdam sagen · Auswertung daten/kennzahlen.json, Stand {datum_de(KZ['stand_auswertung'])}", None, None)
        def ein(t0, d=0.45): return max(0.0, min(1.0, (lt - t0) / d))
        a1 = ein(0.15)
        text(cu, punkt(GEB), 72, 250, 128, C["paper"], DISP, a1)
        text(cu, f"Gebäude in den {N_ST} Stadtteilen zugeordnet", 78, 300, 28, C["ink"], TXT_M, a1)
        text(cu, f"von {punkt(GEB_RECHT)} im Abrufrechteck geladen (Lauf {G['gebaeude_alkis']['id']})", 78, 336, 20, C["muted"], TXT, a1)
        a2 = ein(0.8)
        text(cu, punkt(EW), 1000, 250, 128, C["paper"], DISP, a2)
        text(cu, f"Einwohner in {punkt(ZELLEN)} 100-m-Zellen mit Mittelpunkt in Potsdam", 1006, 300, 28, C["ink"], TXT_M, a2)
        text(cu, f"Zensus 2022, Stichtag {STICHTAG}; von {punkt(ZELLEN_GELADEN)} geladenen Zellen (Lauf {G['zensus_gitter']['id']})",
             1006, 336, 20, C["muted"], TXT, a2)
        cu.set_source_rgba(*C["petrol_l"], 0.45 * ein(1.3)); cu.rectangle(72, 384, W - 144, 1); cu.fill()
        a3 = ein(1.5)
        BY, BH = 566, 200                       # Balken: Oberkante der Achse 100 %, Höhe
        text(cu, f"{de(FERN['wert'])} %", 72, 486, 92, C["paper"], DISP, a3)
        text(cu, "der Wohnungen heizen mit Fernwärme", 330, 470, 28, C["ink"], TXT_M, a3)
        text(cu, f"{punkt(FERN['zaehler'])} von {punkt(FERN['nenner'])} Wohnungen", 330, 502, 20, C["muted"], TXT, a3)
        text(cu, "je Stadtteil, absteigend nach Fernwärme", 72, 540, 17, C["muted"], TXT, ein(1.8))
        aus1 = 1 - ein(5.9, 0.3)                # Extreme je Reihe, danach die drei Beispiele in beiden Reihen
        ein2 = ein(7.7, 0.4)
        mix = ein(6.2, 1.4)
        def hv(h1):
            d = {k: aus1 for k in h1}
            for b in BEISPIELE: d[b["nr"]] = max(d.get(b["nr"], 0.0), ein2)
            return d
        bsp = [(B_FERN, "l", ein2), (B_BEIDES, "l", ein2), (B_ALT, "r", ein2)]
        if lt > 1.8:
            balken(cu, 72, BY, 820, BH, FERN_S, "fern", 100, min(1.0, (lt - 1.8) / 1.6), hv({F_MAX["nr"], F_MIN["nr"]}),
                   ([(F_MAX, "l", aus1), (F_MIN, "r", aus1)] if lt >= 3.4 else []) + bsp)
        a4 = ein(3.0)
        text(cu, f"{de(ALT['wert'])} %", 1000, 486, 92, C["paper"], DISP, a4)
        text(cu, "der Wohnungen in Gebäuden von vor 1949", 1258, 470, 28, C["ink"], TXT_M, a4)
        text(cu, f"{punkt(ALT['zaehler'])} von {punkt(ALT['nenner'])} Wohnungen", 1258, 502, 20, C["muted"], TXT, a4)
        if lt < 6.2:
            text(cu, "je Stadtteil, absteigend nach Altbau", 1000, 540, 17, C["muted"], TXT, ein(3.3))
        else:
            text(cu, "je Stadtteil, umsortiert in die Reihenfolge links (nach Fernwärme)", 1000, 540, 17, C["paper"], TXT_M, ein(6.2, 0.3))
        if lt > 3.3:
            balken(cu, 1000, BY, 848, BH, FERN_S, "alt", 100, min(1.0, (lt - 3.3) / 1.6), hv({A_MAX["nr"], A_MIN["nr"]}),
                   ([(A_MAX, "l", aus1), (A_MIN, "r", aus1)] if lt >= 4.9 else []) + bsp, von=ALT_S, mix=mix)
        text(cu, MERKZEILE, 72, 852, 30, C["paper"], TXT_SB, ein(8.5))
        text(cu, MERK_AUSNAHME, 72, 884, 19, C["muted"], TXT, ein(9.1))
        fuss(cu, f"schematisch: Die Balken wachsen ein und sortieren sich um. Je Balken ein Stadtteil ab {punkt(MIN_EW)} Einwohnern "
                 f"({len(ST)} von {N_ST}), Achse 0 bis 100 %; kleinere sind durch die Geheimhaltung des Zensus unscharf. "
                 "Alle Werte wörtlich aus daten/kennzahlen.json, Anteile gegen alle Wohnungen wie auf der Seite.",
             "Quelle: daten/kennzahlen.json (stadt, stadtteile, kontrolle), belege/20261104T132333Z.json, 20261104T132325Z.json, "
             f"README.md „Zur Prüfung“, {LOG_REL} (pruefen/daten.py)", [VERMERK_KENNZ])

    term.flush(); ui.flush()
    bg, vign, scan, grain = statik(clean)
    trgb, ta = surf_np(term)
    urgb, ua = surf_np(ui)
    if name == "schluss":
        trgb = trgb * 0; ta = ta * 0
    img = bg * (1 - ta) + trgb
    img = img + (0.55 * blur(trgb, 9) + 0.25 * blur(trgb, 26) if not clean else 0.35 * blur(trgb, 9))
    img = img * scan
    if grain is not None: img = img + grain
    img = img * vign
    img = img * (1 - ua) + urgb          # Beschriftung scharf, ohne Leuchten
    if name == "titel" and hell < 1:
        h = int(H * hell / 2)
        maske = np.zeros((H, 1, 1), np.float32); maske[H // 2 - h:H // 2 + h + 2] = 1
        img = img * maske; img[H // 2 - 1:H // 2 + 2] += (1 - hell) * 0.8
    elif hell < 1:
        img = img * hell
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)

def _f(args):
    i, clean = args
    return frame(i, clean).tobytes()

T_STANDBILD = szene_start("import") + next(E for E in IMPORT if E["L"] is KITA)["t_fertig"] + 2.6   # Kita-Warnung mit Erklärung
T_STANDBILD_BEFUND = szene_start("schluss") + T_SCHLUSS - 0.5                                     # Zahlenkarte mit Merkzeile

def pruefe_layout():
    """Beschriftung: nichts über den Rand, keine Überlappung (je Ebene)."""
    fehler = 0
    zeiten = [szene_start(n) + x for n, d in SZENEN for x in (0.05, d / 2, d - 0.05)]
    zeiten += [szene_start("import") + E["t_fertig"] + E["halt"] - 0.05 for E in IMPORT]
    for t in zeiten:
        BOXEN.clear(); frame(int(t * FPS), True)
        for k, (c, x0, y0, x1, y1, s) in enumerate(BOXEN):
            if x1 > W - 30 or x0 < 0 or y1 > H - 8:
                print(f"t={t:.2f}: über den Rand: {s[:60]!r} ({x1:.0f}, {y1:.0f})"); fehler += 1
            for c2, a0, b0, a1, b1, s2 in BOXEN[k + 1:]:
                if c2 == c and x0 < a1 - 1 and a0 < x1 - 1 and y0 < b1 - 1 and b0 < y1 - 1:
                    print(f"t={t:.2f}: Überlappung {s[:40]!r} / {s2[:40]!r}"); fehler += 1
    print("Layout ok" if not fehler else f"{fehler} Befunde")
    return fehler

def render_video(out, jobs, clean):
    print(f"Dauer {GESAMT:.2f} s, {NFRAMES} Bilder", file=sys.stderr)
    # Pool vor ffmpeg starten: sonst erben die Rechenprozesse das Schreibende der Pipe, ffmpeg bekommt
    # kein Dateiende und wartet für immer (so am 08.11.2026 passiert)
    pool = None
    if jobs > 1:
        try:
            from multiprocessing import Pool
            pool = Pool(jobs)
        except (OSError, PermissionError) as e:
            print(f"kein Multiprocessing ({e}), rechne seriell", file=sys.stderr)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p",
                           "-profile:v", "high", "-level", "4.1", "-r", str(FPS), "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    auftraege = [(i, clean) for i in range(NFRAMES)]
    bilder = pool.imap(_f, auftraege, chunksize=4) if pool else map(_f, auftraege)
    for k, b in enumerate(bilder):
        ff.stdin.write(b)
        if k % 150 == 0: print(k, file=sys.stderr)
    if pool: pool.close(); pool.join()
    ff.stdin.close(); ff.wait()
    if ff.returncode: sys.exit(ff.returncode)

def render_gif(mp4, out, fps=8, breite=960, farben=80):
    """GIF für die README: 960 px breit, 8 fps, entrauscht (Körnung frisst sonst die Palette), Palette aus dem Film mit
    80 Farben ohne Dithering. Die Palette würde das helle Violett der Kita-Warnung zu Grau mitteln; deshalb kommen
    Violett und zwei Abstufungen über dem Grund fest dazu. Ziel unter 6 MB."""
    import tempfile
    vor = f"fps={fps},scale={breite}:-1:flags=lanczos,hqdn3d=6:6:4:4"
    with tempfile.TemporaryDirectory() as tmp:
        pal = os.path.join(tmp, "palette.png")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-vf",
                        f"{vor},palettegen=max_colors={farben}:stats_mode=full", pal], check=True)
        im = Image.open(pal).convert("RGB"); px = np.asarray(im).reshape(-1, 3).copy()
        assert len(px) == 256
        fest = [C["violett"], mischen(C["violett"], C["bg_in"], 0.3), mischen(C["violett"], C["bg_in"], 0.55),
                C["accent"], mischen(C["violett"], C["accent"], 0.5)]
        for k, c in enumerate(fest):
            px[farben + k] = tuple(int(round(v * 255)) for v in c)   # Einträge hinter den genutzten Farben
        Image.fromarray(px.reshape(im.height, im.width, 3).astype(np.uint8)).save(pal)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-i", pal, "-lavfi",
                        f"{vor}[v];[v][1:v]paletteuse=dither=none:diff_mode=rectangle", "-loop", "0", out], check=True)
    print(f"{out}: {os.path.getsize(out) / 1e6:.2f} MB", file=sys.stderr)

def manifest():
    t0 = 0.0; zeiten = {}
    for n, d in SZENEN: zeiten[n] = (round(t0, 2), round(t0 + d, 2)); t0 += d
    out = dict(
        gesamt_s=round(NFRAMES / FPS, 2), frames=NFRAMES, szenen=zeiten, faktenblatt_abgeglichen=FAKTEN_GEPRUEFT,
        importlaeufe=[dict(lauf_id=L["id"], befehl=CMD[L["id"]], quelle=L["quelle"], laufzeit_s=L["sek"], zaehler=L["zaehler"],
                           warnungen=L["warnungen"], unvollstaendig=L["unvollstaendig"], zeitraffer=FAKTOR[L["id"]],
                           belegt=BELEGT[L["id"]], vermerk=VERMERK[L["quelle"]], datei=f"belege/{L['id']}.txt/.json")
                      for L in LAEUFE],
        summe_laufzeit_s=round(SUMME_SEK, 2),
        kita=dict(erhalten=KITA_ERH, gemeldet=KITA_GEM, grund=KITA_GRUND, fundstelle=f"belege/README.md Z. {KITA_GRUND_Z}"),
        pruefen=dict(log_sha256=LOG_SHA, zeilen=len(PLOG), commit=P_COMMIT, datum=P_DATUM, dauer_s=P_ENDE, zaehlung=P_ZAEHL[1],
                     rueckgabe=P_RUECK, abschnitte={a["name"]: round(a["s1"] - a["s0"], 3) for a in ABSCHNITTE},
                     auszug=[t for _, t, _ in P_AUSZUG]),
        zahlenkarte=dict(gebaeude=GEB, gebaeude_im_rechteck=GEB_RECHT, einwohner=EW, zellen=ZELLEN, zellen_geladen=ZELLEN_GELADEN,
                         fernwaerme=FERN, altbau=ALT, fern_max=F_MAX, fern_min=F_MIN, alt_max=A_MAX, alt_min=A_MIN,
                         stadtteile_ab_1000=len(ST), datei="daten/kennzahlen.json",
                         rangkorrelation_spearman=round(RHO, 4), merkzeile=MERKZEILE, ausnahme=MERK_AUSNAHME,
                         beispiele=dict(fernwaerme_ohne_altbau=B_FERN, viel_von_beidem=B_BEIDES, altbau_ohne_fernwaerme=B_ALT)),
        pruefen_log=LOG_REL,
        vermerk_kennzahlen=VERMERK_KENNZ)
    print(json.dumps(out, ensure_ascii=False, indent=1))

def main():
    ap = argparse.ArgumentParser(description="Film „Der Lauf im Terminal“ des Kiezatlas Potsdam bauen", parents=[_ap0])
    ap.add_argument("--clean", action="store_true", help="ohne Rasterzeilen und Körnung")
    ap.add_argument("--still", default="", help="Probebilder zu Zeitpunkten in s, Komma-getrennt")
    ap.add_argument("--probe-dir", default=os.path.join(ROOT, "berichte", "filme-2026-11-08", "terminal"))
    ap.add_argument("--standbild", nargs="?", const="kita", choices=["kita", "befund"],
                    help="standbild.png (kita: Warnung mit Erklärung); befund: Zahlenkarte als standbild-befund.png in --probe-dir")
    ap.add_argument("--gif", action="store_true", help="film.gif aus film.mp4 erzeugen")
    ap.add_argument("--check", action="store_true", help="Layout der Beschriftung prüfen")
    ap.add_argument("--out", default=os.path.join(HERE, "film.mp4"))
    ap.add_argument("--jobs", type=int, default=min(6, os.cpu_count() or 1))
    ap.add_argument("--manifest", action="store_true")
    a = ap.parse_args()
    if a.manifest: return manifest()
    if a.check: sys.exit(1 if pruefe_layout() else 0)
    if a.still:
        os.makedirs(a.probe_dir, exist_ok=True)
        for s in a.still.split(","):
            Image.fromarray(frame(int(round(float(s) * FPS)), a.clean)).save(os.path.join(a.probe_dir, f"probe-{s}.png"))
        return
    if a.standbild == "befund":
        os.makedirs(a.probe_dir, exist_ok=True)
        Image.fromarray(frame(int(round(T_STANDBILD_BEFUND * FPS)), a.clean)).save(
            os.path.join(a.probe_dir, "standbild-befund.png"), optimize=True)
        return
    if a.standbild:
        Image.fromarray(frame(int(round(T_STANDBILD * FPS)), a.clean)).save(os.path.join(HERE, "standbild.png"), optimize=True)
        return
    if a.gif: return render_gif(a.out, os.path.join(HERE, "film.gif"))
    render_video(a.out, a.jobs, a.clean)

if __name__ == "__main__":
    main()
