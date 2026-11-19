"""DM Co-Pilot engine for the pre-execution veto window (TASK-0568).

State lives in ``PendingActionAggregate``. This engine runs the commands and owns only the
expiry timers, which are process handles and not state. A restarted process re-arms the timers
from the deadlines in the event store.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from typing import Any, cast
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from eventsource.application.aggregates.repository import AggregateRepository
from opentelemetry import metrics
from runefoble_auth.errors import AuthzUnavailableError
from runefoble_events.events import (
    PENDING_ACTIONS_AGGREGATE,
)
from runefoble_platform.aggregate_loading import (
    STORE_UNAVAILABLE_ERRORS,
    load_if_exists,
    load_or_create,
)
from runefoble_platform.event_sourcing import FullEventStore
from the_watcher.copilot_state.errors import PendingActionNotFoundError
from the_watcher.copilot_state.pending_actions import OPEN_STATUSES, PendingActionAggregate
from the_watcher.models import PendingAction, ProposeActionRequest

logger = logging.getLogger("runefoble.the_watcher.copilot")

RETRY_SECONDS = 1.0
MAX_EXPIRY_RETRIES = 5
DEFAULT_PAUSE_WINDOW_MS = 2000

# Only an outage of the event store or of SpiceDB is retried. Other errors are defects.
RETRYABLE_EXPIRY_ERRORS: tuple[type[BaseException], ...] = (
    *STORE_UNAVAILABLE_ERRORS,
    AuthzUnavailableError,
)

_meter = metrics.get_meter("runefoble.the_watcher")
_expiry_failures = _meter.create_counter(
    "runefoble.watcher.pending_action.expiry_failures",
    description="Pending action expiry timers that stopped after the retry limit",
)

Callback = Callable[[], Coroutine[Any, Any, None]]


def pending_action_key(session_id: str) -> UUID:
    """Return the aggregate id of one session's pending actions."""
    return uuid5(NAMESPACE_DNS, f"pending-actions:{session_id}")


def _new_pending_aggregate(aggregate_id: UUID) -> PendingActionAggregate:
    return PendingActionAggregate(aggregate_id=aggregate_id)


class CopilotEngine:
    """Runs DM whisper and pending action commands over the copilot aggregates."""

    def __init__(
        self,
        *,
        pending_repo: AggregateRepository[PendingActionAggregate],
        retry_seconds: float = RETRY_SECONDS,
        max_retries: int = MAX_EXPIRY_RETRIES,
    ) -> None:
        self._pending_repo = pending_repo
        self._retry_seconds = retry_seconds
        self._max_retries = max_retries
        self._timer_tasks: dict[str, asyncio.Task[None]] = {}
        self._callbacks: dict[str, Callback] = {}

    def shutdown(self) -> None:
        """Cancel every expiry timer. Stored deadlines remain for the next start-up."""
        for task in self._timer_tasks.values():
            _cancel(task)
        self._timer_tasks.clear()
        self._callbacks.clear()

    # -------------------------------------------------------------------------
    # Pre-execution veto window
    # -------------------------------------------------------------------------

    async def propose_action(
        self,
        req: ProposeActionRequest,
        on_execute: Callback | None = None,
    ) -> PendingAction:
        """Open a pause window for an AI proposed mutation. Expiry commits it if not decided."""
        pause_window_ms = (
            req.pause_window_ms if req.pause_window_ms > 0 else DEFAULT_PAUSE_WINDOW_MS
        )
        now = time.time()
        action = PendingAction(
            action_id=f"act-{uuid4().hex[:8]}",
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
            expires_at=now + pause_window_ms / 1000.0,
        )

        repo = self._pending_repo
        agg = await load_or_create(repo, pending_action_key(req.session_id), _new_pending_aggregate)
        agg.propose(action)
        await repo.save(agg)

        if on_execute is not None:
            self._callbacks[action.action_id] = on_execute
        self._arm_timer(action.session_id, action.action_id, action.expires_at)

        logger.info(
            "Proposed action %s (%s) with %dms pause window",
            action.action_id,
            action.action_type,
            pause_window_ms,
        )
        return action

    async def veto_action(
        self, session_id: str, action_id: str, vetoed_by: str, reason: str = ""
    ) -> PendingAction:
        """Cancel a pending action before it mutates state."""
        repo = self._pending_repo
        agg = await _load_session(repo, session_id)
        agg.veto(action_id, vetoed_by=vetoed_by, reason=reason)
        action = agg.find(action_id)
        await repo.save(agg)
        self._release(action_id)
        logger.info("Action %s vetoed by %s: %s", action_id, vetoed_by, reason)
        return action

    async def approve_action(
        self, session_id: str, action_id: str, approved_by: str
    ) -> PendingAction:
        """Commit a pending action now, then run its callback."""
        repo = self._pending_repo
        agg = await _load_session(repo, session_id)
        agg.approve(action_id, approved_by=approved_by)
        action = agg.find(action_id)
        await repo.save(agg)
        self._release(action_id)
        logger.info("Action %s immediately approved by %s", action_id, approved_by)
        return await self._run_callback(action_id, action)

    async def modify_action(
        self,
        session_id: str,
        action_id: str,
        modified_by: str,
        description: str | None = None,
        target: str | None = None,
        parameters: dict[str, Any] | None = None,
        auto_approve: bool = True,
    ) -> PendingAction:
        """Change a pending action. With auto_approve, also commit it in the same save."""
        repo = self._pending_repo
        agg = await _load_session(repo, session_id)
        agg.modify(
            action_id,
            modified_by=modified_by,
            description=description,
            target=target,
            parameters=parameters,
        )
        if auto_approve:
            agg.approve(action_id, approved_by=modified_by)
        await repo.save(agg)

        final = agg.find(action_id)
        if not auto_approve:
            return final
        self._release(action_id)
        return await self._run_callback(action_id, final)

    async def list_pending_actions(
        self, session_id: str, campaign_id: str | None = None
    ) -> list[PendingAction]:
        """Return every action the session holds, with its current status."""
        agg = await load_if_exists(self._pending_repo, pending_action_key(session_id))
        if agg is None:
            return []
        actions = list(agg.state.actions.values())
        if campaign_id:
            actions = [a for a in actions if not a.campaign_id or a.campaign_id == campaign_id]
        return actions

    # -------------------------------------------------------------------------
    # Expiry timers
    # -------------------------------------------------------------------------

    async def rearm_open_actions(self) -> int:
        """Start a timer for every open action in the store. Return how many were armed."""
        repo = self._pending_repo
        store = cast(FullEventStore, repo.event_store)
        aggregate_ids: set[UUID] = set()
        async for envelope in store.read_category(PENDING_ACTIONS_AGGREGATE):
            aggregate_ids.add(envelope.stream_id.aggregate_id)

        armed = 0
        for aggregate_id in aggregate_ids:
            agg = await repo.load(aggregate_id)
            for action in agg.state.actions.values():
                if action.status in OPEN_STATUSES:
                    self._arm_timer(action.session_id, action.action_id, action.expires_at)
                    armed += 1
        logger.info("Re-armed %d open pending action timers", armed)
        return armed

    def _arm_timer(self, session_id: str, action_id: str, expires_at: float) -> None:
        self._release(action_id)
        self._schedule(session_id, action_id, expires_at)

    def _schedule(self, session_id: str, action_id: str, due_at: float, attempt: int = 0) -> None:
        delay = max(0.0, due_at - time.time())
        self._timer_tasks[action_id] = asyncio.create_task(
            self._run_timer(session_id, action_id, delay, attempt)
        )

    async def _run_timer(self, session_id: str, action_id: str, delay: float, attempt: int) -> None:
        """Expire the action after `delay`. Retry a store or SpiceDB outage up to the limit.

        After the limit the timer stops, and the action stays open in the store. A restart
        re-arms it. Any other error propagates and ends the timer task.
        """
        await asyncio.sleep(delay)
        try:
            await self._expire(session_id, action_id)
        except RETRYABLE_EXPIRY_ERRORS:
            if attempt >= self._max_retries:
                self._timer_tasks.pop(action_id, None)
                _expiry_failures.add(1)
                logger.error(
                    "Expiry of action %s failed %d times; the timer stopped",
                    action_id,
                    attempt + 1,
                    exc_info=True,
                )
                return
            logger.warning(
                "Expiry of action %s failed; retry %d of %d in %.2fs",
                action_id,
                attempt + 1,
                self._max_retries,
                self._retry_seconds,
                exc_info=True,
            )
            self._schedule(session_id, action_id, time.time() + self._retry_seconds, attempt + 1)

    async def _expire(self, session_id: str, action_id: str) -> None:
        repo = self._pending_repo
        agg = await load_if_exists(repo, pending_action_key(session_id))
        if agg is None:
            return
        action = agg.state.actions.get(action_id)
        if action is None or action.status not in OPEN_STATUSES:
            self._timer_tasks.pop(action_id, None)
            return

        agg.expire(action_id)
        expired = agg.find(action_id)
        await repo.save(agg)
        self._timer_tasks.pop(action_id, None)
        logger.info("Pending action %s auto-executed after timeout", action_id)
        await self._run_callback(action_id, expired)

    def _release(self, action_id: str) -> None:
        task = self._timer_tasks.pop(action_id, None)
        if task is not None:
            _cancel(task)
        self._callbacks.pop(action_id, None)

    async def _run_callback(self, action_id: str, action: PendingAction) -> PendingAction:
        """Run the in-process execute hook, if any. A failure is logged and returned."""
        callback = self._callbacks.pop(action_id, None)
        if callback is None:
            return action
        try:
            await callback()
        except Exception as exc:
            logger.exception("Callback for action %s failed", action_id)
            return action.model_copy(update={"execution_error": str(exc) or type(exc).__name__})
        return action


async def _load_session(
    repo: AggregateRepository[PendingActionAggregate], session_id: str
) -> PendingActionAggregate:
    """Load the session's aggregate. Raise PendingActionNotFoundError when it has none."""
    agg = await load_if_exists(repo, pending_action_key(session_id))
    if agg is None:
        raise PendingActionNotFoundError("No pending action exists in this session.")
    return agg


def _cancel(task: asyncio.Task[None]) -> None:
    """Cancel a timer task unless it is finished or its event loop has closed."""
    if task.done() or task.get_loop().is_closed():
        return
    task.cancel()


__all__ = [
    "CopilotEngine",
    "pending_action_key",
]
