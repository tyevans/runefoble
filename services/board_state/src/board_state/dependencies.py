"""Shared dependencies, repository, and event bus for Board State microservice."""

from __future__ import annotations

import contextlib
import logging
from uuid import NAMESPACE_DNS, UUID, uuid5

from board_state.aggregate import BoardAggregate
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus

logger = logging.getLogger("runefoble.board_state")
platform_settings = PlatformSettings()
_event_bus: RedisStreamsEventBus | None = None

repo: AggregateRepository[BoardAggregate] = create_aggregate_repository(BoardAggregate)


def to_board_uuid(session_id: str) -> UUID:
    """Deterministically convert session_id string or UUID into UUID."""
    try:
        return UUID(session_id)
    except ValueError:
        return uuid5(NAMESPACE_DNS, session_id)


def get_event_bus() -> RedisStreamsEventBus | None:
    global _event_bus
    if _event_bus is None and platform_settings.redis_url:
        with contextlib.suppress(Exception):
            _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus


async def get_or_create_board(session_id: str) -> BoardAggregate:
    board_id = to_board_uuid(session_id)
    try:
        return await repo.load(board_id)
    except Exception:
        # Initialize default 12x12 grid with demo tokens for session
        board = BoardAggregate(board_id)
        board.initialize_grid(cols=12, rows=12, session_id=session_id)
        # Place standard tokens
        board.place_token(
            "t1", name="Valeros", token_type="pc", x=2, y=3, is_friendly=True, vision_radius=2
        )
        board.place_token(
            "t2", name="Kyra", token_type="pc", x=3, y=3, is_friendly=True, vision_radius=2
        )
        board.place_token(
            "t3", name="Goblin Scout", token_type="monster", x=8, y=8, is_friendly=False
        )
        await repo.save(board)
        return board
