"""Blackbox TDD tests for leave-activates-stand-in (TASK-0690, ADR-0015 (a) and (b)).

A player who leaves a session with a lobby character hands that character to the AI
stand-in. game_session sends the command to character_sheet. character_sheet owns the flag.
All setup and assertions use public HTTP routes only.
"""

import os
from collections.abc import Iterator

import httpx
import pytest
from character_sheet.main import app as character_app
from game_session.character_client import CHARACTER_SHEET_URL_ENV
from game_session.main import app as session_app
from game_session.main import set_event_bus as session_set_event_bus
from game_session.main import set_spicedb_client as session_set_spicedb
from httpx import ASGITransport, AsyncClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER

from tests.helpers.live_services import serve
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

PLAYER_ID = "sarah-user"
UNREACHABLE_CHARACTER_SHEET_URL = "http://127.0.0.1:9"


def _bearer(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def character_service(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Run character_sheet as a live upstream that game_session calls over HTTP."""
    with serve(character_app) as url:
        monkeypatch.setenv(CHARACTER_SHEET_URL_ENV, url)
        yield url


@pytest.fixture
def session_client(mock_redis: MockAsyncRedis) -> Iterator[None]:
    session_set_event_bus(RedisStreamsEventBus(client=mock_redis))
    session_set_spicedb(MockSpiceDBClient())
    yield


def _create_character(character_url: str) -> str:
    """Create an active character through the character_sheet frontdoor. Stand-in stays off."""
    with httpx.Client(base_url=character_url, headers=_bearer(PLAYER_ID)) as http:
        created = http.post(
            "/api/v1/characters",
            json={"name": "Kyra", "character_class": "Cleric", "max_hp": 20},
        )
        assert created.status_code == 200, created.text
        return created.json()["character_id"]


def _read_stand_in_flag(character_url: str, char_id: str) -> bool:
    """Read the character sheet flag through the service credential (no user needed)."""
    with httpx.Client(base_url=character_url) as http:
        sheet = http.get(
            f"/api/v1/characters/{char_id}",
            headers={SERVICE_CREDENTIAL_HEADER: os.environ["RUNEFOBLE_SERVICE_CREDENTIAL"]},
        )
        assert sheet.status_code == 200, sheet.text
        return sheet.json()["is_stand_in_active"]


async def _lobby_session(client, char_id: str, *, select_character: bool = True) -> str:
    """The DM creates a session. The player redeems an invite, joins, and picks a character."""
    campaign = await client.post("/api/v1/campaigns", json={"title": "Owned Campaign"})
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    invite = await client.post(f"/api/v1/campaigns/{campaign_id}/invites", json={"role": "player"})
    assert invite.status_code == 201, invite.text
    redeemed = await client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=_bearer(PLAYER_ID),
    )
    assert redeemed.status_code == 200, redeemed.text
    create_res = await client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": campaign_id, "title": "Tomb", "dm_id": "the_watcher"},
    )
    assert create_res.status_code == 200, create_res.text
    session_id = create_res.json()["session_id"]
    join = await client.post(
        f"/api/v1/sessions/{session_id}/join",
        json={"character_id": char_id, "character_name": "Kyra", "character_class": "Cleric"},
        headers=_bearer(PLAYER_ID),
    )
    assert join.status_code == 200, join.text
    if select_character:
        pick = await client.post(
            f"/api/v1/sessions/{session_id}/lobby/character",
            json={"character_id": char_id},
            headers=_bearer(PLAYER_ID),
        )
        assert pick.status_code == 200, pick.text
    started = await client.post(f"/api/v1/sessions/{session_id}/start")
    assert started.status_code == 200, started.text
    return session_id


def _client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=session_app),
        base_url="http://test",
        headers=_bearer("test-user"),
    )


@pytest.mark.asyncio
async def test_leave_activates_stand_in_on_character_sheet(session_client, character_service: str):
    """Leaving with a lobby character sets is_stand_in_active on the character sheet."""
    char_id = _create_character(character_service)
    assert _read_stand_in_flag(character_service, char_id) is False

    async with _client() as client:
        session_id = await _lobby_session(client, char_id)
        leave = await client.post(
            f"/api/v1/sessions/{session_id}/leave",
            json={"reason": "Late arrival"},
            headers=_bearer(PLAYER_ID),
        )
        assert leave.status_code == 200, leave.text
        body = leave.json()
        assert body["stand_in_character_id"] == char_id
        assert body["participants"][PLAYER_ID]["is_stand_in_active"] is True

    assert _read_stand_in_flag(character_service, char_id) is True


@pytest.mark.asyncio
async def test_leave_without_lobby_character_records_absence_only(
    session_client, monkeypatch: pytest.MonkeyPatch, character_service: str
):
    """With no lobby character, leave records the absence and calls no character sheet."""
    char_id = _create_character(character_service)
    monkeypatch.delenv(CHARACTER_SHEET_URL_ENV, raising=False)

    async with _client() as client:
        session_id = await _lobby_session(client, char_id, select_character=False)
        leave = await client.post(
            f"/api/v1/sessions/{session_id}/leave",
            json={"reason": "Late arrival"},
            headers=_bearer(PLAYER_ID),
        )
        assert leave.status_code == 200, leave.text
        body = leave.json()
        assert body["stand_in_character_id"] is None
        assert body["participants"][PLAYER_ID]["is_present"] is False


@pytest.mark.asyncio
async def test_leave_returns_503_and_keeps_presence_when_character_sheet_unreachable(
    session_client, monkeypatch: pytest.MonkeyPatch, character_service: str
):
    """A failed stand-in activation returns 503 and does not record the leave."""
    char_id = _create_character(character_service)

    async with _client() as client:
        session_id = await _lobby_session(client, char_id)
        monkeypatch.setenv(CHARACTER_SHEET_URL_ENV, UNREACHABLE_CHARACTER_SHEET_URL)

        leave = await client.post(
            f"/api/v1/sessions/{session_id}/leave",
            json={"reason": "Late arrival"},
            headers=_bearer(PLAYER_ID),
        )
        assert leave.status_code == 503, leave.text

        state = await client.get(f"/api/v1/sessions/{session_id}")
        participant = state.json()["participants"][PLAYER_ID]
        assert participant["is_present"] is True
        assert participant["is_stand_in_active"] is False

    assert _read_stand_in_flag(character_service, char_id) is False


@pytest.mark.asyncio
async def test_rejoin_releases_stand_in_on_character_sheet(session_client, character_service: str):
    """A returning player who rejoins clears the character sheet stand-in flag."""
    char_id = _create_character(character_service)

    async with _client() as client:
        session_id = await _lobby_session(client, char_id)
        leave = await client.post(
            f"/api/v1/sessions/{session_id}/leave",
            json={"reason": "Late arrival"},
            headers=_bearer(PLAYER_ID),
        )
        assert leave.status_code == 200, leave.text
        assert _read_stand_in_flag(character_service, char_id) is True

        rejoin = await client.post(
            f"/api/v1/sessions/{session_id}/join",
            json={"character_id": char_id, "character_name": "Kyra", "character_class": "Cleric"},
            headers=_bearer(PLAYER_ID),
        )
        assert rejoin.status_code == 200, rejoin.text
        assert rejoin.json()["participants"][PLAYER_ID]["is_stand_in_active"] is False

    assert _read_stand_in_flag(character_service, char_id) is False
