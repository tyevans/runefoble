"""Blackbox TDD CloudEvents registration and serialization suite for Character Leitmotifs.

Governed by:
- ADR-0002, ADR-0006, ADR-0009
- Hard Invariant 2 (eventsource-py), Hard Invariant 6 (File length < 500 lines)
- PRD-0016 & US-0046 (Character Leitmotifs and Dynamic Theme Scoring)
"""

from __future__ import annotations

from eventsource.domain.event_registry import get_event_class_or_none
from runefoble_events import (
    CriticalHitRolled,
    CriticalHitScored,
    DeathSaveStarted,
    LeitmotifProfileConfigured,
    LeitmotifTriggered,
)


def test_leitmotif_cloudevents_registration() -> None:
    """Verify leitmotif and combat trigger domain events register with CloudEvents."""
    profile_cls = get_event_class_or_none("runefoble.events.soundscape.leitmotif_configured")
    assert profile_cls is not None
    assert profile_cls is LeitmotifProfileConfigured

    triggered_cls = get_event_class_or_none("runefoble.events.soundscape.leitmotif_triggered")
    assert triggered_cls is not None
    assert triggered_cls is LeitmotifTriggered

    crit_cls = get_event_class_or_none("runefoble.events.character.critical_hit_scored")
    assert crit_cls is not None
    assert crit_cls is CriticalHitScored
    assert CriticalHitRolled is CriticalHitScored

    death_cls = get_event_class_or_none("runefoble.events.character.death_save_started")
    assert death_cls is not None
    assert death_cls is DeathSaveStarted


def test_leitmotif_triggered_cloudevent_serialization() -> None:
    """Verify LeitmotifTriggered CloudEvent serialization and payload roundtrip."""
    event = LeitmotifTriggered(
        session_id="session-tomb-14",
        character_id="char-nadia",
        character_name="Nadia",
        motif_type="triumphant",
        instrument_timbre="lute",
        stem_url="http://silo:9000/runefoble-assets/audio/leitmotif/lute_triumphant.ogg",
        tempo_multiplier=1.05,
        volume_gain=1.0,
        trigger_reason="critical_hit",
    )
    ce = event.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.soundscape.leitmotif_triggered"
    assert ce["data"]["character_id"] == "char-nadia"
    assert ce["data"]["motif_type"] == "triumphant"
    assert ce["data"]["instrument_timbre"] == "lute"
    assert ce["data"]["tempo_multiplier"] == 1.05
    assert ce["data"]["volume_gain"] == 1.0
    assert ce["data"]["trigger_reason"] == "critical_hit"

    restored = LeitmotifTriggered.model_validate(ce["data"])
    assert restored.character_id == event.character_id
    assert restored.motif_type == event.motif_type
    assert restored.volume_gain == event.volume_gain


def test_leitmotif_profile_configured_serialization() -> None:
    """Verify LeitmotifProfileConfigured CloudEvent serialization and envelope parameters."""
    event = LeitmotifProfileConfigured(
        session_id="session-tomb-14",
        character_id="char-nadia",
        character_name="Nadia",
        instrument_timbre="lute",
        tempo_multiplier=1.05,
        volume_gain=1.0,
        attack_ms=120,
        release_ms=300,
        duration_ms=4000,
        triumphant_stem_url="http://silo:9000/audio/lute_triumphant.ogg",
        somber_stem_url="http://silo:9000/audio/lute_somber.ogg",
    )
    ce = event.to_cloudevent_dict()
    assert ce["type"] == "runefoble.events.soundscape.leitmotif_configured"
    assert ce["data"]["character_id"] == "char-nadia"
    assert ce["data"]["instrument_timbre"] == "lute"
    assert ce["data"]["volume_gain"] == 1.0
    assert ce["data"]["tempo_multiplier"] == 1.05
    assert ce["data"]["attack_ms"] == 120
    assert ce["data"]["release_ms"] == 300
    assert ce["data"]["duration_ms"] == 4000

    restored = LeitmotifProfileConfigured.model_validate(ce["data"])
    assert restored.character_id == event.character_id
    assert restored.instrument_timbre == event.instrument_timbre
    assert restored.tempo_multiplier == event.tempo_multiplier
    assert restored.duration_ms == 4000
