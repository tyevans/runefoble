"""Assert that domain events reached a Redis stream through the public event bus.

One helper replaces the per-directory copies. Event names match without case and without
underscores, so `"WorkerHired"` and `"worker_hired"` find the same entry.

Governed by ADR-0014: assertions read published events, never private state.
"""

from __future__ import annotations

from game_session.events import STREAM_WEST_MARCHES

from tests.helpers.mock_redis import MockAsyncRedis


def _normal(text: object) -> str:
    return str(text).lower().replace("_", "")


def assert_stream_events(
    mock_bus: MockAsyncRedis, *event_names: str, stream: str = STREAM_WEST_MARCHES
) -> None:
    """Assert that each named event was published to `stream` (West Marches by default)."""
    entries = mock_bus.streams.get(stream, [])
    for name in event_names:
        assert any(_normal(name) in _normal(entry[1]) for entry in entries), (
            f"Expected event '{name}' in stream '{stream}', but found: {entries}"
        )
