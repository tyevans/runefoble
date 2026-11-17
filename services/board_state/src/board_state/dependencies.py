"""Shared dependencies, repository, and event bus for Board State microservice."""

from __future__ import annotations

import logging
from uuid import NAMESPACE_DNS, UUID, uuid5

from board_state.aggregate import BoardAggregate
from eventsource.domain.exceptions import AggregateNotFoundError
from fastapi import Header
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus

logger = logging.getLogger("runefoble.board_state")
platform_settings = PlatformSettings()
_event_bus: RedisStreamsEventBus | None = None
_spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None

repo: AggregateRepository[BoardAggregate] = create_aggregate_repository(BoardAggregate)


def to_board_uuid(session_id: str) -> UUID:
    """Deterministically convert session_id string or UUID into UUID."""
    try:
        return UUID(session_id)
    except ValueError:
        return uuid5(NAMESPACE_DNS, session_id)


class BoardNotFoundError(LookupError):
    """Raised when no board exists for a session id. Routers map it to HTTP 404."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Board not found: {session_id}")


def get_event_bus() -> RedisStreamsEventBus | None:
    """Return the Redis Streams bus, creating it on first use.

    Initialization errors propagate. They are never hidden behind a silent None.
    """
    global _event_bus
    if _event_bus is None and platform_settings.redis_url:
        _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus


def get_spicedb_client() -> SpiceDBClient | MockSpiceDBClient:
    """Provide SpiceDB Zanzibar authorization client."""
    global _spicedb_client
    if _spicedb_client is None:
        _spicedb_client = SpiceDBClient(
            endpoint=getattr(platform_settings, "spicedb_endpoint", "localhost:50051")
            or "localhost:50051",
            token=getattr(platform_settings, "spicedb_token", "secret"),
        )
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient | MockSpiceDBClient | None) -> None:
    """Override SpiceDB client for testing."""
    global _spicedb_client
    _spicedb_client = client


def get_current_user_id(
    x_user_id: str | None = Header(default=None, alias="x-user-id"),
) -> str | None:
    """Extract authenticated caller identity from x-user-id header."""
    return x_user_id


async def check_user_can_manage_traps(
    user_id: str | None,
    board_id: str,
    campaign_id: str | None = None,
    spicedb: SpiceDBClient | MockSpiceDBClient | None = None,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can manage traps."""
    if not user_id:
        return False
    client = spicedb or get_spicedb_client()
    target = campaign_id or board_id

    for perm in ("dungeon_master", "run_session", "manage", "owner"):
        try:
            if await client.check_permission("campaign", str(target), perm, "user", user_id):
                return True
        except Exception:
            pass

    for perm in ("manage_traps", "view_secret_layer", "switch_map", "dungeon_master"):
        try:
            if await client.check_permission("board", str(board_id), perm, "user", user_id):
                return True
        except Exception:
            pass

    for perm in ("control", "run_session", "dungeon_master"):
        try:
            if await client.check_permission("session", str(target), perm, "user", user_id):
                return True
            if await client.check_permission("game_session", str(target), perm, "user", user_id):
                return True
        except Exception:
            pass

    return False


async def check_user_can_view_secret_layer(
    user_id: str | None,
    board_id: str,
    campaign_id: str | None = None,
    spicedb: SpiceDBClient | None = None,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can view secret DM layer."""
    return await check_user_can_manage_traps(user_id, board_id, campaign_id, spicedb)


async def check_user_can_switch_map(
    user_id: str | None,
    board_id: str,
    campaign_id: str | None = None,
    spicedb: SpiceDBClient | None = None,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can switch active battlemap."""
    return await check_user_can_manage_traps(user_id, board_id, campaign_id, spicedb)


async def get_board(session_id: str) -> BoardAggregate:
    """Load an existing board. Raise BoardNotFoundError when the session has no board.

    Only a missing event stream means "not found". Every other load error propagates.
    Boards are created only through the POST /api/v1/boards command.
    """
    board_id = to_board_uuid(session_id)
    try:
        return await repo.load(board_id)
    except AggregateNotFoundError as exc:
        raise BoardNotFoundError(session_id) from exc
