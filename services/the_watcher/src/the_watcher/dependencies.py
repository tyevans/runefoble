"""Shared dependencies, engine instances, and event bus for The Watcher service."""

from __future__ import annotations

import logging

from fastapi import HTTPException
from runefoble_auth.contract import permission_for_action
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.permissions import check_subject
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_sourcing import create_aggregate_repository
from runefoble_platform.lazy_repository import LazyRepository
from the_watcher.autonomous_dm_engine import AutonomousDMEngine
from the_watcher.chronicle import ChronicleRecapEngine
from the_watcher.compound_actions import CompoundActionEngine
from the_watcher.copilot import CopilotEngine
from the_watcher.copilot_state.disambiguations import DisambiguationAggregate
from the_watcher.copilot_state.pending_actions import PendingActionAggregate
from the_watcher.copilot_state.whispers import WhisperAggregate
from the_watcher.copilot_whispers import WhisperService
from the_watcher.disambiguation import DisambiguationEngine, DisambiguationStore
from the_watcher.factions import FactionAggregate
from the_watcher.factions.campaign_world import CampaignWorldAggregate
from the_watcher.factions.resources import FactionResourceAggregate
from the_watcher.simulation_engine import FactionSimulationEngine
from the_watcher.turf_war.aggregate import RegionalUnrestAggregate
from the_watcher.watcher_ai import TheWatcherEngine

logger = logging.getLogger("runefoble.the_watcher")

STREAM_WATCHER = "runefoble.events.watcher"
STREAM_BOARD = "runefoble.events.board"
STREAM_WORLD = "runefoble.events.world"

engine = TheWatcherEngine()
chronicle_engine = ChronicleRecapEngine()
autonomous_dm_engine = AutonomousDMEngine()
disambiguation_engine = DisambiguationEngine()
compound_action_engine = CompoundActionEngine()

platform_settings = PlatformSettings()

_faction_simulation_engine = FactionSimulationEngine()


def get_faction_simulation_engine() -> FactionSimulationEngine:
    return _faction_simulation_engine


def set_faction_simulation_engine(engine: FactionSimulationEngine) -> None:
    global _faction_simulation_engine
    _faction_simulation_engine = engine


_faction = LazyRepository(lambda: create_aggregate_repository(FactionAggregate))
_campaign_world = LazyRepository(lambda: create_aggregate_repository(CampaignWorldAggregate))
_faction_resource = LazyRepository(lambda: create_aggregate_repository(FactionResourceAggregate))
_regional_unrest = LazyRepository(lambda: create_aggregate_repository(RegionalUnrestAggregate))

get_faction_repo = _faction.get
set_faction_repo = _faction.set
get_campaign_world_repo = _campaign_world.get
set_campaign_world_repo = _campaign_world.set
get_faction_resource_repo = _faction_resource.get
set_faction_resource_repo = _faction_resource.set
get_regional_unrest_repo = _regional_unrest.get
set_regional_unrest_repo = _regional_unrest.set


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
    return await check_subject(
        get_spicedb_client(), resource_type, str(resource_id), permission, user_id
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


event_bus_provider = EventBusProvider(platform_settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set


_pending_action = LazyRepository(lambda: create_aggregate_repository(PendingActionAggregate))
_whisper = LazyRepository(lambda: create_aggregate_repository(WhisperAggregate))
_disambiguation = LazyRepository(lambda: create_aggregate_repository(DisambiguationAggregate))

get_pending_action_repo = _pending_action.get
set_pending_action_repo = _pending_action.set
get_whisper_repo = _whisper.get
set_whisper_repo = _whisper.set
get_disambiguation_repo = _disambiguation.get
set_disambiguation_repo = _disambiguation.set


def build_copilot_engine() -> CopilotEngine:
    """Build a copilot engine over the current repositories and event bus."""
    return CopilotEngine(pending_repo=get_pending_action_repo)


copilot_engine = build_copilot_engine()
whisper_service = WhisperService(whisper_repo=get_whisper_repo)
disambiguation_store = DisambiguationStore(get_disambiguation_repo, disambiguation_engine)


def get_copilot_engine() -> CopilotEngine:
    return copilot_engine


def get_whisper_service() -> WhisperService:
    return whisper_service


def set_copilot_engine(engine: CopilotEngine) -> None:
    """Replace the copilot engine. A restart installs a fresh engine over the same stores."""
    global copilot_engine
    copilot_engine = engine


def get_disambiguation_store() -> DisambiguationStore:
    return disambiguation_store
