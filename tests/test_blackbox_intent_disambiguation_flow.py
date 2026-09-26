"""Blackbox TDD test suite for Conversational Intent Disambiguation Flow (TASK-0054, TASK-0094).

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


def _entity(id_: str, name: str, tag: str, desc: str, x: int, y: int, hp: int) -> dict:
    return {
        "id": id_,
        "name": name,
        "tag": tag,
        "descriptor": desc,
        "x": x,
        "y": y,
        "hp": hp,
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
        _entity("goblin_1", "Goblin", "archer", "archer by the pillar", 5, 3, 7),
        _entity("goblin_2", "Goblin", "shaman", "shaman on the altar", 8, 9, 12),
        _entity("skeleton_1", "Skeleton", "warrior", "skeleton warrior with shield", 2, 2, 10),
    ]


async def _parse(
    client: AsyncClient,
    transcript: str,
    session_id: str,
    campaign_id: str | None = None,
    entities: list[dict] | None = None,
    from_x: int | None = None,
    from_y: int | None = None,
):
    body = {
        "speaker_id": "marcus-1",
        "speaker_name": "Marcus",
        "transcript": transcript,
        "session_id": session_id,
    }
    if campaign_id:
        body["campaign_id"] = campaign_id
    if entities:
        body["entities"] = entities
    if from_x is not None:
        body.update(from_x=from_x, from_y=from_y)
    return await client.post("/api/v1/watcher/intent/parse", json=body)


@pytest.mark.asyncio
async def test_target_disambiguation_multi_candidate_detection_and_prompt(sample_board_entities):
    """Verify ambiguous target query returns requires_disambiguation=True with prompt and candidates."""
    s_id, c_id = str(uuid4()), str(uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test"
    ) as client:
        resp = await _parse(
            client, "I shoot the goblin", s_id, c_id, sample_board_entities, from_x=1, from_y=1
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["requires_disambiguation"] is True and data["disambiguation_id"] is not None
        assert len(data["candidates"]) == 2
        candidate_ids = [c["id"] for c in data["candidates"]]
        assert "goblin_1" in candidate_ids and "goblin_2" in candidate_ids
        prompt = data["clarification_prompt"]
        assert "Which goblin?" in prompt and "archer by the pillar" in prompt
        assert "shaman on the altar" in prompt and data["execution_latency_ms"] < 400.0


@pytest.mark.asyncio
async def test_unambiguous_target_with_distinguishing_descriptor(sample_board_entities):
    """Verify that specific distinguishing tags bypass disambiguation."""
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test"
    ) as client:
        resp = await _parse(
            client, "I shoot the goblin archer", str(uuid4()), entities=sample_board_entities
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["requires_disambiguation"] is False and len(data["actions"]) == 1
        assert "archer" in data["actions"][0]["target"].lower()


@pytest.mark.asyncio
async def test_redis_streams_events_on_disambiguation_request(
    mock_redis: MockAsyncRedis, sample_board_entities
):
    """Verify IntentDisambiguationRequested and CandidateGhostPreviewEmitted events are emitted."""
    s_id, c_id = str(uuid4()), str(uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test"
    ) as client:
        resp = await _parse(
            client, "I attack the goblin", s_id, c_id, sample_board_entities, from_x=0, from_y=0
        )
        assert resp.status_code == 200
        disambig_id = resp.json()["disambiguation_id"]

    assert STREAM_WATCHER in mock_redis.streams
    d_events = [
        deserialize_event(f)
        for _, f in mock_redis.streams[STREAM_WATCHER]
        if isinstance(deserialize_event(f), IntentDisambiguationRequested)
    ]
    assert len(d_events) == 1 and d_events[0].disambiguation_id == disambig_id
    assert d_events[0].speaker_name == "Marcus" and len(d_events[0].candidates) == 2

    assert STREAM_BOARD in mock_redis.streams
    g_events = [
        deserialize_event(f)
        for _, f in mock_redis.streams[STREAM_BOARD]
        if isinstance(deserialize_event(f), CandidateGhostPreviewEmitted)
    ]
    assert len(g_events) == 2
    g_ids = [g.candidate_id for g in g_events]
    assert "goblin_1" in g_ids and "goblin_2" in g_ids


@pytest.mark.asyncio
async def test_resolve_intent_disambiguation_flow(
    mock_redis: MockAsyncRedis, sample_board_entities
):
    """Verify player disambiguation selection updates action target and emits CompoundActionResolved."""
    s_id, c_id = str(uuid4()), str(uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test"
    ) as client:
        parse_resp = await _parse(client, "I shoot the goblin", s_id, c_id, sample_board_entities)
        d_id = parse_resp.json()["disambiguation_id"]

        resolve_resp = await client.post(
            "/api/v1/watcher/intent/resolve",
            json={
                "session_id": s_id,
                "campaign_id": c_id,
                "disambiguation_id": d_id,
                "selected_candidate_id": "goblin_2",
            },
        )
        assert resolve_resp.status_code == 200
        data = resolve_resp.json()
        assert data["disambiguation_id"] == d_id and data["status"] == "ready"
        assert "shaman on the altar" in data["resolved_target"]
        assert "shaman" in data["actions"][0]["target"]

    r_events = [
        deserialize_event(f)
        for _, f in mock_redis.streams[STREAM_WATCHER]
        if isinstance(deserialize_event(f), CompoundActionResolved)
    ]
    assert len(r_events) == 1 and r_events[0].disambiguation_id == d_id
    assert "shaman on the altar" in r_events[0].resolved_target


@pytest.mark.asyncio
async def test_timing_budget_sub_400ms_compliance(sample_board_entities):
    """Verify disambiguation candidate evaluation executes in < 400ms SLA."""
    s_id = str(uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test"
    ) as client:
        latencies = []
        for _ in range(20):
            t0 = time.perf_counter()
            resp = await _parse(client, "I attack the goblin", s_id, entities=sample_board_entities)
            latencies.append((time.perf_counter() - t0) * 1000)
            assert resp.status_code == 200

        assert max(latencies) < 400.0, f"Max latency exceeded 400ms: {max(latencies):.2f}ms"
        assert sum(latencies) / len(latencies) < 50.0, "Average latency too high"


@pytest.mark.asyncio
async def test_resolve_invalid_disambiguation_id_returns_404():
    """Verify resolving unknown or expired disambiguation ID returns 404."""
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/watcher/intent/resolve",
            json={
                "session_id": str(uuid4()),
                "disambiguation_id": "nonexistent-id",
                "selected_candidate_id": "c-1",
            },
        )
        assert resp.status_code == 404
