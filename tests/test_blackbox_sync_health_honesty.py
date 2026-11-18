"""Blackbox frontdoor tests: the sync health route reports failures honestly (TASK-0796).

Public surface: GET /api/v1/auth/sync/health on the gateway. The gateway runs its real lifespan.

1. A SpiceDB that cannot be reached reports `unhealthy` with the cause. It never reports healthy.
2. A health reply without `status` (a malformed reply) reports `unhealthy`. The gateway never
   fills the missing key with a default.
3. A failure that is not a SpiceDB failure is not swallowed as a health reply.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.sync import ZitadelSpiceDBSyncService

from tests.helpers.spicedb import find_free_port
from tests.helpers.spicedb_factory import shared_spicedb_client

HEALTH_PATH = "/api/v1/auth/sync/health"


@pytest.fixture
def gateway(game_session_upstream) -> Iterator[TestClient]:
    """Enter the gateway lifespan after game_session is served, so the routes have their upstreams."""
    with TestClient(app) as gateway_client:
        yield gateway_client


def test_unreachable_spicedb_reports_unhealthy_with_cause(gateway: TestClient) -> None:
    """With SpiceDB unreachable, the sync health route answers 503 and reports unhealthy."""
    closed_port = find_free_port()
    unreachable = SpiceDBClient(endpoint=f"127.0.0.1:{closed_port}", token="test-only-key")

    with shared_spicedb_client(unreachable):
        res = gateway.get(HEALTH_PATH)

    assert res.status_code == 503
    detail = res.json()["detail"]
    assert detail["status"] == "unhealthy"
    assert detail["spicedb_connected"] is False
    assert detail["backend"] == "grpc"
    assert "UNAVAILABLE" in detail["error"]


def test_healthy_spicedb_reports_healthy(gateway: TestClient) -> None:
    """With SpiceDB answering, the route reports healthy and names the backend."""
    res = gateway.get(HEALTH_PATH)

    assert res.status_code == 200
    assert res.json() == {
        "status": "healthy",
        "spicedb_connected": True,
        "sync_service": "operational",
        "backend": "mock",
    }


def test_reply_without_status_reports_unhealthy(
    gateway: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A malformed health reply (no `status`) is unhealthy. The gateway adds no default status."""

    async def malformed_reply(self: ZitadelSpiceDBSyncService) -> dict[str, object]:
        return {"spicedb_connected": True, "sync_service": "operational", "backend": "mock"}

    monkeypatch.setattr(ZitadelSpiceDBSyncService, "check_health", malformed_reply)

    res = gateway.get(HEALTH_PATH)

    assert res.status_code == 503
    detail = res.json()["detail"]
    assert detail["status"] == "unhealthy"
    assert "status" in detail["missing_fields"]


def test_non_spicedb_failure_is_not_reported_as_health(
    gateway: TestClient, spicedb, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure outside SpiceDB is a defect. It propagates. It is not a health reply."""

    async def defect(*_args: object, **_kwargs: object) -> None:
        raise KeyError("sync bookkeeping defect")

    monkeypatch.setattr(spicedb, "read_relationships", defect)

    with pytest.raises(KeyError, match="sync bookkeeping defect"):
        gateway.get(HEALTH_PATH)
