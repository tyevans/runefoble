"""Root pytest configuration and global fixtures for Runefoble test suite."""

import contextlib
import os
from collections.abc import Iterator

# Test mode: the SpiceDB preshared key has no default outside tests. Tests supply a throwaway
# value before any settings object is built. Live tests may override it in their environment.
os.environ.setdefault("RUNEFOBLE_SPICEDB_PRESHARED_KEY", "test-only-spicedb-key")
# ruff: noqa: E402  (imports below construct settings, so the key must be set first)

import pytest
from game_session.settlement.auth.tokens import get_zitadel_auth_service as get_session_auth
from game_session.settlement.auth.tokens import set_zitadel_auth_service as set_session_auth
from gateway_api.auth import get_zitadel_auth_service, set_zitadel_auth_service
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

from tests.helpers.ws_identity import SIGNING_ISSUER

pytest_plugins = [
    "tests.helpers.audio_synth",
    "tests.helpers.lore_backends",
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
    "game_session.dependencies",
    "the_watcher.dependencies",
]


@pytest.fixture(autouse=True)
def default_redis_event_bus():
    """Route board and watcher publishes to an in-memory Redis double unless a test overrides it.

    Redis is an external process. Tests must not open real connections to localhost:6379.
    """
    import importlib

    from runefoble_platform.redis_bus import RedisStreamsEventBus

    from tests.helpers.mock_redis import MockAsyncRedis

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


@pytest.fixture
def trusted_ws_issuer() -> Iterator[SigningTestIssuer]:
    """Trust the shared test issuer in the gateway and game_session verifiers."""
    previous_gateway = get_zitadel_auth_service()
    previous_session = get_session_auth()
    set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    set_session_auth(SIGNING_ISSUER.verifier())
    yield SIGNING_ISSUER
    set_zitadel_auth_service(previous_gateway)
    set_session_auth(previous_session)
