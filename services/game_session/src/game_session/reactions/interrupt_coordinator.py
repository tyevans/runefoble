"""Combat turn interruption coordinator for spoken reaction windows."""

from __future__ import annotations

import contextlib
import logging
from typing import Any
from uuid import UUID, uuid4

from game_session.aggregate import GameSessionAggregate
from game_session.dependencies import STREAM_SESSION, get_event_bus
from game_session.dependencies import repo as default_repo
from game_session.models import DeclareReactionResponse, ResolveReactionResponse
from runefoble_events.events import CombatTurnPausedForReactionEvent, ReactionResolvedEvent
from runefoble_platform.event_sourcing import AggregateRepository

logger = logging.getLogger(__name__)


class ReactionInterruptCoordinator:
    """Coordinates pausing and resuming active combat turn timers during reaction windows."""

    def __init__(self, repo: AggregateRepository[GameSessionAggregate] | None = None) -> None:
        self._repo = repo or default_repo

    async def declare_reaction(
        self,
        session_id: UUID,
        reacting_combatant_id: str,
        trigger_phrase: str,
        reaction_type: str = "reaction",
        reacting_combatant_name: str = "",
        timeout_seconds: float = 15.0,
        target_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> DeclareReactionResponse:
        """Halt active combat turn and initiate a reaction window within 500ms."""
        session = await self._repo.load(session_id)
        if not session.state.in_combat:
            raise ValueError("Cannot declare a combat reaction: encounter is not in combat")

        reaction_id = str(uuid4())
        details_payload = dict(details or {})
        if target_id:
            details_payload["target_id"] = target_id

        session.declare_reaction(
            reaction_id=reaction_id,
            reacting_combatant_id=reacting_combatant_id,
            reacting_combatant_name=reacting_combatant_name,
            trigger_phrase=trigger_phrase,
            reaction_type=reaction_type,
            timeout_seconds=timeout_seconds,
            details=details_payload,
        )
        await self._repo.save(session)

        event = CombatTurnPausedForReactionEvent(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=session.state.campaign_id,
            reaction_id=reaction_id,
            reacting_combatant_id=reacting_combatant_id,
            reacting_combatant_name=reacting_combatant_name,
            trigger_phrase=trigger_phrase,
            reaction_type=reaction_type,
            paused_turn_combatant_id=session.state.combat_active_id or "",
            timeout_seconds=timeout_seconds,
            details=details_payload,
        )
        if bus := get_event_bus():
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_SESSION, event)

        return DeclareReactionResponse(
            session_id=session_id,
            reaction_id=reaction_id,
            status="paused",
            reacting_combatant_id=reacting_combatant_id,
            reacting_combatant_name=reacting_combatant_name,
            paused_turn_combatant_id=session.state.combat_active_id,
            reaction_type=reaction_type,
            timeout_seconds=timeout_seconds,
            message="Combat turn paused for reaction window",
        )

    async def resolve_reaction(
        self,
        session_id: UUID,
        reaction_id: str,
        action_taken: str = "executed",
        details: dict[str, Any] | None = None,
    ) -> ResolveReactionResponse:
        """Resolve or dismiss declared reaction, resuming active turn resolution."""
        session = await self._repo.load(session_id)
        if not session.state.turn_paused_for_reaction:
            raise ValueError(
                f"No active reaction interrupt currently paused on session {session_id}"
            )

        active_react = session.state.active_reaction or {}
        active_reaction_id = active_react.get("reaction_id")
        if active_reaction_id and active_reaction_id != reaction_id:
            raise ValueError(
                f"Active reaction ID mismatch: expected {active_reaction_id}, got {reaction_id}"
            )

        session.resolve_reaction(
            reaction_id=reaction_id,
            action_taken=action_taken,
            resumed=True,
            details=details or {},
        )
        await self._repo.save(session)

        event = ReactionResolvedEvent(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=session.state.campaign_id,
            reaction_id=reaction_id,
            reacting_combatant_id=active_react.get("reacting_combatant_id", ""),
            action_taken=action_taken,
            resumed=True,
            details=details or {},
        )
        if bus := get_event_bus():
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_SESSION, event)

        return ResolveReactionResponse(
            session_id=session_id,
            reaction_id=reaction_id,
            status="resolved",
            resumed=True,
            action_taken=action_taken,
            message="Reaction resolved and turn resumed",
            session_state=session.state,
        )
