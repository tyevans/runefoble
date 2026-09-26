"""Unit tests for decomposed movement_parser, grammars, and spatial math submodules."""

import pytest
from the_watcher.grammars import (
    CARDINAL_DIR_FIRST_PATTERN,
    CARDINAL_DIST_FIRST_PATTERN,
    COORD_PATTERN,
    DICE_PATTERN,
    FLANK_PATTERN,
    MOVE_TO_TOKEN_PATTERN,
    SKILL_PATTERN,
    SPELL_PATTERN,
)
from the_watcher.movement_parser import SpeechIntentParser
from the_watcher.spatial import (
    calculate_bounded_destination,
    calculate_steps,
    compute_directional_deltas,
)


@pytest.fixture
def parser() -> SpeechIntentParser:
    return SpeechIntentParser()


def test_spatial_compute_directional_deltas():
    assert compute_directional_deltas("north", 3) == (0, -3)
    assert compute_directional_deltas("up", 2) == (0, -2)
    assert compute_directional_deltas("south", 4) == (0, 4)
    assert compute_directional_deltas("down", 1) == (0, 1)
    assert compute_directional_deltas("east", 5) == (5, 0)
    assert compute_directional_deltas("right", 2) == (2, 0)
    assert compute_directional_deltas("west", 3) == (-3, 0)
    assert compute_directional_deltas("left", 1) == (-1, 0)
    assert compute_directional_deltas("northeast", 2) == (2, -2)
    assert compute_directional_deltas("north-west", 3) == (-3, -3)
    assert compute_directional_deltas("south-east", 1) == (1, 1)
    assert compute_directional_deltas("southwest", 2) == (-2, 2)


def test_spatial_calculate_steps():
    assert calculate_steps(15, "feet") == 3
    assert calculate_steps(10, "ft") == 2
    assert calculate_steps(3, "foot") == 1
    assert calculate_steps(0, "feet") == 0
    assert calculate_steps(4, "squares") == 4
    assert calculate_steps(2, None) == 2


def test_spatial_calculate_bounded_destination():
    assert calculate_bounded_destination(5, 5, 2, -2, cols=12, rows=12) == (7, 3)
    assert calculate_bounded_destination(1, 1, -5, -5, cols=12, rows=12) == (0, 0)
    assert calculate_bounded_destination(10, 10, 5, 5, cols=12, rows=12) == (11, 11)


def test_grammar_patterns_direct_matching():
    assert COORD_PATTERN.search("dash to 8, 9") is not None
    assert CARDINAL_DIST_FIRST_PATTERN.search("charge 4 squares east") is not None
    assert CARDINAL_DIR_FIRST_PATTERN.search("advance west 2 tiles") is not None
    assert FLANK_PATTERN.search("flank goblin chief") is not None
    assert SPELL_PATTERN.search("channel cure wounds at paladin") is not None
    assert MOVE_TO_TOKEN_PATTERN.search("run adjacent to the dragon") is not None
    assert SKILL_PATTERN.search("roll for acrobatics check") is not None
    assert DICE_PATTERN.search("roll 3d6+2") is not None


def test_parser_backward_compatible_methods(parser: SpeechIntentParser):
    assert parser.compute_directional_deltas("north", 2) == (0, -2)
    assert parser.calculate_steps(20, "feet") == 4
    assert parser.calculate_bounded_destination(2, 2, 3, 3, 10, 10) == (5, 5)
    assert hasattr(parser, "_coord_pattern")
    assert hasattr(parser, "_cardinal_pattern_dist_first")
    assert hasattr(parser, "_flank_pattern")


def test_parser_intent_extraction_actions(parser: SpeechIntentParser):
    # Coordinate
    c_res = parser.parse_speech_intent("step to (7, 9)", "Valeros")
    assert c_res.action_type == "move"
    assert c_res.parameters["to_x"] == 7 and c_res.parameters["to_y"] == 9

    # Direction-first cardinal
    d_res = parser.parse_speech_intent("walk north 2 squares", "Kyra")
    assert d_res.action_type == "move"
    assert d_res.parameters["direction"] == "north"
    assert d_res.parameters["dy"] == -2

    # Spellcasting with coordinate target
    s_res = parser.parse_speech_intent("cast fireball at (3, 4)", "Ezren")
    assert s_res.action_type == "cast_spell"
    assert s_res.parameters["target_x"] == 3 and s_res.parameters["target_y"] == 4

    # Move to target token
    m_res = parser.parse_speech_intent("advance next to the troll", "Merisiel")
    assert m_res.action_type == "move"
    assert m_res.parameters["target_token"] == "troll"

    # Generic attack
    a_res = parser.parse_speech_intent("cleave", "Valeros")
    assert a_res.action_type == "attack"
    assert a_res.parameters["target"] == "nearest_enemy"

    # Generic check
    g_res = parser.parse_speech_intent("roll strength check", "Valeros")
    assert g_res.action_type == "skill_check"
    assert g_res.parameters["skill"] == "strength"

    # Dice roll starting with d
    r_res = parser.parse_speech_intent("roll a d20", "Kyra")
    assert r_res.action_type == "roll_dice"
    assert r_res.parameters["notation"] == "1d20"

    # Narrative default
    n_res = parser.parse_speech_intent("I search the dark walls for ancient runes", "Ezren")
    assert n_res.action_type == "narrative"
    assert "dark walls" in n_res.details
