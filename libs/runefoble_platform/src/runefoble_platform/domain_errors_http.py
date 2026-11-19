"""One HTTP mapping for domain errors on a service app (TASK-0752, TASK-0914, ADR-0015).

Routes do not catch domain errors. They let them reach these handlers:

- `DomainRefusedError` (a refused command) answers 400 with the error text.
- `DomainNotFoundError` and `AggregateNotFoundError` answer 404 with the error text.

The handlers do not map `ValueError`. A `ValueError` or a `pydantic.ValidationError` that
service code raises is a defect. It reaches the server error handler, which answers 500
with the fixed text `Internal Server Error` and does not send the exception text.

Every other error reaches its own platform handler: a store outage answers 503
(`register_store_unavailable_handlers`) and a SpiceDB outage answers 503
(`install_authz_error_handlers`). Routes never catch `Exception` to turn an outage into 400 or 500.
"""

from __future__ import annotations

from eventsource.domain.exceptions import AggregateNotFoundError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from runefoble_platform.domain_errors import DomainNotFoundError, DomainRefusedError


async def _bad_request(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def _not_found(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def install_domain_error_handlers(app: FastAPI) -> None:
    """Map `DomainRefusedError` to 400, and `DomainNotFoundError` and `AggregateNotFoundError` to 404."""
    app.add_exception_handler(DomainRefusedError, _bad_request)
    app.add_exception_handler(DomainNotFoundError, _not_found)
    app.add_exception_handler(AggregateNotFoundError, _not_found)


__all__ = ["install_domain_error_handlers"]
