"""Unit tests for Missing Player AI Stand-In Tactics and Personality Mechanics (TASK-0070, TASK-0003).

Verifies:
1. Stand-in action generation penalty modifiers ("drunk", "foolishness", "cowardice", "greed").
2. Dice roll formula adjustments, slurred dialogue, defensive positioning, distraction effects, and looting behavior.
3. Personality trait flavor integration ("scholarly", "valiant", "impulsive") with combined penalty conditions.
"""

import pytest
from the_watcher.watcher_ai import TheWatcherEngine


@pytest.fixture
def watcher_engine() -> TheWatcherEngine:
    return TheWatcherEngine()


# ---------------------------------------------------------------------------
# Stand-In Penalties & Personality Trait Mechanics Unit Tests
# ---------------------------------------------------------------------------


def test_stand_in_drunk_penalty_mechanics(watcher_engine: TheWatcherEngine):
    """'drunk' penalty must inflict disadvantage / roll penalty (1d20-2) and slurred speech."""
    action = watcher_engine.generate_stand_in_action(
        character_name="Kyra",
        character_class="Cleric",
        penalties=["drunk"],
        scene_context="Goblins surrounding the campsite",
    )
    assert action.character_name == "Kyra"
    assert action.dice_roll_required == "1d20-2"
    assert "Hic!" in action.dialogue
    assert "Drunk" in (action.penalty_influence or "")
    assert "-2 penalty" in (action.penalty_influence or "")
    assert "sway" in action.action_description.lower()
    assert action.action_type == "attack"


def test_stand_in_foolishness_penalty_mechanics(watcher_engine: TheWatcherEngine):
    """'foolishness' penalty must create reckless distraction and impose disadvantage on enemies attacking allies."""
    action = watcher_engine.generate_stand_in_action(
        character_name="Valeros",
        character_class="Fighter",
        penalties=["foolishness"],
        scene_context="Dragon lair encounter",
    )
    assert action.character_name == "Valeros"
    assert "danger" in action.dialogue.lower()
    assert "Foolishness" in (action.penalty_influence or "")
    assert "distraction" in (action.penalty_influence or "").lower()
    assert "disadvantage on enemy attacks" in (action.penalty_influence or "").lower()
    assert "recklessly" in action.action_description.lower()
    assert action.action_type == "attack"


def test_stand_in_cowardice_penalty_mechanics(watcher_engine: TheWatcherEngine):
    """'cowardice' penalty must trigger full defensive posturing and retreat behavior."""
    action = watcher_engine.generate_stand_in_action(
        character_name="Merisiel",
        character_class="Rogue",
        penalties=["cowardice"],
        scene_context="Troll ambush",
    )
    assert action.character_name == "Merisiel"
    assert action.action_type == "defend"
    assert "Cowardice" in (action.penalty_influence or "")
    assert "defensive posture" in (action.penalty_influence or "").lower()
    assert "retreat" in (action.penalty_influence or "").lower()


def test_stand_in_greed_penalty_mechanics(watcher_engine: TheWatcherEngine):
    """'greed' penalty must prioritize looting and chest searching over tactical positioning."""
    action = watcher_engine.generate_stand_in_action(
        character_name="Ezren",
        character_class="Wizard",
        penalties=["greed"],
        scene_context="Ancient crypt fight",
    )
    assert action.character_name == "Ezren"
    assert action.action_type == "loot"
    assert "Greed" in (action.penalty_influence or "")
    assert "looting" in (action.penalty_influence or "").lower()


def test_personality_traits_alter_dialogue_and_tactics(watcher_engine: TheWatcherEngine):
    """Personality traits ('scholarly', 'valiant', 'impulsive') must flavor dialogue and action choices."""
    # Scholarly + Drunk
    scholarly_drunk = watcher_engine.generate_stand_in_action(
        character_name="Ezren",
        character_class="Wizard",
        penalties=["drunk"],
        scene_context="Library skirmish",
        personality_traits=["scholarly"],
    )
    assert (
        "Arcane Volume IV" in scholarly_drunk.dialogue
        or "statistically" in scholarly_drunk.dialogue
    )
    assert "slurring arcane citations" in scholarly_drunk.action_description

    # Valiant + Foolishness
    valiant_fool = watcher_engine.generate_stand_in_action(
        character_name="Valeros",
        character_class="Fighter",
        penalties=["foolishness"],
        scene_context="Colosseum battle",
        personality_traits=["valiant"],
    )
    assert "glory" in valiant_fool.dialogue.lower()
    assert "distraction" in valiant_fool.action_description
    assert "disadvantage on enemy attacks" in (valiant_fool.penalty_influence or "").lower()

    # Impulsive (no penalty)
    impulsive_action = watcher_engine.generate_stand_in_action(
        character_name="Merisiel",
        character_class="Rogue",
        penalties=[],
        scene_context="In combat",
        personality_traits=["impulsive"],
    )
    assert "strike hard and fast" in impulsive_action.dialogue.lower()


def test_stand_in_test_suite_modular_decomposition_invariants():
    """Verify TASK-0070 decomposition: monolithic test file removed, modular suites < 220 lines."""
    from pathlib import Path

    tests_dir = Path(__file__).resolve().parent
    monolithic_file = tests_dir / "test_stand_in_engine.py"
    unit_suite = tests_dir / "test_stand_in_tactics_unit.py"
    service_suite = tests_dir / "test_blackbox_stand_in_service.py"

    assert not monolithic_file.exists(), "test_stand_in_engine.py should be decomposed and removed"
    assert unit_suite.exists()
    assert service_suite.exists()

    unit_lines = len(unit_suite.read_text().splitlines())
    service_lines = len(service_suite.read_text().splitlines())

    assert unit_lines < 220, (
        f"test_stand_in_tactics_unit.py exceeds 220 lines (current: {unit_lines})"
    )
    assert service_lines < 220, (
        f"test_blackbox_stand_in_service.py exceeds 220 lines (current: {service_lines})"
    )
