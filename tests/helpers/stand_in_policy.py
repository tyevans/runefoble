"""Live character_sheet upstream for auto-pilot tests that need a stored stand-in policy (TASK-0779).

Auto-pilot reads the policy stored on the absent character through character_sheet. These helpers
create that character and store its policy through public character_sheet routes only. The owner
of the character is the same user who joins the session, so the leave-time stand-in hand-off
passes its permission check.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from character_sheet.main import app as character_app
from game_session.character_client import CHARACTER_SHEET_URL_ENV

from tests.helpers.live_services import serve
from tests.helpers.ws_identity import SIGNING_ISSUER


def _bearer(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def live_character_sheet(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Run character_sheet on a loopback port and point game_session at it."""
    with serve(character_app) as url:
        monkeypatch.setenv(CHARACTER_SHEET_URL_ENV, url)
        yield url


def create_character(character_url: str, owner: str, name: str = "Kyra") -> str:
    """Create a character as its owner. Return the new character id."""
    with httpx.Client(base_url=character_url, headers=_bearer(owner)) as http:
        created = http.post(
            "/api/v1/characters",
            json={"name": name, "character_class": "Cleric", "max_hp": 20},
        )
        assert created.status_code == 200, created.text
        return str(created.json()["character_id"])


def store_policy(character_url: str, owner: str, character_id: str, policy: dict[str, Any]) -> None:
    """Store a stand-in policy on the character through the public PUT route."""
    with httpx.Client(base_url=character_url, headers=_bearer(owner)) as http:
        put = http.put(f"/api/v1/characters/{character_id}/guardrails", json=policy)
        assert put.status_code == 200, put.text
