"""Deploy-Kopie des Kiezatlas mit Cache-Busting (Integration I1/I2, 05.11.2026).

Kopiert genau die Dateien, die auf souverain-systems.de/kiezatlas/ gehören, in einen Ordner außerhalb des Repos
und hängt in den HTML-Seiten an jeden lokalen Verweis auf .js, .css, .svg, .png und .woff2 ein ?v=<mtime> der
Zieldatei an. Für nachgeladene Dateien (KIEZ_THEMEN.laden, Gebäude, Schrifteinbettung) setzt jede Seite
window.KIEZ_V = jüngste mtime unter daten/ und fonts/; themen.js hängt den Wert an. Das Repo bleibt unverändert,
file:// im Repo läuft ohne ?v.

Lädt nichts hoch und ruft nichts aus dem Netz ab. Der Upload ist Andres Schritt (additiver rsync, kein --delete).
Am Ende schreibt das Skript MD5SUMS in den Zielordner: dagegen prüft man nach dem Upload die live geladenen Dateien.

Aufruf: python3 -I skripte/deploy_kopie.py [--ziel ../kiezatlas-deploy/<datum>] [--liste]
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

# Seiten und Dateien der Website. Nicht dabei: Quellcode-Zulieferungen, Prüfskripte, Belege, Berichte,
# daten/fixtures/ (Beispielwerte), daten/schema/ (Verträge, nur im Repo), Rohdaten.
SEITEN = ["index.html", "karte.html", "404.html", "planer.html", "planer-methode.html", "planer-daten.html",
          "jahre.html", "jahre-methode.html", "jahre-daten.html"]
DATEIEN = ["atlas.css", "karte.css", "planer.css", "jahre.css", "atlas.js", "karte.js", "planer.js", "jahre.js",
           "themen.js", "kopf.js", "schaugrafik.js", "favicon.svg", "og.png"]
ORDNER = ["vendor", "fonts", "daten"]
AUSSER = ["daten/fixtures", "daten/schema"]

VERWEIS = re.compile(r'((?:src|href)=")([^"#?:]+\.(?:js|css|svg|png|woff2))(")')


def dateiliste():
    out = [Path(p) for p in SEITEN + DATEIEN]
    for o in ORDNER:
        for p in sorted((WURZEL / o).rglob("*")):
            r = p.relative_to(WURZEL)
            if p.is_file() and not any(str(r).startswith(a + "/") for a in AUSSER):
                out.append(r)
    fehlt = [str(p) for p in out if not (WURZEL / p).is_file()]
    if fehlt:
        sys.exit("fehlt: " + ", ".join(fehlt))
    return out


def stand(liste):
    return max(int((WURZEL / p).stat().st_mtime) for p in liste if p.parts[0] in ("daten", "fonts"))


def html_umschreiben(text, stempel):
    def ersetze(m):
        ziel = WURZEL / m.group(2)
        if not ziel.is_file():
            return m.group(0)
        return f"{m.group(1)}{m.group(2)}?v={int(ziel.stat().st_mtime)}{m.group(3)}"
    text = VERWEIS.sub(ersetze, text)
    marke = '<meta charset="utf-8">'
    if marke not in text:
        sys.exit("Seite ohne <meta charset>: KIEZ_V lässt sich nicht setzen")
    return text.replace(marke, f'{marke}\n<script>window.KIEZ_V="{stempel}"</script>', 1)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--ziel", default=str(WURZEL.parent / "kiezatlas-deploy" / "kopie"))
    a.add_argument("--liste", action="store_true", help="nur die Dateiliste ausgeben")
    o = a.parse_args()
    liste = dateiliste()
    if o.liste:
        print("\n".join(str(p) for p in liste))
        return
    ziel = Path(o.ziel).resolve()
    if ziel == WURZEL or WURZEL in ziel.parents:
        sys.exit("Ziel liegt im Repo")
    if ziel.exists():
        shutil.rmtree(ziel)
    stempel = stand(liste)
    md5 = []
    for p in liste:
        q, z = WURZEL / p, ziel / p
        z.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".html" and len(p.parts) == 1:
            z.write_text(html_umschreiben(q.read_text(encoding="utf-8"), stempel), encoding="utf-8")
        else:
            shutil.copy2(q, z)
        md5.append(f"{hashlib.md5(z.read_bytes()).hexdigest()}  {p}")
    (ziel / "MD5SUMS").write_text("\n".join(md5) + "\n", encoding="utf-8")
    groesse = sum((ziel / p).stat().st_size for p in liste)
    print(f"{len(liste)} Dateien, {groesse / 1e6:.1f} MB nach {ziel} (KIEZ_V={stempel}); MD5SUMS geschrieben")
    print("Upload (Andre, additiv):")
    print(f"  rsync -az -n --itemize-changes {ziel}/ relais:/opt/www/souverain-systems.de/kiezatlas/   # Probelauf")
    print(f"  rsync -az --exclude MD5SUMS {ziel}/ relais:/opt/www/souverain-systems.de/kiezatlas/")


if __name__ == "__main__":
    os.umask(0o022)
    main()
