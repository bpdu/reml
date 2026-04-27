from __future__ import annotations

import pytest

pytest.importorskip("psycopg")

from reml.ingestion.repository import IngestionRepository


def test_request_fingerprint_is_deterministic() -> None:
    repo = IngestionRepository(dsn="postgresql://example")
    fp1 = repo.build_request_fingerprint(
        endpoint="https://rest-app.net/api-cian/ads",
        request_params={
            "date1": "2026-04-27 00:00:00",
            "date2": "2026-04-27 23:59:59",
            "limit": 1000,
            "offset": 0,
            "deal_id": 1,
        },
    )
    fp2 = repo.build_request_fingerprint(
        endpoint="https://rest-app.net/api-cian/ads",
        request_params={
            "offset": 0,
            "limit": 1000,
            "deal_id": 1,
            "date2": "2026-04-27 23:59:59",
            "date1": "2026-04-27 00:00:00",
        },
    )
    assert fp1 == fp2
