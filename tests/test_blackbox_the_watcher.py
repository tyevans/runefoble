"""Blackbox frontdoor tests for The Watcher speech-to-intent and board actions."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from runefoble_events.events import SpeechIntentParsed
from runefoble_platform.event_deserializer import deserialize_event

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spicedb_factory import bind_character_owner, make_table_runner
from tests.helpers.the_watcher_app import watcher_app
from tests.helpers.watcher_board import open_board_with_tokens, token_position
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

VALEROS_TOKEN = {
    "token_id": "tok-valeros",
    "name": "Valeros",
    "token_type": "pc",
    "x": 2,
    "y": 2,
    "hp": 40,
}


async def _bound_session() -> tuple[str, str]:
    """Bind a fresh session to a fresh campaign whose DM is the test user."""
    session_id, campaign_id = str(uuid.uuid4()), str(uuid.uuid4())
    await make_table_runner("test-user", session_id, campaign_id)
    for speaker in ("spk-1", "spk-2", "spk-3", "spk-4", "spk-5", "spk-6"):
        await bind_character_owner("test-user", speaker)
    return session_id, campaign_id


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.mark.asyncio
async def test_blackbox_coordinate_movement_frontdoor(
    mock_redis: MockAsyncRedis, use_redis_client, board_state_upstream: str
):
    sid, cid = await _bound_session()
    use_redis_client(mock_redis)
    open_board_with_tokens(
        board_state_upstream,
        sid,
        cid,
        owner="test-user",
        cols=12,
        rows=12,
        tokens=[VALEROS_TOKEN],
    )

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
    ) as client:
        resp = await client.post(
            "/api/v1/watcher/transcribe-and-act",
            json={
                "speaker_id": "spk-1",
                "speaker_name": "Valeros",
                "transcript": "move to 6, 8",
                "session_id": sid,
                "campaign_id": cid,
                "token_id": "tok-valeros",
                "from_x": 2,
                "from_y": 2,
                "grid_cols": 12,
                "grid_rows": 12,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_type"] == "move"
        assert data["parameters"]["to_x"] == 6
        assert data["parameters"]["to_y"] == 8

    # Verify observable domain events on Redis Streams frontdoor
    watcher_entries = mock_redis.streams.get("runefoble.events.watcher", [])
    assert len(watcher_entries) == 1
    evt1 = deserialize_event(watcher_entries[0][1])
    assert isinstance(evt1, SpeechIntentParsed)
    assert evt1.action_type == "move"

    # The proposal to (6, 8) stages a preview. The token stays at (2, 2) until confirm.
    assert token_position(board_state_upstream, sid, "tok-valeros", "test-user") == (2, 2)


@pytest.mark.asyncio
async def test_blackbox_cardinal_movement_with_boundary_clamping(
    mock_redis: MockAsyncRedis, use_redis_client, board_state_upstream: str
):
    sid, cid = await _bound_session()
    use_redis_client(mock_redis)
    open_board_with_tokens(
        board_state_upstream,
        sid,
        cid,
        owner="test-user",
        cols=10,
        rows=10,
        tokens=[
            {
                "token_id": "tok-meri",
                "name": "Merisiel",
                "token_type": "pc",
                "x": 5,
                "y": 5,
                "hp": 30,
            }
        ],
    )

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
    ) as client:
        resp = await client.post(
            "/api/v1/watcher/transcribe-and-act",
            json={
                "speaker_id": "spk-2",
                "speaker_name": "Merisiel",
                "transcript": "advance 20 squares east",
                "session_id": sid,
                "campaign_id": cid,
                "token_id": "tok-meri",
                "from_x": 5,
                "from_y": 5,
                "grid_cols": 10,
                "grid_rows": 10,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_type"] == "move"
        assert data["parameters"]["direction"] == "east"

    # The proposal clamps to grid_cols - 1 = 9 and stages there. The token does not move.
    assert token_position(board_state_upstream, sid, "tok-meri", "test-user") == (5, 5)


@pytest.mark.asyncio
async def test_blackbox_intent_endpoint_attack_and_spell(
    mock_redis: MockAsyncRedis, use_redis_client
):
    sid, cid = await _bound_session()
    use_redis_client(mock_redis)

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
    ) as client:
        # Attack
        resp_attack = await client.post(
            "/api/v1/watcher/transcribe-and-act",
            json={
                "speaker_id": "spk-3",
                "speaker_name": "Valeros",
                "transcript": "attack skeleton with mace",
                "session_id": sid,
                "campaign_id": cid,
            },
        )
        assert resp_attack.status_code == 200
        att_data = resp_attack.json()
        assert att_data["action_type"] == "attack"
        assert att_data["parameters"]["target"] == "skeleton"
        assert att_data["parameters"]["weapon"] == "mace"

        # Spell
        resp_spell = await client.post(
            "/api/v1/watcher/transcribe-and-act",
            json={
                "speaker_id": "spk-4",
                "speaker_name": "Ezren",
                "transcript": "cast magic missile at goblin archer",
                "session_id": sid,
                "campaign_id": cid,
            },
        )
        assert resp_spell.status_code == 200
        spell_data = resp_spell.json()
        assert spell_data["action_type"] == "cast_spell"
        assert spell_data["parameters"]["spell"] == "magic missile"


@pytest.mark.asyncio
async def test_blackbox_skill_check_and_dice_roll_frontdoors(
    mock_redis: MockAsyncRedis, use_redis_client
):
    sid, cid = await _bound_session()
    use_redis_client(mock_redis)

    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
    ) as client:
        # Skill check
        resp_skill = await client.post(
            "/api/v1/watcher/transcribe-and-act",
            json={
                "speaker_id": "spk-5",
                "speaker_name": "Kyra",
                "transcript": "make a religion check",
                "session_id": sid,
                "campaign_id": cid,
            },
        )
        assert resp_skill.status_code == 200
        assert resp_skill.json()["action_type"] == "skill_check"
        assert resp_skill.json()["parameters"]["skill"] == "religion"

        # Dice roll
        resp_roll = await client.post(
            "/api/v1/watcher/transcribe-and-act",
            json={
                "speaker_id": "spk-6",
                "speaker_name": "Ezren",
                "transcript": "roll 2d6+3",
                "session_id": sid,
                "campaign_id": cid,
            },
        )
        assert resp_roll.status_code == 200
        assert resp_roll.json()["action_type"] == "roll_dice"
        assert resp_roll.json()["parameters"]["notation"] == "2d6+3"
