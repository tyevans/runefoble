"""Frontdoor blackbox tests: tavern drink DSP conditioning calls voice_agent over HTTP.

TASK-0675 / PRD-0024 / US-0047 / ADR-0007 / ADR-0014 / ADR-0015.

The voice_agent service runs as a real HTTP upstream on a loopback port. The drink
route under test sends real requests to it. Nothing patches the HTTP client.
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_spicedb_client as set_session_spicedb
from game_session.main import app as session_app
from runefoble_auth.spicedb import MockSpiceDBClient
from voice_agent.main import app as voice_app

from tests.helpers.live_services import closed_port_url, serve, unavailable_app

SPEECH = "I can drink the whole tavern under the table!"
CHARACTER = "char_bram"
CONDITION_PATH = "/api/v1/voice/dsp/condition"
VOICE_URL_ENV = "RUNEFOBLE_VOICE_AGENT_URL"


@pytest.fixture
def session_client() -> Iterator[TestClient]:
    set_session_spicedb(MockSpiceDBClient())
    with TestClient(session_app) as client:
        yield client


def _start_contest(client: TestClient) -> tuple[str, str]:
    session_id = "sess-tavern-dsp-upstream"
    res = client.post(
        f"/api/v1/sessions/{session_id}/tavern/games",
        json={
            "game_type": "drinking_contest",
            "wager_gold": 15,
            "initiator_id": CHARACTER,
            "challenger_id": "npc_dwarf",
        },
    )
    assert res.status_code == 200, res.text
    return session_id, res.json()["game_id"]


def _drink(
    client: TestClient,
    session_id: str,
    game_id: str,
    con_roll: int,
    speech_text: str | None = None,
) -> httpx.Response:
    body: dict[str, object] = {
        "actor_id": CHARACTER,
        "action_type": "drink",
        "con_roll": con_roll,
    }
    if speech_text is not None:
        body["speech_text"] = speech_text
    return client.post(f"/api/v1/sessions/{session_id}/tavern/games/{game_id}/turn", json=body)


def _drink_two_rounds(client: TestClient, session_id: str, game_id: str) -> None:
    """Round 1 (roll 18 vs DC 10) stays sober. Round 2 (roll 5 vs DC 12) becomes tipsy."""
    assert _drink(client, session_id, game_id, 18).status_code == 200
    assert _drink(client, session_id, game_id, 5).status_code == 200


def _character_state(client: TestClient, session_id: str, game_id: str) -> dict:
    res = client.get(f"/api/v1/sessions/{session_id}/tavern/games/{game_id}")
    assert res.status_code == 200, res.text
    return res.json()


def test_drink_roll_returns_voice_dsp_from_live_voice_agent(
    session_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The drink roll returns the voice_agent response for the same text and filters."""
    with serve(voice_app) as voice_url:
        monkeypatch.setenv(VOICE_URL_ENV, voice_url)
        session_id, game_id = _start_contest(session_client)
        _drink_two_rounds(session_client, session_id, game_id)

        res = _drink(session_client, session_id, game_id, 6, speech_text=SPEECH)

        assert res.status_code == 200, res.text
        result = res.json()["result"]
        assert result["intoxication_level"] == "drunk"
        assert result["voice_dsp"] is not None

        with httpx.Client(base_url=voice_url) as direct:
            upstream = direct.post(CONDITION_PATH, json={"text": SPEECH, "filters": ["drunk"]})
        assert upstream.status_code == 200, upstream.text
        assert result["voice_dsp"] == upstream.json()
        assert result["voice_dsp"]["original_text"] == SPEECH
        assert result["voice_dsp"]["active_filters"] == ["drunk"]
        assert result["voice_dsp"]["conditioned_text"] != SPEECH


def test_drink_roll_without_speech_does_not_call_voice_agent(
    session_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A drink with no speech text returns no voice_dsp and needs no upstream."""
    monkeypatch.setenv(VOICE_URL_ENV, closed_port_url())
    session_id, game_id = _start_contest(session_client)
    _drink_two_rounds(session_client, session_id, game_id)

    res = _drink(session_client, session_id, game_id, 6)

    assert res.status_code == 200, res.text
    assert res.json()["result"]["voice_dsp"] is None


def test_drink_roll_returns_503_when_voice_agent_returns_503(
    session_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An upstream 503 becomes a 503 for the roll. No substitute voice_dsp value is returned."""
    session_id, game_id = _start_contest(session_client)
    _drink_two_rounds(session_client, session_id, game_id)

    with serve(unavailable_app(503)) as down_url:
        monkeypatch.setenv(VOICE_URL_ENV, down_url)
        res = _drink(session_client, session_id, game_id, 6, speech_text=SPEECH)

    assert res.status_code == 503, res.text
    assert "voice_dsp" not in res.text
    assert "conditioned_text" not in res.text


def test_drink_roll_returns_503_when_voice_agent_is_unreachable(
    session_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stopped voice_agent becomes a 503 for the roll. No substitute voice_dsp value is returned."""
    session_id, game_id = _start_contest(session_client)
    _drink_two_rounds(session_client, session_id, game_id)

    monkeypatch.setenv(VOICE_URL_ENV, closed_port_url())
    res = _drink(session_client, session_id, game_id, 6, speech_text=SPEECH)

    assert res.status_code == 503, res.text
    assert "voice_dsp" not in res.text
    assert "conditioned_text" not in res.text


def test_failed_drink_roll_records_no_intoxication_change(
    session_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A roll that fails at the upstream leaves the public game state unchanged."""
    session_id, game_id = _start_contest(session_client)
    _drink_two_rounds(session_client, session_id, game_id)
    before = _character_state(session_client, session_id, game_id)

    monkeypatch.setenv(VOICE_URL_ENV, closed_port_url())
    res = _drink(session_client, session_id, game_id, 6, speech_text=SPEECH)
    after = _character_state(session_client, session_id, game_id)

    assert res.status_code == 503, res.text
    assert after["intoxication_levels"][CHARACTER] == before["intoxication_levels"][CHARACTER]
    assert after["intoxication_levels"][CHARACTER] == "tipsy"
    assert after["consecutive_drinks"][CHARACTER] == before["consecutive_drinks"][CHARACTER] == 2


def test_drink_roll_returns_503_when_voice_agent_url_is_not_configured(
    session_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no RUNEFOBLE_VOICE_AGENT_URL, a roll with speech fails loudly with 503."""
    monkeypatch.delenv(VOICE_URL_ENV, raising=False)
    session_id, game_id = _start_contest(session_client)
    _drink_two_rounds(session_client, session_id, game_id)

    res = _drink(session_client, session_id, game_id, 6, speech_text=SPEECH)

    assert res.status_code == 503, res.text
    assert "voice_dsp" not in res.text
