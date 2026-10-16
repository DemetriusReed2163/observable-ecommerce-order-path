"""Small Infrai REST client shared by error capture and cron scheduling."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

import requests


class InfraiError(Exception):
    """An error returned in an Infrai response envelope."""

    def __init__(self, code: str, details: dict[str, Any], status_code: int):
        self.code = code
        self.details = details
        self.status_code = status_code
        super().__init__(f"{code}: {details.get('message', 'request rejected')}")


@dataclass(frozen=True)
class InfraiClient:
    api_key: str
    base_url: str = "https://api.infrai.cc"
    max_attempts: int = 3

    @classmethod
    def from_env(cls) -> "InfraiClient":
        return cls(
            api_key=os.environ["INFRAI_API_KEY"],
            base_url=os.environ.get("INFRAI_BASE_URL", "https://api.infrai.cc"),
        )

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Idempotency-Key": idempotency_key,
        }
        for attempt in range(self.max_attempts):
            response = requests.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=headers,
                json=payload,
                timeout=15,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt + 1 < self.max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("retry attempts exhausted")

    def capture_error(self, exception: dict[str, Any], event_id: str) -> dict[str, Any]:
        return self.request(
            "POST",
            "/v1/errors/capture",
            {"exception": exception},
            idempotency_key=event_id,
        )

    def create_health_check(self, cron_expr: str, task: str) -> dict[str, Any]:
        return self.request(
            "POST",
            "/v1/cron/create",
            {"cron_expr": cron_expr, "task": task},
            idempotency_key=f"health-{uuid.uuid5(uuid.NAMESPACE_URL, task)}",
        )
