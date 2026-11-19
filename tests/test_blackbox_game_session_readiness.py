"""Blackbox tests: game_session is ready only when its write dependencies answer (TASK-0929).

A Kubernetes readiness probe calls `GET /readyz`. While SpiceDB or the event store is not
reachable yet, `/readyz` answers 503 and names the dependency, and a write route answers
503 with a log line. When the dependency comes up, `/readyz` answers 200 and the write
succeeds. A loopback TCP relay stands for the dependency that is not up yet. The test
changes only the network. Every call goes through the public HTTP routes.

Governed by ADR-0005, ADR-0015 and Hard Invariant 7.
"""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client, set_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import build_event_store, get_event_store, set_event_store

from tests.helpers.game_session_app import app_with_container, build_test_container
from tests.helpers.module_state import SeamRestorer
from tests.helpers.polling import wait_until
from tests.helpers.spicedb import LiveSpiceDB
from tests.helpers.tcp_relay import TcpRelay
from tests.helpers.ws_identity import bearer

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

OWNER = "readiness-owner"


def _create_campaign(http: TestClient) -> int:
    res = http.post("/api/v1/campaigns", json={"title": "Readiness Keep"}, headers=bearer(OWNER))
    return res.status_code


def _ready(http: TestClient) -> bool:
    return http.get("/readyz").status_code == 200


def _wait_ready(http: TestClient) -> None:
    assert wait_until(lambda: _ready(http), timeout_s=30, interval_s=0.5), http.get("/readyz").text


@pytest.fixture
def live_client(live_spicedb_with_schema: LiveSpiceDB, seam_restorer: SeamRestorer) -> LiveSpiceDB:
    """Make the live SpiceDB the factory client for one test."""
    seam_restorer.replace(get_spicedb_client, set_spicedb_client, live_spicedb_with_schema.client)
    return live_spicedb_with_schema


def test_ready_when_every_dependency_answers(live_client: LiveSpiceDB) -> None:
    with TestClient(app_with_container(build_test_container())) as http:
        res = http.get("/readyz")
        assert res.status_code == 200, res.text
        assert res.json() == {"status": "ready", "service": "game_session"}
        assert http.get("/healthz").status_code == 200


def test_not_ready_and_write_refused_until_spicedb_answers(
    live_client: LiveSpiceDB,
    seam_restorer: SeamRestorer,
    caplog: pytest.LogCaptureFixture,
) -> None:
    host, port = live_client.endpoint.rsplit(":", 1)
    with TcpRelay(host, int(port)) as relay:
        late = SpiceDBClient(endpoint=f"127.0.0.1:{relay.port}", token=live_client.client.token)
        seam_restorer.replace(get_spicedb_client, set_spicedb_client, late)
        with TestClient(app_with_container(build_test_container())) as http:
            with caplog.at_level(logging.WARNING):
                not_ready = http.get("/readyz")
                assert not_ready.status_code == 503, not_ready.text
                assert list(not_ready.json()["pending"]) == ["spicedb"]
                assert _create_campaign(http) == 503
            assert "Readiness probe spicedb failed" in caplog.text
            assert "SpiceDB session link write failed" in caplog.text

            relay.come_up()
            _wait_ready(http)
            assert _create_campaign(http) == 201


def test_not_ready_and_write_refused_until_the_event_store_answers(
    live_client: LiveSpiceDB,
    postgres_service: dict[str, str | int],
    seam_restorer: SeamRestorer,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with TcpRelay(str(postgres_service["host"]), int(postgres_service["port"])) as relay:
        dsn = str(postgres_service["async_dsn"]).replace(
            f":{postgres_service['port']}/", f":{relay.port}/"
        )
        # PostgreSQL is gone after the start-up check passed, so the store skips that check.
        settings = PlatformSettings(database_url=dsn, event_store_backend="postgresql")
        store = build_event_store(settings, probe_connection=False)
        seam_restorer.replace(get_event_store, set_event_store, store)
        with TestClient(app_with_container(build_test_container())) as http:
            with caplog.at_level(logging.WARNING):
                not_ready = http.get("/readyz")
                assert not_ready.status_code == 503, not_ready.text
                assert list(not_ready.json()["pending"]) == ["event_store"]
                assert _create_campaign(http) == 503
            assert "Readiness probe event_store failed" in caplog.text
            assert "Event store unavailable on POST /api/v1/campaigns" in caplog.text

            relay.come_up()
            _wait_ready(http)
            assert _create_campaign(http) == 201
