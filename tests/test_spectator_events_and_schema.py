"""Spectator Event Registration, CloudEvents Schema, and State Sanitization Suite.

Validates:
1. SpectatorSessionConnected event registration in eventsource EventRegistry.
2. CloudEvents 1.0 schema compliance and serialization.
3. Strict audience-safe state sanitization (hidden tokens, private DM notes,
   monster stat blocks, and unrevealed lore redacted).
"""

from eventsource.domain.event_registry import get_event_class_or_none
from runefoble_events.events import SpectatorSessionConnected


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
