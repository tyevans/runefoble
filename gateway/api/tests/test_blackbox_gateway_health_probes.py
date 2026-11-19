"""Blackbox checks for the gateway health route's downstream probes (TASK-0674).

The gateway sends a real HTTP request to each downstream service. Each test sets the
upstream URLs in the environment, as a deployed gateway does, and reads only the public
`GET /healthz` response. The services are loopback doubles at the network boundary.
"""

import asyncio
from collections.abc import Iterator
from contextlib import ExitStack

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import closed_port_url, serve, unavailable_app

DOWNSTREAM_URL_ENV = {
    "game_session": "RUNEFOBLE_GAME_SESSION_URL",
    "the_watcher": "RUNEFOBLE_WATCHER_URL",
    "board_state": "RUNEFOBLE_BOARD_STATE_URL",
    "character_sheet": "RUNEFOBLE_CHARACTER_SHEET_URL",
    "voice_agent": "RUNEFOBLE_VOICE_AGENT_URL",
}


def _healthy_service() -> FastAPI:
    app = FastAPI()

    @app.get("/healthz")
    def _healthz() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return app


def _slow_service(delay_s: float) -> FastAPI:
    app = FastAPI()

    @app.get("/healthz")
    async def _healthz() -> JSONResponse:
        await asyncio.sleep(delay_s)
        return JSONResponse({"status": "ok"})

    return app


@pytest.fixture
def downstream_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    """Remove every downstream URL from the environment before a test sets its own."""
    for env_name in DOWNSTREAM_URL_ENV.values():
        monkeypatch.delenv(env_name, raising=False)
    yield monkeypatch


def _health(client: TestClient) -> dict:
    res = client.get("/healthz")
    assert res.status_code == 200
    return res.json()


def test_health_route_reports_the_probe_result_for_each_downstream(downstream_env):
    with ExitStack() as doubles:
        downstream_env.setenv(
            DOWNSTREAM_URL_ENV["game_session"], doubles.enter_context(serve(_healthy_service()))
        )
        downstream_env.setenv(
            DOWNSTREAM_URL_ENV["the_watcher"], doubles.enter_context(serve(_healthy_service()))
        )
        downstream_env.setenv(
            DOWNSTREAM_URL_ENV["board_state"], doubles.enter_context(serve(_healthy_service()))
        )
        downstream_env.setenv(
            DOWNSTREAM_URL_ENV["character_sheet"],
            doubles.enter_context(serve(unavailable_app(500))),
        )
        downstream_env.setenv(DOWNSTREAM_URL_ENV["voice_agent"], closed_port_url())

        with TestClient(gateway_app) as client:
            body = _health(client)

    assert body["status"] == "healthy"
    assert body["downstream_services"] == {
        "game_session": "operational",
        "the_watcher": "operational",
        "board_state": "operational",
        "character_sheet": "degraded",
        "voice_agent": "unreachable",
    }


def test_stopped_downstream_reports_unreachable_on_the_next_request(downstream_env):
    with ExitStack() as doubles:
        game_session_double = ExitStack()
        doubles.push(game_session_double)
        downstream_env.setenv(
            DOWNSTREAM_URL_ENV["game_session"],
            game_session_double.enter_context(serve(_healthy_service())),
        )
        for service in ("the_watcher", "board_state", "character_sheet", "voice_agent"):
            downstream_env.setenv(
                DOWNSTREAM_URL_ENV[service], doubles.enter_context(serve(_healthy_service()))
            )

        with TestClient(gateway_app) as client:
            first = _health(client)["downstream_services"]["game_session"]
            game_session_double.close()
            second = _health(client)["downstream_services"]["game_session"]

    assert first == "operational"
    assert second == "unreachable"


def test_unset_downstream_url_reports_not_configured(downstream_env):
    with TestClient(gateway_app) as client:
        body = _health(client)

    assert body["status"] == "healthy"
    assert body["downstream_services"] == dict.fromkeys(DOWNSTREAM_URL_ENV, "not_configured")


def test_downstream_slower_than_the_probe_timeout_reports_unreachable(downstream_env):
    downstream_env.setenv("RUNEFOBLE_GATEWAY_HEALTH_PROBE_TIMEOUT_S", "0.2")
    with ExitStack() as doubles:
        downstream_env.setenv(
            DOWNSTREAM_URL_ENV["game_session"],
            doubles.enter_context(serve(_slow_service(delay_s=3.0))),
        )

        with TestClient(gateway_app) as client:
            body = _health(client)

    assert body["status"] == "healthy"
    assert body["downstream_services"]["game_session"] == "unreachable"
