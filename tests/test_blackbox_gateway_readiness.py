"""Blackbox tests: the gateway is ready only when SpiceDB and Redis answer (TASK-0930).

A Kubernetes readiness probe calls `GET /readyz` on the gateway. While SpiceDB is not
reachable yet, `/readyz` answers 503, names `spicedb` and logs the failed probe. When SpiceDB
comes up, `/readyz` answers 200. A loopback TCP relay stands for the SpiceDB that is not up
yet. The test changes only the network. Every call goes through the public HTTP routes.

Governed by ADR-0005, ADR-0015 and Hard Invariant 7.
"""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app
from runefoble_auth.spicedb import SpiceDBClient

from tests.helpers.polling import wait_until
from tests.helpers.spicedb import LiveSpiceDB
from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.tcp_relay import TcpRelay


def test_ready_when_spicedb_and_redis_answer(live_spicedb_with_schema: LiveSpiceDB) -> None:
    with shared_spicedb_client(live_spicedb_with_schema.client), TestClient(app) as http:
        res = http.get("/readyz")
        assert res.status_code == 200, res.text
        assert res.json() == {"status": "ready", "service": "gateway_api"}


def test_not_ready_until_spicedb_answers(
    live_spicedb_with_schema: LiveSpiceDB, caplog: pytest.LogCaptureFixture
) -> None:
    host, port = live_spicedb_with_schema.endpoint.rsplit(":", 1)
    token = live_spicedb_with_schema.client.token
    with TcpRelay(host, int(port)) as relay:
        late = SpiceDBClient(endpoint=f"127.0.0.1:{relay.port}", token=token)
        with shared_spicedb_client(late), TestClient(app) as http:
            with caplog.at_level(logging.WARNING):
                not_ready = http.get("/readyz")
            assert not_ready.status_code == 503, not_ready.text
            body = not_ready.json()
            assert body["status"] == "not_ready"
            assert list(body["pending"]) == ["spicedb"]
            assert "Readiness probe spicedb failed" in caplog.text

            relay.come_up()
            assert wait_until(
                lambda: http.get("/readyz").status_code == 200, timeout_s=30, interval_s=0.5
            ), http.get("/readyz").text
