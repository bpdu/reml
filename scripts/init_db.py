from __future__ import annotations

import argparse
from pathlib import Path
import os

import psycopg


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize REML ingestion schema")
    parser.add_argument(
        "--dsn",
        default=os.getenv("REML_DB_DSN"),
        help="PostgreSQL DSN (default: REML_DB_DSN env)",
    )
    parser.add_argument(
        "--migration-file",
        default="migrations/001_ingestion_init.sql",
        help="Path to SQL migration file",
    )
    args = parser.parse_args()

    if not args.dsn:
        raise RuntimeError("Provide --dsn or set REML_DB_DSN")

    sql_text = Path(args.migration_file).read_text(encoding="utf-8")
    with psycopg.connect(args.dsn) as conn:
        with conn.transaction():
            conn.execute(sql_text)
    print("Database initialization completed")


if __name__ == "__main__":
    main()
