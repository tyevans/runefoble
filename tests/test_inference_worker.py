"""Unit and integration tests for Runefoble AI Inference Worker and LangGraph workflows."""

import pytest
from httpx import ASGITransport, AsyncClient
from inference_worker.api import app
from inference_worker.config import WorkerSettings
from inference_worker.graphs import (
    build_intent_graph,
    build_narration_graph,
    build_stand_in_graph,
)
from inference_worker.llm_client import MultiBackendLLMClient
from the_watcher.main import app as watcher_app


@pytest.fixture
def mock_client():
    settings = WorkerSettings(backend="mock")
    return MultiBackendLLMClient(settings)


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "inference_worker"


@pytest.mark.asyncio
async def test_intent_graph_spell_casting(mock_client):
    graph = build_intent_graph(mock_client)
    state = await graph.ainvoke(
        {
            "request": {
                "campaign_id": "camp-123",
                "session_id": "sess-456",
                "speaker_id": "spk-1",
                "speaker_name": "Valeros",
                "transcript": "I cast magic missile at the goblin archer behind the column",
                "visible_tokens": [
                    {
                        "token_id": "tok-gob-1",
                        "name": "Goblin Archer",
                        "token_type": "monster",
                        "x": 8,
                        "y": 12,
                    }
                ],
            }
        }
    )
    action = state.get("parsed_action", {})
    assert action["action_type"] == "cast_spell"
    assert "magic missile" in action["spell_or_ability"].lower()
    assert action["target_token_id"] == "tok-gob-1"
    assert action["target_token_name"] == "Goblin Archer"
    assert action["target_x"] == 8
    assert action["target_y"] == 12


@pytest.mark.asyncio
async def test_intent_graph_movement_coordinates(mock_client):
    graph = build_intent_graph(mock_client)
    state = await graph.ainvoke(
        {
            "request": {
                "campaign_id": "camp-123",
                "session_id": "sess-456",
                "speaker_id": "spk-1",
                "speaker_name": "Kyra",
                "transcript": "I move to 5, 9 and take cover",
                "visible_tokens": [],
            }
        }
    )
    action = state.get("parsed_action", {})
    assert action["action_type"] == "move"
    assert action["target_x"] == 5
    assert action["target_y"] == 9


@pytest.mark.asyncio
async def test_intent_api_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "campaign_id": "camp-test",
            "session_id": "sess-test",
            "speaker_id": "usr-test",
            "speaker_name": "Merisiel",
            "transcript": "I attack the skeleton with my rapier",
            "visible_tokens": [
                {
                    "token_id": "tok-skel-1",
                    "name": "Skeleton",
                    "token_type": "monster",
                    "x": 3,
                    "y": 4,
                }
            ],
        }
        resp = await ac.post("/inference/v1/intent", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess-test"
        assert data["action"]["action_type"] == "attack"
        assert data["action"]["target_token_id"] == "tok-skel-1"
        assert data["execution_time_ms"] >= 0


@pytest.mark.asyncio
async def test_narration_graph_and_api(mock_client):
    graph = build_narration_graph(mock_client)
    state = await graph.ainvoke(
        {
            "request": {
                "campaign_id": "camp-1",
                "session_id": "sess-1",
                "recent_events": ["Merisiel picked the lock", "A poisoned dart flew past"],
                "scene_environment": "Crypt of the Shadow King",
                "tone": "dark_fantasy",
                "guidance_prompt": "Describe the chamber beyond the heavy stone door.",
            }
        }
    )
    final = state.get("final_response", {})
    assert (
        "Crypt of the Shadow King" in final["narration"] or "silence" in final["narration"].lower()
    )
    assert len(final["sensory_details"]) >= 1
    assert len(final["suggested_dm_prompts"]) >= 1

    # Also test via API
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/inference/v1/dm-narration",
            json={
                "campaign_id": "camp-1",
                "session_id": "sess-1",
                "recent_events": ["Door creaks open"],
                "scene_environment": "Forgotten Library",
                "guidance_prompt": "What do the adventurers see?",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "narration" in data
        assert len(data["sensory_details"]) > 0


@pytest.mark.asyncio
async def test_stand_in_graph_with_penalties(mock_client):
    graph = build_stand_in_graph(mock_client)

    # Test "drunk" penalty
    state_drunk = await graph.ainvoke(
        {
            "request": {
                "campaign_id": "camp-1",
                "session_id": "sess-1",
                "character_name": "Seoni",
                "character_class": "Sorcerer",
                "personality_traits": ["proud", "fiery"],
                "penalties": ["drunk"],
                "scene_context": "Orc warband charging",
                "visible_enemies": ["Orc Chieftain"],
            }
        }
    )
    drunk_resp = state_drunk.get("final_response", {})
    assert "drunk" in [p.lower() for p in drunk_resp["penalties_applied"]]
    assert (
        "*hic*" in drunk_resp["dialogue"].lower()
        or "sways" in drunk_resp["narrative_flavor"].lower()
    )
    assert drunk_resp["mechanics"]["penalty"] == "drunk"

    # Test "foolishness" penalty
    state_fool = await graph.ainvoke(
        {
            "request": {
                "campaign_id": "camp-1",
                "session_id": "sess-1",
                "character_name": "Valeros",
                "character_class": "Fighter",
                "penalties": ["foolishness"],
                "visible_enemies": ["Red Dragon"],
            }
        }
    )
    fool_resp = state_fool.get("final_response", {})
    assert fool_resp["action_type"] == "foolish_act"
    assert "foolishness" in [p.lower() for p in fool_resp["penalties_applied"]]


@pytest.mark.asyncio
async def test_watcher_service_fallback():
    # Test that the_watcher still functions cleanly when no inference worker url is set
    async with AsyncClient(transport=ASGITransport(app=watcher_app), base_url="http://test") as ac:
        resp = await ac.get("/healthz")
        assert resp.status_code == 200
        assert "inference_worker_url" in resp.json()

        act_resp = await ac.post(
            "/api/v1/watcher/transcribe-and-act",
            json={
                "speaker_id": "user-1",
                "speaker_name": "Valeros",
                "transcript": "I strike the goblin with my sword",
                "session_id": "sess-1",
                "campaign_id": "camp-1",
            },
        )
        assert act_resp.status_code == 200
        assert act_resp.json()["action_type"] == "attack"
