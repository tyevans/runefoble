"""Shared dependency injection, repositories, mixer, and event bus for Soundscape."""

from __future__ import annotations

import contextlib
import logging
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import Header
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.base import BaseRunefobleEvent
from runefoble_events.session import (
    CombatEncounterStarted,
    CombatRoundAdvanced,
    InitiativeTurnAdvanced,
)
from runefoble_events.watcher import PlayerSpokeEvent
from runefoble_platform.bus import bus as platform_bus
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus

from soundscape.aggregate import SoundscapeAggregate
from soundscape.mixer import AudioStemMixer
from soundscape.scoring import calculate_encounter_tension, derive_stem_profile

logger = logging.getLogger("runefoble.soundscape")
settings = PlatformSettings()

_event_bus: RedisStreamsEventBus | None = None
_soundscape_repo: AggregateRepository[SoundscapeAggregate] = create_aggregate_repository(
    SoundscapeAggregate
)
_spicedb_client: SpiceDBClient = SpiceDBClient(
    endpoint=settings.spicedb_endpoint or "localhost:50051",
    token=getattr(settings, "spicedb_token", "secret"),
)

# In-memory mapping of session_id -> aggregate_id and session_id -> AudioStemMixer
_session_to_aggregate: dict[str, UUID] = {}
_session_mixers: dict[str, AudioStemMixer] = {}


def get_soundscape_repo() -> AggregateRepository[SoundscapeAggregate]:
    """Provide SoundscapeAggregate repository singleton."""
    return _soundscape_repo


def get_spicedb_client() -> SpiceDBClient:
    """Provide SpiceDB Zanzibar authorization client."""
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient) -> None:
    """Override SpiceDB client for testing."""
    global _spicedb_client
    _spicedb_client = client


def get_event_bus() -> RedisStreamsEventBus | None:
    """Provide RedisStreamsEventBus instance."""
    global _event_bus
    if _event_bus is None and settings.redis_url:
        with contextlib.suppress(Exception):
            _event_bus = RedisStreamsEventBus(redis_url=settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    """Override event bus for testing."""
    global _event_bus
    _event_bus = bus


def get_or_create_aggregate_id(session_id: str) -> UUID:
    """Resolve or generate UUID for a session's soundscape aggregate."""
    if session_id not in _session_to_aggregate:
        _session_to_aggregate[session_id] = uuid4()
    return _session_to_aggregate[session_id]


def get_or_create_mixer(session_id: str) -> AudioStemMixer:
    """Resolve or instantiate AudioStemMixer for a session."""
    if session_id not in _session_mixers:
        _session_mixers[session_id] = AudioStemMixer(stem_profile="exploration", master_volume=1.0)
    return _session_mixers[session_id]


def reset_dependencies() -> None:
    """Clear in-memory session registries and reset mocks."""
    global _event_bus
    _session_to_aggregate.clear()
    _session_mixers.clear()
    _event_bus = None


def get_current_user_id(
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
) -> str | None:
    """Extract authenticated caller identity from x-user-id header."""
    return x_user_id


async def check_user_can_control_soundscape(
    user_id: str | None,
    session_id: str,
    campaign_id: UUID | None,
    spicedb: SpiceDBClient,
) -> bool:
    """Check Zanzibar authorization for managing audio soundscapes."""
    if not user_id:
        return True

    # 1. Check session permission directly if session_id provided
    try:
        can_control = await spicedb.check_permission(
            resource_type="session",
            resource_id=session_id,
            permission="control",
            subject_type="user",
            subject_id=user_id,
        )
        if can_control:
            return True
    except Exception:
        pass

    # 2. Check campaign context
    if campaign_id:
        try:
            can_run = await spicedb.check_permission(
                resource_type="campaign",
                resource_id=str(campaign_id),
                permission="run_session",
                subject_type="user",
                subject_id=user_id,
            )
            if can_run:
                return True
            return await spicedb.check_permission(
                resource_type="campaign",
                resource_id=str(campaign_id),
                permission="play",
                subject_type="user",
                subject_id=user_id,
            )
        except Exception:
            return False

    return False


async def publish_soundscape_event(event: BaseRunefobleEvent) -> None:
    """Publish soundscape domain event across in-memory platform bus and Redis Streams."""
    # 1. In-memory bus
    with contextlib.suppress(Exception):
        await platform_bus.publish(event.event_type, event)

    # 2. Redis stream bus
    bus = get_event_bus()
    if bus:
        stream = "runefoble.events.soundscape"
        with contextlib.suppress(Exception):
            await bus.publish_event(stream, event)


async def handle_incoming_domain_event(event: Any) -> None:
    """Process domain events (CombatStarted, CombatRoundAdvanced, PlayerSpokeEvent) to adjust soundscape."""
    repo = get_soundscape_repo()

    if isinstance(event, (CombatEncounterStarted,)):
        session_id = str(getattr(event, "session_id", "default") or "default")
        agg_id = get_or_create_aggregate_id(session_id)
        try:
            agg = await repo.load(agg_id)
        except Exception:
            agg = SoundscapeAggregate(agg_id)

        tension = calculate_encounter_tension(
            combat_active=True, combat_round=1, enemy_cr_balance=2.0
        )
        profile = derive_stem_profile(tension)
        mixer = get_or_create_mixer(session_id)
        mixer.stem_profile = profile

        agg.record_tension_update(
            session_id=session_id,
            tension_score=tension,
            stem_profile=profile,
            combat_round=1,
            enemy_cr_balance=2.0,
        )
        agg.record_track_change(
            session_id=session_id,
            track_id="track-combat-01",
            stem_profile=profile,
            tension_score=tension,
            crossfade_duration_ms=1500,
            active_stems=[profile],
        )
        events = list(agg.uncommitted_events)
        await repo.save(agg)
        for ev in events:
            await publish_soundscape_event(ev)

    elif isinstance(event, (CombatRoundAdvanced, InitiativeTurnAdvanced)):
        session_id = str(getattr(event, "session_id", "default") or "default")
        round_num = getattr(event, "round_number", 1)
        agg_id = get_or_create_aggregate_id(session_id)
        try:
            agg = await repo.load(agg_id)
        except Exception:
            agg = SoundscapeAggregate(agg_id)

        tension = calculate_encounter_tension(
            combat_active=True, combat_round=round_num, enemy_cr_balance=2.5
        )
        profile = derive_stem_profile(tension)
        mixer = get_or_create_mixer(session_id)
        old_profile = mixer.stem_profile
        mixer.stem_profile = profile

        agg.record_tension_update(
            session_id=session_id,
            tension_score=tension,
            stem_profile=profile,
            combat_round=round_num,
        )
        if profile != old_profile:
            agg.record_track_change(
                session_id=session_id,
                track_id=f"track-{profile}-01",
                stem_profile=profile,
                tension_score=tension,
                crossfade_duration_ms=1500,
                active_stems=[profile],
            )
        events = list(agg.uncommitted_events)
        await repo.save(agg)
        for ev in events:
            await publish_soundscape_event(ev)

    elif isinstance(event, PlayerSpokeEvent):
        # Speech detected: trigger -12dB WebAudio ducking
        session_id = str(getattr(event, "session_id", "default") or "default")
        mixer = get_or_create_mixer(session_id)
        mixer.set_ducking(True, reason="speech")
        agg_id = get_or_create_aggregate_id(session_id)
        try:
            agg = await repo.load(agg_id)
        except Exception:
            agg = SoundscapeAggregate(agg_id)
        agg.record_ducking_toggle(
            session_id=session_id,
            is_ducked=True,
            attenuation_db=-12.0,
            reason="speech",
        )
        events = list(agg.uncommitted_events)
        await repo.save(agg)
        for ev in events:
            await publish_soundscape_event(ev)
