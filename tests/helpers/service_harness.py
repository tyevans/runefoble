"""One shared service test harness: the seam registry and the fixtures that read it.

Every service keeps its seams (SpiceDB client, event bus, bearer verifier) in a
`dependencies` module with a getter and a setter. `SERVICE_SEAMS` is the one table that
names them. The fixtures here set each seam for one test (or one session) and restore the
previous value. Per-directory conftests request these fixtures and never set a seam by hand.

Mocks stand in only for process boundaries: SpiceDB and Redis.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
- ADR-0015: Audit remediation decisions
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from types import ModuleType
from typing import Literal

import pytest
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.ws_identity import SIGNING_ISSUER

VerifierScope = Literal["session", "test", "on_demand"]


@dataclass(frozen=True)
class ServiceSeams:
    """The seam modules of one service.

    `spicedb` and `bus` name a module that has `get_/set_spicedb_client` or
    `get_/set_event_bus`. `verifier` names a module that has `get_/set_zitadel_auth_service`.
    `verifier_scope` says when the shared test issuer is trusted there:
    - `session`: for the whole session (module-scoped live upstreams send signed requests).
    - `test`: for every test, restored after it.
    - `on_demand`: only for tests that request `trusted_ws_issuer`.
    """

    name: str
    spicedb: str | None = None
    bus: str | None = None
    verifier: str | None = None
    verifier_scope: VerifierScope | None = None


SERVICE_SEAMS: tuple[ServiceSeams, ...] = (
    ServiceSeams(
        "asset_forge",
        bus="asset_forge.dependencies",
        verifier="asset_forge.dependencies",
        verifier_scope="test",
    ),
    ServiceSeams(
        "board_state",
        bus="board_state.dependencies",
        verifier="board_state.dependencies",
        verifier_scope="session",
    ),
    ServiceSeams(
        "campaign_analytics",
        verifier="campaign_analytics.dependencies",
        verifier_scope="session",
    ),
    ServiceSeams(
        "campaign_lore",
        bus="campaign_lore.dependencies",
        verifier="campaign_lore.identity",
        verifier_scope="test",
    ),
    ServiceSeams(
        "character_sheet",
        spicedb="character_sheet.dependencies",
        bus="character_sheet.dependencies",
        verifier="character_sheet.dependencies",
        verifier_scope="test",
    ),
    ServiceSeams(
        "game_session",
        spicedb="game_session.dependencies",
        bus="game_session.dependencies",
        verifier="game_session.settlement.auth.tokens",
        verifier_scope="on_demand",
    ),
    ServiceSeams(
        "gateway_api",
        bus="gateway_api.dependencies",
        verifier="gateway_api.auth",
        verifier_scope="on_demand",
    ),
    ServiceSeams(
        "gateway_mcp", spicedb="gateway_mcp.dynamic.auth", bus="gateway_mcp.dynamic.events"
    ),
    ServiceSeams(
        "rules_compendium",
        verifier="rules_compendium.dependencies",
        verifier_scope="session",
    ),
    ServiceSeams(
        "soundscape",
        bus="soundscape.dependencies",
        verifier="soundscape.dependencies",
        verifier_scope="test",
    ),
    ServiceSeams(
        "the_watcher",
        bus="the_watcher.dependencies",
        verifier="the_watcher.identity",
        verifier_scope="on_demand",
    ),
    ServiceSeams("voice_agent", bus="voice_agent.dependencies"),
)


def _modules(attr: str, scope: VerifierScope | None = None) -> list[ModuleType]:
    """Import the distinct modules that a registry column names, in registry order."""
    names: list[str] = []
    for row in SERVICE_SEAMS:
        name = getattr(row, attr)
        if name is None or (scope is not None and row.verifier_scope != scope):
            continue
        if name not in names:
            names.append(name)
    return [importlib.import_module(name) for name in names]


def _swap(
    modules: list[ModuleType], getter: str, setter: str, value_for: Callable[[], object]
) -> list[tuple[ModuleType, object]]:
    """Set a seam on each module and return the previous values for the restore."""
    previous = [(mod, getattr(mod, getter)()) for mod in modules]
    for mod in modules:
        getattr(mod, setter)(value_for())
    return previous


def _restore(previous: list[tuple[ModuleType, object]], setter: str) -> None:
    for mod, value in previous:
        getattr(mod, setter)(value)


@pytest.fixture
def mock_bus() -> MockAsyncRedis:
    """The in-memory Redis double behind the event bus every service publishes to."""
    return MockAsyncRedis()


@pytest.fixture(autouse=True)
def default_redis_event_bus(mock_bus: MockAsyncRedis) -> Iterator[object]:
    """Route every service publish to `mock_bus` unless a test overrides it.

    Redis is an external process. Tests must not open real connections to localhost:6379.
    """
    from runefoble_platform.redis_bus import RedisStreamsEventBus

    bus = RedisStreamsEventBus(client=mock_bus)
    previous = _swap(_modules("bus"), "get_event_bus", "set_event_bus", lambda: bus)
    try:
        yield bus
    finally:
        _restore(previous, "set_event_bus")


@pytest.fixture
def use_event_bus(default_redis_event_bus: object) -> Callable[[object], object]:
    """Return a function that routes every service publish to another event bus.

    Use it for a test that needs a recording bus or a bus on a real Redis. The default
    fixture restores every bus seam after the test.
    """

    def use(bus: object) -> object:
        _swap(_modules("bus"), "get_event_bus", "set_event_bus", lambda: bus)
        return bus

    return use


@pytest.fixture
def use_redis_client(use_event_bus: Callable[[object], object]) -> Callable[[object], object]:
    """Return a function that routes every service publish to another Redis double.

    Use it for a test that needs a failing or recording Redis.
    """
    from runefoble_platform.redis_bus import RedisStreamsEventBus

    def use(client: object) -> object:
        return use_event_bus(RedisStreamsEventBus(client=client))

    return use


@pytest.fixture(autouse=True)
def default_spicedb_client(request: pytest.FixtureRequest) -> Iterator[MockSpiceDBClient | None]:
    """Route every SpiceDB call to a fresh strict mock unless a live SpiceDB fixture is requested.

    The shared factory client (`runefoble_auth.factory`) is the one seam. Service modules that
    keep their own client get the same mock through their setter.
    """
    if {"live_spicedb_endpoint", "live_spicedb_with_schema"} & set(request.fixturenames):
        yield None
        return

    mock_db = MockSpiceDBClient()
    previous = _swap(
        _modules("spicedb"), "get_spicedb_client", "set_spicedb_client", lambda: mock_db
    )
    factory_swap = shared_spicedb_client(mock_db)
    factory_swap.start()
    try:
        yield mock_db
    finally:
        factory_swap.stop()
        _restore(previous, "set_spicedb_client")


@pytest.fixture(autouse=True)
def clean_soundscape_registries() -> Iterator[None]:
    """Clear the soundscape session registries (mixers, aggregates, engines) around each test."""
    from soundscape.dependencies import reset_dependencies

    reset_dependencies()
    yield
    reset_dependencies()


@pytest.fixture
def spicedb(default_spicedb_client: MockSpiceDBClient | None) -> MockSpiceDBClient:
    """The strict SpiceDB mock that every service of this test already uses."""
    assert default_spicedb_client is not None, "a live SpiceDB test has no SpiceDB mock"
    return default_spicedb_client


@pytest.fixture(autouse=True, scope="session")
def shared_issuer_in_session_verifiers() -> Iterator[None]:
    """Trust the shared test issuer for the whole session in each `session` verifier service.

    Session scope lets module-scoped fixtures that start live upstreams send signed requests.
    """
    modules = _modules("verifier", "session")
    previous = _swap(
        modules, "get_zitadel_auth_service", "set_zitadel_auth_service", SIGNING_ISSUER.verifier
    )
    yield
    _restore(previous, "set_zitadel_auth_service")


@pytest.fixture(autouse=True)
def default_service_verifiers() -> Iterator[None]:
    """Trust the shared test issuer in each `test` verifier service, for one test.

    A test that needs another issuer overrides the verifier itself.
    """
    previous = _swap(
        _modules("verifier", "test"),
        "get_zitadel_auth_service",
        "set_zitadel_auth_service",
        SIGNING_ISSUER.verifier,
    )
    try:
        yield
    finally:
        _restore(previous, "set_zitadel_auth_service")


@pytest.fixture
def trusted_ws_issuer() -> Iterator[SigningTestIssuer]:
    """Trust the shared test issuer in the gateway, game_session and the_watcher verifiers."""
    previous = _swap(
        _modules("verifier", "on_demand"),
        "get_zitadel_auth_service",
        "set_zitadel_auth_service",
        SIGNING_ISSUER.verifier,
    )
    try:
        yield SIGNING_ISSUER
    finally:
        _restore(previous, "set_zitadel_auth_service")


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
