"""Platform In-Memory & Distributed Event Bus interfaces."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")
Handler = Callable[[Any], Coroutine[Any, Any, None]]


class EventBus:
    """Async event bus supporting local and cross-service subscription dispatch."""

    def __init__(self):
        self._handlers: dict[str, list[Handler]] = {}

    def subscribe(self, event_type: str, handler: Handler) -> None:
        """Subscribe a coroutine handler to a specific event topic."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler {handler.__name__} to {event_type}")

    async def publish(self, event_type: str, event_data: Any) -> None:
        """Publish an event to all registered handlers concurrently."""
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            return

        tasks = [asyncio.create_task(h(event_data)) for h in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)


# Global default event bus
bus = EventBus()
