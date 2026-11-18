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
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.service_credential import expected_service_credential

logger = logging.getLogger("runefoble.board_state")
platform_settings = PlatformSettings()
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


event_bus_provider = EventBusProvider(platform_settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set


def get_zitadel_auth_service() -> ZitadelAuthService:
    """Provide the Zitadel verifier that this service trusts, built from platform settings."""
    global _zitadel_auth_service
    if _zitadel_auth_service is None:
        _zitadel_auth_service = ZitadelAuthService(
            issuer=platform_settings.zitadel_issuer,
            audience=platform_settings.zitadel_audience,
            internal_url=platform_settings.zitadel_internal_url,
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
