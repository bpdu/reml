from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import logging
from typing import Protocol

from reml.ingestion.ads_api_client import AdsApiClient
from reml.ingestion.parser import parse_response_items, resolve_deal_id

logger = logging.getLogger(__name__)


class RepositoryProtocol(Protocol):
    def ingest_response(
        self,
        *,
        schema_name: str,
        endpoint: str,
        request_params: dict,
        deal_id: int,
        category_id: int,
        region_id: int,
        window_start: date,
        window_end: date,
        page_limit: int,
        page_offset: int,
        response_payload: dict,
        observed_at: datetime,
        parsed_items: list,
    ) -> int: ...

    def upsert_checkpoint(
        self,
        *,
        schema_name: str,
        deal_id: int,
        category_id: int,
        region_id: int,
        window_start: date,
        window_end: date,
        status: str,
        records_loaded: int,
        offset: int,
    ) -> None: ...

    def get_checkpoint(
        self,
        *,
        schema_name: str,
        deal_id: int,
        category_id: int,
        region_id: int,
        window_start: date,
        window_end: date,
    ) -> dict | None: ...


@dataclass(slots=True)
class HistoricalBackfillService:
    client: AdsApiClient
    repository: RepositoryProtocol
    category_id: int = 1
    region_id: int = 1
    window_days: int = 1
    daily_quota: int = 10_000

    def run(
        self,
        *,
        schema_name: str,
        start_date: date | None = None,
        end_date: date | None = None,
        ingestion_ts: datetime | None = None,
    ) -> int:
        deal_id = resolve_deal_id(schema_name)
        if self.window_days < 1:
            raise ValueError("window_days must be >= 1")
        if self.daily_quota < 1:
            raise ValueError("daily_quota must be >= 1")

        run_anchor = ingestion_ts or datetime.now(tz=UTC)
        max_date = end_date or run_anchor.date()
        min_date = start_date or max_date
        if min_date > max_date:
            raise ValueError("start_date must be <= end_date")

        daily_loaded = 0
        total_loaded = 0
        current_end = max_date

        while current_end >= min_date:
            window_start = max(
                min_date, current_end - timedelta(days=self.window_days - 1)
            )
            checkpoint = self.repository.get_checkpoint(
                schema_name=schema_name,
                deal_id=deal_id,
                category_id=self.category_id,
                region_id=self.region_id,
                window_start=window_start,
                window_end=current_end,
            )
            if checkpoint and checkpoint.get("status") == "completed":
                current_end = window_start - timedelta(days=1)
                continue

            offset = int(checkpoint["offset"]) if checkpoint else 0
            window_loaded = int(checkpoint["records_loaded"]) if checkpoint else 0

            while True:
                if daily_loaded >= self.daily_quota:
                    self.repository.upsert_checkpoint(
                        schema_name=schema_name,
                        deal_id=deal_id,
                        category_id=self.category_id,
                        region_id=self.region_id,
                        window_start=window_start,
                        window_end=current_end,
                        status="quota_reached",
                        records_loaded=window_loaded,
                        offset=offset,
                    )
                    logger.info(
                        "backfill_quota_reached",
                        extra={
                            "schema_name": schema_name,
                            "daily_loaded": daily_loaded,
                            "daily_quota": self.daily_quota,
                        },
                    )
                    return total_loaded

                remaining_quota = self.daily_quota - daily_loaded
                limit = min(1000, remaining_quota)
                date1 = datetime.combine(window_start, datetime.min.time()).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                date2 = datetime.combine(
                    current_end, datetime.max.time().replace(microsecond=0)
                ).strftime("%Y-%m-%d %H:%M:%S")
                response_payload = self.client.fetch_ads(
                    category_id=self.category_id,
                    deal_id=deal_id,
                    region_id=self.region_id,
                    date1=date1,
                    date2=date2,
                    limit=limit,
                    offset=offset,
                )
                observed_at = datetime.now(tz=UTC)
                parsed_items = parse_response_items(
                    response_payload, observed_at=observed_at
                )
                records_count = len(parsed_items)

                self.repository.ingest_response(
                    schema_name=schema_name,
                    endpoint=self.client.endpoint,
                    request_params={
                        "category_id": self.category_id,
                        "deal_id": deal_id,
                        "region_id": self.region_id,
                        "date1": date1,
                        "date2": date2,
                        "limit": limit,
                        "offset": offset,
                    },
                    deal_id=deal_id,
                    category_id=self.category_id,
                    region_id=self.region_id,
                    window_start=window_start,
                    window_end=current_end,
                    page_limit=limit,
                    page_offset=offset,
                    response_payload=response_payload,
                    observed_at=observed_at,
                    parsed_items=parsed_items,
                )
                daily_loaded += records_count
                total_loaded += records_count
                window_loaded += records_count

                next_offset = offset + limit
                self.repository.upsert_checkpoint(
                    schema_name=schema_name,
                    deal_id=deal_id,
                    category_id=self.category_id,
                    region_id=self.region_id,
                    window_start=window_start,
                    window_end=current_end,
                    status="running",
                    records_loaded=window_loaded,
                    offset=next_offset,
                )

                logger.info(
                    "backfill_page_loaded",
                    extra={
                        "schema_name": schema_name,
                        "window_start": str(window_start),
                        "window_end": str(current_end),
                        "offset": offset,
                        "limit": limit,
                        "records_count": records_count,
                    },
                )

                if records_count < limit:
                    self.repository.upsert_checkpoint(
                        schema_name=schema_name,
                        deal_id=deal_id,
                        category_id=self.category_id,
                        region_id=self.region_id,
                        window_start=window_start,
                        window_end=current_end,
                        status="completed",
                        records_loaded=window_loaded,
                        offset=next_offset,
                    )
                    break
                offset = next_offset

            current_end = window_start - timedelta(days=1)
        return total_loaded
