"""Blackbox frontdoor tests: a forged battlemap reaches the board (TASK-0704).

Governed by Hard Invariant 7 and ADR-0006 (Redis Streams event bus) and ADR-0015 (e).
- The map is forged through the public asset_forge route `POST /api/v1/forge/battlemap`.
- The board is read through the public board_state route `GET /api/v1/boards/{session_id}`.
- Redis is the only double: MockAsyncRedis at the `redis.asyncio.from_url` boundary. The
  board_state consumer starts through the real FastAPI lifespan and reads the asset stream.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import redis.asyncio
from asset_forge.main import app as forge_app
from board_state.main import app as board_app
from fastapi.testclient import TestClient

from tests.helpers.campaign_setup import create_dm_campaign
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.polling import wait_until
from tests.helpers.ws_identity import bearer

ASSET_STREAM = "runefoble.events.asset"
ASSET_DLQ = f"{ASSET_STREAM}.dlq"
PROMPT = "Subterranean dwarven forge with lava canals and broken anvil statues"

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def shared_redis(mock_bus: MockAsyncRedis, monkeypatch: pytest.MonkeyPatch) -> MockAsyncRedis:
    """One Redis double for every service client, so forge publishes reach the board consumer."""
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_args, **_kwargs: mock_bus)
    return mock_bus


def _forge(campaign_id: str, session_id: str) -> dict:
    """Forge a battlemap through the public route and return the response body."""
    client = TestClient(forge_app, headers=bearer("user-test"))
    res = client.post(
        "/api/v1/forge/battlemap",
        json={
            "campaign_id": campaign_id,
            "session_id": session_id,
            "prompt": PROMPT,
            "width_cells": 16,
            "height_cells": 16,
            "cell_size_px": 64,
            "wall_density": 0.25,
            "hazard_density": 0.15,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def _create_board(client: TestClient, campaign_id: str, session_id: str) -> None:
    res = client.post(
        "/api/v1/boards",
        json={"campaign_id": campaign_id, "session_id": session_id, "cols": 16, "rows": 16},
    )
    assert res.status_code == 200, res.text


def test_forged_battlemap_walls_and_hazards_appear_on_board_read(shared_redis: MockAsyncRedis):
    """A map forged for a session becomes the board geometry that the public board read returns."""
    campaign_id = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"

    with TestClient(board_app, headers=bearer("user-test")) as board_client:
        assert board_client.get("/healthz").json()["consumers"] == {"board_state": "running"}
        _create_board(board_client, campaign_id, session_id)

        forged = _forge(campaign_id, session_id)
        walls = forged["wall_segments"]
        hazards = forged["hazard_cells"]
        assert walls and hazards, "the test map must carry walls and hazards"

        def board_has_forged_geometry() -> bool:
            body = board_client.get(f"/api/v1/boards/{session_id}").json()
            return body["wall_segments"] == walls

        assert wait_until(board_has_forged_geometry, timeout_s=10.0, interval_s=0.05)

        board = board_client.get(f"/api/v1/boards/{session_id}").json()
        assert board["cols"] == 16
        assert board["rows"] == 16
        for hazard in hazards:
            cell = board["terrain_cells"][f"{hazard['x']},{hazard['y']}"]
            assert cell["hazard"] == hazard["hazard_type"]
            assert cell["terrain_type"] == hazard["terrain_type"]


def test_forged_battlemap_for_another_campaign_is_refused_to_dead_letter(
    shared_redis: MockAsyncRedis,
):
    """A map forged for campaign A never changes a board that belongs to campaign B."""
    campaign_a = create_dm_campaign("user-test")
    campaign_b = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"

    with TestClient(board_app, headers=bearer("user-test")) as board_client:
        _create_board(board_client, campaign_b, session_id)
        forged = _forge(campaign_a, session_id)
        assert forged["wall_segments"]

        assert wait_until(lambda: bool(shared_redis.streams.get(ASSET_DLQ)), timeout_s=10.0)
        (_entry_id, dead_letter), *_ = shared_redis.streams[ASSET_DLQ]
        assert "belongs to campaign" in dead_letter["error_reason"]
        board = board_client.get(f"/api/v1/boards/{session_id}").json()
        assert board["wall_segments"] == []
        assert board["terrain_cells"] == {}
