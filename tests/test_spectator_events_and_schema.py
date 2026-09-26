"""Spectator Event Registration, CloudEvents Schema, and State Sanitization Suite.

Validates:
1. SpectatorSessionConnected event registration in eventsource EventRegistry.
2. CloudEvents 1.0 schema compliance and serialization.
3. Strict audience-safe state sanitization (hidden tokens, private DM notes,
   monster stat blocks, and unrevealed lore redacted).
"""

from eventsource.domain.event_registry import get_event_class_or_none
from gateway_api.spectator import sanitize_spectator_state
from runefoble_events import SpectatorSessionConnected


def test_spectator_session_connected_event_registration():
    """Verify SpectatorSessionConnected is properly registered in eventsource EventRegistry."""
    event_cls = get_event_class_or_none("runefoble.events.spectator.connected")
    assert event_cls is not None
    assert event_cls is SpectatorSessionConnected

    event = SpectatorSessionConnected(
        session_id="session-alpha",
        viewer_id="viewer-101",
        viewer_name="TwitchSpectator",
        connected_at="2026-09-26T04:00:00Z",
    )
    assert event.aggregate_type == "Spectator"
    assert event.session_id == "session-alpha"
    assert event.viewer_id == "viewer-101"
    assert event.viewer_name == "TwitchSpectator"


def test_spectator_session_connected_cloudevents_compliance():
    """Verify SpectatorSessionConnected satisfies standard CloudEvents 1.0 schema."""
    event = SpectatorSessionConnected(
        session_id="session-ce-1",
        viewer_id="obs_source_main",
        viewer_name="OBS Stream Source",
        connected_at="2026-09-26T04:15:00Z",
    )
    ce = event.to_cloudevent_dict()

    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.spectator.connected"
    assert ce["source"] == f"/runefoble/spectator/{event.aggregate_id}"
    assert ce["datacontenttype"] == "application/json"
    assert ce["data"]["session_id"] == "session-ce-1"
    assert ce["data"]["viewer_id"] == "obs_source_main"
    assert ce["data"]["viewer_name"] == "OBS Stream Source"
    assert ce["data"]["connected_at"] == "2026-09-26T04:15:00Z"


def test_sanitize_spectator_state_strips_hidden_tokens_and_secret_notes():
    """Verify that hidden tokens, monster stat blocks, and private notes are completely stripped."""
    raw_state = {
        "session_id": "sess-san-1",
        "status": "active",
        "round": 4,
        "cols": 10,
        "rows": 10,
        "tokens": [
            {
                "id": "t-valeros",
                "name": "Valeros",
                "x": 2,
                "y": 3,
                "color": "#2563eb",
                "conditions": ["Blessed"],
                "hp": 45,
                "max_hp": 45,
                "ac": 18,
                "dm_notes": "Carries secret map.",
            },
            {
                "id": "t-kyra",
                "name": "Kyra",
                "x": 3,
                "y": 3,
                "color": "#db2777",
                "conditions": ["Drunk (Missed Session)"],
                "is_ai_controlled": True,
                "hp": 28,
                "max_hp": 32,
            },
            {
                "id": "t-hidden-scout",
                "name": "Goblin Scout",
                "x": 7,
                "y": 7,
                "hidden": True,
                "hp": 10,
                "stat_block": {"cr": "1/4", "stealth": "+6"},
            },
            {
                "id": "t-secret-mimic",
                "name": "Treasure Chest",
                "x": 5,
                "y": 5,
                "is_secret": True,
                "hp": 58,
                "dm_notes": "Mimic waiting to strike.",
            },
            {
                "id": "t-phantom",
                "name": "Shadow Phantom",
                "x": 1,
                "y": 1,
                "is_hidden": True,
                "hp": 30,
            },
        ],
        "dm_notes": "Secret GM encounter notes: Trap at (5,5), DC 15 Dex save or 3d6 poison.",
        "monster_stat_blocks": {
            "goblin_scout": {"cr": "1/4", "hp": 10, "ac": 13},
            "mimic": {"cr": "2", "hp": 58, "ac": 12},
        },
        "atmosphere": {
            "location_name": "Forgotten Sepulcher",
            "lighting": "Pale eerie luminescence",
            "mood": "Ominous",
            "description": "Granite walls sweat ancient moisture.",
            "ambient_audio_prompt": "dripping water, distant scraping",
            "private_dm_lore": "This was the resting place of Emperor Taraph.",
        },
        "chronicle": [
            {
                "id": "c1",
                "speaker": "Valeros",
                "text": "I ready my sword and shield.",
                "timestamp": "2026-09-26T04:20:00Z",
                "action_type": "speech",
            },
            {
                "id": "c2",
                "speaker": "The Watcher",
                "text": "The crypt air is heavy with suspense.",
                "timestamp": "2026-09-26T04:20:05Z",
                "action_type": "dm_ruling",
            },
            {
                "id": "c_secret",
                "speaker": "The Watcher (Private Note)",
                "text": "Secret DC 14 stealth check passed by goblin.",
                "timestamp": "2026-09-26T04:20:06Z",
                "is_private": True,
            },
        ],
    }

    sanitized = sanitize_spectator_state(raw_state)

    # 1. Hidden tokens must be filtered out
    token_ids = [t["id"] for t in sanitized["tokens"]]
    assert "t-valeros" in token_ids
    assert "t-kyra" in token_ids
    assert "t-hidden-scout" not in token_ids
    assert "t-secret-mimic" not in token_ids
    assert "t-phantom" not in token_ids
    assert len(sanitized["tokens"]) == 2

    # 2. Token stat blocks and private DM notes must be redacted
    for t in sanitized["tokens"]:
        assert "hp" not in t
        assert "max_hp" not in t
        assert "ac" not in t
        assert "stat_block" not in t
        assert "dm_notes" not in t
        assert "name" in t
        assert "x" in t
        assert "y" in t
        assert "conditions" in t

    # 3. Root secret fields must NOT be present
    assert "dm_notes" not in sanitized
    assert "monster_stat_blocks" not in sanitized

    # 4. Private chronicle entries must be stripped
    chronicle_ids = [c["id"] for c in sanitized["chronicle"]]
    assert "c1" in chronicle_ids
    assert "c2" in chronicle_ids
    assert "c_secret" not in chronicle_ids

    # 5. Atmosphere retains public sensory info and strips private lore
    assert sanitized["atmosphere"]["location_name"] == "Forgotten Sepulcher"
    assert sanitized["atmosphere"]["mood"] == "Ominous"
    assert "private_dm_lore" not in sanitized["atmosphere"]
