#!/bin/sh
# Paket A3: OSM-Einrichtungen und Fußwegnetz. Umgebung wie skripte/lauf.sh (P0), aber mit der Rolle
# kiezatlas_rechnen und nur offline (uv --offline: Pakete aus dem lokalen Zwischenspeicher, kein Paketindex).
#
#   skripte/12_osm.sh laden --pbf DATEI [--trockenlauf]   PBF lesen, auswertung.osm_poi/netz_* füllen, Bericht
#   skripte/12_osm.sh pruefen                             Abnahme A3 gegen die Datenbank (pruefen/a3_pruefen.py)
#   skripte/12_osm.sh test                                Tests mit selbst erzeugter Mini-PBF (pruefen/a3_test_osm.py)
#
# KIEZ_ENV: Datei mit RECHNEN_PASSWORD (chmod 600), Standard ./.env, in Worktrees ../kiezatlas-potsdam/.env.
set -eu
cd "$(dirname "$0")/.."
KIEZ_DATEN="${KIEZ_DATEN:-$(cd .. && pwd)/kiezatlas-daten}"
if [ -z "${KIEZ_ENV:-}" ]; then
  if [ -f ./.env ]; then KIEZ_ENV=./.env; else KIEZ_ENV=../kiezatlas-potsdam/.env; fi
fi
case "$KIEZ_ENV" in */*) ;; *) KIEZ_ENV="./$KIEZ_ENV" ;; esac
# Pakete mit exakten Versionen und Prüfsummen aus requirements.txt (seit 06.11.2026; vorher „--with numpy
# --with scipy“ ohne Version, also die jeweils neueste im Zwischenspeicher). pytest aus requirements-pruefen.txt.
UV="uv run -q --offline --python 3.13 --no-project --with-requirements requirements.txt"

lade_umgebung() {
  set -a; . "$KIEZ_ENV"; set +a
  export KIEZ_DATEN PGHOST=127.0.0.1 PGPORT="${PG_PORT:-55461}" PGDATABASE=kiezatlas
  export PGUSER=kiezatlas_rechnen PGPASSWORD="$RECHNEN_PASSWORD"
  unset POSTGRES_PASSWORD IMPORT_PASSWORD LESE_PASSWORD
}

schritt="${1:-}"
[ $# -gt 0 ] && shift
case "$schritt" in
  laden)   lade_umgebung; $UV python -I skripte/12_osm.py "$@" ;;
  pruefen) lade_umgebung; $UV python -I pruefen/a3_pruefen.py "$@" ;;
  test)
    # Datenbanktest (Trockenlauf mit ROLLBACK) nur mit A3_DB_TEST=1
    if [ "${A3_DB_TEST:-0}" = 1 ]; then lade_umgebung; fi
    $UV --with-requirements requirements-pruefen.txt python -I -m pytest -q -p no:cacheprovider pruefen/a3_test_osm.py "$@" ;;
  *) echo "Aufruf: skripte/12_osm.sh laden --pbf DATEI [--trockenlauf] | pruefen | test" >&2; exit 2 ;;
esac
