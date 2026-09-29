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


@pytest.fixture(autouse=True)
def default_spicedb_client(request):
    """Provide MockSpiceDBClient singleton for tests unless live_spicedb_endpoint is requested."""
    if "live_spicedb_endpoint" in getattr(request, "fixturenames", []):
        yield None
        return

    import gateway_api.auth as gw_auth

    prev_gw = gw_auth._spicedb_client
    mock_db = MockSpiceDBClient()
    gw_auth.set_spicedb_client(mock_db)

    import sys

    modules_to_restore = []
    for mod_name in [
        "game_session.dependencies",
        "soundscape.dependencies",
        "the_watcher.dependencies",
        "campaign_lore.dependencies",
        "gateway_mcp.dynamic.auth",
    ]:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            if hasattr(mod, "get_spicedb_client") and hasattr(mod, "set_spicedb_client"):
                with contextlib.suppress(Exception):
                    prev = mod.get_spicedb_client()
                    mod.set_spicedb_client(mock_db)
                    modules_to_restore.append((mod, prev))

    try:
        yield mock_db
    finally:
        gw_auth.set_spicedb_client(prev_gw)
        for mod, prev in modules_to_restore:
            with contextlib.suppress(Exception):
                mod.set_spicedb_client(prev)
