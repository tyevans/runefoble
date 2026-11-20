"""voice_agent waits longer for The Watcher than The Watcher's own worst case.

The Watcher calls its intent engine, board_state and the proposal step in turn. Each call has a
budget. If voice_agent gives up first, the player gets a timeout and not the Watcher reply.
"""

from the_watcher.engine_selection import WatcherEngineSettings
from voice_agent.watcher_intent import WATCHER_TIMEOUT_SECONDS


def test_voice_agent_waits_longer_than_the_watcher_worst_case() -> None:
    watcher = WatcherEngineSettings()
    worst_case = (
        watcher.watcher_intent_timeout_s
        + watcher.watcher_board_timeout_s
        + watcher.watcher_proposal_timeout_s
    )

    assert worst_case < WATCHER_TIMEOUT_SECONDS
