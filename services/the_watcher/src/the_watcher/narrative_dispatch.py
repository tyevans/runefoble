"""The DM sends an audience narration to the table (TASK-0838).

Governed by ADR-0006 (Redis Streams event bus), ADR-0011 (the whisper log is an aggregate) and
ADR-0015 (fail loud). Only a whisper of type `audience_narration` can be sent, and only once.
The event is published before the whisper is marked, so a failed publish leaves the whisper
pending and the DM can retry.
"""

from __future__ import annotations

from eventsource.application.aggregates.repository import AggregateRepository
from runefoble_events.events import WatcherNarrativeDispatched
from runefoble_platform.aggregate_loading import load_or_create
from runefoble_platform.event_publish import publish_or_fail
from runefoble_platform.redis_bus import RedisStreamsEventBus
from the_watcher.copilot_state import WhisperNotFoundError, WhisperStateError
from the_watcher.copilot_state.whispers import WhisperAggregate, whisper_log_id
from the_watcher.dependencies import STREAM_WATCHER
from the_watcher.models import WhisperSuggestion

AUDIENCE_NARRATION = "audience_narration"


def _new_whisper_log(aggregate_id: object) -> WhisperAggregate:
    return WhisperAggregate(aggregate_id=aggregate_id)


async def dispatch_audience_narration(
    *,
    bus: RedisStreamsEventBus,
    whisper_repo: AggregateRepository[WhisperAggregate],
    session_id: str,
    campaign_id: str,
    whisper_id: str,
    text: str | None,
) -> WhisperSuggestion:
    """Publish the narration to the table and mark the whisper as sent.

    `text` replaces the recorded narration when it is set. Raises WhisperNotFoundError when the
    session log has no such whisper. Raises WhisperStateError when the whisper is not a narration
    or was sent before.
    """
    log = await load_or_create(whisper_repo, whisper_log_id(session_id), _new_whisper_log)
    whisper = log.find(whisper_id)
    if whisper is None:
        raise WhisperNotFoundError(f"Whisper {whisper_id} is not in session {session_id}.")
    if whisper.whisper_type != AUDIENCE_NARRATION:
        raise WhisperStateError(
            f"Whisper {whisper_id} is a '{whisper.whisper_type}' whisper. "
            "Only a narration goes to the table."
        )
    if whisper.metadata.get("dispatched") is True:
        raise WhisperStateError(f"Whisper {whisper_id} was already sent to the table.")
    sent_text = text if text is not None else whisper.content
    event = WatcherNarrativeDispatched(
        session_id=session_id,
        campaign_id=campaign_id or whisper.campaign_id,
        whisper_id=whisper_id,
        text=sent_text,
        source_proposal_id=str(whisper.metadata.get("source_proposal_id", "")),
    )
    await publish_or_fail(bus, STREAM_WATCHER, event)
    log.mark_dispatched(whisper_id, sent_text)
    await whisper_repo.save(log)
    return whisper
