"""Shared dependencies, repository, and event bus for Board State microservice."""

from __future__ import annotations

import logging

from board_state.aggregate import BoardAggregate
from runefoble_auth.settings import load_spicedb_settings
from runefoble_auth.wiring import (
    build_identity_dependencies,
    make_verifier_holder,
    verifier_from_settings,
)
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.identifiers import opaque_aggregate_id
from runefoble_platform.service_credential import expected_service_credential

logger = logging.getLogger("runefoble.board_state")
platform_settings = PlatformSettings()
# This service checks SpiceDB permissions. Fail fast at start-up without the key (TASK-0720).
load_spicedb_settings()

repo: AggregateRepository[BoardAggregate] = create_aggregate_repository(BoardAggregate)


class BoardNotFoundError(LookupError):
    """Raised when no board exists for a session id. Routers map it to HTTP 404."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Board not found: {session_id}")


event_bus_provider = EventBusProvider(platform_settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set


get_zitadel_auth_service, set_zitadel_auth_service = make_verifier_holder(
    lambda: verifier_from_settings(platform_settings)
)
SERVICE_CREDENTIAL = expected_service_credential()
get_principal, _caller_principal, CallerId, _caller_or_service, CallerOrService = (
    build_identity_dependencies(get_zitadel_auth_service, SERVICE_CREDENTIAL)
)


async def get_board(session_id: str) -> BoardAggregate:
    """Load an existing board. Raise BoardNotFoundError when the session has no board.

    Only a missing event stream means "not found". Every other load error propagates.
    Boards are created only through the POST /api/v1/boards command.
    """
    board_id = opaque_aggregate_id(session_id, field="session_id")
    board = await load_if_exists(repo, board_id)
    if board is None:
        raise BoardNotFoundError(session_id)
    return board
