"""Prüfung vor einer Veröffentlichung (übernommen aus dem Kiezatlas Kraków, 16.11.2026): Arbeitsbaum (und auf Wunsch die Git-Historie) auf Dinge, die nicht hinausgehen.

Kein Netz, keine Datenbank, nur Python-Standardbibliothek (läuft mit `python3 -I` und in der Projektumgebung).

Geprüft wird jede Datei, die Git veröffentlichen würde: eingecheckte Dateien und neue, nicht ignorierte Dateien.
Kategorien:
  pfad          persönliche Pfade (/home/<name>/, /Users/<name>/, C:\\Users\\<name>\\, Zwischenordner /tmp/claude-…)
  email         E-Mail-Adressen; Rollen- und Behördenadressen stehen begründet in der Ausnahmeliste
  rechner       Rechnernamen dieses Rechners: der eigene Name (socket.gethostname) und die Host-Einträge aus
                ~/.ssh/config, dazu Namen aus der Datei in $OEFFENTLICH_RECHNER (ein Name je Zeile). Die Namen
                stehen bewusst nicht in diesem Skript, weil es selbst veröffentlicht wird. Namen mit Bindestrich
                oder Ziffer gelten überall als Treffer, alle übrigen nur in eindeutiger Stellung
                (name:/pfad, ssh name, @name, name.local); so bleiben Wörter wie „Relais“ im Text unberührt.
  geheimnis     Schlüssel und Tokens (privater Schlüssel, AWS, GitHub, GitLab, Slack, sk-…), Zuweisungen wie
                PASSWORD=wert, Anmeldedaten in URLs. Der Wert wird nie ausgegeben, nur Datei und Zeile.
  plankennung   interne Plankennungen im Fließtext: „Tor M“, „Phase 2b“, „Paket D4“, Zweignamen bau/…,
                P0 bis P9, „Master-Session“, interne Tags. Dateinamen wie belege/D4_*.md und die Nummern der
                Entscheidungen sind öffentliche Ordnung des Repos und keine Treffer. In ausgelieferten
                Seiten prüft pruefen/geruest.py strenger.
  gross         Dateien über --max-mb (Standard 5 MB)
  lizenz        Datei ohne Lizenzregel: Code und Text fallen unter LICENSE (Apache-2.0); Dateien unter daten/
                müssen in daten/LIZENZ.md stehen, Fremdbestandteile unter vendor/ und fonts/ in NOTICE, Binärdateien
                brauchen eine Regel in der Ausnahmeliste

Ausnahmen: skripte/oeffentlich_ausnahmen.tsv (Kategorie, Pfadmuster, Wertmuster, Art, Begründung). Art
  ausnahme              begründet, bleibt so; zählt nicht als Befund
  vor_veroeffentlichung bekannt, gehört einem anderen Eigentümer und ist vor der Veröffentlichung zu beheben;
                        zählt nur mit --veroeffentlichung als Befund
  befund                immer ein Befund, auch wenn eine spätere Zeile passen würde (für Dateien, deren Eigentümer
                        sie selbst sauber halten muss)
Alles andere ist ein Befund.

Aufruf:
  python3 -I skripte/oeffentlich_pruefen.py [--max-mb 5] [--veroeffentlichung] [--alle]
  python3 -I skripte/oeffentlich_pruefen.py --historie [--max-mb 5]
      Git-Historie: jede Datei in jedem Commit (alle Zweige und Tags), Autor- und Committer-Adressen, Commit-Texte.
      Gibt eine Zusammenfassung je Kategorie aus; Rückgabe 1, sobald ein Geheimnis ohne begründete Ausnahme oder
      eine eingecheckte Umgebungsdatei (.env) auftaucht, sonst 0 (Adressen und Kennungen stehen im Bericht).
--alle zeigt auch Ausnahmen einzeln (sonst nur ihre Zahl je Regel).
Rückgabe 0 = keine Befunde, 1 = Befund, 2 = falscher Aufruf.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import os
import re
import socket
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
AUSNAHMEN = WURZEL / "skripte" / "oeffentlich_ausnahmen.tsv"

PFAD = re.compile(r"(?:/home/[A-Za-z0-9._-]+/|/Users/[A-Za-z0-9._-]+/|[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\|/tmp/claude-[0-9]+|~/(?:Workspace|localWorkspace)/)")
EMAIL = re.compile(r"(?<![A-Za-z0-9._%+:/-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
URL_ANMELDUNG = re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@\"'<>]+:[^/\s@\"'<>]+@")
GEHEIMNIS = [
    ("privater Schlüssel", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("AWS-Schlüssel", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub-Token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("GitLab-Token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}")),
    ("Slack-Token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("API-Schlüssel sk-", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{24,}")),
    # Umgebungszeile NAME=wert (wie in .env) und Literal in Anführungszeichen; Variablennamen als Wert zählen nicht
    ("Zuweisung eines Geheimnisses", re.compile(
        r"^\s*(?:export\s+)?[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY)[A-Z0-9_]*\s*=\s*[^\s$\"'{<]{8,}")),
    ("Geheimnis als Literal", re.compile(
        r"(?i)(?:password|passwd|secret|token|api_?key)\w*[\"']?\s*[:=]\s*[\"'][^\"'\s$<{]{8,}[\"']")),
    ("Anmeldedaten in URL", URL_ANMELDUNG),
]
PLAN = [
    ("Tor", re.compile(r"\bTor [A-Z]\b")),
    ("Phase", re.compile(r"\bPhase [0-9]+[a-z]?\b")),
    ("Paket mit Kennung", re.compile(r"\b[Pp]akets? (?:D[0-9]{1,2}|S[0-9]|DE|DF|DK|DS|DW|DZ|dk|d3)\b")),
    ("Zweig bau/", re.compile(r"\bbau/[a-z0-9]+")),
    ("Plan P<n>", re.compile(r"(?<![\w./-])P[0-9](?![\w])")),
    ("Master-Session", re.compile(r"Master-Session")),
    ("interner Tag", re.compile(r"\bangebot-[a-z]+-[0-9]{4}-[0-9]+\b")),
]


TEXT_ENDUNGEN = {".py", ".js", ".mjs", ".sh", ".md", ".html", ".css", ".yaml", ".yml", ".json", ".sql", ".txt",
                 ".tsv", ".csv", ".log", ".cff", ".svg", ".in", ".patch", ".sha256", ".beispiel", ".gitignore",
                 ".toml", ".cfg", ".ini", ".xml", ".vtt"}
TEXT_NAMEN = {"LICENSE", "NOTICE", "Makefile", ".gitignore", ".gitattributes", ".env.beispiel", "atlas.sh"}


def git(*args: str, eingabe: bytes | None = None) -> bytes:
    return subprocess.run(["git", "-C", str(WURZEL), *args], check=True, capture_output=True, input=eingabe).stdout


def arbeitsbaum() -> list[str]:
    roh = git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
    namen = sorted({n for n in roh.decode("utf-8").split("\0") if n})
    return [n for n in namen if (WURZEL / n).is_file() and not (WURZEL / n).is_symlink()]


def rechnernamen() -> tuple[set[str], set[str]]:
    """(überall, nur_eindeutig): Namen aus dem eigenen Rechnernamen, ~/.ssh/config und $OEFFENTLICH_RECHNER."""
    namen: set[str] = set()
    eigen = socket.gethostname().split(".")[0].strip()
    if eigen:
        namen.add(eigen)
    ssh = Path.home() / ".ssh" / "config"
    try:
        for zeile in ssh.read_text(encoding="utf-8", errors="replace").splitlines():
            teile = zeile.split()
            if len(teile) >= 2 and teile[0].lower() == "host":
                namen.update(t for t in teile[1:] if not any(c in t for c in "*?!"))
    except OSError:
        pass
    extra = os.environ.get("OEFFENTLICH_RECHNER")
    zusatz: set[str] = set()
    if extra:
        try:
            zusatz = {z.strip() for z in Path(extra).read_text(encoding="utf-8").splitlines()
                      if z.strip() and not z.startswith("#")}
        except OSError as e:
            print(f"Warnung: $OEFFENTLICH_RECHNER nicht lesbar ({e})", file=sys.stderr)
    namen = {n for n in namen if len(n) >= 3 and "." not in n}
    ueberall = {n for n in namen if re.search(r"[-0-9]", n)} | zusatz | ({eigen} if eigen else set())
    return ueberall, namen - ueberall


def rechner_muster(ueberall: set[str], eindeutig: set[str]) -> list[re.Pattern]:
    muster = []
    if ueberall:
        alt = "|".join(sorted((re.escape(n) for n in ueberall), key=len, reverse=True))
        muster.append(re.compile(rf"(?i)(?<![\w.-])(?:{alt})(?![\w-])"))
    if eindeutig:
        alt = "|".join(sorted((re.escape(n) for n in eindeutig), key=len, reverse=True))
        muster.append(re.compile(rf"(?<![\w.-])(?:{alt})(?=:[/~]|\.local\b|\.lan\b)"))
        muster.append(re.compile(rf"(?:\bssh\s+(?:-\S+\s+)*|@)(?:{alt})(?![\w-])"))
    return muster


class Ausnahmen:
    def __init__(self, datei: Path):
        self.regeln: list[dict] = []
        if datei.exists():
            with datei.open(encoding="utf-8", newline="") as f:
                for z in csv.DictReader((l for l in f if not l.startswith("#")), delimiter="\t"):
                    z["treffer"] = 0
                    z["wert_re"] = re.compile(z["wertmuster"]) if z["wertmuster"] not in ("", "*") else None
                    self.regeln.append(z)

    def suche(self, kategorie: str, pfad: str, wert: str) -> dict | None:
        for r in self.regeln:
            if r["kategorie"] not in (kategorie, "*") or not fnmatch.fnmatchcase(pfad, r["pfadmuster"]):
                continue
            if r["wert_re"] is not None and not r["wert_re"].search(wert):
                continue
            r["treffer"] += 1
            return r
        return None


def lizenz_regeln() -> tuple[set[str], str]:
    lizenz = (WURZEL / "daten" / "LIZENZ.md").read_text(encoding="utf-8") if (WURZEL / "daten" / "LIZENZ.md").exists() else ""
    notice = (WURZEL / "NOTICE").read_text(encoding="utf-8") if (WURZEL / "NOTICE").exists() else ""
    genannt = set(re.findall(r"`([^`]+)`", lizenz))
    return genannt, notice


def lizenz_pruefen(pfad: str, genannt: set[str], notice: str) -> str | None:
    """Grund, warum keine Lizenzregel greift, oder None."""
    p = Path(pfad)
    if pfad.startswith("daten/") and not pfad.startswith("daten/schema/") and pfad != "daten/LIZENZ.md":
        teile = p.parts
        if teile[1] == "pobierz":
            return None if (WURZEL / "daten" / "pobierz" / "licencje.csv").exists() else "daten/pobierz/licencje.csv fehlt"
        # nur genaue Namen oder Pfade unter daten/; ein Muster gilt nur, wenn LIZENZ.md es ausdrücklich als Glob führt
        # (`*` im Eintrag), nicht über eine Teilzeichenfolge eines anderen Namens
        rel = "/".join(teile[1:])
        if p.name in genannt or rel in genannt or any("*" in g and fnmatch.fnmatchcase(rel, g) for g in genannt):
            return None
        return "nicht in daten/LIZENZ.md genannt"
    if pfad.startswith("vendor/"):
        if p.suffix in (".txt",):
            return None
        stamm = p.name.split(".")[0].split("-")[0].lower()
        return None if stamm and stamm.lower() in notice.lower() else "Fremdbestandteil nicht in NOTICE"
    if pfad.startswith("fonts/") and p.suffix == ".woff2":
        return None if (WURZEL / "fonts" / "OFL.txt").exists() and "OFL" in notice else "Schrift ohne OFL.txt oder NOTICE-Zeile"
    if pfad.startswith("schriften/noto/") and p.suffix == ".ttf":
        return None if (WURZEL / "schriften" / "noto" / "OFL.txt").exists() and "schriften/noto/" in notice \
            else "Kartenschrift ohne schriften/noto/OFL.txt oder NOTICE-Zeile"
    if p.suffix in TEXT_ENDUNGEN or p.name in TEXT_NAMEN:
        return None
    return "Binärdatei ohne Lizenzregel"


def zeilen(pfad: Path):
    try:
        daten = pfad.read_bytes()
    except OSError:
        return
    if b"\0" in daten[:8192]:
        return
    text = daten.decode("utf-8", errors="replace")
    for i, z in enumerate(text.splitlines(), 1):
        yield i, z


def treffer_in_zeile(z: str, rmuster: list[re.Pattern]):
    for m in PFAD.finditer(z):
        yield "pfad", m.group(0)
    for m in EMAIL.finditer(z):
        yield "email", m.group(0)
    for muster in rmuster:
        for m in muster.finditer(z):
            yield "rechner", m.group(0)
    for name, muster in GEHEIMNIS:
        if muster.search(z):
            yield "geheimnis", name
    for name, muster in PLAN:
        for m in muster.finditer(z):
            yield "plankennung", m.group(0)


def arbeitsbaum_pruefen(args) -> int:
    ausnahmen = Ausnahmen(AUSNAHMEN)
    ueberall, eindeutig = rechnernamen()
    rmuster = rechner_muster(ueberall, eindeutig)
    genannt, notice = lizenz_regeln()
    befunde: list[str] = []
    gemeldet: dict[str, list[str]] = defaultdict(list)
    ausgenommen: dict[str, list[str]] = defaultdict(list)
    dateien = arbeitsbaum()
    grenze = args.max_mb * 1024 * 1024

    def einordnen(kat: str, pfad: str, zeile: int | None, wert: str, zeige_wert: bool = True):
        ort = f"{pfad}:{zeile}" if zeile else pfad
        text = f"{kat:12} {ort}" + (f"  „{wert}“" if zeige_wert else f"  ({wert})")
        r = ausnahmen.suche(kat, pfad, wert)
        if r is None or r["art"] == "befund":
            befunde.append(text)
        elif r["art"] == "vor_veroeffentlichung":
            gemeldet[r["begruendung"]].append(text)
        else:
            ausgenommen[r["begruendung"]].append(text)

    for pfad in dateien:
        voll = WURZEL / pfad
        groesse = voll.stat().st_size
        if groesse > grenze:
            einordnen("gross", pfad, None, f"{groesse / 1048576:.1f} MB")
        grund = lizenz_pruefen(pfad, genannt, notice)
        if grund:
            einordnen("lizenz", pfad, None, grund, zeige_wert=False)
        for i, z in zeilen(voll):
            for kat, wert in treffer_in_zeile(z, rmuster):
                einordnen(kat, pfad, i, wert, zeige_wert=(kat != "geheimnis"))

    print(f"Prüfung vor Veröffentlichung, {len(dateien)} Dateien im Arbeitsbaum "
          f"(eingecheckt und neu, ohne ignorierte), Grenze {args.max_mb} MB, "
          f"{len(ueberall) + len(eindeutig)} Rechnernamen dieses Rechners")
    n_gem = sum(len(v) for v in gemeldet.values())
    n_aus = sum(len(v) for v in ausgenommen.values())
    if ausgenommen:
        print(f"\nAusnahmen (begründet, bleiben so): {n_aus}")
        for grund, liste in sorted(ausgenommen.items()):
            print(f"  {len(liste):4} × {grund}")
            if args.alle:
                for t in liste:
                    print(f"         {t}")
    if gemeldet:
        print(f"\nVor einer Veröffentlichung zu beheben (andere Eigentümer): {n_gem}")
        for grund, liste in sorted(gemeldet.items()):
            print(f"  {len(liste):4} × {grund}")
            for t in liste[: (None if args.alle else 5)]:
                print(f"         {t}")
            if not args.alle and len(liste) > 5:
                print(f"         … und {len(liste) - 5} weitere (--alle)")
    unbenutzt = [r for r in ausnahmen.regeln if r["treffer"] == 0 and r["art"] != "befund"]
    if unbenutzt:
        print(f"\nAusnahmeregeln ohne Treffer (veraltet?): {len(unbenutzt)}")
        for r in unbenutzt:
            print(f"  {r['kategorie']} {r['pfadmuster']} {r['wertmuster']}")
    print(f"\nBefunde: {len(befunde)}")
    for t in befunde:
        print(f"  {t}")
    fehler = len(befunde) + (n_gem if args.veroeffentlichung else 0)
    if args.veroeffentlichung and n_gem:
        print(f"Mit --veroeffentlichung zählen die {n_gem} gemeldeten Stellen als Befund.")
    print(f"\nErgebnis: {'grün' if not fehler else 'BEFUND'} ({len(befunde)} Befunde, {n_gem} gemeldet, {n_aus} Ausnahmen)")
    return 1 if fehler else 0


def historie_pruefen(args) -> int:
    ausnahmen = Ausnahmen(AUSNAHMEN)
    ueberall, eindeutig = rechnernamen()
    rmuster = rechner_muster(ueberall, eindeutig)
    commits = git("rev-list", "--all").decode().split()
    objekte = git("rev-list", "--all", "--objects").decode("utf-8", errors="replace").splitlines()
    pfad_zu = {}
    for z in objekte:
        teile = z.split(" ", 1)
        if len(teile) == 2 and teile[0] not in pfad_zu:
            pfad_zu[teile[0]] = teile[1]
    typen = git("cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                eingabe="\n".join(pfad_zu).encode()).decode().splitlines()
    blobs = [(o, int(s)) for o, t, s in (z.split() for z in typen) if t == "blob"]
    zaehl: Counter = Counter()
    beispiele: dict[str, list[str]] = defaultdict(list)
    geheim_orte: list[str] = []
    gross: list[str] = []
    env_dateien = sorted({p for p in pfad_zu.values() if re.search(r"(^|/)\.env($|\.)", p) and not p.endswith(".beispiel")})
    for o, s in blobs:
        if s > args.max_mb * 1048576:
            gross.append(f"{pfad_zu[o]} ({s / 1048576:.1f} MB)")
    # Inhalte in Blöcken lesen
    block = 400
    for start in range(0, len(blobs), block):
        teil = blobs[start:start + block]
        roh = git("cat-file", "--batch", eingabe="\n".join(o for o, _ in teil).encode())
        pos = 0
        for o, s in teil:
            kopf_ende = roh.index(b"\n", pos)
            inhalt = roh[kopf_ende + 1: kopf_ende + 1 + s]
            pos = kopf_ende + 1 + s + 1
            if b"\0" in inhalt[:8192]:
                continue
            for i, z in enumerate(inhalt.decode("utf-8", errors="replace").splitlines(), 1):
                for kat, wert in treffer_in_zeile(z, rmuster):
                    if kat == "plankennung":
                        zaehl["plankennung (Dateiinhalt)"] += 1
                        continue
                    schluessel = f"{kat}: {wert}" if kat != "geheimnis" else f"geheimnis: {wert}"
                    zaehl[schluessel] += 1
                    if len(beispiele[schluessel]) < 3:
                        beispiele[schluessel].append(f"{pfad_zu[o]}:{i}")
                    if kat == "geheimnis":
                        r = ausnahmen.suche(kat, pfad_zu[o], wert)
                        if r is not None and r["art"] == "ausnahme":
                            zaehl[f"geheimnis (Ausnahme: {r['begruendung'][:60]}…)"] += 1
                        else:
                            geheim_orte.append(f"{pfad_zu[o]}:{i} ({wert})")
    autoren = Counter(git("log", "--all", "--format=%an <%ae>").decode().splitlines())
    committer = Counter(git("log", "--all", "--format=%cn <%ce>").decode().splitlines())
    texte = git("log", "--all", "--format=%B%x00").decode("utf-8", errors="replace").split("\0")
    plan_texte = Counter()
    for t in texte:
        for name, muster in PLAN:
            if muster.search(t):
                plan_texte[name] += 1
    print(f"Git-Historie: {len(commits)} Commits (alle Zweige und Tags), {len(blobs)} verschiedene Dateiinhalte")
    print("\nAutoren (Name <Adresse>): ")
    for a, n in autoren.most_common():
        print(f"  {n:5} × {a}")
    print("Committer:")
    for a, n in committer.most_common():
        print(f"  {n:5} × {a}")
    print(f"\nUmgebungsdateien (.env) je eingecheckt: {env_dateien or 'keine'}")
    print(f"Dateien über {args.max_mb} MB in der Historie: {len(gross)}")
    for g in gross[:10]:
        print(f"  {g}")
    print("\nTreffer in Dateiinhalten aller Stände (Zahl der Zeilen; Beispiele):")
    for k, n in sorted(zaehl.items()):
        print(f"  {n:6} × {k}  " + ", ".join(beispiele.get(k, [])))
    print("\nCommit-Texte mit internen Plankennungen:")
    for k, n in plan_texte.most_common():
        print(f"  {n:5} × {k}")
    print(f"\nGeheimnis-Muster ohne begründete Ausnahme: {len(geheim_orte)} Zeilen")
    for g in geheim_orte[:20]:
        print(f"  {g}")
    return 1 if (env_dateien or geheim_orte) else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--max-mb", type=float, default=5.0)
    ap.add_argument("--veroeffentlichung", action="store_true")
    ap.add_argument("--alle", action="store_true")
    ap.add_argument("--historie", action="store_true")
    args = ap.parse_args()
    if args.historie:
        return historie_pruefen(args)
    return arbeitsbaum_pruefen(args)


if __name__ == "__main__":
    sys.exit(main())
