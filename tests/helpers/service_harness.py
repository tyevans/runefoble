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
from contextlib import contextmanager
from dataclasses import dataclass
from types import ModuleType
from typing import Literal

import pytest
from fastapi import FastAPI
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.live_services import serve
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.signing_test_issuer import SigningTestIssuer
from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.ws_identity import SIGNING_ISSUER

VerifierScope = Literal["session", "test", "on_demand"]


@dataclass(frozen=True)
class ServiceSeams:
    """The seam modules of one service.

    `bus` names a module that has `get_/set_event_bus`. `verifier` names a module that has
    `get_/set_zitadel_auth_service`. The SpiceDB client has one seam, `runefoble_auth.factory`.
    `verifier_scope` says when the shared test issuer is trusted there:
    - `session`: for the whole session (module-scoped live upstreams send signed requests).
    - `test`: for every test, restored after it.
    - `on_demand`: only for tests that request `trusted_ws_issuer`.
    """

    name: str
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
    ServiceSeams("campaign_analytics"),
    ServiceSeams(
        "campaign_lore",
        bus="campaign_lore.dependencies",
        verifier="campaign_lore.identity",
        verifier_scope="test",
    ),
    ServiceSeams(
        "character_sheet",
        bus="character_sheet.dependencies",
        verifier="character_sheet.dependencies",
        verifier_scope="test",
    ),
    ServiceSeams(
        "game_session",
        bus="game_session.dependencies",
        verifier="game_session.shared.identity",
        verifier_scope="on_demand",
    ),
    ServiceSeams(
        "gateway_api",
        bus="gateway_api.dependencies",
        verifier="gateway_api.auth",
        verifier_scope="on_demand",
    ),
    ServiceSeams("gateway_mcp"),
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


def _check_seam_modules_at_collection() -> None:
    """Import every seam module named in `SERVICE_SEAMS` when the harness loads.

    The harness is a pytest plugin, so a misspelled module name or a missing setter fails the
    whole run at collection. No seam is skipped silently.
    """
    for row in SERVICE_SEAMS:
        if row.bus is not None:
            module = importlib.import_module(row.bus)
            assert callable(getattr(module, "set_event_bus", None)), (
                f"{row.bus} has no set_event_bus"
            )
        if row.verifier is not None:
            importlib.import_module(row.verifier)


_check_seam_modules_at_collection()


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


def _current(module: ModuleType, getter: str) -> object:
    """Return the seam value now. A seam that no startup configured yet reads as None.

    The gateway-mcp bus raises until its own process start-up injects one.
    """
    try:
        return getattr(module, getter)()
    except RuntimeError:
        return None


def _swap(
    modules: list[ModuleType], getter: str, setter: str, value_for: Callable[[], object]
) -> list[tuple[ModuleType, object]]:
    """Set a seam on each module and return the previous values for the restore."""
    previous = [(mod, _current(mod, getter)) for mod in modules]
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


@contextmanager
def routed_event_bus(redis: MockAsyncRedis) -> Iterator[object]:
    """Route every service publish to `redis` in this block, then restore the previous buses.

    Use it in module-scoped setup, which runs before the function-scoped default bus exists.
    """
    from runefoble_platform.redis_bus import RedisStreamsEventBus

    bus = RedisStreamsEventBus(client=redis)
    previous = _swap(_modules("bus"), "get_event_bus", "set_event_bus", lambda: bus)
    try:
        yield bus
    finally:
        _restore(previous, "set_event_bus")


@pytest.fixture(autouse=True)
def default_redis_event_bus(mock_bus: MockAsyncRedis) -> Iterator[object]:
    """Route every service publish to `mock_bus` unless a test overrides it.

    Redis is an external process. Tests must not open real connections to localhost:6379.
    """
    with routed_event_bus(mock_bus) as bus:
        yield bus


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

    The shared factory client (`runefoble_auth.factory`) is the one seam. No service keeps a copy.
    """
    if {"live_spicedb_endpoint", "live_spicedb_with_schema"} & set(request.fixturenames):
        yield None
        return

    mock_db = MockSpiceDBClient()
    with shared_spicedb_client(mock_db):
        yield mock_db


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


@contextmanager
def live_upstream(app: FastAPI, env_var: str) -> Iterator[str]:
    """Serve `app` on a loopback port and point `env_var` at it for the block.

    The gateway reads the owning service URL from `env_var`. Build the gateway client after the
    block starts, because the gateway lifespan reads the URL. The variable is restored on exit.
    """
    with serve(app) as url, pytest.MonkeyPatch.context() as env:
        env.setenv(env_var, url)
        yield url


@pytest.fixture
def character_sheet_upstream(monkeypatch, trusted_ws_issuer) -> Iterator[str]:
    """Serve character_sheet with a fresh event store (TASK-0585).

    The aggregate repository is replaced for this test, so characters from earlier tests do not
    leak in.
    """
    from character_sheet import dependencies as sheet_deps
    from character_sheet.aggregate import CharacterAggregate
    from character_sheet.main import app as sheet_app
    from eventsource.adapters.memory.store import InMemoryEventStore
    from runefoble_platform.event_sourcing import create_aggregate_repository

    fresh_repo = create_aggregate_repository(CharacterAggregate, event_store=InMemoryEventStore())
    monkeypatch.setattr(sheet_deps, "repo", fresh_repo)
    with live_upstream(sheet_app, "RUNEFOBLE_CHARACTER_SHEET_URL") as url:
        yield url


@pytest.fixture
def board_state_upstream(trusted_ws_issuer) -> Iterator[str]:
    """Serve board_state as a live loopback upstream (TASK-0582).

    Boards are created through its public `POST /api/v1/boards`.
    """
    from board_state.main import app as board_app

    with live_upstream(board_app, "RUNEFOBLE_BOARD_STATE_URL") as url:
        yield url


@pytest.fixture
def voice_agent_upstream(trusted_voice_issuer) -> Iterator[str]:
    """Serve voice_agent as a live loopback upstream (TASK-0593).

    Tokens minted by the voice test issuer are accepted.
    """
    from voice_agent.main import app as voice_app

    with live_upstream(voice_app, "RUNEFOBLE_VOICE_AGENT_URL") as url:
        yield url


@pytest.fixture
def asset_forge_upstream() -> Iterator[str]:
    """Serve asset_forge as a live loopback upstream (TASK-0595).

    The asset_forge verifier and SpiceDB mock are already set for each test.
    """
    from asset_forge.main import app as forge_app

    with live_upstream(forge_app, "RUNEFOBLE_ASSET_FORGE_URL") as url:
        yield url


@pytest.fixture
def game_session_upstream(trusted_ws_issuer) -> Iterator[str]:
    """Serve game_session with fresh in-memory campaign state.

    Tokens minted by `trusted_ws_issuer` are accepted by both services (TASK-0591).
    """
    from eventsource.adapters.memory.store import InMemoryEventStore
    from game_session.campaign.repositories import (
        get_campaign_repositories,
        set_campaign_repositories,
    )
    from game_session.main import app as session_app
    from runefoble_platform.event_sourcing import get_event_store, set_event_store

    from tests.helpers.module_state import restored_seam

    with (
        restored_seam(get_event_store, set_event_store, InMemoryEventStore(), replace=True),
        restored_seam(get_campaign_repositories, set_campaign_repositories, None, replace=True),
        live_upstream(session_app, "RUNEFOBLE_GAME_SESSION_URL") as url,
    ):
        yield url
