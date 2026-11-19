"""Each HTTP operation is served under one path (ADR-0015, Definition of Ready rule 9).

The test reads the route table of every service app. It fails when one endpoint answers two
paths, or when one method and path pair is registered twice. WebSocket routes are not OpenAPI
operations, so this check leaves them out.
"""

from collections import defaultdict
from importlib import import_module

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.routing import Route

SERVICE_APPS = [
    "asset_forge.main",
    "board_state.main",
    "campaign_analytics.main",
    "campaign_lore.main",
    "character_sheet.main",
    "game_session.main",
    "inference_worker.api",
    "rules_compendium.main",
    "soundscape.main",
    "the_watcher.main",
    "voice_agent.main",
    "gateway_api.main",
]


def _http_routes(app) -> list[Route]:
    return [route for route in app.routes if isinstance(route, (APIRoute, Route))]


def _operations(app) -> list[tuple[str, str, object]]:
    return [
        (method, route.path, route.endpoint)
        for route in _http_routes(app)
        for method in sorted(route.methods or ())
    ]


@pytest.mark.parametrize("module_name", SERVICE_APPS)
def test_each_method_and_path_is_served_once(module_name: str) -> None:
    app = import_module(module_name).app
    operations = _operations(app)
    assert operations, f"{module_name} serves no HTTP routes"

    seen: set[tuple[str, str]] = set()
    duplicates = []
    for method, path, _endpoint in operations:
        if (method, path) in seen:
            duplicates.append(f"{method} {path}")
        seen.add((method, path))
    assert not duplicates, f"{module_name} serves a method and path twice: {duplicates}"


@pytest.mark.parametrize("module_name", SERVICE_APPS)
def test_no_handler_answers_two_paths(module_name: str) -> None:
    app = import_module(module_name).app
    paths_by_handler: defaultdict[object, set[str]] = defaultdict(set)
    for _method, path, endpoint in _operations(app):
        paths_by_handler[endpoint].add(path)

    aliased = {
        getattr(endpoint, "__qualname__", repr(endpoint)): sorted(paths)
        for endpoint, paths in paths_by_handler.items()
        if len(paths) > 1
    }
    assert not aliased, f"{module_name} serves one handler under two paths: {aliased}"


def test_game_session_settlement_and_bounty_routes_answer_only_on_api_v1() -> None:
    from tests.helpers.game_session_app import session_app as app

    client = TestClient(app)
    assert client.post("/settlements", json={}).status_code == 404
    assert client.get("/settlements/settlement-1").status_code == 404
    assert client.get("/sessions/session-1/contracts/bounties").status_code == 404
    assert client.get("/sessions/session-1/reactions/active").status_code == 404
