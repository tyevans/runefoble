"""Service credential guard for inference worker routes (ADR-0015 e).

Callers are other services, never browsers. Each request presents
`Authorization: Bearer <service token>`. The token comparison is constant time.
"""

from __future__ import annotations

import hmac
from collections.abc import Callable
from typing import Annotated

from fastapi import Header, HTTPException


def _bearer_value(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme != "Bearer":
        return None
    return value.strip() or None


def service_token_guard(expected_token: str) -> Callable[..., None]:
    """Build a dependency that accepts only the configured service token. No fallback."""
    expected = expected_token.encode()

    def _guard(authorization: Annotated[str | None, Header()] = None) -> None:
        presented = _bearer_value(authorization)
        if presented is None or not hmac.compare_digest(presented.encode(), expected):
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized", "message": "Missing or invalid service token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

    return _guard
