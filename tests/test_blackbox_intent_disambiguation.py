"""Blackbox TDD test suite for Conversational Intent Disambiguation and Compound Action Intents (TASK-0054).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Interacts strictly through public HTTP routes and Redis Streams event contracts.
"""

from __future__ import annotations

import time
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from runefoble_events.events import (
    CandidateGhostPreviewEmitted,
    CompoundActionResolved,
    IntentDisambiguationRequested,
)
from runefoble_platform.redis_bus import (
    MockAsyncRedis,
    RedisStreamsEventBus,
    deserialize_event,
)
from the_watcher.dependencies import (
    STREAM_BOARD,
    STREAM_WATCHER,
)
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus as watcher_set_event_bus


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture(autouse=True)
def configure_watcher_bus(mock_redis: MockAsyncRedis):
    event_bus = RedisStreamsEventBus(client=mock_redis)
    watcher_set_event_bus(event_bus)
    yield
    watcher_set_event_bus(None)


@pytest.fixture
def sample_board_entities() -> list[dict]:
    return [
        {
            "id": "goblin_1",
            "name": "Goblin",
            "tag": "archer",
            "descriptor": "archer by the pillar",
            "x": 5,
            "y": 3,
            "hp": 7,
            "is_friendly": False,
        },
        {
            "id": "goblin_2",
            "name": "Goblin",
            "tag": "shaman",
            "descriptor": "shaman on the altar",
            "x": 8,
            "y": 9,
            "hp": 12,
            "is_friendly": False,
        },
        {
            "id": "skeleton_1",
            "name": "Skeleton",
            "tag": "warrior",
            "descriptor": "skeleton warrior with shield",
            "x": 2,
            "y": 2,
            "hp": 10,
            "is_friendly": False,
        },
    ]


@pytest.mark.asyncio
async def test_target_disambiguation_multi_candidate_detection_and_prompt(sample_board_entities):
    """Verify ambiguous target query returns requires_disambiguation=True with audible prompt and candidates."""
    session_id = str(uuid4())
    campaign_id = str(uuid4())

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/watcher/intent/parse",
            json={
                "speaker_id": "marcus-1",
                "speaker_name": "Marcus",
                "transcript": "I shoot the goblin",
                "session_id": session_id,
                "campaign_id": campaign_id,
                "from_x": 1,
                "from_y": 1,
                "entities": sample_board_entities,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert data["requires_disambiguation"] is True
        assert data["disambiguation_id"] is not None
        assert len(data["candidates"]) == 2
        candidate_ids = [c["id"] for c in data["candidates"]]
        assert "goblin_1" in candidate_ids
        assert "goblin_2" in candidate_ids

        # Prompt format check: e.g. "Which goblin? The archer by the pillar or the shaman on the altar?"
        prompt = data["clarification_prompt"]
        assert "Which goblin?" in prompt
        assert "archer by the pillar" in prompt
        assert "shaman on the altar" in prompt
        assert data["execution_latency_ms"] < 400.0


@pytest.mark.asyncio
async def test_unambiguous_target_with_distinguishing_descriptor(sample_board_entities):
    """Verify that specific distinguishing tags bypass disambiguation."""
    session_id = str(uuid4())

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/watcher/intent/parse",
            json={
                "speaker_id": "marcus-1",
                "speaker_name": "Marcus",
                "transcript": "I shoot the goblin archer",
                "session_id": session_id,
                "entities": sample_board_entities,
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["requires_disambiguation"] is False
        assert len(data["actions"]) == 1
        assert "archer" in data["actions"][0]["target"].lower()


@pytest.mark.asyncio
async def test_redis_streams_events_on_disambiguation_request(
    mock_redis: MockAsyncRedis, sample_board_entities
):
    """Verify IntentDisambiguationRequested and CandidateGhostPreviewEmitted events are emitted to Redis Streams."""
    session_id = str(uuid4())
    campaign_id = str(uuid4())

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/watcher/intent/parse",
            json={
                "speaker_id": "marcus-1",
                "speaker_name": "Marcus",
                "transcript": "I attack the goblin",
                "session_id": session_id,
                "campaign_id": campaign_id,
                "from_x": 0,
                "from_y": 0,
                "entities": sample_board_entities,
            },
        )
        assert resp.status_code == 200
        disambig_id = resp.json()["disambiguation_id"]

    # 1. Check STREAM_WATCHER for IntentDisambiguationRequested
    assert STREAM_WATCHER in mock_redis.streams
    watcher_entries = mock_redis.streams[STREAM_WATCHER]
    disambig_events = [
        deserialize_event(fields)
        for _, fields in watcher_entries
        if isinstance(deserialize_event(fields), IntentDisambiguationRequested)
    ]
    assert len(disambig_events) == 1
    event = disambig_events[0]
    assert event.speaker_name == "Marcus"
    assert event.disambiguation_id == disambig_id
    assert event.ambiguous_target == "goblin"
    assert len(event.candidates) == 2

    # 2. Check STREAM_BOARD for CandidateGhostPreviewEmitted
    assert STREAM_BOARD in mock_redis.streams
    board_entries = mock_redis.streams[STREAM_BOARD]
    ghost_events = [
        deserialize_event(fields)
        for _, fields in board_entries
        if isinstance(deserialize_event(fields), CandidateGhostPreviewEmitted)
    ]
    assert len(ghost_events) == 2
    ghost_cand_ids = [g.candidate_id for g in ghost_events]
    assert "goblin_1" in ghost_cand_ids
    assert "goblin_2" in ghost_cand_ids


@pytest.mark.asyncio
async def test_resolve_intent_disambiguation_flow(
    mock_redis: MockAsyncRedis, sample_board_entities
):
    """Verify player disambiguation selection updates action target and emits CompoundActionResolved."""
    session_id = str(uuid4())
    campaign_id = str(uuid4())

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Parse ambiguous intent
        parse_resp = await client.post(
            "/api/v1/watcher/intent/parse",
            json={
                "speaker_id": "marcus-1",
                "speaker_name": "Marcus",
                "transcript": "I shoot the goblin",
                "session_id": session_id,
                "campaign_id": campaign_id,
                "entities": sample_board_entities,
            },
        )
        d_id = parse_resp.json()["disambiguation_id"]

        # Step 2: Resolve with selected candidate
        resolve_resp = await client.post(
            "/api/v1/watcher/intent/resolve",
            json={
                "session_id": session_id,
                "campaign_id": campaign_id,
                "disambiguation_id": d_id,
                "selected_candidate_id": "goblin_2",
            },
        )
        assert resolve_resp.status_code == 200
        resolved_data = resolve_resp.json()
        assert resolved_data["disambiguation_id"] == d_id
        assert "shaman on the altar" in resolved_data["resolved_target"]
        assert resolved_data["status"] == "ready"
        assert len(resolved_data["actions"]) == 1
        assert "shaman" in resolved_data["actions"][0]["target"]

    # Verify CompoundActionResolved on Redis Streams
    watcher_entries = mock_redis.streams[STREAM_WATCHER]
    resolved_events = [
        deserialize_event(fields)
        for _, fields in watcher_entries
        if isinstance(deserialize_event(fields), CompoundActionResolved)
    ]
    assert len(resolved_events) == 1
    r_event = resolved_events[0]
    assert r_event.disambiguation_id == d_id
    assert "shaman on the altar" in r_event.resolved_target


@pytest.mark.asyncio
async def test_compound_action_combo_ordering():
    """Verify multi-clause compound action parses into ordered capability checks."""
    session_id = str(uuid4())

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
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

        assert data["is_compound"] is True
        assert data["requires_disambiguation"] is False
        assert len(data["actions"]) == 2

        # Node 1: Skill check (athletics jump)
        node1 = data["actions"][0]
        assert node1["order"] == 1
        assert node1["action_type"] == "skill_check"
        assert node1["parameters"]["skill"] == "athletics"
        assert "pit" in node1["target"]

        # Node 2: Attack necromancer with greataxe
        node2 = data["actions"][1]
        assert node2["order"] == 2
        assert node2["action_type"] == "attack"
        assert "necromancer" in node2["target"].lower()
        assert node2["parameters"]["weapon"] == "greataxe"


@pytest.mark.asyncio
async def test_compound_action_with_intermediate_disambiguation(sample_board_entities):
    """Verify compound combo flags disambiguation only on ambiguous node and resolves cleanly."""
    session_id = str(uuid4())

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Utterance: stunt check + attack ambiguous goblin
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

        assert data["is_compound"] is True
        assert data["requires_disambiguation"] is True
        assert len(data["actions"]) == 2
        assert data["actions"][0]["action_type"] == "skill_check"
        assert data["actions"][1]["requires_disambiguation"] is True
        assert len(data["actions"][1]["candidates"]) == 2

        # Resolve the combo
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

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Parse 3-action combo: move -> jump -> attack
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

        # 1. Execute with skill check failure and rollback enabled
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
        rollback_data = exec_rollback.json()
        assert rollback_data["status"] == "rolled_back"
        assert rollback_data["failed_node_id"] == skill_node_id
        # Preceding move rolled back
        assert rollback_data["actions"][0]["status"] == "rolled_back"
        # Skill check failed
        assert rollback_data["actions"][1]["status"] == "failed"
        # Subsequent strike aborted
        assert rollback_data["actions"][2]["status"] == "aborted"

        # 2. Execute with skill check failure and rollback disabled (partial failure)
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
        partial_data = exec_partial.json()
        assert partial_data["status"] == "partial_failure"
        assert partial_data["failed_node_id"] == skill_node_id
        # Preceding move completed
        assert partial_data["actions"][0]["status"] == "completed"
        # Skill check failed
        assert partial_data["actions"][1]["status"] == "failed"
        # Subsequent strike aborted
        assert partial_data["actions"][2]["status"] == "aborted"


@pytest.mark.asyncio
async def test_timing_budget_sub_400ms_compliance(sample_board_entities):
    """Verify disambiguation candidate evaluation executes in < 400ms SLA."""
    session_id = str(uuid4())

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        latencies = []
        for _ in range(20):
            t0 = time.perf_counter()
            resp = await client.post(
                "/api/v1/watcher/intent/parse",
                json={
                    "speaker_id": "marcus-1",
                    "speaker_name": "Marcus",
                    "transcript": "I attack the goblin",
                    "session_id": session_id,
                    "entities": sample_board_entities,
                },
            )
            latencies.append((time.perf_counter() - t0) * 1000)
            assert resp.status_code == 200

        max_latency = max(latencies)
        avg_latency = sum(latencies) / len(latencies)
        assert max_latency < 400.0, f"Max latency exceeded 400ms SLA: {max_latency:.2f}ms"
        assert avg_latency < 50.0, f"Average latency too high: {avg_latency:.2f}ms"


@pytest.mark.asyncio
async def test_resolve_invalid_disambiguation_id_returns_404():
    """Verify resolving unknown or expired disambiguation ID returns 404."""
    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/watcher/intent/resolve",
            json={
                "session_id": str(uuid4()),
                "disambiguation_id": "nonexistent-id",
                "selected_candidate_id": "c-1",
            },
        )
        assert resp.status_code == 404
