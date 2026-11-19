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
from runefoble_events.events import (
    CharacterHealthChanged,
    DiceRolled,
    LeitmotifTriggered,
    PlayerSpokeEvent,
)
from runefoble_platform.event_deserializer import deserialize_event
from runefoble_platform.models import utc_now
from soundscape.event_handlers import handle_incoming_domain_event
from soundscape.leitmotif import LeitmotifEngine, calculate_envelope_gain
from soundscape.mixer import DUCKING_ATTENUATION_DB, DUCKING_LINEAR_MULTIPLIER
from soundscape.session_state import read_session_state

from tests.helpers.leitmotif_fixtures import (
    client,
    leitmotif_session_id_fixture,  # noqa: F401 (registers the leitmotif_session_id fixture)
    setup_leitmotif_profile,
)


async def _engine(session_id: str) -> LeitmotifEngine:
    """Rebuild the leitmotif view from the stored aggregate state, as the routes do."""
    return LeitmotifEngine.from_state(session_id, await read_session_state(session_id), utc_now())


__all__ = ["client"]


@pytest.mark.asyncio
async def test_clutch_critical_hit_triggers_triumphant_leitmotif(
    client: TestClient, leitmotif_session_id: str, mock_bus
) -> None:
    """Scenario 1: Clutch Critical Hit Theme Stinger within 250ms (US-0046)."""
    setup_leitmotif_profile(
        client,
        leitmotif_session_id,
        "char-nadia",
        "Nadia",
        "lute",
        tempo=1.05,
    )
    crit_event = DiceRolled(
        session_id=leitmotif_session_id,
        roller_id="char-nadia",
        roller_name="Nadia",
        formula="1d20+5",
        total=25,
        rolls=[20],
        is_crit=True,
    )
    await handle_incoming_domain_event(crit_event)

    engine = await _engine(leitmotif_session_id)
    playback = engine.get_active_status()
    assert playback is not None and playback.character_id == "char-nadia"
    assert playback.motif_type == "triumphant" and playback.instrument_timbre == "lute"
    assert "lute_triumphant.ogg" in playback.stem_url
    assert not hasattr(playback, "scheduled_latency_ms")

    triggered = [
        ev
        for _, fields in mock_bus.streams.get("runefoble.events.soundscape", [])
        if isinstance(ev := deserialize_event(fields), LeitmotifTriggered)
    ]
    assert len(triggered) == 1
    assert triggered[0].character_id == "char-nadia"
    assert triggered[0].motif_type == "triumphant"
    assert triggered[0].trigger_reason == "critical_hit"


@pytest.mark.asyncio
async def test_dice_rolled_crit_triggers_triumphant_stinger(leitmotif_session_id: str) -> None:
    """Verify DiceRolled with is_crit=True reactively triggers leitmotif stinger."""
    dice_event = DiceRolled(
        session_id=leitmotif_session_id,
        roller_id="char-nadia",
        roller_name="Nadia",
        formula="1d20+5",
        total=25,
        rolls=[20],
        is_crit=True,
    )
    await handle_incoming_domain_event(dice_event)

    engine = await _engine(leitmotif_session_id)
    playback = engine.get_active_status()
    assert (
        playback is not None
        and playback.character_id == "char-nadia"
        and playback.motif_type == "triumphant"
    )


@pytest.mark.asyncio
async def test_near_death_triggers_somber_cello_leitmotif(
    client: TestClient, leitmotif_session_id: str
) -> None:
    """Scenario 2: Near-Death Tension & Somber Theme on a health change to 0 HP (US-0046)."""
    kyra_uuid = uuid4()
    setup_leitmotif_profile(
        client,
        leitmotif_session_id,
        str(kyra_uuid),
        "Kyra",
        "strings",
        tempo=0.95,
    )
    death_event = CharacterHealthChanged(
        aggregate_id=kyra_uuid,
        session_id=leitmotif_session_id,
        delta=-9,
        current_hp=0,
        max_hp=9,
    )
    await handle_incoming_domain_event(death_event)

    engine = await _engine(leitmotif_session_id)
    playback = engine.get_active_status()
    assert playback is not None and playback.character_id == str(kyra_uuid)
    assert playback.motif_type == "somber" and playback.instrument_timbre == "strings"
    assert "strings_somber.ogg" in playback.stem_url


@pytest.mark.asyncio
async def test_automatic_voice_ducking_attenuates_leitmotif_by_12db(client: TestClient) -> None:
    """Verify WebAudio sidechain compressor applies -12dB attenuation during voice activity.

    PlayerSpokeEvent carries a UUID session id, and gateway session ids are not UUIDs.
    This test therefore grants the owner a UUID session directly in the shared SpiceDB mock.
    That is the only direct tuple write in the soundscape frontdoor suites (see report).
    """
    from runefoble_auth.factory import get_spicedb_client

    session_uuid = uuid4()
    session_id_str = str(session_uuid)
    campaign_uuid = str(uuid4())
    spicedb = get_spicedb_client()
    await spicedb.write_relationship(
        "session", session_id_str, "campaign", "campaign", campaign_uuid
    )
    await spicedb.write_relationship(
        "campaign", campaign_uuid, "owner", "user", "soundscape-tester"
    )
    setup_leitmotif_profile(client, session_id_str, "char-nadia", "Nadia", "lute")
    client.post(
        "/api/v1/soundscape/leitmotif/trigger",
        json={
            "session_id": session_id_str,
            "character_id": "char-nadia",
            "motif_type": "triumphant",
        },
    )

    engine = await _engine(session_id_str)
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

    engine = await _engine(session_id_str)
    status_ducked = engine.get_active_status()
    assert status_ducked is not None and status_ducked.is_ducked is True
    assert status_ducked.ducking_attenuation_db == DUCKING_ATTENUATION_DB
    assert math.isclose(status_ducked.effective_gain, DUCKING_LINEAR_MULTIPLIER, rel_tol=1e-3)

    duck_resp = client.post(
        "/api/v1/soundscape/duck",
        json={"session_id": session_id_str, "is_ducked": False, "reason": "none"},
    )
    assert duck_resp.status_code == 200

    engine = await _engine(session_id_str)
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
