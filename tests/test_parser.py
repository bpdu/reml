from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from reml.ingestion.parser import (
    map_listing_item,
    parse_nullable_int,
    parse_numeric,
    parse_timestamp,
    resolve_deal_id,
    sha256_text,
)


def test_schema_deal_mapping() -> None:
    assert resolve_deal_id("sale") == 1
    assert resolve_deal_id("rent") == 2
    with pytest.raises(ValueError):
        resolve_deal_id("unknown")


def test_hash_generation() -> None:
    assert sha256_text("") == sha256_text(None)
    assert (
        sha256_text("abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_safe_parsing_helpers() -> None:
    assert parse_timestamp("2026-04-27T12:00:00Z") == datetime(
        2026, 4, 27, 12, 0, tzinfo=UTC
    )
    assert parse_timestamp("invalid") is None
    assert parse_numeric("10.55") == Decimal("10.55")
    assert parse_numeric("x") is None
    assert parse_nullable_int("14") == 14
    assert parse_nullable_int("a") is None


def test_field_mapping() -> None:
    observed_at = datetime(2026, 4, 27, 10, 0, tzinfo=UTC)
    item = {
        "Id": 123,
        "url": "https://example/listing/123",
        "phone": "+70000000000",
        "time": "2026-04-27T09:50:00Z",
        "time_publish": "2026-04-27T09:00:00Z",
        "time_creation": "2026-04-26T09:00:00Z",
        "region": "Moscow",
        "city": "Moscow",
        "address": "Arbat",
        "metro": "Smolenskaya",
        "rooms_count": 2,
        "floor_number": 5,
        "floors_count": 9,
        "area": "45.2",
        "area_kitchen": "9.1",
        "area_living": "20.0",
        "area_land": None,
        "building_year": 2001,
        "deal_type": "sale",
        "repair_type": "cosmetic",
        "person_type": "agent",
        "building_material_type": "brick",
        "category": "flat",
        "subcategory": "secondary",
        "category_Id": 1,
        "region_Id": 1,
        "city_Id": 1,
        "coords": {"lat": "55.75", "lng": "37.61"},
        "layout": "isolated",
        "class_type": "economy",
        "condition_type": "good",
        "published_user_id": 100,
        "source_user_id": 200,
        "images": ["a.jpg", "b.jpg"],
        "description": "nice flat",
        "price": "15500000",
    }
    mapped = map_listing_item(item, observed_at=observed_at)
    assert mapped.external_id == 123
    assert mapped.object_record["lat"] == Decimal("55.75")
    assert mapped.object_record["lng"] == Decimal("37.61")
    assert mapped.object_record["area_total"] == Decimal("45.2")
    assert mapped.object_record["first_seen_at"] == observed_at
    assert mapped.price_record["price"] == Decimal("15500000")
