"""Domain event subscribers and tension recalculation triggers for Soundscape."""

from __future__ import annotations

import logging
from typing import Any

from runefoble_events.character import (
    CharacterHealthChanged,
    CriticalHitScored,
    DeathSaveStarted,
)
from runefoble_events.session import (
    CombatEncounterStarted,
    CombatRoundAdvanced,
    InitiativeTurnAdvanced,
)
from runefoble_events.watcher import DiceRolled, PlayerSpokeEvent

from soundscape.aggregate import SoundscapeAggregate
from soundscape.scoring import calculate_encounter_tension, derive_stem_profile

logger = logging.getLogger("runefoble.soundscape.events")

SOUNDSCAPE_SUBSCRIBED_EVENTS: list[str] = [
    "CombatEncounterStarted",
    "CombatStarted",
    "CombatRoundAdvanced",
    "InitiativeTurnAdvanced",
    "PlayerSpokeEvent",
    "CriticalHitScored",
    "DiceRolled",
    "DeathSaveStarted",
    "CharacterHealthChanged",
]

_handlers_registered: bool = False


def _deps() -> Any:
    import soundscape.dependencies as deps

    return deps


async def _get_aggregate(session_id: str) -> SoundscapeAggregate:
    d = _deps()
    agg_id = d.get_or_create_aggregate_id(session_id)
    try:
        return await d.get_soundscape_repo().load(agg_id)
    except Exception:
        return SoundscapeAggregate(agg_id)


async def _save_and_publish(agg: SoundscapeAggregate) -> None:
    d = _deps()
    events = list(agg.uncommitted_events)
    await d.get_soundscape_repo().save(agg)
    for ev in events:
        await d.publish_soundscape_event(ev)


async def _handle_combat_start(session_id: str) -> None:
    agg = await _get_aggregate(session_id)
    tension = calculate_encounter_tension(combat_active=True, combat_round=1, enemy_cr_balance=2.0)
    profile = derive_stem_profile(tension)
    _deps().get_or_create_mixer(session_id).stem_profile = profile
    agg.record_tension_update(session_id, tension, profile, combat_round=1, enemy_cr_balance=2.0)
    agg.record_track_change(
        session_id, "track-combat-01", profile, tension, 1500, active_stems=[profile]
    )
    await _save_and_publish(agg)


async def _handle_combat_advance(session_id: str, round_num: int) -> None:
    agg = await _get_aggregate(session_id)
    tension = calculate_encounter_tension(
        combat_active=True, combat_round=round_num, enemy_cr_balance=2.5
    )
    profile = derive_stem_profile(tension)
    mixer = _deps().get_or_create_mixer(session_id)
    old_profile = mixer.stem_profile
    mixer.stem_profile = profile
    agg.record_tension_update(session_id, tension, profile, combat_round=round_num)
    if profile != old_profile:
        agg.record_track_change(
            session_id, f"track-{profile}-01", profile, tension, 1500, active_stems=[profile]
        )
    await _save_and_publish(agg)


async def _handle_player_speech(session_id: str) -> None:
    _deps().get_or_create_mixer(session_id).set_ducking(True, reason="speech")
    _deps().get_or_create_leitmotif_engine(session_id).set_ducking(True)
    agg = await _get_aggregate(session_id)
    agg.record_ducking_toggle(session_id, is_ducked=True, attenuation_db=-12.0, reason="speech")
    await _save_and_publish(agg)


async def _handle_leitmotif_trigger(
    session_id: str, char_id: str, char_name: str, motif: str, reason: str
) -> None:
    engine = _deps().get_or_create_leitmotif_engine(session_id)
    pb = engine.trigger_leitmotif(
        character_id=char_id, motif_type=motif, trigger_reason=reason, character_name=char_name
    )
    agg = await _get_aggregate(session_id)
    agg.record_leitmotif_trigger(
        session_id=session_id,
        character_id=char_id,
        character_name=char_name,
        motif_type=pb.motif_type,
        instrument_timbre=pb.instrument_timbre,
        stem_url=pb.stem_url,
        tempo_multiplier=pb.tempo_multiplier,
        volume_gain=pb.volume_gain,
        attack_ms=pb.attack_ms,
        release_ms=pb.release_ms,
        duration_ms=pb.duration_ms,
        duck_music=False,
        trigger_reason=reason,
    )
    await _save_and_publish(agg)


async def handle_incoming_domain_event(event: Any) -> None:
    """Process domain events to dynamically adjust soundscape, tension, and leitmotifs."""
    session_id = str(getattr(event, "session_id", "default") or "default")

    if isinstance(event, (CombatEncounterStarted,)):
        await _handle_combat_start(session_id)
    elif isinstance(event, (CombatRoundAdvanced, InitiativeTurnAdvanced)):
        await _handle_combat_advance(session_id, getattr(event, "round_number", 1))
    elif isinstance(event, PlayerSpokeEvent):
        await _handle_player_speech(session_id)
    elif isinstance(event, (CriticalHitScored,)) or (
        isinstance(event, DiceRolled) and getattr(event, "is_crit", False)
    ):
        char_id = str(
            getattr(event, "character_id", None)
            or getattr(event, "roller_id", None)
            or "char-player"
        )
        char_name = str(
            getattr(event, "character_name", None) or getattr(event, "roller_name", None) or "Hero"
        )
        await _handle_leitmotif_trigger(
            session_id, char_id, char_name, "triumphant", "critical_hit"
        )
    elif isinstance(event, (DeathSaveStarted,)) or (
        isinstance(event, CharacterHealthChanged) and getattr(event, "current_hp", 1) <= 0
    ):
        char_id = str(getattr(event, "character_id", None) or "char-player")
        char_name = str(getattr(event, "character_name", None) or "Hero")
        await _handle_leitmotif_trigger(session_id, char_id, char_name, "somber", "death_save")


def register_soundscape_event_handlers() -> None:
    """Register soundscape domain event handlers to the platform in-memory event bus."""
    global _handlers_registered
    if _handlers_registered:
        return
    from runefoble_platform.bus import bus as platform_bus

    for topic in SOUNDSCAPE_SUBSCRIBED_EVENTS:
        platform_bus.subscribe(topic, handle_incoming_domain_event)
    _handlers_registered = True
