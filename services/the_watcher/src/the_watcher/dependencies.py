"""Shared dependencies, engine instances, and event bus for The Watcher service."""

from __future__ import annotations

import logging
import os
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from fastapi import HTTPException
from runefoble_auth.contract import permission_for_action
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus
from the_watcher.autonomous_dm import AutonomousDMEngine
from the_watcher.chronicle import ChronicleRecapEngine
from the_watcher.compound_actions import CompoundActionEngine
from the_watcher.copilot import CopilotEngine
from the_watcher.disambiguation import DisambiguationEngine
from the_watcher.factions import FactionAggregate
from the_watcher.factions.campaign_world import CampaignWorldAggregate
from the_watcher.factions.resources import FactionResourceAggregate
from the_watcher.simulation_engine import FactionSimulationEngine
from the_watcher.turf_war.aggregate import RegionalUnrestAggregate
from the_watcher.watcher_ai import TheWatcherEngine

logger = logging.getLogger("runefoble.the_watcher")
INFERENCE_URL = os.environ.get("RUNEFOBLE_INFERENCE_URL")
BOARD_STATE_URL = os.environ.get("RUNEFOBLE_BOARD_STATE_URL")

STREAM_WATCHER = "runefoble.events.watcher"
STREAM_BOARD = "runefoble.events.board"
STREAM_WORLD = "runefoble:events:world"

engine = TheWatcherEngine()
chronicle_engine = ChronicleRecapEngine()
autonomous_dm_engine = AutonomousDMEngine()
copilot_engine = CopilotEngine()
disambiguation_engine = DisambiguationEngine()
compound_action_engine = CompoundActionEngine()

platform_settings = PlatformSettings()

_event_bus: RedisStreamsEventBus | None = None
_faction_repo: AggregateRepository[FactionAggregate] | None = None
_campaign_world_repo: AggregateRepository[CampaignWorldAggregate] | None = None
_faction_resource_repo: AggregateRepository[FactionResourceAggregate] | None = None
_regional_unrest_repo: AggregateRepository[RegionalUnrestAggregate] | None = None


def get_copilot_engine() -> CopilotEngine:
    return copilot_engine


_faction_simulation_engine = FactionSimulationEngine()


def get_faction_simulation_engine() -> FactionSimulationEngine:
    return _faction_simulation_engine


def set_faction_simulation_engine(engine: FactionSimulationEngine) -> None:
    global _faction_simulation_engine
    _faction_simulation_engine = engine


def get_faction_repo() -> AggregateRepository[FactionAggregate]:
    global _faction_repo
    if _faction_repo is None:
        _faction_repo = create_aggregate_repository(FactionAggregate)
    return _faction_repo


def set_faction_repo(repo: AggregateRepository[FactionAggregate] | None) -> None:
    global _faction_repo
    _faction_repo = repo


def get_campaign_world_repo() -> AggregateRepository[CampaignWorldAggregate]:
    global _campaign_world_repo
    if _campaign_world_repo is None:
        _campaign_world_repo = create_aggregate_repository(CampaignWorldAggregate)
    return _campaign_world_repo


def set_campaign_world_repo(repo: AggregateRepository[CampaignWorldAggregate] | None) -> None:
    global _campaign_world_repo
    _campaign_world_repo = repo


def get_faction_resource_repo() -> AggregateRepository[FactionResourceAggregate]:
    global _faction_resource_repo
    if _faction_resource_repo is None:
        _faction_resource_repo = create_aggregate_repository(FactionResourceAggregate)
    return _faction_resource_repo


def set_faction_resource_repo(repo: AggregateRepository[FactionResourceAggregate] | None) -> None:
    global _faction_resource_repo
    _faction_resource_repo = repo


def get_regional_unrest_repo() -> AggregateRepository[RegionalUnrestAggregate]:
    global _regional_unrest_repo
    if _regional_unrest_repo is None:
        _regional_unrest_repo = create_aggregate_repository(RegionalUnrestAggregate)
    return _regional_unrest_repo


def set_regional_unrest_repo(repo: AggregateRepository[RegionalUnrestAggregate] | None) -> None:
    global _regional_unrest_repo
    _regional_unrest_repo = repo


async def check_action_permission(
    user_id: str,
    resource_type: str,
    resource_id: str,
    action: str,
) -> bool:
    """Return True when the user holds the schema permission behind `action`.

    `action` is a key of `ACTION_PERMISSIONS`. The type of the action must match
    `resource_type`. SpiceDB errors propagate (fail closed): only a definitive denial
    returns False.
    """
    action_type, permission = permission_for_action(action)
    if action_type != resource_type:
        raise ValueError(f"Action '{action}' checks '{action_type}', not '{resource_type}'")
    return await get_spicedb_client().check_permission(
        resource_type, str(resource_id), permission, "user", user_id
    )


async def require_campaign_permission(user_id: str, campaign_id: str | None, action: str) -> None:
    """Raise 403 unless the user holds the campaign permission behind `action`.

    A missing campaign id is a denial. The check never passes by default.
    """
    if not campaign_id or not await check_action_permission(
        user_id, "campaign", campaign_id, action
    ):
        raise HTTPException(status_code=403, detail=_denied(action, "campaign", campaign_id))


async def require_character_permission(user_id: str, character_id: str | None, action: str) -> None:
    """Raise 403 unless the user holds the character permission behind `action`."""
    if not character_id or not await check_action_permission(
        user_id, "character", character_id, action
    ):
        raise HTTPException(status_code=403, detail=_denied(action, "character", character_id))


async def require_speaker(user_id: str, speaker_id: str) -> None:
    """Allow a player to speak as themselves, or for a character they can edit.

    A speaker that is neither the caller nor an editable character gets 403.
    """
    if speaker_id == user_id:
        return
    await require_character_permission(user_id, speaker_id, "character.edit")


async def require_session_permission(user_id: str, session_id: str | None, action: str) -> None:
    """Raise 403 unless the user holds the session permission behind `action`."""
    if not session_id or not await check_action_permission(user_id, "session", session_id, action):
        raise HTTPException(status_code=403, detail=_denied(action, "session", session_id))


async def require_dm(
    user_id: str, campaign_id: str | None = None, session_id: str | None = None
) -> None:
    """Raise 403 unless `check_dm_authorization` grants the table-run permission for the scope."""
    if not await check_dm_authorization(user_id, campaign_id=campaign_id, session_id=session_id):
        action = "session.control" if session_id else "campaign.run_session"
        resource_type, resource_id = (
            ("session", session_id) if session_id else ("campaign", campaign_id)
        )
        raise HTTPException(status_code=403, detail=_denied(action, resource_type, resource_id))


def _denied(action: str, resource_type: str, resource_id: str | None) -> str:
    return (
        f"Forbidden: Zanzibar authorization denied. Action '{action}' requires "
        f"permission on {resource_type} '{resource_id or 'unknown'}'."
    )


async def check_dm_authorization(
    user_id: str,
    campaign_id: str | None = None,
    session_id: str | None = None,
) -> bool:
    """Return True when the user may run the table (DM, GM, or owner).

    A session scope is decided by `session.control` only. Mixing a campaign id from one
    campaign with a session from another must not pass. Without a session the campaign
    permission `campaign.run_session` decides.
    """
    if session_id:
        return await check_action_permission(user_id, "session", session_id, "session.control")
    if campaign_id:
        return await check_action_permission(
            user_id, "campaign", campaign_id, "campaign.run_session"
        )
    return False


def get_event_bus() -> RedisStreamsEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus


def to_uuid(val: str | UUID | None) -> UUID:
    """Deterministically convert a string or UUID into a valid UUID."""
    if val is None:
        return uuid4()
    if isinstance(val, UUID):
        return val
    try:
        return UUID(val)
    except ValueError:
        return uuid5(NAMESPACE_DNS, str(val))
