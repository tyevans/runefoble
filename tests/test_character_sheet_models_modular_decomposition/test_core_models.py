"""Core attributes, vitals, and model facade invariant tests."""

from __future__ import annotations

from character_sheet.models import (
    AttributeScores,
    CharacterState,
)


def test_attribute_scores_and_serialization() -> None:
    """Verify AttributeScores property access and serialization."""
    scores = AttributeScores(str=16, dex=14, con=15, intelligence=12, wis=10, cha=8)
    assert scores.str == 16 and scores.int == 12
    dict_scores = scores.to_dict()
    assert dict_scores["str"] == 16 and dict_scores["int"] == 12


def test_vitals_health_transitions_and_guardrails(sample_character_state: CharacterState) -> None:
    """Verify health mutations, stand-in guardrails, and unconscious stabilization."""
    damaged = sample_character_state.with_health(25)
    assert sample_character_state.current_hp == 40
    assert damaged.current_hp == 25

    guardrails = damaged.with_stand_in_guardrails(
        {"avoid_melee": False, "risk_threshold": "reckless"}
    )
    assert guardrails.stand_in_guardrails.risk_threshold == "reckless"

    stabilized = damaged.with_stabilized()
    assert stabilized.current_hp == 0 and stabilized.is_stabilized is True
    assert "unconscious_stabilized" in stabilized.conditions
