"""One HTTP mapping for domain errors on a service app (TASK-0752, ADR-0015).

Routes do not catch domain errors. They let them reach these handlers:

- `ValueError` (a refused command or bad input) answers 400 with the error text.
- `AggregateNotFoundError`, and each not-found type that the service names, answers 404.

Every other error reaches its own platform handler: a store outage answers 503
(`register_store_unavailable_handlers`) and a SpiceDB outage answers 503
(`install_authz_error_handlers`). Routes never catch `Exception` to turn an outage into 400 or 500.

Starlette picks the most specific registered class. A not-found type that subclasses
`ValueError` therefore answers 404, not 400.
"""

from __future__ import annotations

from eventsource.domain.exceptions import AggregateNotFoundError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


async def _bad_request(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def _not_found(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def install_domain_error_handlers(
    app: FastAPI, *, not_found: tuple[type[Exception], ...] = ()
) -> None:
    """Map `ValueError` to 400, and `AggregateNotFoundError` and `not_found` types to 404."""
    app.add_exception_handler(ValueError, _bad_request)
    for error_type in (AggregateNotFoundError, *not_found):
        app.add_exception_handler(error_type, _not_found)


__all__ = ["install_domain_error_handlers"]
