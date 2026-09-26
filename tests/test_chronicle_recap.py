"""Tests for Absentee Session Chronicle and Audio Recap Engine (TASK-0011).

Verifies:
1. ChronicleRecapEngine generation with 'drunk', 'foolishness', 'greed', and no penalties.
2. AbsenteeRecapGenerated event serialization, CloudEvents 1.0 compliance, and registry lookup.
3. The Watcher REST endpoint POST /api/v1/watcher/chronicle/recap with FastAPI TestClient.
"""

import pytest
from eventsource.domain.event_registry import default_registry
from fastapi.testclient import TestClient
from runefoble_events.events import AbsenteeRecapGenerated
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from the_watcher.chronicle import ChronicleRecapEngine
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus


@pytest.fixture
def chronicle_engine() -> ChronicleRecapEngine:
    return ChronicleRecapEngine()


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(watcher_app)


# ---------------------------------------------------------------------------
# 1. Unit Tests: ChronicleRecapEngine Penalty & Persona Generation
# ---------------------------------------------------------------------------


def test_chronicle_recap_drunk_penalty(chronicle_engine: ChronicleRecapEngine):
    """'drunk' penalty must incorporate slurred speech, swaying, hiccups, and stumble heroics."""
    recap = chronicle_engine.generate_recap(
        session_id="session-drunk-1",
        character_id="char-kyra-1",
        character_name="Kyra",
        stand_in_persona="scholarly",
        penalties=["drunk"],
        actions=[
            {
                "action_description": "Kyra swayed on her heels and swung wildly at shadows.",
                "dialogue": "Hic! The ale only sharpens my divine aim!",
            }
        ],
        hp_delta=-4,
        items_acquired=["Tavern Mug", "Half-empty Dwarven Stout"],
    )

    assert isinstance(recap, AbsenteeRecapGenerated)
    assert recap.character_name == "Kyra"
    assert recap.stand_in_persona == "scholarly"
    assert "drunk" in recap.penalties
    assert recap.hp_delta == -4
    assert "Tavern Mug" in recap.items_acquired

    narrative = recap.narrative_summary.lower()
    assert "drunk" in narrative
    assert "sway" in narrative
    assert "hiccup" in narrative or "hic" in narrative
    assert "slur" in narrative or "stumble" in narrative
    assert "4 damage" in narrative

    assert len(recap.highlights) >= 2
    assert any("sway" in h.lower() or "stumble" in h.lower() for h in recap.highlights)


def test_chronicle_recap_foolishness_penalty(chronicle_engine: ChronicleRecapEngine):
    """'foolishness' penalty must include coat rack blunder, ignoring tactical cover, and absurd bravado."""
    recap = chronicle_engine.generate_recap(
        session_id="session-foolish-2",
        character_id="char-merisiel-2",
        character_name="Merisiel",
        stand_in_persona="impulsive",
        penalties=["foolishness"],
        actions=[],
        hp_delta=0,
        items_acquired=["Rusty Key"],
    )

    assert recap.character_name == "Merisiel"
    assert "foolishness" in recap.penalties

    narrative = recap.narrative_summary.lower()
    assert "coat rack" in narrative
    assert "goblin" in narrative
    assert "tactical cover" in narrative or "foolishness" in narrative

    assert len(recap.highlights) >= 2
    assert any("coat rack" in h.lower() for h in recap.highlights)


def test_chronicle_recap_greed_and_cowardice_penalties(chronicle_engine: ChronicleRecapEngine):
    """Multiple penalties ('greed', 'cowardice') should blend both narrative elements."""
    recap = chronicle_engine.generate_recap(
        session_id="session-multi-3",
        character_id="char-valeros-3",
        character_name="Valeros",
        stand_in_persona="valiant",
        penalties=["greed", "cowardice"],
        actions=[
            {
                "action_description": "Valeros ducked behind a column to count shiny silver pieces.",
                "dialogue": "Securing the spoils for the kingdom!",
            }
        ],
        hp_delta=5,
        items_acquired=["Cursed Copper Coins", "Gilded Urn"],
    )

    assert "greed" in recap.penalties
    assert "cowardice" in recap.penalties
    assert recap.hp_delta == 5

    narrative = recap.narrative_summary.lower()
    assert "greed" in narrative
    assert "cursed copper" in narrative
    assert "cowardice" in narrative or "cover" in narrative
    assert "5 hp healthier" in narrative


def test_chronicle_recap_no_penalties(chronicle_engine: ChronicleRecapEngine):
    """Absence without penalties generates a disciplined, heroic chronicle."""
    recap = chronicle_engine.generate_recap(
        session_id="session-heroic-4",
        character_id="char-ezren-4",
        character_name="Ezren",
        stand_in_persona="scholarly",
        penalties=[],
        actions=[
            {
                "action_description": "Ezren maintained precise defensive wards protecting the flank.",
                "dialogue": "Hold your positions!",
            }
        ],
        hp_delta=0,
        items_acquired=["Ancient Scroll"],
    )

    assert recap.penalties == []
    assert recap.character_name == "Ezren"
    narrative = recap.narrative_summary.lower()
    assert "steadfast" in narrative or "discipline" in narrative
    assert "drunk" not in narrative
    assert "foolishness" not in narrative
    assert len(recap.highlights) >= 1


# ---------------------------------------------------------------------------
# 2. CloudEvents Compliance & Event Serialization
# ---------------------------------------------------------------------------


def test_recap_cloudevents_compliance(chronicle_engine: ChronicleRecapEngine):
    """AbsenteeRecapGenerated must serialize into valid CloudEvents 1.0 JSON."""
    recap = chronicle_engine.generate_recap(
        session_id="e5b12850-8919-4cb3-a607-b3fae32230be",
        character_id="c001",
        character_name="Kyra",
        stand_in_persona="scholarly",
        penalties=["drunk"],
        actions=[],
        hp_delta=-2,
        items_acquired=["Holy Symbol"],
        audio_url="https://cdn.runefoble.local/audio/recap-001.mp3",
    )

    ce = recap.to_cloudevent_dict()

    assert ce["specversion"] == "1.0"
    assert ce["id"] == str(recap.event_id)
    assert ce["type"] == "runefoble.events.recap.generated"
    assert ce["datacontenttype"] == "application/json"
    assert "/runefoble/chronicle/" in ce["source"]

    data = ce["data"]
    assert data["session_id"] == "e5b12850-8919-4cb3-a607-b3fae32230be"
    assert data["character_name"] == "Kyra"
    assert data["penalties"] == ["drunk"]
    assert data["hp_delta"] == -2
    assert data["items_acquired"] == ["Holy Symbol"]
    assert data["audio_url"] == "https://cdn.runefoble.local/audio/recap-001.mp3"


def test_recap_registered_in_default_registry():
    """Event must be discovered in the global eventsource-py EventRegistry."""
    cls = default_registry.get("runefoble.events.recap.generated")
    assert cls is not None
    assert cls is AbsenteeRecapGenerated


# ---------------------------------------------------------------------------
# 3. Integration Tests: The Watcher API Endpoint
# ---------------------------------------------------------------------------


def test_post_chronicle_recap_endpoint(test_client: TestClient):
    """POST /api/v1/watcher/chronicle/recap must accept RecapRequest and return AbsenteeRecapGenerated."""
    mock_bus = RedisStreamsEventBus(client=MockAsyncRedis())
    set_event_bus(mock_bus)

    payload = {
        "session_id": "sess-test-42",
        "character_id": "char-test-7",
        "character_name": "Seoni",
        "stand_in_persona": "impulsive",
        "penalties": ["foolishness", "greed"],
        "actions": [
            {
                "action_description": "Seoni launched a dazzling firework at a stone statue.",
                "dialogue": "Watch this sparkle!",
            }
        ],
        "hp_delta": -5,
        "items_acquired": ["Ruby Amulet", "Cursed Copper"],
        "audio_url": "/api/v1/voice/chronicle/sess-test-42/char-test-7.mp3",
    }

    res = test_client.post("/api/v1/watcher/chronicle/recap", json=payload)
    assert res.status_code == 200, res.text

    data = res.json()
    assert data["session_id"] == "sess-test-42"
    assert data["character_name"] == "Seoni"
    assert data["stand_in_persona"] == "impulsive"
    assert data["penalties"] == ["foolishness", "greed"]
    assert data["hp_delta"] == -5
    assert data["items_acquired"] == ["Ruby Amulet", "Cursed Copper"]
    assert data["audio_url"] == "/api/v1/voice/chronicle/sess-test-42/char-test-7.mp3"
    assert len(data["highlights"]) >= 2
    assert "coat rack" in data["narrative_summary"].lower()
    assert "cursed copper" in data["narrative_summary"].lower()
