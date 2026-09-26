"""DM Co-Pilot engine: private narrative whisper streams and pre-execution action veto interceptor."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from the_watcher.models import (
    PendingAction,
    ProposeActionRequest,
    WhisperSuggestion,
)

logger = logging.getLogger("runefoble.the_watcher.copilot")


class CopilotEngine:
    """Manages DM whisper suggestions and pending AI action veto windows."""

    def __init__(self) -> None:
        self._whispers: list[WhisperSuggestion] = []
        self._pending_actions: dict[str, PendingAction] = {}
        self._timer_tasks: dict[str, asyncio.Task[None]] = {}
        self._callbacks: dict[str, Callable[[], Coroutine[Any, Any, None]]] = {}

    def clear(self) -> None:
        """Reset all in-memory whisper suggestions, pending actions, and active timers."""
        for task in self._timer_tasks.values():
            if not task.done():
                task.cancel()
        self._timer_tasks.clear()
        self._callbacks.clear()
        self._pending_actions.clear()
        self._whispers.clear()

    # -------------------------------------------------------------------------
    # Whisper Suggestions
    # -------------------------------------------------------------------------

    def add_whisper(self, whisper: WhisperSuggestion) -> WhisperSuggestion:
        """Record a private narrative suggestion for the DM."""
        if not whisper.timestamp:
            whisper.timestamp = datetime.now(UTC).isoformat()
        if not whisper.whisper_id:
            whisper.whisper_id = f"whisp-{uuid4().hex[:8]}"
        self._whispers.append(whisper)
        return whisper

    def generate_default_whispers(
        self,
        session_id: str,
        campaign_id: str = "",
        scene_context: str = "",
        location_type: str = "dungeon",
        threat_level: str = "medium",
    ) -> list[WhisperSuggestion]:
        """Generate atmospheric hints, monster tactics, and passive perception cues."""
        now = datetime.now(UTC).isoformat()
        defaults = [
            WhisperSuggestion(
                whisper_id=f"whisp-{uuid4().hex[:8]}",
                session_id=session_id,
                campaign_id=campaign_id,
                whisper_type="atmospheric_hint",
                content=(
                    f"In this {location_type}, damp cold clings to stone. "
                    "The smell of ozone foreshadows ancient necrotic wards."
                ),
                recipient_role="dungeon_master",
                timestamp=now,
                metadata={"scene_context": scene_context, "location_type": location_type},
            ),
            WhisperSuggestion(
                whisper_id=f"whisp-{uuid4().hex[:8]}",
                session_id=session_id,
                campaign_id=campaign_id,
                whisper_type="monster_tactics",
                content=(
                    f"Threat level is {threat_level}. Frontline creatures attempt to disengage "
                    "and flank isolated squishy spellcasters when provoked."
                ),
                recipient_role="dungeon_master",
                timestamp=now,
                metadata={"threat_level": threat_level},
            ),
            WhisperSuggestion(
                whisper_id=f"whisp-{uuid4().hex[:8]}",
                session_id=session_id,
                campaign_id=campaign_id,
                whisper_type="passive_perception",
                content=(
                    "Characters with Passive Perception >= 14 notice the hairline trigger "
                    "of a floorplate trap 10 feet ahead."
                ),
                recipient_role="dungeon_master",
                timestamp=now,
                metadata={"dc": 14, "trap_type": "floorplate"},
            ),
        ]
        for w in defaults:
            self.add_whisper(w)
        return defaults

    def list_whispers(
        self,
        session_id: str,
        campaign_id: str | None = None,
        page: int = 1,
        limit: int = 20,
        whisper_type: str | None = None,
    ) -> tuple[list[WhisperSuggestion], int]:
        """Return paginated whispers for a given session and campaign."""
        matches = [w for w in self._whispers if w.session_id == session_id]
        if campaign_id:
            matches = [w for w in matches if not w.campaign_id or w.campaign_id == campaign_id]
        if whisper_type:
            matches = [w for w in matches if w.whisper_type == whisper_type]

        if not matches:
            # Seed initial suggestions if empty for this session
            matches = self.generate_default_whispers(session_id, campaign_id or "")
            if whisper_type:
                matches = [w for w in matches if w.whisper_type == whisper_type]

        total = len(matches)
        start = max(0, (page - 1) * limit)
        end = start + limit
        return matches[start:end], total

    # -------------------------------------------------------------------------
    # Pre-Execution Veto Interceptor
    # -------------------------------------------------------------------------

    def propose_action(
        self,
        req: ProposeActionRequest,
        on_execute: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> PendingAction:
        """Register an AI proposed game mutation with a pre-execution pause window."""
        action_id = f"act-{uuid4().hex[:8]}"
        now = time.time()
        pause_window_ms = req.pause_window_ms if req.pause_window_ms > 0 else 2000
        expires_at = now + (pause_window_ms / 1000.0)

        action = PendingAction(
            action_id=action_id,
            session_id=req.session_id,
            campaign_id=req.campaign_id,
            actor_name=req.actor_name,
            action_type=req.action_type,
            description=req.description,
            target=req.target,
            parameters=dict(req.parameters),
            status="pending",
            pause_window_ms=pause_window_ms,
            created_at=now,
            expires_at=expires_at,
        )

        self._pending_actions[action_id] = action
        if on_execute is not None:
            self._callbacks[action_id] = on_execute

        task = asyncio.create_task(self._auto_execute(action_id, pause_window_ms))
        self._timer_tasks[action_id] = task

        logger.info(
            "Proposed action %s (%s) with %dms pause window",
            action_id,
            action.action_type,
            pause_window_ms,
        )
        return action

    async def _auto_execute(self, action_id: str, pause_window_ms: int) -> None:
        """Automatically execute action if pause window elapses without veto."""
        try:
            await asyncio.sleep(pause_window_ms / 1000.0)
            action = self._pending_actions.get(action_id)
            if action and action.status == "pending":
                action.status = "executed"
                callback = self._callbacks.pop(action_id, None)
                if callback:
                    await callback()
                logger.info("Pending action %s auto-executed after timeout", action_id)
        except asyncio.CancelledError:
            logger.debug("Auto-execution timer cancelled for action %s", action_id)

    def veto_action(self, action_id: str, vetoed_by: str, reason: str = "") -> PendingAction:
        """Cancel a pending action before it mutates game state."""
        action = self._pending_actions.get(action_id)
        if not action:
            action = PendingAction(
                action_id=action_id,
                session_id="unknown",
                actor_name="unknown",
                action_type="unknown",
                description="Unknown action",
                status="vetoed",
            )
            self._pending_actions[action_id] = action

        task = self._timer_tasks.pop(action_id, None)
        if task and not task.done():
            task.cancel()

        self._callbacks.pop(action_id, None)
        action.status = "vetoed"
        action.vetoed_by = vetoed_by
        action.veto_reason = reason
        logger.info("Action %s vetoed by %s: %s", action_id, vetoed_by, reason)
        return action

    async def approve_action(self, action_id: str, approved_by: str) -> PendingAction:
        """Immediately commit a pending action without waiting for timeout."""
        action = self._pending_actions.get(action_id)
        if not action:
            action = PendingAction(
                action_id=action_id,
                session_id="unknown",
                actor_name="unknown",
                action_type="unknown",
                description="Unknown action",
                status="approved",
            )
            self._pending_actions[action_id] = action

        task = self._timer_tasks.pop(action_id, None)
        if task and not task.done():
            task.cancel()

        action.status = "approved"
        action.approved_by = approved_by

        callback = self._callbacks.pop(action_id, None)
        if callback:
            try:
                await callback()
            except Exception as e:
                logger.warning("Callback for approved action %s failed: %s", action_id, e)

        logger.info("Action %s immediately approved by %s", action_id, approved_by)
        return action

    async def modify_action(
        self,
        action_id: str,
        modified_by: str,
        description: str | None = None,
        target: str | None = None,
        parameters: dict[str, Any] | None = None,
        auto_approve: bool = True,
    ) -> PendingAction:
        """Modify parameters or intent of a pending action, optionally committing immediately."""
        action = self._pending_actions.get(action_id)
        if not action:
            action = PendingAction(
                action_id=action_id,
                session_id="unknown",
                actor_name="unknown",
                action_type="unknown",
                description=description or "",
                target=target,
                status="pending",
            )
            self._pending_actions[action_id] = action

        if description is not None:
            action.description = description
        if target is not None:
            action.target = target
        if parameters is not None:
            action.parameters.update(parameters)
        action.modified_by = modified_by

        if auto_approve:
            return await self.approve_action(action_id, approved_by=modified_by)

        action.status = "modified"
        return action

    def get_pending_action(self, action_id: str) -> PendingAction | None:
        """Retrieve pending action by ID."""
        return self._pending_actions.get(action_id)

    def list_pending_actions(
        self, session_id: str | None = None, campaign_id: str | None = None
    ) -> list[PendingAction]:
        """List active pending actions."""
        actions = list(self._pending_actions.values())
        if session_id:
            actions = [a for a in actions if a.session_id == session_id]
        if campaign_id:
            actions = [a for a in actions if not a.campaign_id or a.campaign_id == campaign_id]
        return actions
