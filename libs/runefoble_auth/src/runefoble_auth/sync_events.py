"""Domain event ingestion and Zanzibar relationship dispatch handlers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_event_field(event: Any, field_name: str, default: Any = None) -> Any:
    """Extract a field from an event object or dictionary payload."""
    if isinstance(event, dict):
        if field_name in event and event[field_name] is not None:
            return event[field_name]
        data = event.get("data")
        if isinstance(data, dict) and field_name in data and data[field_name] is not None:
            return data[field_name]
        return default
    val = getattr(event, field_name, None)
    return val if val is not None else default


def extract_event_type(event: Any) -> str:
    """Extract canonical event type name from a domain event object or CloudEvent dictionary."""
    if isinstance(event, dict):
        raw = event.get("type") or event.get("event_type")
        if not raw and isinstance(event.get("data"), dict):
            raw = event["data"].get("event_type")
        raw_type = raw or ""
    else:
        raw_type = (
            getattr(event, "event_type", None)
            or getattr(event, "type", None)
            or event.__class__.__name__
        )
    return raw_type.split(".")[-1] if "." in raw_type else raw_type


async def handle_session_created(sync_service: Any, event: Any) -> list[str]:
    """Handle SessionCreated domain event to configure DM and session binding."""
    campaign_id = (
        get_event_field(event, "campaign_id")
        or get_event_field(event, "session_id")
        or str(get_event_field(event, "aggregate_id", ""))
    )
    dm_id = get_event_field(event, "dm_id") or get_event_field(event, "created_by", "system")
    session_id = get_event_field(event, "session_id") or str(
        get_event_field(event, "aggregate_id", campaign_id)
    )

    synced: list[str] = []
    if campaign_id and dm_id:
        synced.extend(await sync_service.sync_membership(str(campaign_id), str(dm_id), "gm"))
    if session_id and campaign_id:
        synced.extend(await sync_service.sync_session_campaign(str(session_id), str(campaign_id)))
    return synced


async def handle_participant_joined(sync_service: Any, event: Any) -> list[str]:
    """Handle ParticipantJoined or PlayerJoinedSession domain events."""
    campaign_id = (
        get_event_field(event, "campaign_id")
        or get_event_field(event, "session_id")
        or str(get_event_field(event, "aggregate_id", ""))
    )
    user_id = get_event_field(event, "user_id") or get_event_field(event, "player_id")
    role = get_event_field(event, "role", "player")

    synced: list[str] = []
    if campaign_id and user_id:
        synced.extend(await sync_service.sync_membership(str(campaign_id), str(user_id), str(role)))

    char_id = get_event_field(event, "character_id")
    if char_id and user_id:
        camp_arg = str(campaign_id) if campaign_id else None
        synced.extend(await sync_service.sync_character_ownership(char_id, str(user_id), camp_arg))

    return synced


async def handle_character_created(sync_service: Any, event: Any) -> list[str]:
    """Handle CharacterCreated domain event to establish character ownership."""
    char_id = get_event_field(event, "character_id") or str(
        get_event_field(event, "aggregate_id", "")
    )
    player_id = get_event_field(event, "player_id")
    campaign_id = get_event_field(event, "campaign_id")

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
    token_id = str(get_event_field(event, "token_id") or get_event_field(event, "aggregate_id", ""))
    character_id = get_event_field(event, "character_id")
    camp_id = get_event_field(event, "campaign_id") or campaign_id

    return await sync_service.sync_board_token(
        token_id, character_id, str(camp_id) if camp_id else None
    )


async def handle_domain_event(
    sync_service: Any, event: Any, campaign_id: str | None = None
) -> list[str]:
    """Route a domain event or CloudEvent payload to appropriate relationship handlers."""
    event_type = extract_event_type(event)
    if event_type == "SessionCreated":
        return await handle_session_created(sync_service, event)
    if event_type in ("ParticipantJoined", "PlayerJoinedSession"):
        return await handle_participant_joined(sync_service, event)
    if event_type == "CharacterCreated":
        return await handle_character_created(sync_service, event)
    if event_type in ("TokenPlaced", "TokenPlacedOnBoard"):
        return await handle_token_placed(sync_service, event, campaign_id=campaign_id)

    logger.debug("No Zanzibar synchronization mapped for event type: %s", event_type)
    return []
