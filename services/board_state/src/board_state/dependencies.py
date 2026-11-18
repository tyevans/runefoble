"""Shared dependencies, repository, and event bus for Board State microservice."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import NAMESPACE_DNS, UUID, uuid5

from board_state.aggregate import BoardAggregate
from eventsource.domain.exceptions import AggregateNotFoundError
from fastapi import Depends
from runefoble_auth.caller import CallerIdentity, require_user_or_service_credential
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.service_credential import expected_service_credential

logger = logging.getLogger("runefoble.board_state")
platform_settings = PlatformSettings()
_event_bus: RedisStreamsEventBus | None = None
_spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None
_zitadel_auth_service: ZitadelAuthService | None = None

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
            token=platform_settings.spicedb_preshared_key,
        )
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient | MockSpiceDBClient | None) -> None:
    """Override SpiceDB client for testing."""
    global _spicedb_client
    _spicedb_client = client


def get_zitadel_auth_service() -> ZitadelAuthService:
    """Provide the Zitadel verifier that this service trusts, built from platform settings."""
    global _zitadel_auth_service
    if _zitadel_auth_service is None:
        _zitadel_auth_service = ZitadelAuthService(
            issuer=platform_settings.zitadel_issuer,
            audience=platform_settings.zitadel_audience,
            jwks_url=platform_settings.zitadel_jwks_url,
        )
    return _zitadel_auth_service


def set_zitadel_auth_service(service: ZitadelAuthService | None) -> None:
    """Override the Zitadel verifier for tests."""
    global _zitadel_auth_service
    _zitadel_auth_service = service


get_current_principal = require_principal(get_zitadel_auth_service)


# Service credential (ADR-0015 e). Read once at import, so a service without it never starts.
SERVICE_CREDENTIAL = expected_service_credential()
get_caller_or_service = require_user_or_service_credential(
    get_zitadel_auth_service, SERVICE_CREDENTIAL
)
CallerOrService = Annotated[CallerIdentity, Depends(get_caller_or_service)]


def get_current_user_id(
    principal: Annotated[VerifiedPrincipal, Depends(get_current_principal)],
) -> str:
    """Return the subject of the verified bearer token. Raise 401 when no token verifies."""
    return principal.user_id


async def check_user_can_manage_traps(
    user_id: str,
    board_id: str,
    campaign_id: str | None = None,
    spicedb: SpiceDBClient | MockSpiceDBClient | None = None,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can manage traps."""
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
    user_id: str,
    board_id: str,
    campaign_id: str | None = None,
    spicedb: SpiceDBClient | None = None,
) -> bool:
    """Evaluate SpiceDB Zanzibar permissions to check whether user can view secret DM layer."""
    return await check_user_can_manage_traps(user_id, board_id, campaign_id, spicedb)


async def check_user_can_switch_map(
    user_id: str,
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
