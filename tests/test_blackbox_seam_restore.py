"""Blackbox checks: a seam that a test replaces is restored to the value it had before.

A later test must see the previous client, not `None`. A `None` seam makes the next getter
build a real SpiceDB client, so the check uses the process seam through its public getter.
"""

from runefoble_auth.factory import get_spicedb_client, set_spicedb_client
from runefoble_auth.mock import MockSpiceDBClient
from the_watcher.dependencies import build_copilot_engine, get_copilot_engine, set_copilot_engine

from tests.helpers.module_state import restored_seam


def test_replaced_spicedb_client_is_restored_to_the_previous_client() -> None:
    previous = get_spicedb_client()
    replacement = MockSpiceDBClient()

    with restored_seam(get_spicedb_client, set_spicedb_client, replacement, replace=True):
        assert get_spicedb_client() is replacement

    assert get_spicedb_client() is previous


def test_seam_restorer_restores_every_seam_in_reverse_order(seam_restorer) -> None:
    previous = get_spicedb_client()
    first = MockSpiceDBClient()
    second = MockSpiceDBClient()

    seam_restorer.replace(get_spicedb_client, set_spicedb_client, first)
    seam_restorer.replace(get_spicedb_client, set_spicedb_client, second)
    assert get_spicedb_client() is second

    seam_restorer.restore()
    assert get_spicedb_client() is previous


def test_replaced_copilot_engine_is_restored_to_the_previous_engine() -> None:
    previous = get_copilot_engine()
    replacement = build_copilot_engine()

    with restored_seam(get_copilot_engine, set_copilot_engine, replacement, replace=True):
        assert get_copilot_engine() is replacement

    assert get_copilot_engine() is previous
    replacement.shutdown()


def test_seam_restorer_keeps_the_copilot_engine_that_a_restart_replaces(seam_restorer) -> None:
    previous = get_copilot_engine()
    restarted = build_copilot_engine()

    seam_restorer.keep(get_copilot_engine, set_copilot_engine)
    set_copilot_engine(restarted)
    assert get_copilot_engine() is restarted

    seam_restorer.restore()
    assert get_copilot_engine() is previous
    restarted.shutdown()
