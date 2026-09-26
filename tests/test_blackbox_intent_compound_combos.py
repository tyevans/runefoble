"""Blackbox TDD test suite for Compound Action Combos and Rollbacks (TASK-0054, TASK-0094).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Interacts strictly through public HTTP routes and Redis Streams event contracts.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from runefoble_platform.redis_bus import (
    MockAsyncRedis,
    RedisStreamsEventBus,
)
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus as watcher_set_event_bus


def _entity(id_: str, name: str, tag: str, desc: str, x: int, y: int) -> dict:
    return {
        "id": id_,
        "name": name,
        "tag": tag,
        "descriptor": desc,
        "x": x,
        "y": y,
        "is_friendly": False,
    }


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture(autouse=True)
def configure_watcher_bus(mock_redis: MockAsyncRedis):
    watcher_set_event_bus(RedisStreamsEventBus(client=mock_redis))
    yield
    watcher_set_event_bus(None)


@pytest.fixture
def sample_board_entities() -> list[dict]:
    return [
        _entity("goblin_1", "Goblin", "archer", "archer by the pillar", 5, 3),
        _entity("goblin_2", "Goblin", "shaman", "shaman on the altar", 8, 9),
    ]


@pytest.mark.asyncio
async def test_compound_action_combo_ordering():
    """Verify multi-clause compound action parses into ordered capability checks."""
    session_id = str(uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/watcher/intent/parse",
            json={
                "speaker_id": "marcus-1",
                "speaker_name": "Marcus",
                "transcript": "I jump over the pit and attack the necromancer with my greataxe",
                "session_id": session_id,
                "entities": [
                    {
                        "id": "necro_1",
                        "name": "Necromancer",
                        "tag": "boss",
                        "descriptor": "necromancer by the sarcophagus",
                        "x": 6,
                        "y": 6,
                    }
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_compound"] is True and data["requires_disambiguation"] is False
        assert len(data["actions"]) == 2

        node1, node2 = data["actions"][0], data["actions"][1]
        assert (
            node1["order"] == 1
            and node1["action_type"] == "skill_check"
            and "pit" in node1["target"]
        )
        assert node1["parameters"]["skill"] == "athletics"
        assert (
            node2["order"] == 2
            and node2["action_type"] == "attack"
            and "necromancer" in node2["target"].lower()
        )
        assert node2["parameters"]["weapon"] == "greataxe"


@pytest.mark.asyncio
async def test_compound_action_with_intermediate_disambiguation(sample_board_entities):
    """Verify compound combo flags disambiguation only on ambiguous node and resolves cleanly."""
    session_id = str(uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/watcher/intent/parse",
            json={
                "speaker_id": "marcus-1",
                "speaker_name": "Marcus",
                "transcript": "I vault the table and strike the goblin with my sword",
                "session_id": session_id,
                "entities": sample_board_entities,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_compound"] is True and data["requires_disambiguation"] is True
        assert len(data["actions"]) == 2
        assert data["actions"][0]["action_type"] == "skill_check"
        assert (
            data["actions"][1]["requires_disambiguation"] is True
            and len(data["actions"][1]["candidates"]) == 2
        )

        resolve_resp = await client.post(
            "/api/v1/watcher/intent/resolve",
            json={
                "session_id": session_id,
                "disambiguation_id": data["disambiguation_id"],
                "selected_candidate_id": "goblin_1",
            },
        )
        assert resolve_resp.status_code == 200
        resolved = resolve_resp.json()
        assert resolved["actions"][1]["requires_disambiguation"] is False
        assert "archer by the pillar" in resolved["actions"][1]["target"]


@pytest.mark.asyncio
async def test_compound_action_partial_failure_and_rollback_coordination():
    """Verify intermediate failure aborts downstream actions and triggers rollback."""
    session_id = str(uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test"
    ) as client:
        parse_resp = await client.post(
            "/api/v1/watcher/intent/parse",
            json={
                "speaker_id": "marcus-1",
                "speaker_name": "Marcus",
                "transcript": "I move to 5, 7, make an athletics check, and strike the brute",
                "session_id": session_id,
                "entities": [{"id": "brute_1", "name": "Brute", "x": 6, "y": 7}],
            },
        )
        assert parse_resp.status_code == 200
        actions = parse_resp.json()["actions"]
        assert len(actions) == 3
        skill_node_id = actions[1]["node_id"]

        exec_rollback = await client.post(
            "/api/v1/watcher/intent/execute",
            json={
                "session_id": session_id,
                "speaker_name": "Marcus",
                "actions": actions,
                "step_results": {skill_node_id: False},
                "rollback_on_failure": True,
            },
        )
        assert exec_rollback.status_code == 200
        rb = exec_rollback.json()
        assert (
            rb["status"] == "rolled_back"
            and rb["failed_node_id"] == skill_node_id
            and rb["actions"][0]["status"] == "rolled_back"
            and rb["actions"][1]["status"] == "failed"
            and rb["actions"][2]["status"] == "aborted"
        )

        exec_partial = await client.post(
            "/api/v1/watcher/intent/execute",
            json={
                "session_id": session_id,
                "speaker_name": "Marcus",
                "actions": actions,
                "step_results": {skill_node_id: False},
                "rollback_on_failure": False,
            },
        )
        assert exec_partial.status_code == 200
        pt = exec_partial.json()
        assert (
            pt["status"] == "partial_failure"
            and pt["failed_node_id"] == skill_node_id
            and pt["actions"][0]["status"] == "completed"
            and pt["actions"][1]["status"] == "failed"
            and pt["actions"][2]["status"] == "aborted"
        )
