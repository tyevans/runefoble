"""Domain event handlers and tension recalculation triggers for Soundscape.

The Redis Streams consumer in `soundscape.consumer` is the only caller. No in-process bus exists.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from runefoble_events.events import (
    CharacterHealthChanged,
    CombatEncounterEnded,
    CombatEncounterStarted,
    CombatRoundAdvanced,
    DiceRolled,
    InitiativeTurnAdvanced,
    PhysicsCollisionOccurred,
    PlayerSpokeEvent,
    TokenHazardTriggered,
)

from soundscape.aggregate import SoundscapeAggregate
from soundscape.leitmotif import LeitmotifEngine
from soundscape.scoring import (
    calculate_encounter_tension,
    derive_stem_profile,
    enemy_cr_balance_from_combatants,
)
from soundscape.session_state import load_session_aggregate, save_session_aggregate
from soundscape.tactical_cues import hazard_cue, impact_cue

logger = logging.getLogger("runefoble.soundscape.events")

# Speech ducking holds for the same window the browser uses (UI default 2500 ms).
SPEECH_DUCK_MS = 2500


def _score_encounter(
    agg: SoundscapeAggregate,
    session_id: str,
    *,
    combat_round: int,
    enemy_cr_balance: float,
    combat_active: bool = True,
) -> tuple[int, str]:
    """Score tension from the encounter inputs and the stored party health, then record it."""
    party_health = agg.state.lowest_party_health_ratio
    tension = calculate_encounter_tension(
        combat_active=combat_active,
        combat_round=combat_round,
        enemy_cr_balance=enemy_cr_balance,
        lowest_party_health_ratio=party_health,
    )
    profile = derive_stem_profile(tension)
    agg.record_tension_update(
        session_id,
        tension,
        profile,
        combat_round=combat_round,
        enemy_cr_balance=enemy_cr_balance,
        lowest_health_ratio=party_health,
        combat_active=combat_active,
    )
    return tension, profile


def _retune_encounter(agg: SoundscapeAggregate, session_id: str, *, combat_round: int) -> None:
    """Re-score the live encounter with its stored CR. Switch track only on a profile change."""
    old_profile = agg.state.stem_profile
    tension, profile = _score_encounter(
        agg,
        session_id,
        combat_round=combat_round,
        enemy_cr_balance=agg.state.enemy_cr_balance,
    )
    if profile != old_profile:
        agg.record_track_change(
            session_id, f"track-{profile}-01", profile, tension, 1500, active_stems=[profile]
        )


async def _handle_combat_start(session_id: str, combatants: list[dict[str, Any]]) -> None:
    agg = await load_session_aggregate(session_id)
    tension, profile = _score_encounter(
        agg,
        session_id,
        combat_round=1,
        enemy_cr_balance=enemy_cr_balance_from_combatants(combatants),
    )
    agg.record_track_change(
        session_id, "track-combat-01", profile, tension, 1500, active_stems=[profile]
    )
    await save_session_aggregate(agg)


async def _handle_combat_end(session_id: str) -> None:
    """Leave combat. Clear the encounter inputs and re-score the ambient tension once."""
    agg = await load_session_aggregate(session_id)
    old_profile = agg.state.stem_profile
    tension, profile = _score_encounter(
        agg, session_id, combat_round=0, enemy_cr_balance=0.0, combat_active=False
    )
    if profile != old_profile:
        agg.record_track_change(
            session_id, f"track-{profile}-01", profile, tension, 1500, active_stems=[profile]
        )
    await save_session_aggregate(agg)


async def _handle_combat_advance(session_id: str, round_num: int) -> None:
    agg = await load_session_aggregate(session_id)
    _retune_encounter(agg, session_id, combat_round=round_num)
    await save_session_aggregate(agg)


async def _handle_health_changed(event: CharacterHealthChanged, session_id: str) -> None:
    """Store the character's HP ratio. In combat, re-score tension with the new party minimum."""
    if event.max_hp <= 0:
        logger.warning(
            "Ignoring health change with non-positive max_hp for character %s",
            event.aggregate_id,
        )
        return
    ratio = min(1.0, max(0.0, event.current_hp / event.max_hp))
    agg = await load_session_aggregate(session_id)
    agg.record_party_health(session_id, str(event.aggregate_id), ratio)
    if agg.state.combat_active:
        _retune_encounter(agg, session_id, combat_round=agg.state.combat_round)
    await save_session_aggregate(agg)


async def _handle_player_speech(session_id: str) -> None:
    agg = await load_session_aggregate(session_id)
    agg.record_ducking_engaged(session_id, reason="speech", duration_ms=SPEECH_DUCK_MS)
    await save_session_aggregate(agg)


async def _handle_leitmotif_trigger(
    session_id: str, char_id: str, char_name: str, motif: str, reason: str
) -> None:
    agg = await load_session_aggregate(session_id)
    engine = LeitmotifEngine.from_state(session_id, agg.state, datetime.now(UTC))
    pb = engine.trigger_leitmotif(
        character_id=char_id, motif_type=motif, trigger_reason=reason, character_name=char_name
    )
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
        playback_id=pb.playback_id,
        triggered_at=pb.triggered_at,
    )
    await save_session_aggregate(agg)


async def _handle_tactical_board_event(
    event: TokenHazardTriggered | PhysicsCollisionOccurred,
) -> None:
    """Record a foley cue for a hazard trip or a physical impact on the board."""
    if not event.session_id:
        # A board event with no session in play feeds no cue.
        return
    if isinstance(event, TokenHazardTriggered):
        cue = hazard_cue(event.hazard_type)
    else:
        cue = impact_cue(event.collision_type, event.impact_energy)
    agg = await load_session_aggregate(str(event.session_id))
    agg.record_cue(
        session_id=str(event.session_id),
        cue_id=f"cue-{str(event.event_id)[:8]}",
        sound_url=cue["sound_url"],
        cue_type=cue["cue_type"],
        volume_gain=cue["volume_gain"],
        duck_music=cue["duck_music"],
    )
    await save_session_aggregate(agg)


async def handle_incoming_domain_event(event: Any) -> None:
    """Process domain events to dynamically adjust soundscape, tension, and leitmotifs."""
    session_id = str(getattr(event, "session_id", "default") or "default")

    if isinstance(event, (CombatEncounterStarted,)):
        await _handle_combat_start(session_id, list(event.combatants))
    elif isinstance(event, CombatEncounterEnded):
        await _handle_combat_end(session_id)
    elif isinstance(event, (CombatRoundAdvanced, InitiativeTurnAdvanced)):
        await _handle_combat_advance(session_id, getattr(event, "round_number", 1))
    elif isinstance(event, PlayerSpokeEvent):
        await _handle_player_speech(session_id)
    elif isinstance(event, DiceRolled) and getattr(event, "is_crit", False):
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
    elif isinstance(event, (TokenHazardTriggered, PhysicsCollisionOccurred)):
        await _handle_tactical_board_event(event)
    elif isinstance(event, CharacterHealthChanged):
        # A health event has no session when no session is in play. Such an event feeds no tension.
        if event.session_id:
            await _handle_health_changed(event, event.session_id)
        if event.current_hp <= 0:
            char_id = str(event.aggregate_id)
            await _handle_leitmotif_trigger(session_id, char_id, "Hero", "somber", "death_save")
