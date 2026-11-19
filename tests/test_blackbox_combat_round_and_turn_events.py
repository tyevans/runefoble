"""Blackbox test: combat round and turn events reach the event bus (TASK-0703).

Governed by Hard Invariant 7. Setup and verification go through public HTTP routes
of game_session. The assertions read the events that the service publishes to the
event bus. No private state is read.
"""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.helpers.game_session_app import session_app as app
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"})


def _published(mock_bus, event_type: str) -> list[dict]:
    """Return the payloads of every published event whose wire type is `event_type`."""
    found: list[dict] = []
    for entries in mock_bus.streams.values():
        for _entry_id, fields in entries:
            if fields.get("event_type") == event_type:
                found.append(json.loads(fields["payload"]))
    return found


def _combat_session_with_two_combatants(client: TestClient) -> tuple[str, str, str]:
    """Create a running session with an encounter that has two combatants.

    Returns (session_id, kyra_id, goblin_id).
    """
    campaign = client.post("/api/v1/campaigns", json={"title": "Round Events"})
    assert campaign.status_code == 201, campaign.text
    session = client.post(
        f"/api/v1/campaigns/{campaign.json()['id']}/sessions",
        json={"title": "Round Events"},
    )
    assert session.status_code == 201, session.text
    session_id = session.json()["id"]
    assert client.post(f"/api/v1/sessions/{session_id}/start").status_code == 200
    assert client.post(f"/api/v1/sessions/{session_id}/combat/start").status_code == 200

    kyra_id = str(uuid4())
    goblin_id = "npc-goblin-archer-round"
    for combatant_id, name, score, is_npc in (
        (kyra_id, "Kyra", 12, False),
        (goblin_id, "Goblin Archer", 15, True),
    ):
        roll = client.post(
            f"/api/v1/sessions/{session_id}/combat/initiative",
            json={
                "combatant_id": combatant_id,
                "combatant_name": name,
                "initiative_score": score,
                "is_npc": is_npc,
            },
        )
        assert roll.status_code == 200, roll.text
    return session_id, kyra_id, goblin_id


def test_blackbox_advancing_past_last_combatant_publishes_round_advanced(
    client: TestClient, mock_bus
):
    """Advancing the turn publishes TurnStarted each time. The wrap to round 2 also publishes CombatRoundAdvanced."""
    session_id, kyra_id, goblin_id = _combat_session_with_two_combatants(client)

    # The goblin rolled the higher score, so it is active at round 1.
    # Advancing once moves to Kyra and stays inside round 1.
    first = client.post(
        f"/api/v1/sessions/{session_id}/combat/next-turn", json={"turn_seconds": 45}
    )
    assert first.status_code == 200, first.text
    assert first.json()["combat_active_id"] == kyra_id
    assert first.json()["combat_round"] == 1
    assert _published(mock_bus, "runefoble.events.session.combat_round_advanced") == []

    # Advancing again wraps to the goblin in round 2.
    second = client.post(
        f"/api/v1/sessions/{session_id}/combat/next-turn", json={"turn_seconds": 45}
    )
    assert second.status_code == 200, second.text
    assert second.json()["combat_active_id"] == goblin_id
    assert second.json()["combat_round"] == 2

    rounds = _published(mock_bus, "runefoble.events.session.combat_round_advanced")
    assert len(rounds) == 1
    assert rounds[0]["round_number"] == 2
    assert rounds[0]["active_combatant_id"] == goblin_id

    turns = _published(mock_bus, "runefoble.events.session.turn_started")
    assert [t["character_id"] for t in turns[-2:]] == [kyra_id, goblin_id]
    assert turns[-2]["character_name"] == "Kyra"
