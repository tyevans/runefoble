"""Fresh copilot aggregate stores for The Watcher tests (TASK-0568).

Each test gets its own in-memory event store, so pending actions, whispers, and
disambiguations never leak between tests. Tests reach the stores only through this seam.
"""

from __future__ import annotations

from eventsource.adapters.memory.store import InMemoryEventStore
from runefoble_platform.event_sourcing import create_aggregate_repository
from the_watcher.copilot_state.disambiguations import DisambiguationAggregate
from the_watcher.copilot_state.pending_actions import PendingActionAggregate
from the_watcher.copilot_state.whispers import WhisperAggregate
from the_watcher.dependencies import (
    set_disambiguation_repo,
    set_pending_action_repo,
    set_whisper_repo,
)


def install_fresh_copilot_stores() -> None:
    """Point every copilot aggregate repository at one new, empty event store."""
    store = InMemoryEventStore()
    set_pending_action_repo(create_aggregate_repository(PendingActionAggregate, event_store=store))
    set_whisper_repo(create_aggregate_repository(WhisperAggregate, event_store=store))
    set_disambiguation_repo(create_aggregate_repository(DisambiguationAggregate, event_store=store))


def reset_copilot_stores() -> None:
    """Restore the process default repositories."""
    set_pending_action_repo(None)
    set_whisper_repo(None)
    set_disambiguation_repo(None)
