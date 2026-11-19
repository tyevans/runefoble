"""Blackbox tests for board and watcher event publishing through the Redis bus (TASK-0562).

Governed by ADR-0006 (Redis Streams Event Bus) and Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Verifies:
- AoE placement publishes AoETemplatePlaced to the board stream.
- UVTT import publishes every uncommitted event, in order.
- A world tick publishes WorldTickExecuted to the watcher stream.

The Redis double (MockAsyncRedis) sits behind RedisStreamsEventBus, which exposes only
``publish_event``. A call to a missing ``publish`` method therefore fails these tests.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient

from tests.helpers.campaign_setup import create_dm_campaign
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.the_watcher_app import watcher_app
from tests.helpers.ws_identity import SIGNING_ISSUER, bearer
from tests.test_blackbox_uvtt_import.conftest import build_sample_dd2vtt_dict

BOARD_STREAM = "runefoble.events.board"
WATCHER_STREAM = "runefoble.events.watcher"
WORLD_TICK_TYPE = "runefoble.events.watcher.world_tick_executed"
AOE_PLACED_TYPE = "runefoble.events.board.aoe_template_placed"


pytestmark = pytest.mark.usefixtures("trusted_ws_issuer", "board_campaign")


def _entries(redis: MockAsyncRedis, stream: str) -> list[dict[str, str]]:
    """Return stream entries as the bus wrote them, with their Redis entry id."""
    return [{"id": entry_id, **fields} for entry_id, fields in redis.streams.get(stream, [])]


@pytest.fixture
def board_redis(mock_bus):
    yield mock_bus


@pytest.fixture
def watcher_redis(mock_bus):
    yield mock_bus


def _create_board(client: TestClient, board_id: str, board_campaign: str) -> None:
    """Create a board through the public POST frontdoor before any board write."""
    res = client.post(
        "/api/v1/boards",
        json={"campaign_id": board_campaign, "session_id": board_id, "cols": 18, "rows": 14},
    )
    assert res.status_code == 200, res.text


def test_aoe_placement_publishes_template_placed_event(
    board_redis: MockAsyncRedis, board_campaign: str
):
    """Placing an AoE template writes one AoETemplatePlaced entry to the board stream."""
    client = TestClient(board_app, headers=bearer("user-test"))
    board_id = f"board-aoe-{uuid4().hex[:8]}"
    _create_board(client, board_id, board_campaign)

    res = client.post(
        f"/api/v1/boards/{board_id}/aoe/place",
        json={
            "shape": "sphere",
            "origin_x": 4,
            "origin_y": 4,
            "radius_ft": 10,
            "spell_name": "Fireball",
        },
    )
    assert res.status_code == 200, res.text

    placed = [e for e in _entries(board_redis, BOARD_STREAM) if e["event_type"] == AOE_PLACED_TYPE]
    assert len(placed) == 1
    assert json.loads(placed[0]["payload"])["spell_name"] == "Fireball"


def test_uvtt_import_publishes_every_uncommitted_event_in_order(
    board_redis: MockAsyncRedis, board_campaign: str
):
    """A UVTT import writes all of its uncommitted events to the board stream, not only the last."""
    client = TestClient(board_app, headers=bearer("user-test"))
    board_id = f"board-uvtt-{uuid4().hex[:8]}"
    _create_board(client, board_id, board_campaign)
    uvtt_data = build_sample_dd2vtt_dict(cols=18, rows=14, pixels_per_grid=100)
    file_bytes = json.dumps(uvtt_data).encode("utf-8")

    res = client.post(
        f"/api/v1/boards/{board_id}/import/uvtt",
        files={"file": ("crypt_dungeon.dd2vtt", file_bytes, "application/json")},
    )
    assert res.status_code == 200, res.text

    entries = _entries(board_redis, BOARD_STREAM)
    assert len(entries) > 1
    positions = [int(e["id"].rsplit("-", 1)[1]) for e in entries]
    assert positions == sorted(positions)


@pytest.mark.asyncio
async def test_world_tick_publishes_world_tick_executed_to_watcher_stream(
    watcher_redis: MockAsyncRedis, trusted_ws_issuer
):
    """Executing a world tick writes a world_tick_executed entry to the watcher stream."""
    client = TestClient(
        watcher_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )
    dm_user = f"dm-{uuid4().hex[:6]}"
    camp_id = create_dm_campaign(dm_user)

    res = client.post(
        f"/api/v1/campaigns/{camp_id}/world-tick",
        json={"regional_stability": 60, "random_seed": 42},
        headers=bearer(dm_user),
    )
    assert res.status_code == 200, res.text

    ticks = [
        e for e in _entries(watcher_redis, WATCHER_STREAM) if e["event_type"] == WORLD_TICK_TYPE
    ]
    assert len(ticks) == 1
