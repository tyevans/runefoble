"""Root pytest configuration and global fixtures for Runefoble test suite."""

import contextlib
import os
from collections.abc import Iterator

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
# ruff: noqa: E402  (imports below construct settings, so the key must be set first)

import pytest
from board_state import dependencies as board_state_dependencies
from campaign_analytics import dependencies as campaign_analytics_dependencies
from game_session.settlement.auth.tokens import get_zitadel_auth_service as get_session_auth
from game_session.settlement.auth.tokens import set_zitadel_auth_service as set_session_auth
from gateway_api.auth import get_zitadel_auth_service, set_zitadel_auth_service
from rules_compendium import dependencies as rules_compendium_dependencies
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
from the_watcher.identity import get_zitadel_auth_service as get_watcher_auth
from the_watcher.identity import set_zitadel_auth_service as set_watcher_auth

from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.ws_identity import SIGNING_ISSUER

pytest_plugins = [
    "tests.helpers.audio_synth",
    "tests.helpers.campaign_analytics_service",
    "tests.helpers.lore_backends",
    "tests.helpers.postgres",
    "tests.helpers.prd_fixtures",
    "tests.helpers.silo_fixtures",
    "tests.helpers.spicedb",
    "tests.helpers.voice_identity",
    "tests.helpers.zitadel_auth",
]
collect_ignore = ["test_blackbox_uvtt_import.py"]


SPICEDB_SERVICE_MODULES = [
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


SERVICE_VERIFIER_MODULES = [
    "asset_forge.dependencies",
    "soundscape.dependencies",
    "character_sheet.dependencies",
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


# Services that verify bearer tokens themselves (ADR-0015). The gateway forwards the caller's
# token to them, so the shared test issuer must be trusted by each of them as well.
SERVICE_IDENTITY_MODULES = [
    board_state_dependencies,
    campaign_analytics_dependencies,
    rules_compendium_dependencies,
]


@pytest.fixture(autouse=True, scope="session")
def shared_issuer_in_token_services() -> Iterator[None]:
    """Trust the shared test issuer in each token-verifying service for the whole session.

    Session scope lets module-scoped fixtures that start live upstreams send signed requests.
    """
    previous = [(mod, mod.get_zitadel_auth_service()) for mod in SERVICE_IDENTITY_MODULES]
    verifier = SIGNING_ISSUER.verifier()
    for mod in SERVICE_IDENTITY_MODULES:
        mod.set_zitadel_auth_service(verifier)
    yield
    for mod, prev in previous:
        mod.set_zitadel_auth_service(prev)


@pytest.fixture(autouse=True)
def default_service_verifiers() -> Iterator[None]:
    """Trust the shared test signing issuer in the token-verifying microservices.

    Tests send bearer tokens minted by SIGNING_ISSUER. A test that needs another issuer
    overrides the verifier itself.
    """
    import importlib

    modules = [importlib.import_module(name) for name in SERVICE_VERIFIER_MODULES]
    previous = [mod.get_zitadel_auth_service() for mod in modules]
    for mod in modules:
        mod.set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    try:
        yield
    finally:
        for mod, prev in zip(modules, previous, strict=True):
            mod.set_zitadel_auth_service(prev)


@pytest.fixture(autouse=True)
def default_spicedb_client(request):
    """Route every SpiceDB call to a fresh strict mock unless live_spicedb_endpoint is requested.

    The shared factory client (`runefoble_auth.factory`) is the one seam. Service-local
    dependency modules that still keep their own client keep their setter swap.
    """
    live_fixtures = {"live_spicedb_endpoint", "live_spicedb_with_schema"}
    if live_fixtures & set(getattr(request, "fixturenames", [])):
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

    factory_swap = shared_spicedb_client(mock_db)
    factory_swap.start()
    try:
        yield mock_db
    finally:
        factory_swap.stop()
        for mod, prev in modules_to_restore:
            with contextlib.suppress(Exception):
                mod.set_spicedb_client(prev)


@pytest.fixture
def trusted_ws_issuer() -> Iterator[SigningTestIssuer]:
    """Trust the shared test issuer in the gateway, game_session, and the_watcher verifiers."""
    previous_gateway = get_zitadel_auth_service()
    previous_session = get_session_auth()
    previous_watcher = get_watcher_auth()
    set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    set_session_auth(SIGNING_ISSUER.verifier())
    set_watcher_auth(SIGNING_ISSUER.verifier())
    yield SIGNING_ISSUER
    set_zitadel_auth_service(previous_gateway)
    set_session_auth(previous_session)
    set_watcher_auth(previous_watcher)


@pytest.fixture
def character_sheet_upstream(monkeypatch, trusted_ws_issuer) -> Iterator[str]:
    """Serve character_sheet as a live loopback upstream with a fresh event store (TASK-0585).

    The gateway reaches it over HTTP through CHARACTER_SHEET_URL. The aggregate repository
    is replaced for this test, so characters from earlier tests do not leak in. The URL is
    set before the gateway lifespan runs, so build the gateway client after this fixture.
    """
    from character_sheet import dependencies as sheet_deps
    from character_sheet.aggregate import CharacterAggregate
    from character_sheet.main import app as sheet_app
    from eventsource.adapters.memory.store import InMemoryEventStore
    from runefoble_platform.event_sourcing import create_aggregate_repository

    from tests.helpers.live_services import serve

    fresh_repo = create_aggregate_repository(CharacterAggregate, event_store=InMemoryEventStore())
    monkeypatch.setattr(sheet_deps, "repo", fresh_repo)
    with serve(sheet_app) as url:
        monkeypatch.setenv("CHARACTER_SHEET_URL", url)
        yield url


@pytest.fixture
def game_session_upstream(monkeypatch, trusted_ws_issuer) -> Iterator[str]:
    """Serve game_session as a live loopback upstream with fresh in-memory campaign state.

    The gateway reaches it over HTTP through RUNEFOBLE_GAME_SESSION_URL (TASK-0591). Tokens
    minted by `trusted_ws_issuer` are accepted by both services. The URL is set before the
    gateway lifespan runs, so build the gateway client after this fixture.
    """
    from eventsource.adapters.memory.store import InMemoryEventStore
    from game_session.campaign.repositories import set_campaign_repositories
    from game_session.main import app as session_app
    from runefoble_platform.event_sourcing import set_event_store

    from tests.helpers.live_services import serve

    set_event_store(InMemoryEventStore())
    set_campaign_repositories(None)
    try:
        with serve(session_app) as url:
            monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", url)
            yield url
    finally:
        set_event_store(None)
        set_campaign_repositories(None)
