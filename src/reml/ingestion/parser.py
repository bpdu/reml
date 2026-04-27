from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any

ALLOWED_SCHEMAS = {"sale", "rent"}
DEAL_ID_BY_SCHEMA = {"sale": 1, "rent": 2}


def resolve_deal_id(schema: str) -> int:
    if schema not in ALLOWED_SCHEMAS:
        raise ValueError(f"Unsupported schema: {schema}")
    return DEAL_ID_BY_SCHEMA[schema]


def sha256_text(value: str | None) -> str:
    payload = value or ""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_timestamp(value: Any) -> datetime | None:
    if value in (None, "", 0):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def parse_numeric(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def parse_nullable_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_text_field(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


@dataclass(slots=True)
class ParsedListing:
    external_id: int
    object_record: dict[str, Any]
    price_record: dict[str, Any]


def map_listing_item(item: dict[str, Any], observed_at: datetime) -> ParsedListing:
    external_id = parse_nullable_int(item.get("Id"))
    if external_id is None:
        raise ValueError("Listing without valid Id")

    coords = item.get("coords") or {}
    images_text = normalize_text_field(item.get("images"))
    description = normalize_text_field(item.get("description"))

    object_record: dict[str, Any] = {
        "external_id": external_id,
        "url": normalize_text_field(item.get("url")),
        "phone": normalize_text_field(item.get("phone")),
        "first_seen_at": observed_at,
        "last_seen_at": observed_at,
        "source_time": parse_timestamp(item.get("time")),
        "first_published_at": parse_timestamp(item.get("time_publish")),
        "created_at_source": parse_timestamp(item.get("time_creation")),
        "region": normalize_text_field(item.get("region")),
        "city": normalize_text_field(item.get("city")),
        "address": normalize_text_field(item.get("address")),
        "metro": normalize_text_field(item.get("metro")),
        "rooms_count": parse_nullable_int(item.get("rooms_count")),
        "floor_number": parse_nullable_int(item.get("floor_number")),
        "floors_count": parse_nullable_int(item.get("floors_count")),
        "area_total": parse_numeric(item.get("area")),
        "area_kitchen": parse_numeric(item.get("area_kitchen")),
        "area_living": parse_numeric(item.get("area_living")),
        "area_land": parse_numeric(item.get("area_land")),
        "building_year": parse_nullable_int(item.get("building_year")),
        "deal_type": normalize_text_field(item.get("deal_type")),
        "repair_type": normalize_text_field(item.get("repair_type")),
        "person_type": normalize_text_field(item.get("person_type")),
        "building_material_type": normalize_text_field(
            item.get("building_material_type")
        ),
        "category": normalize_text_field(item.get("category")),
        "subcategory": normalize_text_field(item.get("subcategory")),
        "category_id": parse_nullable_int(item.get("category_Id")),
        "region_id": parse_nullable_int(item.get("region_Id")),
        "city_id": parse_nullable_int(item.get("city_Id")),
        "lat": parse_numeric(coords.get("lat")),
        "lng": parse_numeric(coords.get("lng")),
        "layout": normalize_text_field(item.get("layout")),
        "class_type": normalize_text_field(item.get("class_type")),
        "condition_type": normalize_text_field(item.get("condition_type")),
        "published_user_id": parse_nullable_int(item.get("published_user_id")),
        "external_user_id": parse_nullable_int(item.get("cian_user_id")),
        "images": images_text,
        "images_hash": sha256_text(images_text),
        "description": description,
        "description_hash": sha256_text(description),
    }

    price = parse_numeric(item.get("price"))
    if price is None:
        raise ValueError(f"Listing {external_id} has invalid price")

    price_record: dict[str, Any] = {
        "external_id": external_id,
        "observed_at": observed_at,
        "source_time": parse_timestamp(item.get("time")),
        "time_publish": parse_timestamp(item.get("time_publish")),
        "price": price,
    }
    return ParsedListing(
        external_id=external_id,
        object_record=object_record,
        price_record=price_record,
    )


def parse_response_items(
    payload: dict[str, Any], observed_at: datetime
) -> list[ParsedListing]:
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("Response payload does not contain list in 'data'")
    parsed: list[ParsedListing] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        parsed.append(map_listing_item(item, observed_at=observed_at))
    return parsed
