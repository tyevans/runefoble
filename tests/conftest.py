"""Root pytest configuration and global fixtures for Runefoble test suite."""

import contextlib

import pytest
from runefoble_auth.spicedb import MockSpiceDBClient

pytest_plugins = [
    "tests.helpers.audio_synth",
    "tests.helpers.postgres",
    "tests.helpers.prd_fixtures",
    "tests.helpers.silo_fixtures",
    "tests.helpers.spicedb",
    "tests.helpers.zitadel_auth",
]
collect_ignore = ["test_blackbox_uvtt_import.py"]


SPICEDB_SERVICE_MODULES = [
    "gateway_api.auth",
    "gateway_mcp.dynamic.auth",
    "character_sheet.dependencies",
    "game_session.dependencies",
    "rules_compendium.dependencies",
    "asset_forge.dependencies",
    "campaign_lore.dependencies",
    "soundscape.dependencies",
    "the_watcher.dependencies",
    "board_state.dependencies",
    "campaign_analytics.dependencies",
]


REDIS_BUS_MODULES = [
    "board_state.dependencies",
    "the_watcher.dependencies",
]


@pytest.fixture(autouse=True)
def default_redis_event_bus():
    """Route board and watcher publishes to an in-memory Redis double unless a test overrides it.

    Redis is an external process. Tests must not open real connections to localhost:6379.
    """
    import importlib

    from runefoble_platform.mock_redis import MockAsyncRedis
    from runefoble_platform.redis_bus import RedisStreamsEventBus

    bus = RedisStreamsEventBus(client=MockAsyncRedis())
    modules_to_restore = []
    for mod_name in REDIS_BUS_MODULES:
        mod = importlib.import_module(mod_name)
        modules_to_restore.append((mod, mod.get_event_bus()))
        mod.set_event_bus(bus)

    try:
        yield bus
    finally:
        for mod, prev in modules_to_restore:
            mod.set_event_bus(prev)


@pytest.fixture(autouse=True)
def default_spicedb_client(request):
    """Provide MockSpiceDBClient singleton for tests unless live_spicedb_endpoint is requested."""
    if "live_spicedb_endpoint" in getattr(request, "fixturenames", []):
        yield None
        return

    import importlib
    import sys

    mock_db = MockSpiceDBClient()
    modules_to_restore = []

    for mod_name in SPICEDB_SERVICE_MODULES:
        with contextlib.suppress(Exception):
            mod = sys.modules.get(mod_name) or importlib.import_module(mod_name)
            if hasattr(mod, "get_spicedb_client") and hasattr(mod, "set_spicedb_client"):
                prev = mod.get_spicedb_client()
                mod.set_spicedb_client(mock_db)
                modules_to_restore.append((mod, prev))

    try:
        yield mock_db
    finally:
        for mod, prev in modules_to_restore:
            with contextlib.suppress(Exception):
                mod.set_spicedb_client(prev)
