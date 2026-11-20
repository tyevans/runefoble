"""DM whisper log service: list, record, and generate private narrative suggestions (TASK-0568).

A generated whisper comes only from the narration port (TASK-0949). The service writes no
whisper text of its own, and an empty log stays empty.

Whispers live in the ``WhisperAggregate`` for each session and recipient. The service runs
the commands over that aggregate. Clients read whispers through the whisper routes.

After each save the service publishes the new ``WhisperRecorded`` events on
``runefoble.events.watcher`` with ``publish_or_fail`` (TASK-0927). The gateway sends each one
as a ``dm_whisper`` frame to the DM session sockets only. A failed publish raises
``DomainEventPublishError``, which the app maps to 503.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from eventsource.application.aggregates.repository import AggregateRepository
from runefoble_platform.aggregate_loading import load_if_exists, load_or_create
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_publish import publish_aggregate_events
from the_watcher.copilot_state.whispers import WhisperAggregate, whisper_log_id
from the_watcher.dependencies import STREAM_WATCHER
from the_watcher.models import DMGuidanceRequest, WhisperGenerateRequest, WhisperSuggestion
from the_watcher.ports import SceneNarrator

logger = logging.getLogger("runefoble.the_watcher.whispers")

NARRATION_WHISPER_TYPE = "narration"


def _new_whisper_log(aggregate_id: Any) -> WhisperAggregate:
    return WhisperAggregate(aggregate_id=aggregate_id)


class WhisperService:
    """Runs DM whisper commands over the whisper log aggregates."""

    def __init__(
        self,
        *,
        whisper_repo: AggregateRepository[WhisperAggregate],
        event_bus: EventBusProvider,
    ) -> None:
        self._whisper_repo = whisper_repo
        self._event_bus = event_bus

    async def _save_and_publish(self, log: WhisperAggregate) -> None:
        """Save the log, then publish the events of this save. Raise when a publish fails."""
        events = list(log.uncommitted_events)
        await self._whisper_repo.save(log)
        await publish_aggregate_events(self._event_bus.get(), STREAM_WATCHER, events)

    async def list_whispers(
        self,
        session_id: str,
        campaign_id: str | None = None,
        page: int = 1,
        limit: int = 20,
        whisper_type: str | None = None,
    ) -> tuple[list[WhisperSuggestion], int]:
        """Return paginated whispers for a session. An empty log gives an empty list."""
        log = await load_if_exists(self._whisper_repo, whisper_log_id(session_id))
        matches = list(log.state.whispers) if log is not None else []
        if campaign_id:
            matches = [w for w in matches if not w.campaign_id or w.campaign_id == campaign_id]
        if whisper_type:
            matches = [w for w in matches if w.whisper_type == whisper_type]

        total = len(matches)
        start = max(0, (page - 1) * limit)
        return matches[start : start + limit], total

    async def add_whisper(self, whisper: WhisperSuggestion) -> WhisperSuggestion:
        """Record a private narrative suggestion for the DM."""
        if not whisper.timestamp:
            whisper.timestamp = datetime.now(UTC).isoformat()
        if not whisper.whisper_id:
            whisper.whisper_id = f"whisp-{uuid4().hex[:8]}"
        repo = self._whisper_repo
        log = await load_or_create(repo, whisper_log_id(whisper.session_id), _new_whisper_log)
        log.record(whisper)
        await self._save_and_publish(log)
        return whisper

    async def generate_whispers(
        self,
        narrator: SceneNarrator,
        req: WhisperGenerateRequest,
    ) -> list[WhisperSuggestion]:
        """Ask the narration port for a whisper, then record it.

        The port raises `EngineUnavailableError` (HTTP 503) when it has no engine or the engine
        fails. Then no whisper is recorded and no text is substituted (ADR-0015, ADR-0022).
        """
        result = await narrator.narrate(_guidance_request(req))
        whisper = WhisperSuggestion(
            whisper_id=f"whisp-{uuid4().hex[:8]}",
            session_id=req.session_id,
            campaign_id=req.campaign_id,
            whisper_type=NARRATION_WHISPER_TYPE,
            content=result.narrative,
            timestamp=datetime.now(UTC).isoformat(),
            metadata={
                "source": result.source,
                "sensory_details": result.sensory_details,
                "suggested_dm_prompts": result.suggested_dm_prompts,
                "tension_level": result.tension_level,
            },
        )
        repo = self._whisper_repo
        log = await load_or_create(repo, whisper_log_id(req.session_id), _new_whisper_log)
        log.record(whisper)
        await self._save_and_publish(log)
        return [whisper]


def _guidance_request(req: WhisperGenerateRequest) -> DMGuidanceRequest:
    """Build the narration request from the scene state that the DM sends."""
    scene = req.scene_context or "the current scene"
    return DMGuidanceRequest(
        session_id=req.session_id,
        campaign_id=req.campaign_id,
        prompt=(
            f"Write one private whisper for the DM only. Scene: {scene}. "
            f"Threat level: {req.threat_level}. Give a hint, a monster tactic or a hidden detail."
        ),
        scene_environment=req.location_type,
        tone=req.tone,
    )
