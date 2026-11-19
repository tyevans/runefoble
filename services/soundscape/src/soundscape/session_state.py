"""Read and write one session's soundscape state through the aggregate (TASK-0576).

Every route and every event handler uses these helpers. A read never creates a stream. A
write loads the aggregate, records events, saves them, and then publishes them.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from runefoble_events.soundscape import SoundscapeSourceEventHandled
from runefoble_platform.aggregate_loading import load_if_exists, load_or_create
from runefoble_platform.models import utc_now

from soundscape.aggregate import SoundscapeAggregate, SoundscapeState
from soundscape.dependencies import get_soundscape_repo, publish_soundscape_event
from soundscape.ids import soundscape_aggregate_id
from soundscape.models import TensionStatusResponse


async def read_session_state(session_id: str) -> SoundscapeState:
    """Return the stored state for a session, or the default state when no event exists."""
    agg = await load_if_exists(get_soundscape_repo(), soundscape_aggregate_id(session_id))
    if agg is None:
        return SoundscapeState(session_id=session_id)
    return agg.state


async def load_session_aggregate(session_id: str) -> SoundscapeAggregate:
    """Load the session aggregate for writing, or start an empty one."""
    return await load_or_create(
        get_soundscape_repo(), soundscape_aggregate_id(session_id), SoundscapeAggregate
    )


async def save_session_aggregate(agg: SoundscapeAggregate) -> None:
    """Save the uncommitted events, then publish them on the soundscape streams.

    The source ledger entry is saved but not published. It is internal bookkeeping.
    """
    events = list(agg.uncommitted_events)
    await get_soundscape_repo().save(agg)
    for event in events:
        if isinstance(event, SoundscapeSourceEventHandled):
            continue
        await publish_soundscape_event(event)


async def source_event_handled(session_id: str, source_event_id: str) -> bool:
    """Return True when the session already saved the effects of this source event."""
    agg = await load_if_exists(get_soundscape_repo(), soundscape_aggregate_id(session_id))
    return agg is not None and agg.has_handled_source_event(source_event_id)


@asynccontextmanager
async def session_write(
    session_id: str, source_event_id: str
) -> AsyncIterator[SoundscapeAggregate]:
    """Load the session aggregate, record the source event, and save once when the block ends.

    The ledger entry and every effect in the block share one save. An exception skips the save,
    so the source event stays unrecorded and a redelivery applies it again.
    """
    agg = await load_session_aggregate(session_id)
    agg.record_source_event(session_id, source_event_id)
    yield agg
    await save_session_aggregate(agg)


def tension_status(
    session_id: str, state: SoundscapeState, now: datetime | None = None
) -> TensionStatusResponse:
    """Project the public tension and mixer view from one aggregate state."""
    instant = now or utc_now()
    mixer = state.mixer_at(instant)
    is_ducked = mixer.is_ducked
    return TensionStatusResponse(
        session_id=session_id,
        tension_score=state.tension_score,
        stem_profile=state.stem_profile,
        active_stems=state.active_stems,
        stem_volumes=mixer.calculate_active_stem_gains(),
        master_volume=mixer.master_volume,
        is_ducked=is_ducked,
        ducking_attenuation_db=state.ducking_attenuation_db if is_ducked else 0.0,
        effective_gain=mixer.get_effective_gain(),
        manual_override=state.manual_override,
        override_mood=state.override_mood,
        recent_cues=state.cues_history,
    )
