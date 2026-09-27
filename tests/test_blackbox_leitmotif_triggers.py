"""Blackbox TDD triggers and DSP ducking suite for Character Leitmotifs.

Governed by:
- ADR-0002, ADR-0006, ADR-0010
- Hard Invariant 2 (eventsource-py), Hard Invariant 6 (File length < 500 lines)
- PRD-0016 & US-0046 (Character Leitmotifs and Dynamic Theme Scoring)
"""

from __future__ import annotations

import math
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_events import (
    CriticalHitScored,
    DeathSaveStarted,
    DiceRolled,
    LeitmotifTriggered,
    PlayerSpokeEvent,
)
from runefoble_platform.bus import bus as platform_bus
from soundscape.dependencies import (
    get_or_create_leitmotif_engine,
    handle_incoming_domain_event,
)
from soundscape.leitmotif import calculate_envelope_gain
from soundscape.mixer import DUCKING_ATTENUATION_DB, DUCKING_LINEAR_MULTIPLIER

from tests.helpers.leitmotif_fixtures import clean_environment, client, setup_leitmotif_profile

__all__ = ["clean_environment", "client"]


@pytest.mark.asyncio
async def test_clutch_critical_hit_triggers_triumphant_leitmotif(client: TestClient) -> None:
    """Scenario 1: Clutch Critical Hit Theme Stinger within 250ms (US-0046)."""
    setup_leitmotif_profile(client, "session-tomb-14", "char-nadia", "Nadia", "lute", tempo=1.05)
    captured_events: list[LeitmotifTriggered] = []

    async def on_event(ev: LeitmotifTriggered) -> None:
        captured_events.append(ev)

    platform_bus.subscribe("runefoble.events.soundscape.leitmotif_triggered", on_event)

    crit_event = CriticalHitScored(
        session_id="session-tomb-14",
        character_id="char-nadia",
        character_name="Nadia",
        roll_total=20,
    )
    await handle_incoming_domain_event(crit_event)

    engine = get_or_create_leitmotif_engine("session-tomb-14")
    playback = engine.get_active_status()
    assert playback is not None and playback.character_id == "char-nadia"
    assert playback.motif_type == "triumphant" and playback.instrument_timbre == "lute"
    assert playback.scheduled_latency_ms <= 250 and "lute_triumphant.ogg" in playback.stem_url

    assert len(captured_events) == 1
    assert captured_events[0].character_id == "char-nadia"
    assert captured_events[0].motif_type == "triumphant"
    assert captured_events[0].trigger_reason == "critical_hit"


@pytest.mark.asyncio
async def test_dice_rolled_crit_triggers_triumphant_stinger() -> None:
    """Verify DiceRolled with is_crit=True reactively triggers leitmotif stinger."""
    dice_event = DiceRolled(
        session_id="session-tomb-14",
        roller_id="char-nadia",
        roller_name="Nadia",
        formula="1d20+5",
        total=25,
        rolls=[20],
        is_crit=True,
    )
    await handle_incoming_domain_event(dice_event)

    engine = get_or_create_leitmotif_engine("session-tomb-14")
    playback = engine.get_active_status()
    assert (
        playback is not None
        and playback.character_id == "char-nadia"
        and playback.motif_type == "triumphant"
    )


@pytest.mark.asyncio
async def test_near_death_triggers_somber_cello_leitmotif(client: TestClient) -> None:
    """Scenario 2: Near-Death Tension & Somber Theme on DeathSaveStarted (US-0046)."""
    setup_leitmotif_profile(client, "session-tomb-14", "char-kyra", "Kyra", "strings", tempo=0.95)
    death_event = DeathSaveStarted(
        session_id="session-tomb-14", character_id="char-kyra", character_name="Kyra", current_hp=0
    )
    await handle_incoming_domain_event(death_event)

    engine = get_or_create_leitmotif_engine("session-tomb-14")
    playback = engine.get_active_status()
    assert playback is not None and playback.character_id == "char-kyra"
    assert playback.motif_type == "somber" and playback.instrument_timbre == "strings"
    assert "strings_somber.ogg" in playback.stem_url


@pytest.mark.asyncio
async def test_automatic_voice_ducking_attenuates_leitmotif_by_12db(client: TestClient) -> None:
    """Verify WebAudio sidechain compressor applies -12dB attenuation during voice activity."""
    session_uuid = uuid4()
    session_id_str = str(session_uuid)
    setup_leitmotif_profile(client, session_id_str, "char-nadia", "Nadia", "lute")
    client.post(
        "/api/v1/soundscape/leitmotif/trigger",
        json={
            "session_id": session_id_str,
            "character_id": "char-nadia",
            "motif_type": "triumphant",
        },
    )

    engine = get_or_create_leitmotif_engine(session_id_str)
    status_before = engine.get_active_status()
    assert (
        status_before is not None
        and status_before.is_ducked is False
        and status_before.effective_gain == 1.0
    )

    spoke_event = PlayerSpokeEvent(
        aggregate_id=uuid4(),
        session_id=session_uuid,
        speaker_id="player-marcus",
        speaker_name="Marcus",
        transcript="Nadia, incredible shot!",
    )
    await handle_incoming_domain_event(spoke_event)

    status_ducked = engine.get_active_status()
    assert status_ducked is not None and status_ducked.is_ducked is True
    assert status_ducked.ducking_attenuation_db == DUCKING_ATTENUATION_DB
    assert math.isclose(status_ducked.effective_gain, DUCKING_LINEAR_MULTIPLIER, rel_tol=1e-3)

    duck_resp = client.post(
        "/api/v1/soundscape/duck",
        json={"session_id": session_id_str, "is_ducked": False, "reason": "none"},
    )
    assert duck_resp.status_code == 200

    engine.set_ducking(False)
    status_restored = engine.get_active_status()
    assert (
        status_restored is not None
        and status_restored.is_ducked is False
        and status_restored.effective_gain == 1.0
    )


@pytest.mark.parametrize(
    ("elapsed_ms", "expected_gain", "expected_stage"),
    [
        (0, 0.0, "attack"),
        (75, 0.5, "attack"),
        (2000, 1.0, "sustain"),
        (3825, 0.5, "release"),
        (4100, 0.0, "decay"),
    ],
)
def test_volume_envelope_ramps_and_stage_transitions(
    elapsed_ms: int, expected_gain: float, expected_stage: str
) -> None:
    """Verify smooth attack, sustain, and release envelope calculations without clipping."""
    gain, stage = calculate_envelope_gain(elapsed_ms, 150, 350, 4000)
    assert math.isclose(gain, expected_gain, rel_tol=1e-2)
    assert stage == expected_stage
