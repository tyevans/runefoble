"""Blackbox tests verifying reaction intent extraction and spoken trigger grammar (TASK-0155)."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from the_watcher.intent.reactions import parse_reaction_intent


def test_reaction_grammar_extraction():
    """Verify regex and lexical extraction of spoken reaction triggers."""
    # 1. Shield
    r1 = parse_reaction_intent("Shield!", "Marcus")
    assert r1 is not None and r1.reaction_type == "shield"
    assert r1.action_type == "reaction"
    assert r1.parameters.get("spell") == "Shield"

    r2 = parse_reaction_intent("I cast Shield", "Marcus")
    assert r2 is not None and r2.reaction_type == "shield"

    # 2. Counterspell
    r3 = parse_reaction_intent("Counterspell!", "Merisiel")
    assert r3 is not None and r3.reaction_type == "counterspell"
    assert r3.action_type == "reaction"

    # 3. Opportunity attack with target
    r4 = parse_reaction_intent("Opportunity attack on the goblin", "Valeros")
    assert r4 is not None and r4.reaction_type == "opportunity_attack"
    assert r4.target == "goblin"

    # 4. Opportunity attack without target
    r5 = parse_reaction_intent("Opportunity attack!", "Valeros")
    assert r5 is not None and r5.reaction_type == "opportunity_attack"
    assert r5.target is None

    # 5. Ready action with condition
    r6 = parse_reaction_intent(
        "I ready my crossbow to shoot if the goblin steps into the hallway", "Marcus"
    )
    assert r6 is not None and r6.action_type == "ready_action"
    assert "crossbow" in (r6.readied_action or "")
    assert "hallway" in (r6.trigger_condition or "")
    assert r6.trigger_type == "enemy_enters_range"

    # 6. Absorb elements and Hellish rebuke
    r7 = parse_reaction_intent("I cast Absorb Elements", "Kyra")
    assert r7 is not None and r7.reaction_type == "absorb_elements"

    r8 = parse_reaction_intent("Hellish Rebuke on the cultist", "Ezren")
    assert r8 is not None and r8.reaction_type == "hellish_rebuke"
    assert r8.target == "cultist"

    # 7. Uncanny dodge
    r9 = parse_reaction_intent("I use uncanny dodge", "Merisiel")
    assert r9 is not None and r9.reaction_type == "uncanny_dodge"


def test_watcher_transcribe_and_act_recognizes_reaction(watcher_client: TestClient):
    """Verify The Watcher public intent endpoint recognizes spoken reactions."""
    session_id = str(uuid4())
    campaign_id = str(uuid4())

    res = watcher_client.post(
        "/api/v1/watcher/transcribe-and-act",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "speaker_id": "player_marcus",
            "speaker_name": "Marcus",
            "transcript": "I cast Shield!",
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["action_type"] == "reaction"
    assert data["confidence"] >= 0.9
    assert data["parameters"].get("spell") == "Shield"
    assert "Marcus" in data["watcher_reply"]
