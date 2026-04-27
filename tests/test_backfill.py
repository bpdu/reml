from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from reml.ingestion.backfill import HistoricalBackfillService


class FakeClient:
    def __init__(self, page_sizes: list[int]):
        self.page_sizes = page_sizes
        self.calls = 0
        self.endpoint = "https://example.invalid/api/ads"

    def fetch_ads(self, **kwargs):  # type: ignore[override]
        size = self.page_sizes[self.calls] if self.calls < len(self.page_sizes) else 0
        size = min(size, int(kwargs["limit"]))
        self.calls += 1
        return {
            "status": "ok",
            "data": [
                {
                    "Id": 1000 + i,
                    "price": "100",
                    "time": "2026-04-27T12:00:00Z",
                    "time_publish": "2026-04-27T12:00:00Z",
                }
                for i in range(size)
            ],
        }


@dataclass
class FakeRepo:
    ingested: int = 0
    checkpoints: dict[tuple[str, int, int, int, date, date], dict] = field(
        default_factory=dict
    )

    def ingest_response(self, **kwargs):
        count = len(kwargs["parsed_items"])
        self.ingested += count
        return count

    def upsert_checkpoint(self, **kwargs):
        key = (
            kwargs["schema_name"],
            kwargs["deal_id"],
            kwargs["category_id"],
            kwargs["region_id"],
            kwargs["window_start"],
            kwargs["window_end"],
        )
        self.checkpoints[key] = kwargs

    def get_checkpoint(self, **kwargs):
        key = (
            kwargs["schema_name"],
            kwargs["deal_id"],
            kwargs["category_id"],
            kwargs["region_id"],
            kwargs["window_start"],
            kwargs["window_end"],
        )
        return self.checkpoints.get(key)


def test_daily_quota_stop_behavior() -> None:
    client = FakeClient(page_sizes=[1000, 1000, 1000])
    repo = FakeRepo()
    service = HistoricalBackfillService(
        client=client,
        repository=repo,
        daily_quota=1500,
        window_days=1,
    )
    loaded = service.run(
        schema_name="sale",
        start_date=date(2026, 4, 27),
        end_date=date(2026, 4, 27),
        ingestion_ts=datetime(2026, 4, 27, 12, 0, tzinfo=UTC),
    )
    assert loaded == 1500
    assert repo.ingested == 1500
    latest_checkpoint = next(iter(repo.checkpoints.values()))
    assert latest_checkpoint["deal_id"] == 1
    assert latest_checkpoint["category_id"] == 1
    assert latest_checkpoint["region_id"] == 1
    assert latest_checkpoint["records_loaded"] >= 1500
