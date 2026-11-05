#!/bin/sh
# Paket A5b: Fußweg je Zelle über das OSM-Wegenetz (ODbL). Umgebung wie skripte/12_osm.sh (A3): Rolle
# kiezatlas_rechnen, nur offline (uv --offline: Pakete aus dem lokalen Zwischenspeicher, kein Paketindex).
#
#   skripte/14b_fussweg.sh rechnen [--trockenlauf]   Fußweg je Zelle und Art nach auswertung.zelle_erreichbar
#                                                    und zelle_gruen (nur methode = fussweg), Bericht berichte/
#   skripte/14b_fussweg.sh pruefen                   Abnahme A5b gegen die Datenbank (pruefen/a5b_pruefen.py)
#   skripte/14b_fussweg.sh test                      Tests ohne Datenbank (pruefen/a5b_test_fussweg.py)
#   A5B_DB_TEST=1 skripte/14b_fussweg.sh test        dazu Probelauf mit Gitternetz in TEMP-Tabellen (ROLLBACK)
#   skripte/14b_fussweg.sh kreuzprobe                Güte des Landesfilters E7 (VBB-Haltestellen, ohne Datenbank)
#
# KIEZ_ENV: Datei mit RECHNEN_PASSWORD (chmod 600), Standard ./.env, in Worktrees ../kiezatlas-potsdam/.env.
set -eu
cd "$(dirname "$0")/.."
PIPELINE="${PIPELINE_DIR:-../geodaten-import-pipeline}"
KIEZ_DATEN="${KIEZ_DATEN:-$(cd .. && pwd)/kiezatlas-daten}"
if [ -z "${KIEZ_ENV:-}" ]; then
  if [ -f ./.env ]; then KIEZ_ENV=./.env; else KIEZ_ENV=../kiezatlas-potsdam/.env; fi
fi
case "$KIEZ_ENV" in */*) ;; *) KIEZ_ENV="./$KIEZ_ENV" ;; esac
UV="uv run -q --offline --no-project --with-requirements $PIPELINE/requirements.txt --with numpy --with scipy"

lade_umgebung() {
  set -a; . "$KIEZ_ENV"; set +a
  export KIEZ_DATEN PGHOST=127.0.0.1 PGPORT="${PG_PORT:-55461}" PGDATABASE=kiezatlas
  export PGUSER=kiezatlas_rechnen PGPASSWORD="$RECHNEN_PASSWORD"
  unset POSTGRES_PASSWORD IMPORT_PASSWORD LESE_PASSWORD
}

schritt="${1:-}"
[ $# -gt 0 ] && shift
case "$schritt" in
  rechnen) lade_umgebung; $UV python -I skripte/14b_fussweg.py "$@" ;;
  pruefen) lade_umgebung; $UV python -I pruefen/a5b_pruefen.py "$@" ;;
  kreuzprobe) $UV python -I pruefen/a5b_landfilter_kreuzprobe.py "$@" ;;
  test)
    if [ "${A5B_DB_TEST:-0}" = 1 ]; then lade_umgebung; fi
    $UV --with pytest python -I -m pytest -q -p no:cacheprovider pruefen/a5b_test_fussweg.py "$@" ;;
  *) echo "Aufruf: skripte/14b_fussweg.sh rechnen [--trockenlauf] | pruefen | test | kreuzprobe" >&2; exit 2 ;;
esac
