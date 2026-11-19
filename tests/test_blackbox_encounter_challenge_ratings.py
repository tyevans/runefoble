"""Blackbox tests: game_session resolves enemy challenge ratings at encounter start (TASK-0918).

POST /api/v1/sessions/{id}/encounters/start accepts enemies without `cr`. game_session reads
each missing rating from the rules_compendium stat block. rules_compendium runs as a live
loopback service. Setup and assertions use public HTTP routes only.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from tests.helpers.game_session_setup import start_session_with_player
from tests.helpers.live_services import closed_port_url, serve, unavailable_app
from tests.helpers.ws_identity import SIGNING_ISSUER, bearer

COMPENDIUM_URL_ENV = "RUNEFOBLE_RULES_COMPENDIUM_URL"


@pytest.fixture(scope="module")
def compendium_url() -> Iterator[str]:
    """Run rules_compendium as a real HTTP service."""
    from rules_compendium.main import app as compendium_app

    with serve(compendium_app, lifespan="on") as url:
        yield url


@pytest.fixture
def session_url() -> Iterator[str]:
    """Run game_session as an HTTP service that verifies the shared test issuer."""
    from game_session.shared.identity import get_zitadel_auth_service, set_zitadel_auth_service

    from tests.helpers.game_session_app import session_app

    previous = get_zitadel_auth_service()
    set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    try:
        with serve(session_app) as url:
            yield url
    finally:
        set_zitadel_auth_service(previous)


def _start(session_url: str, session_id: str, body: dict[str, Any]) -> httpx.Response:
    with httpx.Client(base_url=session_url, headers=bearer("user-test")) as http:
        return http.post(f"/api/v1/sessions/{session_id}/encounters/start", json=body)


def _combat(session_url: str, session_id: str) -> dict[str, Any]:
    with httpx.Client(base_url=session_url, headers=bearer("user-test")) as http:
        response = http.get(f"/api/v1/sessions/{session_id}/combat")
    assert response.status_code == 200, response.text
    return response.json()


def _ratings(combat: dict[str, Any]) -> dict[str, Any]:
    return {c["name"]: c.get("cr") for c in combat["initiative_order"]}


def test_enemy_without_cr_gets_the_compendium_rating(
    session_url: str, compendium_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Enemies without `cr` get the stat block rating. A given `cr` is kept as sent."""
    monkeypatch.setenv(COMPENDIUM_URL_ENV, compendium_url)
    session_id = start_session_with_player(session_url)

    response = _start(
        session_url,
        session_id,
        {
            "enemies": [
                {"name": "Ogre", "x": 1, "y": 1},
                {"name": " goblin ", "x": 2, "y": 1},
                {"name": "Orc", "x": 3, "y": 1, "cr": 4.0},
            ]
        },
    )

    assert response.status_code == 200, response.text
    assert _ratings(_combat(session_url, session_id)) == {
        "Ogre": 2.0,
        " goblin ": 0.25,
        "Orc": 4.0,
    }


def test_unknown_monster_without_cr_is_400_and_starts_no_combat(
    session_url: str, compendium_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An enemy with no rating in the request or the compendium is refused with 400."""
    monkeypatch.setenv(COMPENDIUM_URL_ENV, compendium_url)
    session_id = start_session_with_player(session_url)

    response = _start(
        session_url,
        session_id,
        {
            "enemies": [
                {"name": "Goblin", "x": 1, "y": 1},
                {"name": "Nonexistent Beast Of Nowhere", "x": 2, "y": 2},
            ]
        },
    )

    assert response.status_code == 400, response.text
    detail = response.json()["detail"]
    assert "challenge rating" in detail.lower()
    assert "Nonexistent Beast Of Nowhere" in detail
    assert _combat(session_url, session_id)["in_combat"] is False


def test_unreachable_compendium_is_503_and_starts_no_combat(
    session_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A closed compendium port gives 503. No rating is guessed and no combat starts."""
    monkeypatch.setenv(COMPENDIUM_URL_ENV, closed_port_url())
    session_id = start_session_with_player(session_url)

    response = _start(session_url, session_id, {"enemies": [{"name": "Goblin", "x": 1, "y": 1}]})

    assert response.status_code == 503, response.text
    assert "rules_compendium" in response.json()["detail"]
    assert _combat(session_url, session_id)["in_combat"] is False


def test_failing_compendium_is_503_and_starts_no_combat(
    session_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A compendium that answers 503 gives 503. No combat starts."""
    session_id = start_session_with_player(session_url)
    with serve(unavailable_app(503)) as down_url:
        monkeypatch.setenv(COMPENDIUM_URL_ENV, down_url)
        response = _start(
            session_url, session_id, {"enemies": [{"name": "Goblin", "x": 1, "y": 1}]}
        )

    assert response.status_code == 503, response.text
    assert _combat(session_url, session_id)["in_combat"] is False


def test_unconfigured_compendium_is_503_only_when_a_rating_is_missing(
    session_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no compendium URL, a start with every `cr` given works. One without `cr` gives 503."""
    monkeypatch.delenv(COMPENDIUM_URL_ENV, raising=False)
    rated = start_session_with_player(session_url)
    unrated = start_session_with_player(session_url)

    ok = _start(session_url, rated, {"enemies": [{"name": "Imp", "x": 1, "y": 1, "cr": 1.0}]})
    refused = _start(session_url, unrated, {"enemies": [{"name": "Imp", "x": 1, "y": 1}]})

    assert ok.status_code == 200, ok.text
    assert refused.status_code == 503, refused.text
    assert COMPENDIUM_URL_ENV in refused.json()["detail"]
    assert _combat(session_url, unrated)["in_combat"] is False
