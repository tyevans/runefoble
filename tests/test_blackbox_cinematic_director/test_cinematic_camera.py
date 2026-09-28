"""Cinematic camera math and autonomous tracking blackbox tests (TASK-0190)."""

from typing import Any
from uuid import uuid4

from gateway_api.cinematic_director import (
    CameraTarget,
    CinematicDirector,
    evaluate_cubic_bezier,
    get_cinematic_director,
    parse_cubic_bezier,
)
from runefoble_events.board import TokenMoved
from runefoble_events.session import TurnStarted


def test_cinematic_director_cubic_bezier_calculation(
    camera_coords: tuple[CameraTarget, CameraTarget],
) -> None:
    """Verify cubic-bezier math evaluation and smooth progress calculation."""
    # Standard ease: (0.25, 0.1, 0.25, 1.0)
    p1x, p1y, p2x, p2y = parse_cubic_bezier("cubic-bezier(0.25, 0.1, 0.25, 1.0)")
    assert (p1x, p1y, p2x, p2y) == (0.25, 0.1, 0.25, 1.0)

    # Boundaries
    assert evaluate_cubic_bezier(p1x, p1y, p2x, p2y, 0.0) == 0.0
    assert evaluate_cubic_bezier(p1x, p1y, p2x, p2y, 1.0) == 1.0

    # Intermediate progression is smooth and strictly monotonic
    mid = evaluate_cubic_bezier(p1x, p1y, p2x, p2y, 0.5)
    assert 0.0 < mid < 1.0

    # Interpolation of camera coordinates
    director = CinematicDirector()
    start, end = camera_coords
    interp_x, interp_y, interp_zoom = director.interpolate_position(start, end, 0.5)
    assert 0.0 < interp_x < 10.0
    assert 0.0 < interp_y < 20.0
    assert 1.0 < interp_zoom < 2.0


def test_cinematic_director_turn_started_and_token_moved_tracking(
    mock_party_tokens: list[dict[str, Any]],
) -> None:
    """Verify camera centers on active token on TurnStarted and destination on TokenMoved."""
    director = get_cinematic_director("sess-cam-test")

    # 1. TurnStarted -> Centers on active token within 300ms
    turn_event = TurnStarted(
        session_id="sess-cam-test",
        turn_number=1,
        character_id="char-valeros",
        token_id="tok-1",
    )
    cam_turn = director.handle_turn_started(turn_event, tokens=mock_party_tokens)
    assert cam_turn.target_x == 3.0
    assert cam_turn.target_y == 4.0
    assert cam_turn.duration_ms == 300
    assert cam_turn.reason == "turn_started"
    assert cam_turn.active_token_id == "tok-1"

    # 2. TokenMoved -> Centers on action center (to_x, to_y) within 300ms
    move_event = TokenMoved(
        aggregate_id=uuid4(),
        token_id="tok-1",
        name="Valeros",
        from_x=3,
        from_y=4,
        to_x=5,
        to_y=6,
    )
    cam_move = director.handle_token_moved(move_event)
    assert cam_move.target_x == 5.0
    assert cam_move.target_y == 6.0
    assert cam_move.duration_ms == 300
    assert cam_move.reason == "token_moved"
