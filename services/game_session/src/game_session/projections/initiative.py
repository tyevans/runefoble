"""Turn order and initiative snapshot projection handlers."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from game_session.projections.models import CombatantInitiativeModel, InitiativeReadModel
from runefoble_events.events import (
    CombatEncounterEnded,
    CombatEncounterStarted,
    InitiativeRolled,
    InitiativeTurnAdvanced,
)
from runefoble_platform.models import utc_now

logger = logging.getLogger("runefoble.game_session.projections.initiative")


def _sort_combatants(combatants: list[CombatantInitiativeModel]) -> list[CombatantInitiativeModel]:
    return sorted(
        combatants,
        key=lambda c: (c.initiative_score, 1 if not c.is_npc else 0, c.combatant_name),
        reverse=True,
    )


class InitiativeProjection:
    """Projects combat initiative, rounds, and turn order from stream events."""

    def __init__(self) -> None:
        self.initiatives: dict[str, InitiativeReadModel] = {}

    def _extract_session_id(self, event: Any) -> str:
        if isinstance(event, dict):
            return str(event.get("session_id") or event.get("aggregate_id") or "default")
        return str(
            getattr(event, "session_id", None) or getattr(event, "aggregate_id", None) or "default"
        )

    def apply_event(self, event: Any) -> None:
        """Apply combat and initiative events to update initiative snapshots."""
        session_id = self._extract_session_id(event)
        model = self.initiatives.setdefault(session_id, InitiativeReadModel(session_id=session_id))

        if isinstance(event, CombatEncounterStarted):
            model.in_combat = True
            model.combat_round = getattr(event, "round_number", 1)
        elif isinstance(event, InitiativeRolled):
            self._apply_roll(
                model,
                event.combatant_id,
                event.combatant_name,
                event.initiative_score,
                getattr(event, "is_npc", False),
            )
        elif isinstance(event, InitiativeTurnAdvanced):
            model.combat_round = event.round_number
            model.combat_active_id = event.active_combatant_id
            model.turn_seconds_remaining = getattr(event, "turn_seconds_remaining", 60)
        elif isinstance(event, CombatEncounterEnded):
            model.in_combat = False
            model.combat_active_id = None
        elif isinstance(event, dict):
            self._apply_dict_event(model, event)

        model.last_updated_at = utc_now().isoformat()

    def _apply_roll(
        self, model: InitiativeReadModel, cid: str, name: str, score: float | int, is_npc: bool
    ) -> None:
        entries = [c for c in model.initiative_order if c.combatant_id != cid]
        entries.append(
            CombatantInitiativeModel(
                combatant_id=cid, combatant_name=name, initiative_score=score, is_npc=is_npc
            )
        )
        model.initiative_order = _sort_combatants(entries)
        if not model.combat_active_id and model.initiative_order:
            model.combat_active_id = model.initiative_order[0].combatant_id

    def _apply_dict_event(self, model: InitiativeReadModel, event: dict[str, Any]) -> None:
        etype = event.get("event_type") or event.get("type") or ""
        if "CombatEncounterStarted" in etype or "combat.started" in etype:
            model.in_combat = True
            model.combat_round = int(event.get("round_number", 1))
        elif "InitiativeRolled" in etype or "initiative.rolled" in etype:
            self._apply_roll(
                model,
                str(event.get("combatant_id", "")),
                str(event.get("combatant_name", "Combatant")),
                float(event.get("initiative_score", 0)),
                bool(event.get("is_npc", False)),
            )
        elif "InitiativeTurnAdvanced" in etype or "initiative.turn_advanced" in etype:
            model.combat_round = int(event.get("round_number", model.combat_round))
            model.combat_active_id = str(event.get("active_combatant_id", ""))
            model.turn_seconds_remaining = int(event.get("turn_seconds_remaining", 60))
        elif "CombatEncounterEnded" in etype or "combat.ended" in etype:
            model.in_combat = False
            model.combat_active_id = None

    def get_initiative(self, session_id: str | UUID) -> InitiativeReadModel | None:
        return self.initiatives.get(str(session_id))

    def get_active_combatant(self, session_id: str | UUID) -> CombatantInitiativeModel | None:
        init = self.get_initiative(session_id)
        if not init or not init.combat_active_id:
            return None
        for c in init.initiative_order:
            if c.combatant_id == init.combat_active_id:
                return c
        return None

    def get_initiative_order(self, session_id: str | UUID) -> list[CombatantInitiativeModel]:
        init = self.get_initiative(session_id)
        return init.initiative_order if init else []


__all__ = ["InitiativeProjection"]
