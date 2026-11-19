"""Aggregate loading that treats only "aggregate not found" as absence (ADR-0015 f, TASK-0561).

Routers must never replace a failed load with an empty aggregate. A storage outage then
creates a new stream with an existing aggregate id, and the next save writes conflicting
events. These helpers catch only AggregateNotFoundError. Every other error reaches the
caller. Services map store errors to HTTP 503 with register_store_unavailable_handlers.

Routes use these helpers and never write their own `except AggregateNotFoundError` (TASK-0819).
A version conflict on save is mapped by `save_or_conflict`, the single conflict mapper.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import UUID

from eventsource.application.aggregates.repository import AggregateRepository
from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.exceptions import AggregateNotFoundError, OptimisticLockError
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("runefoble.platform.event_store")


async def load_or_create[T: DeclarativeAggregate](
    repo: AggregateRepository[T],
    aggregate_id: UUID,
    factory: Callable[[UUID], T],
) -> T:
    """Load the aggregate. Create an empty one only when its stream does not exist.

    Any other load error propagates unchanged.
    """
    try:
        return await repo.load(aggregate_id)
    except AggregateNotFoundError:
        return factory(aggregate_id)


async def load_if_exists[T: DeclarativeAggregate](
    repo: AggregateRepository[T],
    aggregate_id: UUID,
) -> T | None:
    """Load the aggregate, or return None when its stream does not exist.

    Any other load error propagates unchanged.
    """
    try:
        return await repo.load(aggregate_id)
    except AggregateNotFoundError:
        return None


async def load_or_404[T: DeclarativeAggregate](
    repo: AggregateRepository[T],
    aggregate_id: UUID,
    detail: str,
) -> T:
    """Load the aggregate. Raise HTTP 404 with `detail` when its stream does not exist.

    Any other load error propagates unchanged.
    """
    try:
        return await repo.load(aggregate_id)
    except AggregateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=detail) from exc


async def save_or_conflict[T: DeclarativeAggregate](
    repo: AggregateRepository[T],
    aggregate: T,
    conflict: Callable[[], Exception],
) -> None:
    """Save the aggregate. Raise the error that `conflict` returns on an optimistic lock failure.

    The caller picks the error: an HTTP 409 for a route, or a domain error for a service.
    Any other save error propagates unchanged.
    """
    try:
        await repo.save(aggregate)
    except OptimisticLockError as exc:
        raise conflict() from exc


STORE_UNAVAILABLE_ERRORS: tuple[type[BaseException], ...] = (SQLAlchemyError, OSError)


async def _store_unavailable(request: Request, exc: Exception) -> JSONResponse:
    """Answer 503 when the event store cannot be reached. No substitute data is returned.

    The log line names the route and the error, so an operator can see why a write failed.
    """
    logger.error(
        "Event store unavailable on %s %s: %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "Event store is unavailable"},
    )


def register_store_unavailable_handlers(app: FastAPI) -> None:
    """Map event store connection and database errors to HTTP 503 for this service."""
    for error_type in STORE_UNAVAILABLE_ERRORS:
        app.add_exception_handler(error_type, _store_unavailable)


__all__ = [
    "STORE_UNAVAILABLE_ERRORS",
    "load_if_exists",
    "load_or_404",
    "load_or_create",
    "register_store_unavailable_handlers",
    "save_or_conflict",
]
