#!/bin/sh
# Alle Prüfungen des Kiezatlas, die ohne Netz und ohne Datenbank laufen, nacheinander.
# Anders als ein Abbruch beim ersten Fehler laufen hier immer alle Prüfungen; am Ende steht die Zählung.
# Rückgabe 0 = alles grün, 1 = mindestens ein Befund. Übersprungene Prüfungen (fehlende Rohdaten,
# --ohne-browser) zählen nicht als Befund, stehen aber in der Zählung.
#
#   ./pruefen.sh                 alles, auch die Browser-Prüfungen (Playwright, je rund eine Minute)
#   ./pruefen.sh --ohne-browser  ohne pruefen/*.mjs
#
# Braucht: uv (Pakete nur aus dem lokalen Zwischenspeicher, --offline, Versionen aus requirements.txt),
# node mit den Paketen aus package.json (node_modules), für die Rohdaten-Prüfsummen rohdaten/ und $KIEZ_DATEN.
# Liest keine .env und keine Datenbank: PG*-Variablen werden vorher entfernt. Was die Datenbank braucht
# (Abnahmen A1, A2, A3, A5a, A5b, A6, B0, B2 bis B4), steht in docs/rundgang.md und läuft nicht hier.
set -u
cd "$(dirname "$0")"
unset PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE PGSERVICE A3_DB_TEST A5B_DB_TEST 2>/dev/null || true
KIEZ_DATEN="${KIEZ_DATEN:-$(cd .. && pwd)/kiezatlas-daten}"
export KIEZ_DATEN
UV="uv run -q --offline --python 3.13 --no-project --with-requirements requirements.txt"
BROWSER=1
[ "${1:-}" = "--ohne-browser" ] && BROWSER=0

gruen=0; befund=0; ueber=0; liste=""
py() { $UV python -I "$@"; }
pruef() {
  name="$1"; shift
  echo; echo "== $name"
  start=$(date +%s)
  "$@"; rc=$?
  dauer=$(( $(date +%s) - start ))
  if [ "$rc" -eq 0 ]; then gruen=$((gruen + 1)); st="grün"; else befund=$((befund + 1)); st="BEFUND (Rückgabe $rc)"; fi
  echo "-- $name: $st, ${dauer} s"
  liste="$liste
  $st  $name"
}
ueberspringe() {
  echo; echo "== $1"; echo "-- übersprungen: $2"
  ueber=$((ueber + 1))
  liste="$liste
  übersprungen  $1 ($2)"
}

js_syntax() {
  n=0; f=0
  for d in *.js pruefen/*.mjs; do
    n=$((n + 1)); node --check "$d" || { echo "  Syntaxfehler: $d"; f=$((f + 1)); }
  done
  echo "  $n Dateien, $f mit Fehler"; [ "$f" -eq 0 ]
}
sh_syntax() {
  n=0; f=0
  for d in pruefen.sh skripte/*.sh; do
    n=$((n + 1)); sh -n "$d" || { echo "  Syntaxfehler: $d"; f=$((f + 1)); }
  done
  echo "  $n Dateien, $f mit Fehler"; [ "$f" -eq 0 ]
}
py_syntax() {
  py -c 'import ast, sys
f = 0
for d in sys.argv[1:]:
    try:
        ast.parse(open(d, encoding="utf-8").read(), d)
    except SyntaxError as e:
        print("  Syntaxfehler:", e); f += 1
print(f"  {len(sys.argv) - 1} Dateien, {f} mit Fehler"); sys.exit(1 if f else 0)' skripte/*.py pruefen/*.py
}
hash_kern() { sha256sum -c --strict --quiet belege/rohdaten.sha256 && echo "  $(wc -l < belege/rohdaten.sha256) Dateien stimmen"; }
hash_kiez() {
  liste_datei="$(pwd)/belege/rohdaten.kiez_daten.sha256"
  (cd "$KIEZ_DATEN" && sha256sum -c --strict --quiet "$liste_datei") && echo "  $(wc -l < "$liste_datei") Dateien stimmen"
}

echo "Kiezatlas Potsdam, Prüflauf $(date '+%d.%m.%Y %H:%M:%S %Z')"
echo "Commit: $(git rev-parse HEAD 2>/dev/null || echo unbekannt)"
offen=$(git status --porcelain 2>/dev/null)
if [ -z "$offen" ]; then echo "Arbeitsstand: sauber (keine offenen Änderungen)"; else echo "Arbeitsstand: offene Änderungen"; echo "$offen" | sed 's/^/  /'; fi
echo "Werkzeuge: $(uv --version), node $(node --version), Python $($UV python -c 'import sys; print(sys.version.split()[0])')"

pruef "Syntax JavaScript (node --check)" js_syntax
pruef "Syntax Shell (sh -n)" sh_syntax
pruef "Syntax Python (ast)" py_syntax
pruef "Datenverträge und Summen (pruefen/daten.py)" py pruefen/daten.py
pruef "Vertrag Bauzeiten-Methode (pruefen/B5_methode.py)" py pruefen/B5_methode.py
pruef "jahre_methode.js aktuell (skripte/26_jahre_methode.py --pruefen)" py skripte/26_jahre_methode.py --pruefen
if [ -f "$KIEZ_DATEN/eingang/planungsraume-in-potsdam.geojson" ]; then
  pruef "planungsraeume.js aktuell (skripte/17_planungsraeume_js.py --pruefen)" py skripte/17_planungsraeume_js.py --pruefen
else
  ueberspringe "planungsraeume.js aktuell (skripte/17_planungsraeume_js.py --pruefen)" "Handdownload H1 fehlt unter \$KIEZ_DATEN/eingang/"
fi
pruef "GIS-Export ohne Datenbank (pruefen/A8_export.py --odbl-erwartet)" py pruefen/A8_export.py --odbl-erwartet
pruef "Codepfade Planer (pruefen/A6_test_pfade.py)" py pruefen/A6_test_pfade.py
pruef "OSM-Leser und Netz, ohne Datenbank (skripte/12_osm.sh test)" skripte/12_osm.sh test
pruef "Fußweg, ohne Datenbank (skripte/14b_fussweg.sh test)" skripte/14b_fussweg.sh test
if ls "$KIEZ_DATEN"/vbb_gtfs/*/GTFS.zip >/dev/null 2>&1; then
  pruef "Landesfilter E7 (skripte/14b_fussweg.sh kreuzprobe)" skripte/14b_fussweg.sh kreuzprobe
else
  ueberspringe "Landesfilter E7 (skripte/14b_fussweg.sh kreuzprobe)" "kein GTFS unter \$KIEZ_DATEN/vbb_gtfs/"
fi
if [ -d rohdaten/zensus ]; then
  pruef "Prüfsummen Kerndaten (belege/rohdaten.sha256)" hash_kern
else
  ueberspringe "Prüfsummen Kerndaten (belege/rohdaten.sha256)" "rohdaten/ fehlt (Verweis auf ../kiezatlas-potsdam-west/rohdaten)"
fi
if [ -d "$KIEZ_DATEN/zensus" ]; then
  pruef "Prüfsummen \$KIEZ_DATEN (belege/rohdaten.kiez_daten.sha256)" hash_kiez
else
  ueberspringe "Prüfsummen \$KIEZ_DATEN (belege/rohdaten.kiez_daten.sha256)" "\$KIEZ_DATEN fehlt"
fi
for m in seiten A7_planer B5_jahre p1_themen; do
  if [ "$BROWSER" -eq 1 ]; then
    pruef "Browser: pruefen/$m.mjs" node "pruefen/$m.mjs"
  else
    ueberspringe "Browser: pruefen/$m.mjs" "--ohne-browser"
  fi
done

summe=$((gruen + befund + ueber))
echo
echo "== Zählung: $summe Prüfungen, $gruen grün, $befund mit Befund, $ueber übersprungen$liste"
[ "$befund" -eq 0 ]
