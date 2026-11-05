"""Spielt sql/002_ausbau.sql als admin ein und setzt das Passwort der Rolle kiezatlas_rechnen.

Das Passwort kommt aus RECHNEN_PASSWORD (.env, chmod 600) und geht nur als SCRAM-Hash an den
Server, wie in pipeline.einrichten: So steht es weder in sql/002 noch im Server-Log.

Aufruf (Umgebung wie in skripte/lauf.sh, PGUSER=admin PGPASSWORD=$POSTGRES_PASSWORD):
    uv run -q --no-project --with-requirements ../geodaten-import-pipeline/requirements.txt \
        python skripte/ausbau_einrichten.py
Läuft beliebig oft. Danach pipeline.einrichten (Rechte der Pipeline-Rollen auf neue public-Ziele).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

WURZEL = Path(__file__).resolve().parent.parent
ROLLE = "kiezatlas_rechnen"


def main() -> int:
    passwort = os.environ.get("RECHNEN_PASSWORD")
    if not passwort:
        raise SystemExit("RECHNEN_PASSWORD fehlt (.env)")
    ddl = (WURZEL / "sql" / "002_ausbau.sql").read_text(encoding="utf-8")
    with psycopg.connect("") as conn, conn.transaction(), conn.cursor() as cur:
        cur.execute(ddl)
        geheim = conn.pgconn.encrypt_password(passwort.encode(), ROLLE.encode(), b"scram-sha-256")
        cur.execute(sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
            sql.Identifier(ROLLE), sql.Literal(geheim.decode("ascii"))))
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'auswertung'")
        n = cur.fetchone()[0]
    print(f"sql/002_ausbau.sql eingespielt, {n} Tabellen in auswertung, Rolle {ROLLE} mit Anmeldung.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
