#!/bin/sh
# Legt GSAP 3.15.1 mit ScrollTrigger nach vendor/. Die Dateien stehen unter der GreenSock Standard „No Charge“
# License (https://gsap.com/standard-license), keiner Open-Source-Lizenz, und liegen deshalb nicht im Repository.
# Quelle ist das npm-Paket aus package-lock.json (feste Version). Ohne GSAP läuft die Seite auch: atlas.js
# schaltet dann auf IntersectionObserver um und lässt die Einblendungen weg.
# Aufruf im Projektordner: sh skripte/vendor_holen.sh
set -eu
cd "$(dirname "$0")/.."
[ -f node_modules/gsap/dist/gsap.min.js ] || npm ci --no-audit --no-fund
v=$(node -p "require('./node_modules/gsap/package.json').version")
[ "$v" = "3.15.1" ] || { echo "gsap $v statt 3.15.1 in node_modules" >&2; exit 1; }
cp node_modules/gsap/dist/gsap.min.js node_modules/gsap/dist/ScrollTrigger.min.js vendor/
echo "GSAP $v nach vendor/ gelegt"
