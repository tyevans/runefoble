import pytest
from the_watcher.watcher_ai import TheWatcherEngine


def test_speech_to_movement_intent():
    engine = TheWatcherEngine()
    result = engine.parse_speech_intent("I step 3 squares north towards the chest", "Valeros")
    assert result.action_type == "move"
    assert result.parameters["steps"] == 3
    assert result.parameters["direction"] == "north"
    assert result.parameters["dy"] == -3
    assert "Valeros" in result.watcher_reply


def test_speech_to_attack_intent():
    engine = TheWatcherEngine()
    result = engine.parse_speech_intent("I slash at the goblin with my sword!", "Valeros")
    assert result.action_type == "attack"
    assert "Valeros" in result.watcher_reply


def test_missing_player_stand_in_with_drunk_penalty():
    engine = TheWatcherEngine()
    stand_in = engine.generate_stand_in_action(
        character_name="Kyra",
        character_class="Cleric",
        penalties=["drunk"],
        scene_context="Cavern ambush",
    )
    assert stand_in.character_name == "Kyra"
    assert "Hic!" in stand_in.dialogue
    assert "Drunk" in (stand_in.penalty_influence or "")
    assert stand_in.dice_roll_required == "1d20-2"


def test_missing_player_stand_in_with_foolishness():
    engine = TheWatcherEngine()
    stand_in = engine.generate_stand_in_action(
        character_name="Kyra",
        character_class="Cleric",
        penalties=["foolishness"],
        scene_context="Cavern ambush",
    )
    assert "danger" in stand_in.dialogue.lower()
    assert "Foolishness" in (stand_in.penalty_influence or "")
