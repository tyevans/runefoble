"""Aggregate loading that treats only "aggregate not found" as absence (ADR-0015 f, TASK-0561).

Routers must never replace a failed load with an empty aggregate. A storage outage then
creates a new stream with an existing aggregate id, and the next save writes conflicting
events. These helpers catch only AggregateNotFoundError. Every other error reaches the
caller. Services map store errors to HTTP 503 with register_store_unavailable_handlers.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from eventsource.application.aggregates.repository import AggregateRepository
from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.exceptions import AggregateNotFoundError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


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


STORE_UNAVAILABLE_ERRORS: tuple[type[BaseException], ...] = (SQLAlchemyError, OSError)


async def _store_unavailable(_request: Request, _exc: Exception) -> JSONResponse:
    """Answer 503 when the event store cannot be reached. No substitute data is returned."""
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
    "load_or_create",
    "register_store_unavailable_handlers",
]
