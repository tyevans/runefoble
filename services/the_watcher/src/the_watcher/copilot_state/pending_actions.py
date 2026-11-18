"""Event-sourced pending DM action windows, one aggregate per game session (TASK-0568).

Each proposed AI action stays open until a DM decision or until its pause window
expires. The deadline is stored in the proposal event, so a restarted service can
re-arm the expiry timer.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.watcher_events.copilot_state import (
    PENDING_ACTIONS_AGGREGATE,
    PendingActionApproved,
    PendingActionExpired,
    PendingActionModified,
    PendingActionProposed,
    PendingActionVetoed,
)
from the_watcher.copilot_state.errors import PendingActionNotFoundError, PendingActionStateError
from the_watcher.models import PendingAction

OPEN_STATUSES = frozenset({"pending", "modified"})


class PendingActionsState(BaseModel):
    """All actions proposed for one game session, keyed by action id."""

    session_id: str = ""
    actions: dict[str, PendingAction] = Field(default_factory=dict)


class PendingActionAggregate(DeclarativeAggregate[PendingActionsState]):
    """Owns the pending action windows of one game session."""

    aggregate_type = PENDING_ACTIONS_AGGREGATE

    def __init__(self, aggregate_id: UUID | None = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = PendingActionsState()

    @handles(PendingActionProposed)
    def _on_proposed(self, event: PendingActionProposed) -> None:
        action = PendingAction.model_validate(event.action)
        self.state.session_id = action.session_id
        self.state.actions[action.action_id] = action

    @handles(PendingActionVetoed)
    def _on_vetoed(self, event: PendingActionVetoed) -> None:
        action = self.state.actions[event.action_id]
        action.status = "vetoed"
        action.vetoed_by = event.vetoed_by
        action.veto_reason = event.reason

    @handles(PendingActionApproved)
    def _on_approved(self, event: PendingActionApproved) -> None:
        action = self.state.actions[event.action_id]
        action.status = "approved"
        action.approved_by = event.approved_by

    @handles(PendingActionModified)
    def _on_modified(self, event: PendingActionModified) -> None:
        action = self.state.actions[event.action_id]
        action.description = event.description
        action.target = event.target
        action.parameters = dict(event.parameters)
        action.modified_by = event.modified_by
        action.status = "modified"

    @handles(PendingActionExpired)
    def _on_expired(self, event: PendingActionExpired) -> None:
        self.state.actions[event.action_id].status = "executed"

    def propose(self, action: PendingAction) -> None:
        """Open a new pause window for an AI proposed action."""
        self.create_event(PendingActionProposed, action=action.model_dump(mode="json"))

    def veto(self, action_id: str, vetoed_by: str, reason: str) -> None:
        """Cancel an open action before it changes game state."""
        self._require_open(action_id)
        self.create_event(
            PendingActionVetoed, action_id=action_id, vetoed_by=vetoed_by, reason=reason
        )

    def approve(self, action_id: str, approved_by: str) -> None:
        """Commit an open action now, without waiting for the pause window."""
        self._require_open(action_id)
        self.create_event(PendingActionApproved, action_id=action_id, approved_by=approved_by)

    def modify(
        self,
        action_id: str,
        modified_by: str,
        description: str | None = None,
        target: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """Change an open action. Parameters merge into the stored parameters."""
        current = self._require_open(action_id)
        self.create_event(
            PendingActionModified,
            action_id=action_id,
            modified_by=modified_by,
            description=current.description if description is None else description,
            target=current.target if target is None else target,
            parameters={**current.parameters, **(parameters or {})},
        )

    def expire(self, action_id: str) -> None:
        """Close an open action whose pause window elapsed with no DM decision."""
        self._require_open(action_id)
        self.create_event(PendingActionExpired, action_id=action_id)

    def find(self, action_id: str) -> PendingAction:
        """Return the stored action, or raise when this session holds no such action."""
        action = self.state.actions.get(action_id)
        if action is None:
            raise PendingActionNotFoundError(f"Pending action '{action_id}' was not found.")
        return action

    def _require_open(self, action_id: str) -> PendingAction:
        action = self.find(action_id)
        if action.status not in OPEN_STATUSES:
            raise PendingActionStateError(
                f"Pending action '{action_id}' is already {action.status}."
            )
        return action
