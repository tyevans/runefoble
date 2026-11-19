"""Blackbox tests: each service is ready only when its dependencies answer (TASK-0931).

A Kubernetes readiness probe calls `GET /readyz`. While a dependency is not reachable yet,
`/readyz` answers 503, names the dependency and logs the failed check. When the dependency
comes up, `/readyz` answers 200. A loopback TCP relay stands for the SpiceDB that is not up
yet, and the FakeSilo HTTP double stands for Silo. The tests change only the network. Every
call goes through the public HTTP routes.

Governed by ADR-0005, ADR-0015 and Hard Invariant 7.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient

from tests.helpers.polling import wait_until
from tests.helpers.silo_fixtures import FakeSilo
from tests.helpers.spicedb import LiveSpiceDB
from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.tcp_relay import TcpRelay


def _asset_forge() -> FastAPI:
    from asset_forge.main import app

    return app


def _board_state() -> FastAPI:
    from board_state.main import app

    return app


def _character_sheet() -> FastAPI:
    from character_sheet.main import app

    return app


def _campaign_lore() -> FastAPI:
    from campaign_lore.main import create_app

    return create_app()


def _soundscape() -> FastAPI:
    from soundscape.main import app

    return app


def _the_watcher() -> FastAPI:
    from tests.helpers.the_watcher_app import app_with_container, build_test_container

    return app_with_container(build_test_container())


@dataclass(frozen=True)
class Service:
    name: str
    build: Callable[[], FastAPI]
    fixtures: tuple[str, ...] = ()


SERVICES = (
    Service("asset_forge", _asset_forge),
    Service("board_state", _board_state),
    Service("character_sheet", _character_sheet),
    Service("campaign_lore", _campaign_lore, ("lore_backends",)),
    Service("soundscape", _soundscape),
    Service("the_watcher", _the_watcher),
)


@pytest.fixture(params=SERVICES, ids=lambda service: service.name)
def service(request: pytest.FixtureRequest) -> Service:
    for name in request.param.fixtures:
        request.getfixturevalue(name)
    return request.param


def _wait_ready(http: TestClient) -> None:
    assert wait_until(
        lambda: http.get("/readyz").status_code == 200, timeout_s=30, interval_s=0.5
    ), http.get("/readyz").text


def test_ready_when_every_dependency_answers(
    service: Service, live_spicedb_with_schema: LiveSpiceDB
) -> None:
    with (
        shared_spicedb_client(live_spicedb_with_schema.client),
        TestClient(service.build()) as http,
    ):
        res = http.get("/readyz")
        assert res.status_code == 200, res.text
        assert res.json() == {"status": "ready", "service": service.name}
        assert http.get("/healthz").status_code == 200


def test_not_ready_until_spicedb_answers(
    service: Service, live_spicedb_with_schema: LiveSpiceDB, caplog: pytest.LogCaptureFixture
) -> None:
    host, port = live_spicedb_with_schema.endpoint.rsplit(":", 1)
    token = live_spicedb_with_schema.client.token
    with TcpRelay(host, int(port)) as relay:
        late = SpiceDBClient(endpoint=f"127.0.0.1:{relay.port}", token=token)
        with shared_spicedb_client(late), TestClient(service.build()) as http:
            with caplog.at_level(logging.WARNING):
                not_ready = http.get("/readyz")
            assert not_ready.status_code == 503, not_ready.text
            body = not_ready.json()
            assert body["status"] == "not_ready"
            assert body["service"] == service.name
            assert list(body["pending"]) == ["spicedb"]
            assert "Readiness probe spicedb failed" in caplog.text

            relay.come_up()
            _wait_ready(http)


def test_asset_forge_is_not_ready_until_silo_answers(
    live_spicedb_with_schema: LiveSpiceDB,
    silo_double: FakeSilo,
    caplog: pytest.LogCaptureFixture,
) -> None:
    silo_double.outage = True
    with shared_spicedb_client(live_spicedb_with_schema.client), TestClient(_asset_forge()) as http:
        with caplog.at_level(logging.WARNING):
            not_ready = http.get("/readyz")
        assert not_ready.status_code == 503, not_ready.text
        assert list(not_ready.json()["pending"]) == ["silo"]
        assert "Readiness probe silo failed" in caplog.text

        silo_double.outage = False
        _wait_ready(http)


def test_asset_forge_is_not_ready_without_its_asset_bucket(
    live_spicedb_with_schema: LiveSpiceDB, silo_double: FakeSilo
) -> None:
    silo_double.buckets.clear()
    with shared_spicedb_client(live_spicedb_with_schema.client), TestClient(_asset_forge()) as http:
        not_ready = http.get("/readyz")
        assert not_ready.status_code == 503, not_ready.text
        assert "returned status 404" in not_ready.json()["pending"]["silo"]

        silo_double.buckets.add("runefoble-assets")
        _wait_ready(http)
