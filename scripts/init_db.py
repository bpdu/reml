from __future__ import annotations

import argparse
from pathlib import Path
import os

import psycopg


def _iter_migration_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise RuntimeError(f"Migration path not found: {path}")
    files = sorted(p for p in path.glob("*.sql") if p.is_file())
    if not files:
        raise RuntimeError(f"No .sql migrations found in: {path}")
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize REML ingestion schema")
    parser.add_argument(
        "--dsn",
        default=os.getenv("REML_DB_DSN"),
        help="PostgreSQL DSN (default: REML_DB_DSN env)",
    )
    parser.add_argument(
        "--migrations-path",
        default="migrations",
        help="Path to SQL migration file or directory with *.sql files",
    )
    args = parser.parse_args()

    if not args.dsn:
        raise RuntimeError("Provide --dsn or set REML_DB_DSN")

    migration_path = Path(args.migrations_path)
    migration_files = _iter_migration_files(migration_path)
    with psycopg.connect(args.dsn) as conn:
        for migration_file in migration_files:
            sql_text = migration_file.read_text(encoding="utf-8")
            with conn.transaction():
                conn.execute(sql_text)
            print(f"Applied migration: {migration_file}")
    print("Database initialization completed.")


if __name__ == "__main__":
    main()
