"""HTTP mapping for SpiceDB failures in The Watcher.

A failed authorization call never becomes a denial and never becomes a success:
- `AuthzUnavailableError` (SpiceDB unreachable or slow) maps to HTTP 503.
- `AuthzSchemaError` (a name is not in runefoble.zed) is a defect. It maps to HTTP 500 with
  an error id. The full error is logged under that id.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
"""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from runefoble_auth.errors import AuthzSchemaError, AuthzUnavailableError

logger = logging.getLogger("runefoble.the_watcher.authz")


def install_authz_error_handlers(app: FastAPI) -> None:
    """Register the SpiceDB error mapping for every route of the app."""

    async def _unavailable(_request: Request, exc: AuthzUnavailableError) -> JSONResponse:
        logger.error("Authorization service unavailable: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "error": "authorization_unavailable",
                "detail": "Authorization service is unavailable. Retry the request.",
            },
        )

    async def _schema(request: Request, exc: AuthzSchemaError) -> JSONResponse:
        error_id = uuid.uuid4().hex
        logger.error(
            "Authorization schema defect on %s (error_id=%s): %s",
            request.url.path,
            error_id,
            exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "authorization_schema_error",
                "detail": "Authorization failed because of an internal schema defect.",
                "error_id": error_id,
            },
        )

    app.add_exception_handler(AuthzUnavailableError, _unavailable)
    app.add_exception_handler(AuthzSchemaError, _schema)
