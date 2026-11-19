"""Domain event ingestion and Zanzibar relationship dispatch handlers."""

from __future__ import annotations

import logging
from typing import Any

from runefoble_platform.event_fields import event_field, event_type_of

logger = logging.getLogger(__name__)


async def handle_session_created(sync_service: Any, event: Any) -> list[str]:
    """Handle SessionCreated domain event to configure DM and session binding."""
    campaign_id = (
        event_field(event, "campaign_id")
        or event_field(event, "session_id")
        or str(event_field(event, "aggregate_id", ""))
    )
    dm_id = event_field(event, "dm_id") or event_field(event, "created_by", "system")
    session_id = event_field(event, "session_id") or str(
        event_field(event, "aggregate_id", campaign_id)
    )

    synced: list[str] = []
    if campaign_id and dm_id:
        synced.extend(
            await sync_service.sync_membership(str(campaign_id), str(dm_id), "game_master")
        )
    if session_id and campaign_id:
        synced.extend(await sync_service.sync_session_campaign(str(session_id), str(campaign_id)))
    return synced


async def handle_participant_joined(sync_service: Any, event: Any) -> list[str]:
    """Handle PlayerJoinedSession domain events."""
    campaign_id = (
        event_field(event, "campaign_id")
        or event_field(event, "session_id")
        or str(event_field(event, "aggregate_id", ""))
    )
    user_id = event_field(event, "user_id") or event_field(event, "player_id")
    role = event_field(event, "role", "player")

    synced: list[str] = []
    if campaign_id and user_id:
        synced.extend(await sync_service.sync_membership(str(campaign_id), str(user_id), str(role)))

    char_id = event_field(event, "character_id")
    if char_id and user_id:
        camp_arg = str(campaign_id) if campaign_id else None
        synced.extend(await sync_service.sync_character_ownership(char_id, str(user_id), camp_arg))

    return synced


async def handle_character_created(sync_service: Any, event: Any) -> list[str]:
    """Handle CharacterCreated domain event to establish character ownership."""
    char_id = event_field(event, "character_id") or str(event_field(event, "aggregate_id", ""))
    player_id = event_field(event, "player_id")
    campaign_id = event_field(event, "campaign_id")

    synced: list[str] = []
    if char_id and player_id:
        camp_arg = str(campaign_id) if campaign_id else None
        synced.extend(
            await sync_service.sync_character_ownership(char_id, str(player_id), camp_arg)
        )
    return synced


async def handle_token_placed(
    sync_service: Any, event: Any, campaign_id: str | None = None
) -> list[str]:
    """Handle TokenPlaced domain event to establish token spatial permissions."""
    token_id = str(event_field(event, "token_id") or event_field(event, "aggregate_id", ""))
    character_id = event_field(event, "character_id")
    camp_id = event_field(event, "campaign_id") or campaign_id

    return await sync_service.sync_board_token(
        token_id, character_id, str(camp_id) if camp_id else None
    )


async def handle_domain_event(
    sync_service: Any, event: Any, campaign_id: str | None = None
) -> list[str]:
    """Route a domain event or CloudEvent payload to appropriate relationship handlers."""
    event_type = event_type_of(event)
    if event_type == "runefoble.events.session.created":
        return await handle_session_created(sync_service, event)
    if event_type == "runefoble.events.session.player_joined_session":
        return await handle_participant_joined(sync_service, event)
    if event_type == "runefoble.events.character.created":
        return await handle_character_created(sync_service, event)
    if event_type == "runefoble.events.board.token_placed":
        return await handle_token_placed(sync_service, event, campaign_id=campaign_id)

    logger.debug("No Zanzibar synchronization mapped for event type: %s", event_type)
    return []
