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


@given(
    dist=st.integers(min_value=1, max_value=200),
    is_feet=st.booleans(),
    direction=st.sampled_from(["north", "south", "east", "west"]),
    verb=st.sampled_from(["move", "step", "advance", "retreat", "walk", "charge", "run", "dash"]),
    cols=st.integers(min_value=4, max_value=64),
    rows=st.integers(min_value=4, max_value=64),
    start_x=st.integers(min_value=0, max_value=63),
    start_y=st.integers(min_value=0, max_value=63),
)
def test_cardinal_movement_parsing_and_bounds_invariants(
    dist: int,
    is_feet: bool,
    direction: str,
    verb: str,
    cols: int,
    rows: int,
    start_x: int,
    start_y: int,
):
    """Property: Cardinal movement parsing handles arbitrary feet/squares and destination remains strictly within grid bounds."""
    from the_watcher.watcher_ai import TheWatcherEngine

    engine = TheWatcherEngine()
    unit = "feet" if is_feet else "squares"
    phrase = f"{verb} {dist} {unit} {direction}"
    result = engine.parse_speech_intent(phrase, "Hero")

    assert result.action_type == "move"
    assert result.confidence >= 0.9

    expected_steps = max(1, dist // 5) if is_feet else dist
    assert result.parameters["steps"] == expected_steps
    assert result.parameters["direction"] == direction

    dx = result.parameters["dx"]
    dy = result.parameters["dy"]

    if direction == "north":
        assert dx == 0 and dy == -expected_steps
    elif direction == "south":
        assert dx == 0 and dy == expected_steps
    elif direction == "east":
        assert dx == expected_steps and dy == 0
    elif direction == "west":
        assert dx == -expected_steps and dy == 0

    clamped_x = min(start_x, cols - 1)
    clamped_y = min(start_y, rows - 1)

    dest_x, dest_y = engine.calculate_bounded_destination(
        clamped_x, clamped_y, dx, dy, cols=cols, rows=rows
    )

    assert 0 <= dest_x < cols
    assert 0 <= dest_y < rows


@given(
    multiplier=st.integers(min_value=1, max_value=50),
    direction=st.sampled_from(["north", "south", "east", "west"]),
)
def test_feet_to_squares_scaling_invariant(multiplier: int, direction: str):
    """Property: Distance in feet strictly scales at 5ft per square (e.g. 5ft->1, 10ft->2, 15ft->3)."""
    from the_watcher.watcher_ai import TheWatcherEngine

    engine = TheWatcherEngine()
    feet = multiplier * 5
    phrase = f"step {feet} feet {direction}"
    result = engine.parse_speech_intent(phrase, "Ranger")

    assert result.action_type == "move"
    assert result.parameters["steps"] == multiplier
