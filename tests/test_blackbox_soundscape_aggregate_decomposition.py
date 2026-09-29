"""Blackbox TDD test suite for Soundscape Aggregate Handlers Modular Decomposition (TASK-0230).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- ADR-0011: PostgreSQL Event Store via eventsource-py
- ADR-0013: Modular Decomposition
- Hard Invariant 6: File length limit (< 80 lines for aggregate.py, < 150 lines for handlers)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.application.aggregates.repository import AggregateRepository
from fastapi.testclient import TestClient
from runefoble_events.soundscape import (
    LeitmotifProfileConfigured,
    LeitmotifTriggered,
    SoundscapeCueTriggered,
    SoundscapeDuckingToggled,
    SoundscapeMoodOverridden,
    SoundscapeTensionUpdated,
    SoundscapeTrackChanged,
)
from soundscape.aggregate import (
    SoundscapeAggregate,
    SoundscapeState,
)
from soundscape.dependencies import reset_dependencies
from soundscape.handlers import (
    FoleyHandlersMixin,
    LeitmotifHandlersMixin,
    StemHandlersMixin,
    TensionHandlersMixin,
)
from soundscape.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean dependencies and aggregate states before and after each test."""
    reset_dependencies()
    yield
    reset_dependencies()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_soundscape_aggregate_facade_and_mixins():
    """Verify that SoundscapeAggregate inherits from all domain handler mixins."""
    assert issubclass(SoundscapeAggregate, StemHandlersMixin)
    assert issubclass(SoundscapeAggregate, FoleyHandlersMixin)
    assert issubclass(SoundscapeAggregate, TensionHandlersMixin)
    assert issubclass(SoundscapeAggregate, LeitmotifHandlersMixin)
    assert SoundscapeState is not None


def test_soundscape_aggregate_submodules_line_count_invariants():
    """Verify aggregate.py is strictly < 80 lines and all handler modules strictly < 150 lines."""
    soundscape_dir = REPO_ROOT / "services" / "soundscape" / "src" / "soundscape"
    aggregate_file = soundscape_dir / "aggregate.py"
    handlers_dir = soundscape_dir / "handlers"

    assert aggregate_file.exists(), "aggregate.py must exist"
    agg_lines = len(aggregate_file.read_text(encoding="utf-8").splitlines())
    assert agg_lines < 80, f"aggregate.py ({agg_lines} lines) exceeds strict 80-line limit"

    expected_handlers = ["__init__.py", "stems.py", "foley.py", "tension.py", "leitmotif.py"]
    for handler_name in expected_handlers:
        handler_file = handlers_dir / handler_name
        assert handler_file.exists(), f"Handler module {handler_file} must exist"
        h_lines = len(handler_file.read_text(encoding="utf-8").splitlines())
        assert h_lines < 150, (
            f"Handler submodule {handler_name} ({h_lines} lines) exceeds strict 150-line limit"
        )


def test_soundscape_event_handlers_registry_completeness():
    """Verify all domain events are mapped to @handles methods on SoundscapeAggregate."""
    registered_events = set(SoundscapeAggregate._event_handlers.keys())
    expected_events = {
        SoundscapeTrackChanged,
        SoundscapeCueTriggered,
        SoundscapeTensionUpdated,
        SoundscapeMoodOverridden,
        SoundscapeDuckingToggled,
        LeitmotifProfileConfigured,
        LeitmotifTriggered,
    }
    missing = expected_events - registered_events
    assert not missing, (
        f"Missing registered domain event handlers on SoundscapeAggregate: {missing}"
    )


@pytest.mark.asyncio
async def test_full_aggregate_domain_lifecycle_and_reconstitution():
    """Verify full domain event sourcing across mixins and event replay via AggregateRepository."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=SoundscapeAggregate)

    agg_id = uuid4()
    session_id = f"session-modular-{agg_id.hex[:8]}"

    # 1. Instantiate and apply domain commands across all mixins
    agg = SoundscapeAggregate(agg_id)

    # Stems mixin
    agg.record_track_change(
        session_id=session_id,
        track_id="track-dungeon-01",
        stem_profile="exploration",
        tension_score=20,
        crossfade_duration_ms=2000,
        active_stems=["ambient"],
    )
    assert agg.state.current_track_id == "track-dungeon-01"
    assert agg.state.stem_profile == "exploration"

    # Tension mixin
    agg.record_tension_update(
        session_id=session_id,
        tension_score=65,
        stem_profile="combat",
        combat_round=2,
        enemy_cr_balance=2.5,
        lowest_health_ratio=0.5,
    )
    assert agg.state.tension_score == 65
    assert agg.state.stem_profile == "combat"

    # Tension mixin mood override
    agg.record_mood_override(session_id=session_id, mood="boss")
    assert agg.state.manual_override is True
    assert agg.state.stem_profile == "boss"

    # Foley mixin
    agg.record_cue(
        session_id=session_id,
        cue_id="cue-sword-clash",
        sound_url="https://s3.local/foley/sword.wav",
        volume_gain=0.9,
        duck_music=True,
    )
    assert len(agg.state.cues_history) == 1
    assert agg.state.cues_history[0]["cue_id"] == "cue-sword-clash"

    agg.record_ducking_toggle(session_id=session_id, is_ducked=True, attenuation_db=-12.0)
    assert agg.state.is_ducked is True
    assert agg.state.ducking_attenuation_db == -12.0

    # Leitmotif mixin
    agg.record_leitmotif_profile(
        session_id=session_id,
        character_id="char-valeros",
        character_name="Valeros",
        instrument_timbre="brass",
        tempo_multiplier=1.1,
    )
    assert "char-valeros" in agg.state.character_profiles

    agg.record_leitmotif_trigger(
        session_id=session_id,
        character_id="char-valeros",
        character_name="Valeros",
        motif_type="triumphant",
        instrument_timbre="brass",
    )
    assert agg.state.active_leitmotif is not None
    assert agg.state.active_leitmotif["character_id"] == "char-valeros"
    assert len(agg.state.leitmotif_history) == 1

    # Save uncommitted events into event store
    await repo.save(agg)

    # 2. Reconstitute aggregate from event store
    reconstituted = await repo.load(agg_id)
    assert reconstituted is not None
    assert reconstituted.state.current_track_id == "track-dungeon-01"
    assert reconstituted.state.tension_score == 65
    assert reconstituted.state.manual_override is True
    assert reconstituted.state.stem_profile == "boss"
    assert reconstituted.state.is_ducked is True
    assert len(reconstituted.state.cues_history) == 1
    assert "char-valeros" in reconstituted.state.character_profiles
    assert reconstituted.state.active_leitmotif["character_id"] == "char-valeros"


def test_frontdoor_http_endpoints_with_decomposed_aggregate(client: TestClient):
    """Verify public HTTP frontdoors interact seamlessly with the decomposed aggregate."""
    session_id = "session-e2e-frontdoor-test"

    # 1. POST /api/v1/soundscape/override
    override_resp = client.post(
        "/api/v1/soundscape/override",
        json={
            "session_id": session_id,
            "mood": "combat",
        },
    )
    assert override_resp.status_code == 200
    data = override_resp.json()
    assert data["session_id"] == session_id
    assert data["stem_profile"] == "combat"
    assert data["manual_override"] is True

    # 2. POST /api/v1/soundscape/tension/calculate
    tension_resp = client.post(
        "/api/v1/soundscape/tension/calculate",
        json={
            "session_id": session_id,
            "combat_active": True,
            "combat_round": 1,
            "enemy_cr_balance": 1.0,
            "lowest_party_health_ratio": 0.8,
        },
    )
    assert tension_resp.status_code == 200
    tension_data = tension_resp.json()
    assert tension_data["session_id"] == session_id
    assert "tension_score" in tension_data

    # 3. POST /api/v1/soundscape/cue
    cue_resp = client.post(
        "/api/v1/soundscape/cue",
        json={
            "session_id": session_id,
            "cue_id": "cue-door-creak",
            "cue_type": "foley",
            "sound_url": "https://s3.local/foley/door.wav",
            "volume_gain": 0.8,
            "duck_music": False,
        },
    )
    assert cue_resp.status_code == 200
    cue_data = cue_resp.json()
    assert "cue_id" in cue_data
    assert cue_data["status"] == "triggered"

    # 4. POST /api/v1/soundscape/duck
    duck_resp = client.post(
        "/api/v1/soundscape/duck",
        json={
            "session_id": session_id,
            "is_ducked": True,
            "reason": "speech",
        },
    )
    assert duck_resp.status_code == 200
    assert duck_resp.json()["is_ducked"] is True

    # 5. POST /api/v1/soundscape/leitmotif/profile
    motif_profile_resp = client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json={
            "session_id": session_id,
            "character_id": "player-1",
            "character_name": "Lyra",
            "instrument_timbre": "lute",
            "tempo_multiplier": 1.0,
            "volume_gain": 1.0,
        },
    )
    assert motif_profile_resp.status_code == 200
    motif_data = motif_profile_resp.json()
    assert motif_data["character_id"] == "player-1"
