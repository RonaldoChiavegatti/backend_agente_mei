"""HTTP client used to communicate with the Billing service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from urllib import error, request
from uuid import UUID

try:  # pragma: no cover - optional dependency
    import httpx  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for local tests
    httpx = None  # type: ignore[assignment]


class BillingClient:
    """Thin wrapper around the Billing service HTTP API."""

    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def log_chat_usage(
        self,
        *,
        user_id: UUID,
        tokens: int,
        operation_type: str,
        occurred_at: Optional[datetime] = None,
    ) -> None:
        payload = {
            "user_id": str(user_id),
            "tokens": max(0, int(tokens)),
            "operation_type": operation_type,
            "occurred_at": (
                (occurred_at or datetime.now(timezone.utc)).isoformat()
            ),
        }

        url = f"{self._base_url}/billing/transactions"
        if httpx is not None and hasattr(httpx, "post"):
            response = httpx.post(url, json=payload, timeout=self._timeout)
            response.raise_for_status()
            return

        self._post_with_urllib(url, payload)

    def _post_with_urllib(self, url: str, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with request.urlopen(req, timeout=self._timeout) as resp:  # type: ignore[arg-type]
                if resp.status >= 400:  # pragma: no cover - handled via HTTPError
                    raise RuntimeError(
                        f"Billing service responded with status {resp.status}"
                    )
        except error.HTTPError as exc:  # pragma: no cover - network failure path
            raise RuntimeError(
                f"Billing service responded with status {exc.code}"
            ) from exc
        except error.URLError as exc:  # pragma: no cover - network failure path
            raise RuntimeError("Failed to reach Billing service") from exc
