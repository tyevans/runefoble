"""Domain event publish policy.

Two policies exist. Decision routes that change state use ``publish_or_fail``. The route
returns 503 when the audit event cannot be published, so the client retries. All other
side effects use ``publish_best_effort`` or ``deliver_best_effort``. These log the failure
at error level and count it. The count is exposed on each service ``/healthz``.

No call site may suppress publish errors silently.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Iterable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from runefoble_platform.errors import RunefobleError
from runefoble_platform.event_fields import event_type_of

logger = logging.getLogger("runefoble.event_publish")

_publish_failures = 0


class DomainEventPublishError(RunefobleError):
    """A decision route could not publish its audit event. The client must retry."""

    def __init__(self, stream: str, event_type: str) -> None:
        super().__init__(
            f"Domain event '{event_type}' could not be published to '{stream}'. Retry the request.",
            {"stream": stream, "event_type": event_type},
        )
        self.stream = stream
        self.event_type = event_type


def event_publish_failures() -> int:
    """Return the number of publish or delivery failures seen by this process."""
    return _publish_failures


def record_publish_failure(destination: str, event_type: str, exc: BaseException) -> None:
    """Log and count a failed publish or delivery. Never raises."""
    global _publish_failures
    _publish_failures += 1
    logger.error(
        "Domain event publish failed: destination=%s event_type=%s error=%s",
        destination,
        event_type,
        exc,
        exc_info=exc,
    )


async def publish_or_fail(bus: Any, stream: str, event: Any) -> str:
    """Publish an event or raise DomainEventPublishError. Use for state-changing decisions."""
    event_type = event_type_of(event)
    try:
        return await bus.publish_event(stream, event)
    except Exception as exc:
        record_publish_failure(stream, event_type, exc)
        raise DomainEventPublishError(stream, event_type) from exc


async def publish_aggregate_events(bus: Any, stream: str, events: Iterable[Any]) -> None:
    """Publish the events of one aggregate to one stream, in order, with publish_or_fail.

    Call it after the aggregate is saved. Read ``uncommitted_events`` before the save and pass
    that list here. The caller keeps its own ``if bus`` guard. The first failed publish raises
    DomainEventPublishError, and the remaining events are not published.
    """
    for event in events:
        await publish_or_fail(bus, stream, event)


async def deliver_best_effort(
    destination: str, event_type: str, delivery: Awaitable[object]
) -> bool:
    """Await a delivery and log and count any failure. Returns False on failure."""
    try:
        await delivery
    except Exception as exc:
        record_publish_failure(destination, event_type, exc)
        return False
    return True


async def publish_best_effort(bus: Any, stream: str, event: Any) -> bool:
    """Publish an event. Log and count a delivery failure, but do not raise.

    An event without a type raises EventTypeMissingError. That is a programming error, so it is
    not counted as a delivery failure.
    """
    return await deliver_best_effort(stream, event_type_of(event), bus.publish_event(stream, event))


def install_publish_failure_handler(app: FastAPI) -> None:
    """Map DomainEventPublishError to HTTP 503 for every route of the app."""

    async def _handle(_request: Request, exc: DomainEventPublishError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Audit event could not be published. The request was not "
                "recorded as complete. Retry the request.",
                "event_type": exc.event_type,
            },
        )

    app.add_exception_handler(DomainEventPublishError, _handle)


__all__ = [
    "DomainEventPublishError",
    "deliver_best_effort",
    "event_publish_failures",
    "install_publish_failure_handler",
    "publish_aggregate_events",
    "publish_best_effort",
    "publish_or_fail",
    "record_publish_failure",
]
