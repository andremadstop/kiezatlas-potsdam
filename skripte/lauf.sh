#!/bin/sh
# Ablauf des Kiezatlas Potsdam in einzelnen Schritten. Seit dem Ausbau (05.11.2026) läuft nichts mehr
# „alles auf einmal“: Mehrere Worktrees teilen sich eine Datenbank, und ein Pipeline-Lauf ohne --nur
# lädt jede fällige Quelle, auch die Gebäude (deren oid der Gebäudejahre-Teil braucht).
#
#   skripte/lauf.sh vorbereiten           lokale Rohdaten aufbereiten (kein Netz), schreibt vorbereitet/
#   skripte/lauf.sh laden --nur QUELLE    eine Quelle aus config/potsdam.yaml laden (Pflicht: --nur)
#   skripte/lauf.sh auswerten             Auswertung mit der Leserolle, schreibt daten/
#   skripte/lauf.sh einrichten            nur Paket P0/Ladekoordinator: sql/002 einspielen, Rollen und
#                                         Rechte setzen (pipeline.einrichten --haerten). Nicht aus
#                                         anderen Paketen starten: ein zweiter Lauf mit anderer YAML
#                                         kann Rechte anderer Pakete entziehen.
#
# Umgebung:
#   KIEZ_DATEN   Rohdaten außerhalb der Repos (Standard ../kiezatlas-daten, HERKUNFT.md je Ordner)
#   KIEZ_ENV     Datei mit POSTGRES_PASSWORD, IMPORT_PASSWORD, LESE_PASSWORD, RECHNEN_PASSWORD
#                (chmod 600). Standard ./.env, in Worktrees ../kiezatlas-potsdam/.env.
# Braucht: Docker, uv, daneben die Repositories geodaten-import-pipeline und kiezatlas-potsdam-west (.venv).
set -eu
cd "$(dirname "$0")/.."
PIPELINE="${PIPELINE_DIR:-../geodaten-import-pipeline}"
PY="../kiezatlas-potsdam-west/.venv/bin/python"
KIEZ_DATEN="${KIEZ_DATEN:-$(cd .. && pwd)/kiezatlas-daten}"
if [ -z "${KIEZ_ENV:-}" ]; then
  if [ -f ./.env ]; then KIEZ_ENV=./.env; else KIEZ_ENV=../kiezatlas-potsdam/.env; fi
fi
case "$KIEZ_ENV" in */*) ;; *) KIEZ_ENV="./$KIEZ_ENV" ;; esac   # „.“ sucht sonst im PATH
set -a; . "$KIEZ_ENV"; set +a
export KIEZ_DATEN PGHOST=127.0.0.1 PGPORT="${PG_PORT:-55461}" PGDATABASE=kiezatlas PYTHONPATH="$PIPELINE"
export PIPELINE_KENNUNG="kiezatlas-potsdam (+https://github.com/andremadstop/kiezatlas-potsdam)"
UV="uv run -q --no-project --with-requirements $PIPELINE/requirements.txt"

schritt="${1:-}"
[ $# -gt 0 ] && shift
case "$schritt" in
  vorbereiten)
    $PY -I skripte/01_vorbereiten.py "$@" ;;
  laden)
    case " $* " in
      *" --nur "*) ;;
      *) echo "laden nur mit --nur QUELLE (Ladebetrieb, pruefen/INVENTAR.md)" >&2; exit 2 ;;
    esac
    PGUSER=pipeline_import PGPASSWORD="$IMPORT_PASSWORD" $UV python -m pipeline.laden --config config/potsdam.yaml "$@" ;;
  auswerten)
    PGUSER=mosidi_lesen PGPASSWORD="$LESE_PASSWORD" $UV python skripte/02_auswerten.py ;;
  einrichten)
    # Kein docker compose aus einem Worktree: der Projektname wäre ein anderer, es entstünde eine
    # zweite Datenbank auf demselben Port. Den Container startet man im Haupt-Repo.
    docker inspect -f '{{.State.Health.Status}}' kiezatlas-potsdam-db-1 | grep -qx healthy \
      || { echo "Container kiezatlas-potsdam-db-1 läuft nicht (im Haupt-Repo: docker compose up -d --wait db)" >&2; exit 1; }
    PGUSER=admin PGPASSWORD="$POSTGRES_PASSWORD" $UV python skripte/ausbau_einrichten.py
    PGUSER=admin PGPASSWORD="$POSTGRES_PASSWORD" $UV python -m pipeline.einrichten --config config/potsdam.yaml --haerten ;;
  *)
    echo "Aufruf: skripte/lauf.sh vorbereiten | laden --nur QUELLE | auswerten | einrichten" >&2
    exit 2 ;;
esac
