from __future__ import annotations

from datetime import UTC, date, datetime
import logging
import os

from reml.ingestion.backfill import HistoricalBackfillService
from reml.ingestion.cian_client import CianClient
from reml.ingestion.repository import IngestionRepository

try:
    from prefect import flow
except Exception:  # pragma: no cover

    def flow(*_args, **_kwargs):  # type: ignore
        def _decorator(func):
            return func

        return _decorator


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable '{name}' is required")
    return value


@flow(name="historical-cian-backfill")
def historical_backfill_flow(
    *,
    schema: str,
    start_date: str | None = None,
    end_date: str | None = None,
    window_days: int = 1,
    daily_quota: int = 10_000,
    category_id: int = 1,
    region_id: int = 1,
) -> int:
    logging.basicConfig(level=logging.INFO)
    db_dsn = _required_env("REML_DB_DSN")
    client = CianClient(
        login=_required_env("CIAN_LOGIN"),
        token=_required_env("CIAN_TOKEN"),
        endpoint=os.getenv("CIAN_ENDPOINT", "https://rest-app.net/api-cian/ads"),
        timeout_seconds=int(os.getenv("CIAN_TIMEOUT_SECONDS", "30")),
        max_retries=int(os.getenv("CIAN_MAX_RETRIES", "3")),
    )
    repo = IngestionRepository(dsn=db_dsn)
    service = HistoricalBackfillService(
        client=client,
        repository=repo,
        category_id=category_id,
        region_id=region_id,
        window_days=window_days,
        daily_quota=daily_quota,
    )
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None
    loaded = service.run(
        schema_name=schema,
        start_date=start,
        end_date=end,
        ingestion_ts=datetime.now(tz=UTC),
    )
    return loaded


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run historical CIAN backfill flow")
    parser.add_argument("--schema", required=True, choices=["sale", "rent"])
    parser.add_argument("--start-date", required=False, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=False, help="YYYY-MM-DD")
    parser.add_argument("--window-days", type=int, default=1)
    parser.add_argument("--daily-quota", type=int, default=10_000)
    parser.add_argument("--category-id", type=int, default=1)
    parser.add_argument("--region-id", type=int, default=1)
    args = parser.parse_args()

    historical_backfill_flow(
        schema=args.schema,
        start_date=args.start_date,
        end_date=args.end_date,
        window_days=args.window_days,
        daily_quota=args.daily_quota,
        category_id=args.category_id,
        region_id=args.region_id,
    )
