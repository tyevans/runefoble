"""Blackbox tests: character_sheet stores level and portrait at creation (TASK-0905).

Setup and assertions go through the public character_sheet routes only
(POST /api/v1/characters, GET /api/v1/characters/{id}).
"""

import httpx
import pytest
from character_sheet.main import app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import bearer

client = TestClient(app, headers=bearer("level-portrait-owner"))

SVG_PORTRAIT = (
    "data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3C%2Fsvg%3E"
)
ASSET_PORTRAIT = "/api/v1/assets/9b2f4a8e-3c1d-4e5f-8a7b-6c5d4e3f2a1b?stream=true"


def _create(**fields) -> httpx.Response:
    body = {"name": "Kyra", "character_class": "Cleric", "max_hp": 32, **fields}
    return client.post("/api/v1/characters", json=body)


@pytest.mark.parametrize(
    "portrait", [SVG_PORTRAIT, ASSET_PORTRAIT, "https://cdn.example.org/k.png"]
)
def test_create_stores_level_and_portrait_and_read_returns_them(portrait):
    res = _create(level=4, portrait_url=portrait)
    assert res.status_code == 200, res.text
    created = res.json()
    assert created["level"] == 4
    assert created["active_portrait_url"] == portrait

    read = client.get(f"/api/v1/characters/{created['character_id']}")
    assert read.status_code == 200, read.text
    assert read.json()["level"] == 4
    assert read.json()["active_portrait_url"] == portrait


def test_create_at_level_four_starts_with_level_four_spell_slots():
    res = _create(level=4)
    assert res.status_code == 200, res.text
    slots = {int(k): v for k, v in res.json()["spell_slots"].items()}
    assert slots == {1: 4, 2: 3}


def test_create_without_level_or_portrait_starts_at_level_one_with_no_portrait():
    res = _create()
    assert res.status_code == 200, res.text
    assert res.json()["level"] == 1
    assert res.json()["active_portrait_url"] is None


@pytest.mark.parametrize("level", [0, 21])
def test_create_refuses_a_level_outside_one_to_twenty(level):
    assert _create(level=level).status_code == 422


@pytest.mark.parametrize(
    "portrait",
    [
        "javascript:alert(1)",
        "blob:https://app.example.org/1234",
        "data:text/html,<p>x</p>",
        "/assets/portraits/fighter.svg",
        'https://cdn.example.org/a.png" onload="x',
        "",
    ],
)
def test_create_refuses_a_portrait_that_is_not_a_url_or_asset_reference(portrait):
    assert _create(portrait_url=portrait).status_code == 422
