"""Tests for Bauhaus dice arithmetic engine, formula parser, and DiceRolled domain event."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from runefoble_events import DiceRolled
from runefoble_platform.dice import evaluate_dice, parse_and_roll

# ---------------------------------------------------------------------------
# Property-Based Invariant Tests (Hypothesis)
# ---------------------------------------------------------------------------


@given(
    count=st.integers(min_value=1, max_value=20),
    sides=st.integers(min_value=2, max_value=100),
    modifier=st.integers(min_value=-50, max_value=50),
)
def test_dice_bounds_property(count: int, sides: int, modifier: int) -> None:
    """Property: count * 1 + modifier <= total <= count * sides + modifier."""
    result = evaluate_dice(count=count, sides=sides, modifier=modifier)

    min_possible = count * 1 + modifier
    max_possible = count * sides + modifier

    assert min_possible <= result["total"] <= max_possible
    assert len(result["rolls"]) == count
    assert all(1 <= r <= sides for r in result["rolls"])
    assert result["kept_rolls"] == result["rolls"]
    assert result["count"] == count
    assert result["sides"] == sides
    assert result["modifier"] == modifier


@given(
    count=st.integers(min_value=2, max_value=10),
    sides=st.integers(min_value=2, max_value=20),
    modifier=st.integers(min_value=-20, max_value=20),
    keep_highest=st.integers(min_value=1, max_value=10),
)
def test_dice_keep_highest_bounds_property(
    count: int, sides: int, modifier: int, keep_highest: int
) -> None:
    """Property: Keep highest rolls bounds invariant."""
    result = evaluate_dice(
        count=count, sides=sides, modifier=modifier, keep_highest=keep_highest
    )
    effective_count = min(count, keep_highest)
    min_possible = effective_count * 1 + modifier
    max_possible = effective_count * sides + modifier

    assert min_possible <= result["total"] <= max_possible
    assert len(result["rolls"]) == count
    assert len(result["kept_rolls"]) == effective_count
    # Kept rolls must match the highest values in rolls
    assert sorted(result["kept_rolls"], reverse=True) == sorted(result["rolls"], reverse=True)[
        :effective_count
    ]


@given(
    count=st.integers(min_value=1, max_value=10),
    sides=st.sampled_from([4, 6, 8, 10, 12, 20, 100]),
    mod=st.integers(min_value=0, max_value=30),
    sign=st.sampled_from(["+", "-"]),
)
def test_parse_and_roll_formula_property(count: int, sides: int, mod: int, sign: str) -> None:
    """Property: Parsing standard XdY+Z generates matching configuration."""
    formula = f"{count}d{sides}{sign}{mod}"
    result = parse_and_roll(formula)

    expected_mod = mod if sign == "+" else -mod
    assert result["count"] == count
    assert result["sides"] == sides
    assert result["modifier"] == expected_mod
    assert len(result["rolls"]) == count


# ---------------------------------------------------------------------------
# Unit Tests for Advantage, Disadvantage, and Specific Notation
# ---------------------------------------------------------------------------


def test_advantage_d20_roll() -> None:
    """Test 2d20kh1+3 (advantage d20 keep highest 1)."""
    parsed = parse_and_roll("2d20kh1+3", fixed_rolls=[7, 19])
    assert parsed["count"] == 2
    assert parsed["sides"] == 20
    assert parsed["keep_highest"] == 1
    assert parsed["keep_lowest"] is None
    assert parsed["modifier"] == 3
    assert parsed["rolls"] == [7, 19]
    assert parsed["kept_rolls"] == [19]
    assert parsed["total"] == 22
    assert not parsed["is_crit"]
    assert not parsed["is_fumble"]


def test_advantage_critical_hit() -> None:
    """Natural 20 on advantage triggers critical hit even if first die was a 1."""
    parsed = parse_and_roll("2d20kh1+5", fixed_rolls=[1, 20])
    assert parsed["kept_rolls"] == [20]
    assert parsed["total"] == 25
    assert parsed["is_crit"] is True
    assert parsed["is_fumble"] is False


def test_disadvantage_d20_roll() -> None:
    """Test 2d20kl1+3 (disadvantage d20 keep lowest 1)."""
    parsed = parse_and_roll("2d20kl1+3", fixed_rolls=[14, 8])
    assert parsed["count"] == 2
    assert parsed["sides"] == 20
    assert parsed["keep_lowest"] == 1
    assert parsed["keep_highest"] is None
    assert parsed["modifier"] == 3
    assert parsed["rolls"] == [14, 8]
    assert parsed["kept_rolls"] == [8]
    assert parsed["total"] == 11
    assert not parsed["is_crit"]
    assert not parsed["is_fumble"]


def test_disadvantage_fumble() -> None:
    """Natural 1 on disadvantage triggers fumble even if second die was a 20."""
    parsed = parse_and_roll("2d20kl1+4", fixed_rolls=[1, 20])
    assert parsed["kept_rolls"] == [1]
    assert parsed["total"] == 5
    assert parsed["is_crit"] is False
    assert parsed["is_fumble"] is True


def test_stat_generation_4d6kh3() -> None:
    """Test 4d6kh3 (character ability score stat generation: roll 4d6, drop lowest)."""
    parsed = parse_and_roll("4d6kh3", fixed_rolls=[2, 6, 5, 4])
    assert parsed["count"] == 4
    assert parsed["sides"] == 6
    assert parsed["keep_highest"] == 3
    assert parsed["modifier"] == 0
    assert parsed["rolls"] == [2, 6, 5, 4]
    assert parsed["kept_rolls"] == [6, 5, 4]
    assert parsed["total"] == 15
    assert not parsed["is_crit"]
    assert not parsed["is_fumble"]


def test_fireball_8d6_plus_4() -> None:
    """Test 8d6+4 Fireball damage roll."""
    parsed = parse_and_roll("8d6+4", fixed_rolls=[3, 4, 2, 6, 1, 5, 4, 3])
    assert parsed["count"] == 8
    assert parsed["sides"] == 6
    assert parsed["modifier"] == 4
    assert sum(parsed["rolls"]) == 28
    assert parsed["total"] == 32
    assert not parsed["is_crit"]
    assert not parsed["is_fumble"]


def test_standard_d20_crit_and_fumble() -> None:
    """Test standard 1d20 crit on 20 and fumble on 1."""
    crit = parse_and_roll("1d20+2", fixed_rolls=[20])
    assert crit["is_crit"] is True
    assert crit["is_fumble"] is False
    assert crit["total"] == 22

    fumble = parse_and_roll("1d20-1", fixed_rolls=[1])
    assert fumble["is_crit"] is False
    assert fumble["is_fumble"] is True
    assert fumble["total"] == 0

    normal = parse_and_roll("1d20+3", fixed_rolls=[10])
    assert normal["is_crit"] is False
    assert normal["is_fumble"] is False
    assert normal["total"] == 13


def test_invalid_formula_raises_error() -> None:
    """Invalid formulas must raise ValueError."""
    with pytest.raises(ValueError, match="Invalid dice formula"):
        parse_and_roll("invalid-formula")

    with pytest.raises(ValueError, match="Dice count must be at least 1"):
        evaluate_dice(0, 20)

    with pytest.raises(ValueError, match="Dice sides must be at least 1"):
        evaluate_dice(1, 0)

    with pytest.raises(ValueError, match="Cannot specify both"):
        evaluate_dice(2, 20, keep_highest=1, keep_lowest=1)


# ---------------------------------------------------------------------------
# CloudEvents Compliance & Event Serialization Tests
# ---------------------------------------------------------------------------


def test_dice_rolled_event_serialization_and_cloudevent() -> None:
    """Verify DiceRolled domain event serialization and CloudEvents 1.0 schema compliance."""
    event = DiceRolled(
        session_id="sess-runic-101",
        roller_id="player-valeros",
        roller_name="Valeros",
        formula="2d20kh1+5",
        total=25,
        rolls=[14, 20],
        is_crit=True,
        is_fumble=False,
    )

    # CloudEvent conversion
    ce = event.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.dice.rolled"
    assert ce["source"] == f"/runefoble/gamesession/{event.aggregate_id}"
    assert ce["datacontenttype"] == "application/json"

    data = ce["data"]
    assert data["session_id"] == "sess-runic-101"
    assert data["roller_id"] == "player-valeros"
    assert data["roller_name"] == "Valeros"
    assert data["formula"] == "2d20kh1+5"
    assert data["total"] == 25
    assert data["rolls"] == [14, 20]
    assert data["is_crit"] is True
    assert data["is_fumble"] is False

    # Check registered event registry lookup
    from eventsource.domain.event_registry import default_registry

    event_cls = default_registry.get("runefoble.events.dice.rolled")
    assert event_cls is DiceRolled
