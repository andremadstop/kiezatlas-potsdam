# Barlow aus fonts/*.woff2 (Repo) als TrueType für cairo/fontconfig ablegen und eine fonts.conf dazuschreiben.
# Aufruf aus der Repo-Wurzel: uv run --no-project --with fonttools --with brotli python docs/filme/karte/schriften.py --aus berichte/filme-2026-11-08/karte/fonts
# Danach: export FONTCONFIG_FILE=<aus>/fonts.conf. Die Dateien sind Einzelschnitte; der Familienname trägt das Gewicht
# („Barlow Medium“, „Barlow Semi Condensed Medium“ …), so wie overlay.py sie anfordert.
import argparse
import glob
import os

from fontTools.ttLib import TTFont

ap = argparse.ArgumentParser()
ap.add_argument("--aus", required=True)
ap.add_argument("--fonts", default="fonts")
args = ap.parse_args()
os.makedirs(args.aus, exist_ok=True)
for p in sorted(glob.glob(os.path.join(args.fonts, "*.woff2"))):
    f = TTFont(p)
    f.flavor = None
    ziel = os.path.join(args.aus, os.path.basename(p)[:-6] + ".ttf")
    f.save(ziel)
    print(ziel)
with open(os.path.join(args.aus, "fonts.conf"), "w", encoding="utf-8") as fh:
    fh.write('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>\n'
             '  <dir prefix="relative">.</dir>\n  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
             '</fontconfig>\n')
