from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from psycopg import sql
import psycopg

from reml.ingestion.parser import ALLOWED_SCHEMAS, ParsedListing

OBJECT_COLUMNS = [
    "external_id",
    "url",
    "phone",
    "first_seen_at",
    "last_seen_at",
    "source_time",
    "first_published_at",
    "created_at_source",
    "region",
    "city",
    "address",
    "metro",
    "rooms_count",
    "floor_number",
    "floors_count",
    "area_total",
    "area_kitchen",
    "area_living",
    "area_land",
    "building_year",
    "deal_type",
    "repair_type",
    "person_type",
    "building_material_type",
    "category",
    "subcategory",
    "category_id",
    "region_id",
    "city_id",
    "lat",
    "lng",
    "layout",
    "class_type",
    "condition_type",
    "published_user_id",
    "external_user_id",
    "images",
    "images_hash",
    "description",
    "description_hash",
]


def _validate_schema(schema_name: str) -> None:
    if schema_name not in ALLOWED_SCHEMAS:
        raise ValueError(f"Unsupported schema_name: {schema_name}")


@dataclass(slots=True)
class IngestionRepository:
    dsn: str

    def ingest_response(
        self,
        *,
        schema_name: str,
        endpoint: str,
        request_params: dict[str, Any],
        response_payload: dict[str, Any],
        observed_at: datetime,
        parsed_items: list[ParsedListing],
    ) -> int:
        _validate_schema(schema_name)
        with psycopg.connect(self.dsn) as conn:
            with conn.transaction():
                raw_response_id = self._insert_raw_response(
                    conn=conn,
                    schema_name=schema_name,
                    endpoint=endpoint,
                    request_params=request_params,
                    response_payload=response_payload,
                )
                for item in parsed_items:
                    listing_id = self._upsert_listing_object(
                        conn=conn,
                        schema_name=schema_name,
                        object_record=item.object_record,
                    )
                    self._insert_price_observation(
                        conn=conn,
                        schema_name=schema_name,
                        listing_id=listing_id,
                        raw_response_id=raw_response_id,
                        price_record=item.price_record,
                    )
        return len(parsed_items)

    def upsert_checkpoint(
        self,
        *,
        schema_name: str,
        window_start: date,
        window_end: date,
        status: str,
        records_loaded: int,
        offset: int,
    ) -> None:
        _validate_schema(schema_name)
        checkpoint_sql = """
            INSERT INTO public.ingestion_backfill_checkpoints
                (schema_name, window_start, window_end, status, records_loaded, offset)
            VALUES
                (%(schema_name)s, %(window_start)s, %(window_end)s, %(status)s, %(records_loaded)s, %(offset)s)
            ON CONFLICT (schema_name, window_start, window_end)
            DO UPDATE SET
                status = EXCLUDED.status,
                records_loaded = EXCLUDED.records_loaded,
                offset = EXCLUDED.offset,
                updated_at = now()
        """
        with psycopg.connect(self.dsn) as conn:
            with conn.transaction():
                conn.execute(
                    checkpoint_sql,
                    {
                        "schema_name": schema_name,
                        "window_start": window_start,
                        "window_end": window_end,
                        "status": status,
                        "records_loaded": records_loaded,
                        "offset": offset,
                    },
                )

    def get_checkpoint(
        self,
        *,
        schema_name: str,
        window_start: date,
        window_end: date,
    ) -> dict[str, Any] | None:
        _validate_schema(schema_name)
        with psycopg.connect(self.dsn) as conn:
            row = conn.execute(
                """
                SELECT schema_name, window_start, window_end, status, records_loaded, offset, updated_at
                FROM public.ingestion_backfill_checkpoints
                WHERE schema_name = %(schema_name)s
                  AND window_start = %(window_start)s
                  AND window_end = %(window_end)s
                """,
                {
                    "schema_name": schema_name,
                    "window_start": window_start,
                    "window_end": window_end,
                },
            ).fetchone()
            if row is None:
                return None
            return {
                "schema_name": row[0],
                "window_start": row[1],
                "window_end": row[2],
                "status": row[3],
                "records_loaded": row[4],
                "offset": row[5],
                "updated_at": row[6],
            }

    def _insert_raw_response(
        self,
        *,
        conn: psycopg.Connection,
        schema_name: str,
        endpoint: str,
        request_params: dict[str, Any],
        response_payload: dict[str, Any],
    ) -> int:
        query = sql.SQL(
            """
            INSERT INTO {}.listing_api_responses (endpoint, request_params, response_payload, records_count)
            VALUES (%(endpoint)s, %(request_params)s, %(response_payload)s, %(records_count)s)
            RETURNING id
            """
        ).format(sql.Identifier(schema_name))

        records_count = (
            len(response_payload.get("data", []))
            if isinstance(response_payload.get("data"), list)
            else 0
        )
        row = conn.execute(
            query,
            {
                "endpoint": endpoint,
                "request_params": request_params,
                "response_payload": response_payload,
                "records_count": records_count,
            },
        ).fetchone()
        if row is None:
            raise RuntimeError("Failed to insert raw response")
        return int(row[0])

    def _upsert_listing_object(
        self,
        *,
        conn: psycopg.Connection,
        schema_name: str,
        object_record: dict[str, Any],
    ) -> int:
        object_columns_sql = sql.SQL(", ").join(
            sql.Identifier(c) for c in OBJECT_COLUMNS
        )
        placeholders_sql = sql.SQL(", ").join(
            sql.Placeholder(c) for c in OBJECT_COLUMNS
        )

        update_columns = [
            c for c in OBJECT_COLUMNS if c not in {"external_id", "first_seen_at"}
        ]
        update_sql_parts = [
            sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c))
            for c in update_columns
        ]
        update_sql_parts.append(
            sql.SQL(
                "first_seen_at = LEAST({table}.first_seen_at, EXCLUDED.first_seen_at)"
            ).format(table=sql.Identifier("listing_objects"))
        )
        update_sql_parts.append(sql.SQL("updated_at = now()"))

        query = sql.SQL(
            """
            INSERT INTO {}.listing_objects ({})
            VALUES ({})
            ON CONFLICT (external_id)
            DO UPDATE SET {}
            RETURNING id
            """
        ).format(
            sql.Identifier(schema_name),
            object_columns_sql,
            placeholders_sql,
            sql.SQL(", ").join(update_sql_parts),
        )

        row = conn.execute(query, object_record).fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert listing object")
        return int(row[0])

    def _insert_price_observation(
        self,
        *,
        conn: psycopg.Connection,
        schema_name: str,
        listing_id: int,
        raw_response_id: int,
        price_record: dict[str, Any],
    ) -> None:
        query = sql.SQL(
            """
            INSERT INTO {}.listing_price_observations
                (listing_id, external_id, observed_at, source_time, time_publish, price, raw_response_id)
            VALUES
                (%(listing_id)s, %(external_id)s, %(observed_at)s, %(source_time)s, %(time_publish)s, %(price)s, %(raw_response_id)s)
            ON CONFLICT (listing_id, observed_at) DO NOTHING
            """
        ).format(sql.Identifier(schema_name))
        payload = {
            "listing_id": listing_id,
            "external_id": price_record["external_id"],
            "observed_at": price_record["observed_at"],
            "source_time": price_record["source_time"],
            "time_publish": price_record["time_publish"],
            "price": price_record["price"],
            "raw_response_id": raw_response_id,
        }
        conn.execute(query, payload)
