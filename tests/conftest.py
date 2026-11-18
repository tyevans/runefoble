"""Root pytest configuration and global fixtures for Runefoble test suite."""

import os

# Test mode: the SpiceDB preshared key has no default outside tests. Tests supply a throwaway
# value before any settings object is built. Live tests may override it in their environment.
os.environ.setdefault("RUNEFOBLE_SPICEDB_PRESHARED_KEY", "test-only-spicedb-key")
# The gateway MCP has no localhost defaults. Unless a test sets an upstream itself, its URLs
# point at a closed loopback port, so no test reaches a real service by accident.
for _upstream in (
    "BOARD_STATE_URL",
    "CHARACTER_SHEET_URL",
    "GAME_SESSION_URL",
    "RULES_COMPENDIUM_URL",
    "THE_WATCHER_URL",
):
    os.environ.setdefault(_upstream, "http://127.0.0.1:9")
# The inference worker refuses to start without its service token (ADR-0015 e). Tests use a
# throwaway value. Process-level tests remove it from the child environment on purpose.
os.environ.setdefault("RUNEFOBLE_SERVICE_CREDENTIAL", "test-only-service-credential")
# Tests select the in-memory event store explicitly. The platform default is PostgreSQL, and a
# deployed environment refuses memory (TASK-0707). Tests that need PostgreSQL pass settings.
os.environ["RUNEFOBLE_EVENT_STORE_BACKEND"] = "memory"
# The Watcher defaults to its inference worker (TASK-0741). Tests that need the local rule engine
# select it here. Tests that need the worker set the worker URL themselves with monkeypatch.
os.environ.setdefault("RUNEFOBLE_WATCHER_ENGINE", "heuristic")

pytest_plugins = [
    "tests.realtime_session",
    "tests.helpers.audio_synth",
    "tests.helpers.campaign_analytics_service",
    "tests.helpers.lore_backends",
    "tests.helpers.postgres",
    "tests.helpers.prd_fixtures",
    "tests.helpers.service_harness",
    "tests.helpers.silo_fixtures",
    "tests.helpers.spicedb",
    "tests.helpers.voice_identity",
    "tests.helpers.zitadel_auth",
]
collect_ignore = ["test_blackbox_uvtt_import.py"]
