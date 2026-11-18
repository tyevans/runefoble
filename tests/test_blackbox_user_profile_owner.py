"""Blackbox frontdoor tests: user profile attributes have a durable owner (TASK-0742).

Governing ADRs: ADR-0011 (eventsource-py), ADR-0015 (decisions a, b, c, f), Hard Invariant 7.

The gateway serves `GET` and `PATCH /api/v1/profile` only by forwarding to game_session.
game_session holds the profile as event-sourced state keyed by the Zitadel subject. A
restart of game_session is a fresh process: the test removes every `game_session` module
from `sys.modules` and imports the app again. The event store is shared, as a durable
store would be. Setup and assertions use only public HTTP routes.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import closed_port_url, serve


def _bearer(issuer, sub: str, username: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub, username=username)}"}


def _is_game_session(name: str) -> bool:
    return name == "game_session" or name.startswith("game_session.")


PATCH_PAYLOAD = {
    "displayName": "Valeros the Undaunted",
    "avatarUrl": "/assets/portraits/valeros-veteran.svg",
    "bio": "Veteran champion of Korvosa.",
}


@pytest.fixture
def isolated_game_session_modules() -> Iterator[None]:
    """Restore the original game_session modules after each test."""
    saved = {name: mod for name, mod in sys.modules.items() if _is_game_session(name)}
    yield
    for name in [n for n in sys.modules if _is_game_session(n)]:
        del sys.modules[name]
    sys.modules.update(saved)


def test_patch_then_get_returns_updated_profile(trusted_ws_issuer, game_session_upstream):
    """PATCH through the gateway, then GET through the gateway, returns the updated fields."""
    headers = _bearer(trusted_ws_issuer, "user-valeros", username="Valeros")
    with TestClient(gateway_app) as client:
        patched = client.patch("/api/v1/profile", json=PATCH_PAYLOAD, headers=headers)
        assert patched.status_code == 200, patched.text
        fetched = client.get("/api/v1/profile", headers=headers)

    assert fetched.status_code == 200, fetched.text
    body = fetched.json()
    assert body["user_id"] == "user-valeros"
    assert body["username"] == "Valeros"
    assert body["display_name"] == "Valeros the Undaunted"
    assert body["avatar_url"] == "/assets/portraits/valeros-veteran.svg"
    assert body["bio"] == "Veteran champion of Korvosa."
    assert body["email"] == "user-valeros@runefoble.local"


def test_default_profile_comes_from_verified_token(trusted_ws_issuer, game_session_upstream):
    """A user who never patched sees the token's username and email as defaults."""
    headers = _bearer(trusted_ws_issuer, "user-fresh", username="Fresh Recruit")
    with TestClient(gateway_app) as client:
        fetched = client.get("/api/v1/profile", headers=headers)

    assert fetched.status_code == 200, fetched.text
    assert fetched.json() == {
        "user_id": "user-fresh",
        "username": "Fresh Recruit",
        "email": "user-fresh@runefoble.local",
        "display_name": "Fresh Recruit",
        "avatar_url": None,
        "bio": "",
    }


def test_profile_edits_are_isolated_per_subject(trusted_ws_issuer, game_session_upstream):
    """An edit to one subject's profile does not change another subject's profile."""
    editor = _bearer(trusted_ws_issuer, "user-editor")
    other = _bearer(trusted_ws_issuer, "user-other", username="Other")
    with TestClient(gateway_app) as client:
        assert (
            client.patch("/api/v1/profile", json={"bio": "Edited"}, headers=editor).status_code
            == 200
        )
        others = client.get("/api/v1/profile", headers=other).json()

    assert others["user_id"] == "user-other"
    assert others["bio"] == ""


def test_profile_is_held_by_game_session(trusted_ws_issuer, game_session_upstream):
    """The owning service returns the edit when called directly, with the same token."""
    headers = _bearer(trusted_ws_issuer, "user-owner-check")
    with TestClient(gateway_app) as client:
        assert (
            client.patch("/api/v1/profile", json={"bio": "Owned here"}, headers=headers).status_code
            == 200
        )

    direct = httpx.get(f"{game_session_upstream}/api/v1/profile", headers=headers)
    assert direct.status_code == 200, direct.text
    assert direct.json()["bio"] == "Owned here"


def test_profile_persists_across_game_session_restart(
    isolated_game_session_modules: None,
    trusted_ws_issuer,
    game_session_upstream,
    monkeypatch,
):
    """An edit made before a game_session restart is still returned after it."""
    headers = _bearer(trusted_ws_issuer, "user-restart", username="Restarted")
    with TestClient(gateway_app) as client:
        patched = client.patch("/api/v1/profile", json=PATCH_PAYLOAD, headers=headers)
    assert patched.status_code == 200, patched.text

    for name in [n for n in sys.modules if _is_game_session(n)]:
        del sys.modules[name]
    main = importlib.import_module("game_session.main")
    tokens = importlib.import_module("game_session.settlement.auth.tokens")
    tokens.set_zitadel_auth_service(trusted_ws_issuer.verifier())

    with serve(main.app) as restarted_url:
        monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", restarted_url)
        with TestClient(gateway_app) as client:
            fetched = client.get("/api/v1/profile", headers=headers)

    assert fetched.status_code == 200, fetched.text
    body = fetched.json()
    assert body["display_name"] == "Valeros the Undaunted"
    assert body["avatar_url"] == "/assets/portraits/valeros-veteran.svg"
    assert body["bio"] == "Veteran champion of Korvosa."


def test_profile_without_token_is_refused(trusted_ws_issuer, game_session_upstream):
    """The gateway refuses a profile request with no bearer token, before any forwarding."""
    with TestClient(gateway_app) as client:
        assert client.get("/api/v1/profile").status_code == 401
        assert client.patch("/api/v1/profile", json={"bio": "x"}).status_code == 401


def test_profile_fails_loud_when_game_session_is_down(trusted_ws_issuer, monkeypatch):
    """With game_session unreachable, the gateway returns 503 and no substitute profile."""
    monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", closed_port_url())
    headers = _bearer(trusted_ws_issuer, "user-offline")
    with TestClient(gateway_app) as client:
        res = client.get("/api/v1/profile", headers=headers)

    assert res.status_code == 503, res.text
    assert res.json()["upstream"] == "game_session"
