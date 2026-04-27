from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class CianApiError(RuntimeError):
    """Raised when API returns invalid response or non-ok status."""


@dataclass(slots=True)
class CianClient:
    login: str
    token: str
    endpoint: str = "https://rest-app.net/api-cian/ads"
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0

    def _build_params(
        self,
        *,
        category_id: int,
        deal_id: int,
        region_id: int,
        date1: str,
        date2: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        if limit > 1000:
            raise ValueError("limit must be <= 1000")
        return {
            "login": self.login,
            "token": self.token,
            "category_id": category_id,
            "deal_id": deal_id,
            "region_id": region_id,
            "date1": date1,
            "date2": date2,
            "limit": limit,
            "offset": offset,
            "format": "json",
        }

    def fetch_ads(
        self,
        *,
        category_id: int,
        deal_id: int,
        region_id: int,
        date1: str,
        date2: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        params = self._build_params(
            category_id=category_id,
            deal_id=deal_id,
            region_id=region_id,
            date1=date1,
            date2=date2,
            limit=limit,
            offset=offset,
        )
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(
                    self.endpoint, params=params, timeout=self.timeout_seconds
                )
                if response.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(
                        f"Transient HTTP status {response.status_code}",
                        response=response,
                    )
                response.raise_for_status()
                payload = response.json()
                if payload.get("status") != "ok":
                    raise CianApiError(f"API status is not ok: {payload}")
                logger.info(
                    "cian_fetch_ok",
                    extra={
                        "offset": offset,
                        "limit": limit,
                        "records_count": len(payload.get("data", [])),
                    },
                )
                return payload
            except (requests.RequestException, ValueError, CianApiError) as exc:
                if attempt >= self.max_retries:
                    logger.exception("cian_fetch_failed", extra={"attempt": attempt})
                    raise
                sleep_for = self.retry_backoff_seconds * attempt
                logger.warning(
                    "cian_fetch_retry",
                    extra={
                        "attempt": attempt,
                        "sleep_for": sleep_for,
                        "error": str(exc),
                    },
                )
                time.sleep(sleep_for)
        raise RuntimeError("Unreachable retry loop")
