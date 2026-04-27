from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
import os

import psycopg
import pytest

from reml.ingestion.parser import ParsedListing
from reml.ingestion.repository import IngestionRepository


def _require_test_dsn() -> str:
    dsn = os.getenv("REML_TEST_DB_DSN")
    if not dsn:
        pytest.skip("Set REML_TEST_DB_DSN to run integration DB test")
    return dsn


def _apply_migrations(dsn: str) -> None:
    migration_dir = Path("migrations")
    migration_files = sorted(migration_dir.glob("*.sql"))
    if not migration_files:
        raise RuntimeError("No migration files found")
    with psycopg.connect(dsn) as conn:
        for migration_file in migration_files:
            with conn.transaction():
                conn.execute(migration_file.read_text(encoding="utf-8"))


def _cleanup_sale(dsn: str) -> None:
    with psycopg.connect(dsn) as conn:
        with conn.transaction():
            conn.execute(
                "TRUNCATE TABLE sale.listing_price_observations RESTART IDENTITY CASCADE"
            )
            conn.execute("TRUNCATE TABLE sale.listing_objects RESTART IDENTITY CASCADE")
            conn.execute(
                "TRUNCATE TABLE sale.listing_api_responses RESTART IDENTITY CASCADE"
            )


def _count_rows(dsn: str, sql_query: str) -> int:
    with psycopg.connect(dsn) as conn:
        row = conn.execute(sql_query).fetchone()
    assert row is not None
    return int(row[0])


def test_ingest_response_idempotency_on_duplicate_page() -> None:
    dsn = _require_test_dsn()
    _apply_migrations(dsn)
    _cleanup_sale(dsn)

    repo = IngestionRepository(dsn=dsn)
    observed_at = datetime.now(tz=UTC)
    parsed_items = [
        ParsedListing(
            external_id=12345,
            object_record={
                "external_id": 12345,
                "url": "https://example/listing/12345",
                "phone": None,
                "first_seen_at": observed_at,
                "last_seen_at": observed_at,
                "source_time": observed_at,
                "first_published_at": observed_at,
                "created_at_source": observed_at,
                "region": "Moscow",
                "city": "Moscow",
                "address": "Arbat",
                "metro": "Smolenskaya",
                "rooms_count": 1,
                "floor_number": 2,
                "floors_count": 5,
                "area_total": Decimal("40"),
                "area_kitchen": None,
                "area_living": None,
                "area_land": None,
                "building_year": 2000,
                "deal_type": "sale",
                "repair_type": None,
                "person_type": None,
                "building_material_type": None,
                "category": "flat",
                "subcategory": "secondary",
                "category_id": 1,
                "region_id": 1,
                "city_id": 1,
                "lat": Decimal("55.75"),
                "lng": Decimal("37.61"),
                "layout": None,
                "class_type": None,
                "condition_type": None,
                "published_user_id": None,
                "external_user_id": 999,
                "images": "[]",
                "images_hash": "h1",
                "description": "desc",
                "description_hash": "h2",
            },
            price_record={
                "external_id": 12345,
                "observed_at": observed_at,
                "source_time": observed_at,
                "time_publish": observed_at,
                "price": Decimal("1000000"),
            },
        )
    ]

    request_params = {
        "category_id": 1,
        "deal_id": 1,
        "region_id": 1,
        "date1": "2026-04-27 00:00:00",
        "date2": "2026-04-27 23:59:59",
        "limit": 1000,
        "offset": 0,
    }
    response_payload = {
        "status": "ok",
        "data": [{"Id": 12345, "price": 1000000}],
    }

    loaded_first = repo.ingest_response(
        schema_name="sale",
        endpoint="https://example.invalid/api/ads",
        request_params=request_params,
        deal_id=1,
        category_id=1,
        region_id=1,
        window_start=date(2026, 4, 27),
        window_end=date(2026, 4, 27),
        page_limit=1000,
        page_offset=0,
        response_payload=response_payload,
        observed_at=observed_at,
        parsed_items=parsed_items,
    )
    loaded_second = repo.ingest_response(
        schema_name="sale",
        endpoint="https://example.invalid/api/ads",
        request_params=request_params,
        deal_id=1,
        category_id=1,
        region_id=1,
        window_start=date(2026, 4, 27),
        window_end=date(2026, 4, 27),
        page_limit=1000,
        page_offset=0,
        response_payload=response_payload,
        observed_at=observed_at,
        parsed_items=parsed_items,
    )

    assert loaded_first == 1
    assert loaded_second == 0

    assert _count_rows(dsn, "SELECT count(*) FROM sale.listing_api_responses") == 1
    assert _count_rows(dsn, "SELECT count(*) FROM sale.listing_objects") == 1
    assert _count_rows(dsn, "SELECT count(*) FROM sale.listing_price_observations") == 1
