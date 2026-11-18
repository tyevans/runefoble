"""DM whisper log service: list, record, and generate private narrative suggestions (TASK-0568).

Whispers live in the ``WhisperAggregate`` for each session and recipient. The service runs
the commands and publishes the public ``DMNarrativeWhispered`` events.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from eventsource.application.aggregates.repository import AggregateRepository
from runefoble_events.events import DMNarrativeWhispered
from runefoble_platform.aggregate_loading import load_or_create
from runefoble_platform.event_publish import publish_best_effort, publish_or_fail
from runefoble_platform.identifiers import opaque_aggregate_id
from the_watcher.copilot_state.whispers import WhisperAggregate, whisper_log_id
from the_watcher.models import WhisperSuggestion

logger = logging.getLogger("runefoble.the_watcher.whispers")


def _new_whisper_log(aggregate_id: Any) -> WhisperAggregate:
    return WhisperAggregate(aggregate_id=aggregate_id)


def build_default_whispers(
    session_id: str,
    campaign_id: str = "",
    scene_context: str = "",
    location_type: str = "dungeon",
    threat_level: str = "medium",
) -> list[WhisperSuggestion]:
    """Build atmospheric hints, monster tactics, and passive perception cues."""
    now = datetime.now(UTC).isoformat()
    return [
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


class WhisperService:
    """Runs DM whisper commands over the whisper log aggregates."""

    def __init__(
        self,
        *,
        bus: Callable[[], Any],
        watcher_stream: str,
        whisper_repo: Callable[[], AggregateRepository[WhisperAggregate]],
    ) -> None:
        self._bus = bus
        self._stream = watcher_stream
        self._whisper_repo = whisper_repo

    async def list_whispers(
        self,
        session_id: str,
        campaign_id: str | None = None,
        page: int = 1,
        limit: int = 20,
        whisper_type: str | None = None,
    ) -> tuple[list[WhisperSuggestion], int]:
        """Return paginated whispers for a session. Seed defaults when the log is empty."""
        repo = self._whisper_repo()
        log = await load_or_create(repo, whisper_log_id(session_id), _new_whisper_log)
        if not log.state.whispers:
            for whisper in build_default_whispers(session_id, campaign_id or ""):
                log.record(whisper)
            await repo.save(log)

        matches = list(log.state.whispers)
        if campaign_id:
            matches = [w for w in matches if not w.campaign_id or w.campaign_id == campaign_id]
        if whisper_type:
            matches = [w for w in matches if w.whisper_type == whisper_type]

        total = len(matches)
        start = max(0, (page - 1) * limit)
        return matches[start : start + limit], total

    async def add_whisper(self, whisper: WhisperSuggestion) -> WhisperSuggestion:
        """Record a private narrative suggestion for the DM. The audit event must publish."""
        if not whisper.timestamp:
            whisper.timestamp = datetime.now(UTC).isoformat()
        if not whisper.whisper_id:
            whisper.whisper_id = f"whisp-{uuid4().hex[:8]}"
        repo = self._whisper_repo()
        log = await load_or_create(repo, whisper_log_id(whisper.session_id), _new_whisper_log)
        log.record(whisper)
        await publish_or_fail(self._bus(), self._stream, _whispered_event(whisper))
        await repo.save(log)
        return whisper

    async def generate_whispers(
        self,
        session_id: str,
        campaign_id: str = "",
        scene_context: str = "",
        location_type: str = "dungeon",
        threat_level: str = "medium",
    ) -> list[WhisperSuggestion]:
        """Generate default suggestions, record them, and publish each one best effort."""
        whispers = build_default_whispers(
            session_id, campaign_id, scene_context, location_type, threat_level
        )
        repo = self._whisper_repo()
        log = await load_or_create(repo, whisper_log_id(session_id), _new_whisper_log)
        for whisper in whispers:
            log.record(whisper)
        await repo.save(log)
        for whisper in whispers:
            await publish_best_effort(self._bus(), self._stream, _whispered_event(whisper))
        return whispers


def _whispered_event(whisper: WhisperSuggestion) -> DMNarrativeWhispered:
    return DMNarrativeWhispered(
        aggregate_id=opaque_aggregate_id(whisper.session_id, field="session_id"),
        whisper_id=whisper.whisper_id,
        session_id=str(whisper.session_id),
        campaign_id=str(whisper.campaign_id) if whisper.campaign_id else "",
        whisper_type=whisper.whisper_type,
        content=whisper.content,
        recipient_role=whisper.recipient_role,
        metadata=whisper.metadata,
    )
