"""Blackbox tests: the remaining five services gate `/readyz` on their dependencies (TASK-0933).

Each service answers `GET /readyz` through its public route. While a dependency is not
reachable, the route answers 503, names the dependency, and logs the failed check. A loopback
TCP relay stands for SpiceDB that is not up yet. The tests change only the network. The voice
agent's speech engine is missing its model cache. The inference worker's LLM backend is an
installed port that does not answer. Each test changes one dependency and nothing else.

Governed by ADR-0005, ADR-0015 and Hard Invariant 7.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from inference_worker.ports import backend_unavailable
from runefoble_auth.spicedb import SpiceDBClient

from tests.helpers.campaign_analytics_service import AnalyticsService
from tests.helpers.inference_worker_port import install_worker_port
from tests.helpers.live_services import serve
from tests.helpers.polling import wait_until
from tests.helpers.spicedb import LiveSpiceDB
from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.tcp_relay import TcpRelay
from tests.test_blackbox_voice_model_cache import (  # noqa: F401 - fixtures of the speech suite
    _cache_model,
    espeak_stub,
    model_dir,
    speech_env,
)


@contextlib.contextmanager
def _spicedb_behind_relay(live: LiveSpiceDB) -> Iterator[TcpRelay]:
    """Make the process SpiceDB client point at a relay that does not listen yet."""
    host, port = live.endpoint.rsplit(":", 1)
    with TcpRelay(host, int(port)) as relay:
        late = SpiceDBClient(endpoint=f"127.0.0.1:{relay.port}", token=live.client.token)
        with shared_spicedb_client(late):
            yield relay


def _wait_until_ready(get: Callable[[str], httpx.Response], path: str) -> None:
    assert wait_until(lambda: get(path).status_code == 200, timeout_s=30, interval_s=0.5)


def test_rules_compendium_readyz_waits_for_spicedb(
    live_spicedb_with_schema: LiveSpiceDB, caplog: pytest.LogCaptureFixture
) -> None:
    from rules_compendium.main import app

    with _spicedb_behind_relay(live_spicedb_with_schema) as relay, TestClient(app) as http:
        with caplog.at_level(logging.WARNING):
            not_ready = http.get("/readyz")
        assert not_ready.status_code == 503, not_ready.text
        assert not_ready.json()["service"] == "rules_compendium"
        assert list(not_ready.json()["pending"]) == ["spicedb"]
        assert "Readiness probe spicedb failed" in caplog.text
        assert http.get("/healthz").status_code == 200

        relay.come_up()
        _wait_until_ready(http.get, "/readyz")


def test_campaign_analytics_readyz_waits_for_spicedb(
    analytics_service: AnalyticsService,
    live_spicedb_with_schema: LiveSpiceDB,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        _spicedb_behind_relay(live_spicedb_with_schema) as relay,
        analytics_service.start() as http,
    ):
        with caplog.at_level(logging.WARNING):
            not_ready = http.get("/readyz")
        assert not_ready.status_code == 503, not_ready.text
        assert not_ready.json()["service"] == "campaign_analytics"
        assert list(not_ready.json()["pending"]) == ["spicedb"]
        assert "Readiness probe spicedb failed" in caplog.text

        relay.come_up()
        _wait_until_ready(http.get, "/readyz")


def test_gateway_mcp_readyz_waits_for_spicedb(
    live_spicedb_with_schema: LiveSpiceDB, caplog: pytest.LogCaptureFixture
) -> None:
    from gateway_mcp.container import GatewayMcpContainer
    from gateway_mcp.server import build_http_app

    app = build_http_app(GatewayMcpContainer.default())
    with (
        _spicedb_behind_relay(live_spicedb_with_schema) as relay,
        serve(app, lifespan="on") as base_url,
    ):
        with caplog.at_level(logging.WARNING):
            not_ready = httpx.get(f"{base_url}/readyz")
        assert not_ready.status_code == 503, not_ready.text
        assert list(not_ready.json()["pending"]) == ["spicedb"]
        assert "Readiness probe spicedb failed" in caplog.text
        # /readyz is public, like /healthz. No bearer is needed to read it.
        assert httpx.get(f"{base_url}/healthz").status_code == 200

        relay.come_up()
        assert wait_until(
            lambda: httpx.get(f"{base_url}/readyz").status_code == 200,
            timeout_s=30,
            interval_s=0.5,
        )


@pytest.mark.usefixtures("default_redis_event_bus", "speech_env")
def test_voice_agent_readyz_waits_for_spicedb(
    model_dir,  # noqa: F811 - the model directory of the speech suite
    live_spicedb_with_schema: LiveSpiceDB,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from voice_agent.main import app

    _cache_model(model_dir)
    with (
        _spicedb_behind_relay(live_spicedb_with_schema) as relay,
        TestClient(app) as http,
    ):
        with caplog.at_level(logging.WARNING):
            not_ready = http.get("/readyz")
        assert not_ready.status_code == 503, not_ready.text
        assert not_ready.json()["service"] == "voice_agent"
        assert list(not_ready.json()["pending"]) == ["spicedb"]
        assert "Readiness probe spicedb failed" in caplog.text

        relay.come_up()
        _wait_until_ready(http.get, "/readyz")


@pytest.mark.usefixtures("default_redis_event_bus", "speech_env")
def test_voice_agent_readyz_names_a_speech_engine_without_its_model(
    model_dir,  # noqa: F811 - the model directory of the speech suite
    live_spicedb_with_schema: LiveSpiceDB,
) -> None:
    from voice_agent.main import app

    # No cached model: the STT engine is not ready. Every other dependency answers.
    with shared_spicedb_client(live_spicedb_with_schema.client), TestClient(app) as http:
        not_ready = http.get("/readyz")
        assert not_ready.status_code == 503, not_ready.text
        assert list(not_ready.json()["pending"]) == ["stt"]

        _cache_model(model_dir)
        _wait_until_ready(http.get, "/readyz")


class _ReadyPort:
    """An LLM port whose backend answers. Only the readiness check is used in these tests."""

    engine_name = "test_backend"

    async def check_ready(self) -> None:
        return None


class _DownPort:
    """An LLM port whose backend does not answer."""

    engine_name = "test_backend"

    async def check_ready(self) -> None:
        raise backend_unavailable("test_backend", "backend is not listening")


@pytest.fixture
def inference_worker_app() -> Iterator[object]:
    from inference_worker.api import app

    yield app


def test_inference_worker_readyz_answers_200_when_the_backend_answers(
    inference_worker_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_worker_port(monkeypatch, _ReadyPort())
    # No `with`: the lifespan builds the real port from the environment. The test installs its own.
    http = TestClient(inference_worker_app)
    res = http.get("/readyz")
    assert res.status_code == 200, res.text
    assert res.json() == {"status": "ready", "service": "inference_worker"}


def test_inference_worker_readyz_names_a_backend_that_does_not_answer(
    inference_worker_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_worker_port(monkeypatch, _DownPort())
    http = TestClient(inference_worker_app)
    res = http.get("/readyz")
    assert res.status_code == 503, res.text
    assert list(res.json()["pending"]) == ["llm_backend"]
