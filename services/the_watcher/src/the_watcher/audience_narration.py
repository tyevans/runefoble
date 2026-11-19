"""Redis Streams consumer that asks for narration of an approved audience modifier (TASK-0838).

Governed by ADR-0006 (Redis Streams event bus), ADR-0007 (each owner applies its own effect),
ADR-0011 (the whisper log is an aggregate) and ADR-0015 (fail loud). The Watcher does not apply
the modifier. It asks the inference worker for narration and records the result as a whisper for
the DM. The DM decides whether the table sees it. When the worker cannot narrate, the DM gets a
notice instead. No canned text is ever recorded.

A modifier that the DM rejected, a modifier of another campaign, and a redelivered modifier
record nothing. A modifier that names no known session is refused and dead-lettered.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from eventsource.application.aggregates.repository import AggregateRepository
from eventsource.domain.exceptions import OptimisticLockError
from fastapi import HTTPException
from runefoble_auth.factory import get_spicedb_client
from runefoble_events.events import AudienceModifierApproved
from runefoble_platform.aggregate_loading import load_or_create
from runefoble_platform.audience_modifiers import (
    approved_audience_modifier,
    refusal,
    require_same_campaign,
)
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.engine_ports import EngineUnavailableError
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import StreamConsumer, SupervisedStreamConsumers
from the_watcher.copilot_state.whispers import WhisperAggregate, whisper_log_id
from the_watcher.dependencies import logger
from the_watcher.engine_selection import WatcherEngineSettings
from the_watcher.models import WhisperSuggestion
from the_watcher.worker_client import call_worker

CONSUMER_NAME = "the_watcher"
GROUP_NAME = "the_watcher_narration_workers"
WORKER_NAME = "the_watcher_narration_consumer_1"
AUDIENCE_STREAM = "runefoble.events.audience"
WORKER_PATH = "/inference/v1/dm-narration"
WORKER_TIMEOUT_S = 10.0
RECORD_ATTEMPTS = 3

NARRATION_WHISPER = "audience_narration"
UNAVAILABLE_WHISPER = "narration_unavailable"
UNAVAILABLE_REASON = "The inference worker did not return narration for this modifier."
HEURISTIC_REASON = "The Watcher runs on the heuristic engine. Narration needs the inference worker."


def _new_whisper_log(aggregate_id: object) -> WhisperAggregate:
    return WhisperAggregate(aggregate_id=aggregate_id)


async def _session_campaign(session_id: str) -> str | None:
    """Return the campaign that the session belongs to in SpiceDB, or None when it has no link."""
    relations = await get_spicedb_client().read_relationships(
        resource_type="game_session", resource_id=session_id, relation="campaign"
    )
    for relation in relations:
        return str(relation.subject_id)
    return None


def _recent_event_line(modifier: AudienceModifierApproved) -> str:
    parameters = json.dumps(modifier.parameters, sort_keys=True)
    return f"Audience modifier {modifier.modifier_type} was approved with {parameters}."


async def _narrate(modifier: AudienceModifierApproved) -> tuple[str, str, dict[str, Any]]:
    """Ask the worker for narration. Return (whisper type, content, metadata).

    An unavailable worker gives a notice, never narration text. A worker call that
    fails for another reason propagates, so the message is dead-lettered.
    """
    base = {
        "source_proposal_id": str(modifier.proposal_id),
        "modifier_type": modifier.modifier_type,
    }
    settings = WatcherEngineSettings()
    if settings.watcher_engine == "heuristic":
        return UNAVAILABLE_WHISPER, HEURISTIC_REASON, base
    if settings.inference_url is None:
        raise refusal(modifier, "cannot be narrated because RUNEFOBLE_INFERENCE_URL is not set.")
    payload = {
        "campaign_id": str(modifier.campaign_id),
        "session_id": str(modifier.session_id),
        "recent_events": [_recent_event_line(modifier)],
    }
    try:
        data = await call_worker(
            settings.inference_url,
            WORKER_PATH,
            payload,
            timeout=WORKER_TIMEOUT_S,
            credential=settings.service_credential,
        )
    except (EngineUnavailableError, HTTPException) as exc:
        logger.error("Narration for modifier %s failed: %s", modifier.proposal_id, exc)
        return UNAVAILABLE_WHISPER, UNAVAILABLE_REASON, base
    metadata = {
        **base,
        "sensory_details": data["sensory_details"],
        "suggested_dm_prompts": data["suggested_dm_prompts"],
        "tension_level": data["tension_level"],
        "source": data["source"],
        "dispatched": False,
    }
    return NARRATION_WHISPER, data["narration"], metadata


async def record_audience_narration(
    event: Any, repo: AggregateRepository[WhisperAggregate]
) -> None:
    """Record one whisper for the DM about an approved modifier.

    A rejected proposal records nothing. A session with no campaign link, or a campaign that is
    not the campaign of the modifier, raises. A proposal that already has a whisper records nothing.
    """
    modifier = approved_audience_modifier(event)
    if modifier is None:
        return
    if modifier.session_id is None:
        raise refusal(modifier, "has no session.")
    session_id = str(modifier.session_id)
    try:
        UUID(session_id)
    except ValueError as exc:
        raise refusal(modifier, "names a session id that is not a UUID.") from exc
    campaign = await _session_campaign(session_id)
    if campaign is None:
        raise refusal(modifier, f"names session {session_id} that has no campaign link.")
    require_same_campaign(modifier, campaign, f"session {session_id}")

    proposal_id = str(modifier.proposal_id)
    outcome: tuple[str, str, dict[str, Any]] | None = None
    for _attempt in range(RECORD_ATTEMPTS):
        log = await load_or_create(repo, whisper_log_id(session_id), _new_whisper_log)
        if any(w.metadata.get("source_proposal_id") == proposal_id for w in log.state.whispers):
            # A redelivery. This proposal already has its whisper, so nothing changes.
            return
        if outcome is None:
            # The worker runs once. A retry after a lost write reuses its answer.
            outcome = await _narrate(modifier)
        whisper_type, content, metadata = outcome
        log.record(
            WhisperSuggestion(
                whisper_id=f"whisp-{uuid4().hex[:8]}",
                session_id=session_id,
                campaign_id=str(modifier.campaign_id),
                whisper_type=whisper_type,
                content=content,
                metadata=metadata,
            )
        )
        try:
            await repo.save(log)
        except OptimisticLockError:
            # Another writer changed the log between the load and the save (for example a DM
            # read that seeds an empty log). Reload and write again.
            logger.warning(
                "Whisper log for session %s changed during a write. Retrying.", session_id
            )
            continue
        return
    raise refusal(modifier, f"could not be recorded after {RECORD_ATTEMPTS} attempts.")


async def start_audience_narration_consumers(
    bus: RedisStreamsEventBus, whisper_repo: AggregateRepository[WhisperAggregate]
) -> SupervisedStreamConsumers:
    """Create the consumer group and start the read loop on the audience stream.

    The lifespan passes the whisper repository of the app container.

    Raises when the consumer group cannot be created, so the service does not start.
    """
    consumer_group = RedisConsumerGroup(client=await bus.get_client())

    async def _handle(_message_id: str, event: Any) -> None:
        await record_audience_narration(event, whisper_repo)

    consumers = SupervisedStreamConsumers(
        CONSUMER_NAME,
        [
            StreamConsumer(
                consumer_group=consumer_group,
                stream=AUDIENCE_STREAM,
                group_name=GROUP_NAME,
                consumer_name=WORKER_NAME,
                handler=_handle,
            )
        ],
    )
    await consumers.start()
    return consumers
