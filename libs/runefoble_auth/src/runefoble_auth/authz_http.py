"""HTTP mapping for SpiceDB failures (TASK-0558, TASK-0813).

This module is the only mapping of SpiceDB failures to HTTP responses. Every service calls
`install_authz_error_handlers` at start-up.

- Any `AuthzError` (SpiceDB unreachable, timed out, or did not apply a write) is not a denial.
  The caller gets 503 with the one body `{"error": "authorization_unavailable"}`.
- `AuthzSchemaError` (a name missing from the schema) is a server defect. The caller gets 500
  with an error id that matches the server log. The gRPC detail stays in the log.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization (fail closed)
- ADR-0015: Audit remediation decisions (SVC-01)
"""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from runefoble_auth.errors import AuthzError, AuthzSchemaError

logger = logging.getLogger("runefoble.auth.authz_http")

AUTHORIZATION_UNAVAILABLE = "authorization_unavailable"
AUTHORIZATION_SCHEMA_ERROR = "authorization_schema_error"


async def authz_unavailable_handler(request: Request, exc: AuthzError) -> JSONResponse:
    """Map a SpiceDB call that was not answered or not applied to HTTP 503."""
    logger.error("Authorization unavailable on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=503, content={"error": AUTHORIZATION_UNAVAILABLE})


async def authz_schema_handler(request: Request, exc: AuthzSchemaError) -> JSONResponse:
    """Map a schema mismatch to HTTP 500 with an error id. The gRPC detail stays in the log."""
    error_id = str(uuid.uuid4())
    logger.error(
        "Authorization schema error %s on %s: %s", error_id, request.url.path, exc, exc_info=exc
    )
    return JSONResponse(
        status_code=500,
        content={"error": AUTHORIZATION_SCHEMA_ERROR, "error_id": error_id},
    )


def install_authz_error_handlers(app: FastAPI) -> None:
    """Register the SpiceDB failure mapping on an application that serves authorized routes.

    Starlette picks the most specific registered class, so a schema error never reaches the 503
    handler registered for the base `AuthzError`.
    """
    app.add_exception_handler(AuthzError, authz_unavailable_handler)
    app.add_exception_handler(AuthzSchemaError, authz_schema_handler)


__all__ = [
    "AUTHORIZATION_SCHEMA_ERROR",
    "AUTHORIZATION_UNAVAILABLE",
    "authz_schema_handler",
    "authz_unavailable_handler",
    "install_authz_error_handlers",
]
