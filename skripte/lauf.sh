#!/bin/sh
# Ganzer Ablauf des Kiezatlas Potsdam:
#   1. lokale Rohdaten aufbereiten (kein Netz)
#   2. Datenbank starten, Rollen und Rechte einrichten (Geodaten-Import-Pipeline)
#   3. Import mit der Pipeline: Stadtteile, Zensus-Gitter, ALKIS-Gebäude per WFS
#   4. Auswertung in PostGIS, Ausgabe nach daten/ für index.html
# Braucht: Docker, uv, .env (POSTGRES_PASSWORD, IMPORT_PASSWORD, LESE_PASSWORD; chmod 600),
# daneben das Repository geodaten-import-pipeline.
set -eu
cd "$(dirname "$0")/.."
PIPELINE="${PIPELINE_DIR:-../geodaten-import-pipeline}"
PY="../kiezatlas-potsdam-west/.venv/bin/python"
set -a; . ./.env; set +a
export PGHOST=127.0.0.1 PGPORT="${PG_PORT:-55461}" PGDATABASE=kiezatlas PYTHONPATH="$PIPELINE"
UV="uv run -q --no-project --with-requirements $PIPELINE/requirements.txt"

echo "== 1 vorbereiten";  $PY -I skripte/01_vorbereiten.py
echo "== 2 datenbank";    docker compose up -d --wait db >/dev/null
PGUSER=admin PGPASSWORD="$POSTGRES_PASSWORD" $UV python -m pipeline.einrichten --config config/potsdam.yaml --haerten | tail -1
echo "== 3 import";       PGUSER=pipeline_import PGPASSWORD="$IMPORT_PASSWORD" $UV python -m pipeline.laden --config config/potsdam.yaml "$@" || echo "(Rückgabe ungleich 0, Bericht lesen)"
echo "== 4 auswerten";    PGUSER=mosidi_lesen PGPASSWORD="$LESE_PASSWORD" $UV python skripte/02_auswerten.py
