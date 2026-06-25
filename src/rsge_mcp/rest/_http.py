"""Low-level HTTP helper: one POST that maps transport failures onto RsgeError.

Shared by the auth session and the REST client. Returns the raw parsed JSON; envelope
unwrapping and retry policy live in the callers.
"""

from __future__ import annotations

from typing import Any

import httpx

from ..errors import RsgeHttpError, RsgeTimeoutError

JSON_HEADERS = {"Content-Type": "application/json"}


async def post_json(
    http: httpx.AsyncClient,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
    method: str = "POST",
) -> Any:
    """Send ``body`` as JSON (POST by default) and return parsed JSON, or raise RsgeError.

    ``method`` allows GET-with-body, which a few rs.ge endpoints (customs) require.
    """
    try:
        resp = await http.request(method, url, json=body, headers=headers, timeout=timeout)
    except httpx.TimeoutException as exc:
        raise RsgeTimeoutError(f"request to {url} timed out") from exc
    except httpx.HTTPError as exc:
        raise RsgeHttpError(f"request to {url} failed: {exc}") from exc

    if resp.status_code != 200:
        raise RsgeHttpError(
            f"{url} returned HTTP {resp.status_code}",
            status_code=resp.status_code,
            retry_after=_retry_after(resp),
        )
    try:
        return resp.json()
    except ValueError as exc:
        raise RsgeHttpError(f"{url} returned a non-JSON body") from exc


def _retry_after(resp: httpx.Response) -> float | None:
    """Parse a Retry-After header in seconds (HTTP-date form is ignored)."""
    raw = resp.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None
