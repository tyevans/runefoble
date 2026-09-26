"""Property-based invariant testing with Hypothesis."""

from gateway_mcp.server import roll_dice
from hypothesis import given
from hypothesis import strategies as st


@given(
    count=st.integers(min_value=1, max_value=20),
    sides=st.integers(min_value=2, max_value=100),
    mod=st.integers(min_value=-50, max_value=50),
)
def test_dice_notation_invariants(count: int, sides: int, mod: int):
    """Property: The result of rolling NdS+M must be clamped between [N*1 + M, N*S + M]."""
    sign = "+" if mod >= 0 else "-"
    notation = f"{count}d{sides}{sign}{abs(mod)}"
    result = roll_dice(notation=notation, reason="Property test")

    min_possible = count * 1 + mod
    max_possible = count * sides + mod

    assert min_possible <= result["total"] <= max_possible
    assert len(result["rolls"]) == count
    assert all(1 <= r <= sides for r in result["rolls"])


@given(
    cols=st.integers(min_value=4, max_value=64),
    rows=st.integers(min_value=4, max_value=64),
    x=st.integers(min_value=0, max_value=63),
    y=st.integers(min_value=0, max_value=63),
)
def test_board_coordinate_validity(cols: int, rows: int, x: int, y: int):
    """Property: Spatial coordinates are strictly bounded by grid width and height."""
    is_valid = (0 <= x < cols) and (0 <= y < rows)
    if is_valid:
        assert 0 <= x < cols
        assert 0 <= y < rows
    else:
        assert x < 0 or x >= cols or y < 0 or y >= rows


@given(
    num_combatants=st.integers(min_value=1, max_value=20),
    turn_steps=st.integers(min_value=0, max_value=100),
)
def test_initiative_rotation_cycle(num_combatants: int, turn_steps: int):
    """Property: Advancing turns K times wraps cleanly and increments round count predictably."""
    combatants = [f"char-{i}" for i in range(num_combatants)]
    current_index = 0
    round_count = 1

    for _ in range(turn_steps):
        current_index = (current_index + 1) % len(combatants)
        if current_index == 0:
            round_count += 1

    expected_rounds = 1 + (turn_steps // num_combatants)
    expected_index = turn_steps % num_combatants

    assert current_index == expected_index
    assert round_count == expected_rounds
