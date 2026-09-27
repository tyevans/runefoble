"""Ready-action conditional registry and combat trigger evaluator."""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID, uuid4

from game_session.aggregate import GameSessionAggregate
from game_session.dependencies import STREAM_SESSION, get_event_bus
from game_session.dependencies import repo as default_repo
from game_session.models import ReadyActionResponse
from runefoble_events.events import ReadyActionRegisteredEvent, ReadyActionTriggeredEvent
from runefoble_platform.event_sourcing import AggregateRepository


class ReadyActionRegistry:
    """Registry evaluating conditional combat triggers against incoming domain events."""

    def __init__(self, repo: AggregateRepository[GameSessionAggregate] | None = None) -> None:
        self._repo = repo or default_repo

    async def register_ready_action(
        self,
        session_id: UUID,
        combatant_id: str,
        combatant_name: str,
        trigger_type: str,
        trigger_condition: str,
        readied_action: str,
        target_id: str | None = None,
        range_cells: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> ReadyActionResponse:
        """Register a conditional ready-action trigger for a combatant."""
        session = await self._repo.load(session_id)
        if not session.state.in_combat:
            raise ValueError("Cannot register ready-action: encounter is not in combat")

        r_id = str(uuid4())
        session.register_ready_action(
            ready_action_id=r_id,
            combatant_id=combatant_id,
            combatant_name=combatant_name,
            trigger_type=trigger_type,
            trigger_condition=trigger_condition,
            target_id=target_id,
            range_cells=range_cells,
            readied_action=readied_action,
            details=details or {},
        )
        await self._repo.save(session)

        event = ReadyActionRegisteredEvent(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=session.state.campaign_id,
            ready_action_id=r_id,
            combatant_id=combatant_id,
            combatant_name=combatant_name,
            trigger_type=trigger_type,
            trigger_condition=trigger_condition,
            target_id=target_id,
            range_cells=range_cells,
            readied_action=readied_action,
            details=details or {},
        )
        if bus := get_event_bus():
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_SESSION, event)

        return ReadyActionResponse(
            session_id=session_id,
            ready_action_id=r_id,
            combatant_id=combatant_id,
            combatant_name=combatant_name,
            trigger_type=trigger_type,
            trigger_condition=trigger_condition,
            readied_action=readied_action,
            status="registered",
            message="Ready-action trigger registered successfully",
        )

    def _matches(self, act: dict[str, Any], event_type: str, data: dict[str, Any]) -> bool:
        t_type = act.get("trigger_type", "").lower()
        el = event_type.lower()
        target = act.get("target_id")
        ent_id = data.get("token_id") or data.get("combatant_id") or data.get("actor_id") or ""
        if target and ent_id and ent_id != target:
            return False
        if t_type in ("spatial", "enemy_enters_range", "cell_range", "movement"):
            return any(k in el for k in ("token_moved", "move")) and ent_id != act.get(
                "combatant_id"
            )
        if t_type in ("spell_cast", "cast_spell"):
            return any(k in el for k in ("spell_cast", "cast")) and ent_id != act.get(
                "combatant_id"
            )
        if t_type in ("attack", "melee_strike"):
            return any(
                k in el for k in ("attack", "strike", "action_executed")
            ) and ent_id != act.get("combatant_id")
        cond = act.get("trigger_condition", "").lower()
        return bool(cond and any(w in cond for w in el.split(".")))

    async def evaluate_triggers(
        self, session_id: UUID, event_type: str, event_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Evaluate combat/board events against ready-actions, triggering matched conditions."""
        session = await self._repo.load(session_id)
        if not session.state.in_combat or not session.state.ready_actions:
            return []

        triggered: list[dict[str, Any]] = []
        ent_id = str(event_data.get("token_id") or event_data.get("combatant_id") or "")
        bus = get_event_bus()

        for act in list(session.state.ready_actions):
            if not self._matches(act, event_type, event_data):
                continue
            r_id = act["ready_action_id"]
            session.trigger_ready_action(
                ready_action_id=r_id,
                combatant_id=act["combatant_id"],
                combatant_name=act.get("combatant_name", ""),
                triggering_entity_id=ent_id,
                trigger_type=act.get("trigger_type", ""),
                readied_action=act.get("readied_action", ""),
                details=event_data,
            )
            triggered.append(
                {
                    "ready_action_id": r_id,
                    "combatant_id": act["combatant_id"],
                    "readied_action": act.get("readied_action", ""),
                    "triggering_entity_id": ent_id,
                }
            )
            if bus:
                ev = ReadyActionTriggeredEvent(
                    aggregate_id=session_id,
                    session_id=session_id,
                    campaign_id=session.state.campaign_id,
                    ready_action_id=r_id,
                    combatant_id=act["combatant_id"],
                    combatant_name=act.get("combatant_name", ""),
                    triggering_entity_id=ent_id,
                    trigger_type=act.get("trigger_type", ""),
                    readied_action=act.get("readied_action", ""),
                    details=event_data,
                )
                with contextlib.suppress(Exception):
                    await bus.publish_event(STREAM_SESSION, ev)

        if triggered:
            await self._repo.save(session)
        return triggered
