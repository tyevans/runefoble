"""Unit and integration tests for Runefoble AI Inference Worker and LangGraph workflows."""

import json
import os

import pytest
from httpx import ASGITransport, AsyncClient
from inference_worker.api import app
from inference_worker.graphs import (
    build_intent_graph,
    build_narration_graph,
    build_stand_in_graph,
)
from inference_worker.llm_factory import build_llm_port
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER
from the_watcher.main import app as watcher_app

from tests.helpers.fake_openai_server import FakeOpenAI
from tests.helpers.inference_worker_port import install_worker_port
from tests.helpers.spicedb_factory import make_table_runner
from tests.helpers.ws_identity import SIGNING_ISSUER

WORKER_AUTH = {SERVICE_CREDENTIAL_HEADER: os.environ["RUNEFOBLE_SERVICE_CREDENTIAL"]}
WATCHER_AUTH = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('user-1')}"}
pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def llm_port(fake_llm: FakeOpenAI):
    """The openai_compatible port, pointed at the loopback fake. The test sets the reply text."""
    return build_llm_port(fake_llm.settings())


@pytest.fixture
def worker_api(monkeypatch: pytest.MonkeyPatch, llm_port):
    """Install the fake-backed port into the worker app. Graphs rebuild for that port."""
    install_worker_port(monkeypatch, llm_port)


def _reply(fake: FakeOpenAI, document: dict) -> None:
    fake.content = json.dumps(document)


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.get("/healthz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "inference_worker"


@pytest.mark.asyncio
async def test_intent_graph_spell_casting(fake_llm, llm_port):
    _reply(
        fake_llm,
        {
            "action_type": "cast_spell",
            "spell_or_ability": "magic missile",
            "target_name": "Goblin Archer",
            "dice_check_required": "1d20+spell",
            "narrative_flavor": "Valeros weaves arcane energy.",
        },
    )
    graph = build_intent_graph(llm_port)
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
    assert "Visible grid tokens" in fake_llm.user_prompts()[0]


@pytest.mark.asyncio
async def test_intent_graph_movement_coordinates(fake_llm, llm_port):
    _reply(fake_llm, {"action_type": "move"})
    graph = build_intent_graph(llm_port)
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
async def test_intent_api_endpoint(fake_llm, worker_api):
    _reply(fake_llm, {"action_type": "attack", "target_name": "Skeleton"})
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
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
        assert data["source"] == "llm"
        assert data["degraded"] is False


@pytest.mark.asyncio
async def test_narration_graph_and_api(fake_llm, llm_port, worker_api):
    narration = {
        "narration": "Dust hangs in the still air of the crypt.",
        "sensory_details": ["Cold stone under the fingers"],
        "suggested_dm_prompts": ["Ask for a Perception check"],
    }
    _reply(fake_llm, narration)
    graph = build_narration_graph(llm_port)
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
    assert final["narration"] == narration["narration"]
    assert final["sensory_details"] == narration["sensory_details"]
    assert final["suggested_dm_prompts"] == narration["suggested_dm_prompts"]
    assert final["source"] == "llm"
    assert "Crypt of the Shadow King" in fake_llm.user_prompts()[0]

    # Also test via API
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
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
        assert data["narration"] == narration["narration"]
        assert data["source"] == "llm"


@pytest.mark.asyncio
async def test_stand_in_graph_with_penalties(fake_llm, llm_port):
    graph = build_stand_in_graph(llm_port)

    # The DM penalty reaches the model prompt. The model's decision reaches the response.
    _reply(
        fake_llm,
        {
            "action_type": "attack",
            "target": "Orc Chieftain",
            "dialogue": "*Hic* 'Stand shtill!'",
            "narrative_flavor": "Seoni sways on one boot.",
            "mechanics": {"penalty": "drunk"},
        },
    )
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
    assert "DM Penalties: drunk" in fake_llm.user_prompts()[-1]
    assert "Slurred speech" in fake_llm.user_prompts()[-1]
    assert drunk_resp["mechanics"]["penalty"] == "drunk"
    assert drunk_resp["source"] == "llm"

    # Test "foolishness" penalty
    _reply(fake_llm, {"action_type": "foolish_act", "target": "Red Dragon"})
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
async def test_watcher_heuristic_engine_is_explicit_and_reported():
    await make_table_runner("user-1", "sess-1", "camp-1")
    # The local rule engine runs only when the setting selects it. The health route reports it.
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test", headers=WATCHER_AUTH
    ) as ac:
        resp = await ac.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["watcher_engine"] == "heuristic"

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
