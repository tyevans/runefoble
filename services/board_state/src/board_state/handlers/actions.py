"""Tactical radial token actions handler mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from runefoble_events import events as ev

if TYPE_CHECKING:
    from board_state.models import BoardState


class ActionsHandlerMixin:
    """Mixin providing tactical token action execution (Dodge, Dash, Melee, Disengage, Cast)."""

    _state: BoardState | None
    state: BoardState
    aggregate_id: Any
    create_event: Any

    def _require_token(self, token_id: str) -> str:
        tid = str(token_id)
        if tid not in self.state.tokens:
            raise ValueError(f"Token '{token_id}' not found on grid")
        return tid

    def execute_token_action(
        self,
        token_id: str,
        action: str,
        target_token_id: str | None = None,
        target_token_ids: list[str] | None = None,
        details: dict[str, Any] | None = None,
        initiated_by: str = "player",
    ) -> None:
        """Execute a tactical token action (Dodge, Dash, Melee/Attack, Disengage, Cast)."""
        tid = self._require_token(token_id)
        targets = list(target_token_ids or [])
        if target_token_id and target_token_id not in targets:
            targets.append(target_token_id)

        self.create_event(
            ev.TokenActionExecuted,
            session_id=str(self.state.session_id),
            board_id=str(self.aggregate_id),
            token_id=tid,
            action=action.lower(),
            target_token_id=target_token_id,
            target_token_ids=targets,
            details=details or {},
            initiated_by=initiated_by,
        )

    @handles(ev.TokenActionExecuted)
    def _on_token_action_executed(self, e: ev.TokenActionExecuted) -> None:
        self._state = self.state.with_token_action(str(e.token_id), e.action)
