"""Blackbox TDD suite for TASK-0614: battlemap layout behind a MapGenerator port.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup) and ADR-0007.
Setup and assertions use only the public HTTP route POST /api/v1/forge/battlemap,
the Silo HTTP boundary (FakeSilo), and the composition-root injection point for
the map generator (the same pattern voice_agent uses for its speech engines).
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from asset_forge.main import app as asset_forge_app
from asset_forge.map_generation_engine import set_map_generator
from fastapi.testclient import TestClient

from tests.helpers.fixture_map_generator import (
    FIXTURE_THEME,
    FixtureMapGenerator,
    UnavailableMapGenerator,
)
from tests.helpers.silo_fixtures import FakeSilo
from tests.helpers.ws_identity import SIGNING_ISSUER


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


ROUTE = "/api/v1/forge/battlemap"
SIZE = {"width_cells": 20, "height_cells": 20, "cell_size_px": 64}
CAMPAIGN_ID = str(uuid4())


@pytest.fixture(autouse=True)
def forge_campaign(spicedb) -> str:
    """The forge tester is a player of the campaign that every request names."""
    asyncio.run(
        spicedb.write_relationship(
            resource_type="campaign",
            resource_id=CAMPAIGN_ID,
            relation="player",
            subject_type="user",
            subject_id="forge-tester",
        )
    )
    return CAMPAIGN_ID


@pytest.fixture
def forge_client() -> TestClient:
    return TestClient(asset_forge_app, headers=auth_headers("forge-tester"))


def _forge(client: TestClient, prompt: str, seed: int | None = None) -> dict:
    body: dict = {"prompt": prompt, "campaign_id": CAMPAIGN_ID, **SIZE}
    if seed is not None:
        body["seed"] = seed
    response = client.post(ROUTE, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _wall_layout(forged: dict) -> list[tuple[int, int, int, int, str]]:
    return sorted(
        (w["x1"], w["y1"], w["x2"], w["y2"], w["wall_type"]) for w in forged["wall_segments"]
    )


PROMPTS = [
    "Flooded crypt with sunken altars and narrow galleries",
    "Elven library with tall shelves and reading alcoves",
    "Goblin camp with wooden palisades",
    "Dwarven forge with lava canals",
    "Swamp shrine with sunken idols",
    "Crystal cavern with narrow ledges",
    "Sky fortress courtyard with broken pillars",
    "Pirate cove with wrecked ships",
]


def test_prompts_with_same_seed_and_size_yield_distinct_layouts(
    forge_client: TestClient, silo_double: FakeSilo
):
    """The prompt is part of the generator input. Same seed and size, other prompt, other walls.

    Before TASK-0614 the layout kept the same divider walls and only ten pillar
    phases, so most prompts of one size produced the same wall layout.
    """
    layouts = [_wall_layout(_forge(forge_client, prompt, seed=7)) for prompt in PROMPTS]

    assert len({tuple(layout) for layout in layouts}) == len(PROMPTS)


def test_same_prompt_seed_and_size_reproduce_the_same_layout(
    forge_client: TestClient, silo_double: FakeSilo
):
    """The deterministic generator is repeatable for identical inputs."""
    prompt = "Flooded crypt with sunken altars and narrow galleries"
    first = _forge(forge_client, prompt, seed=7)
    second = _forge(forge_client, prompt, seed=7)

    assert _wall_layout(first) == _wall_layout(second)
    assert first["doors"] == second["doors"]
    assert first["hazard_cells"] == second["hazard_cells"]


def test_response_names_the_default_generator(forge_client: TestClient, silo_double: FakeSilo):
    """The response names the generator that produced the layout. The default is deterministic."""
    data = _forge(forge_client, "Subterranean dwarven forge with lava canals")

    assert data["generator"] == "deterministic"


@pytest.fixture
def injected_generator():
    """Inject a test generator at the composition root and restore the default after."""
    yield set_map_generator
    set_map_generator(None)


def test_injected_generator_supplies_the_layout(
    forge_client: TestClient, silo_double: FakeSilo, injected_generator
):
    """A provider behind the port supplies the layout, theme and generator name."""
    injected_generator(FixtureMapGenerator())
    data = _forge(forge_client, "Anything at all")

    assert data["generator"] == "fixture"
    assert data["theme"] == FIXTURE_THEME
    assert _wall_layout(data) == [(0, 0, 20, 0, "fixture")]


def test_unavailable_generator_returns_503_and_stores_nothing(
    forge_client: TestClient, silo_double: FakeSilo, injected_generator
):
    """A generator that cannot produce a layout gives 503. No map is stored or indexed."""
    injected_generator(UnavailableMapGenerator())
    response = forge_client.post(
        ROUTE, json={"prompt": "Any crypt", "campaign_id": CAMPAIGN_ID, **SIZE}
    )

    assert response.status_code == 503, response.text
    detail = response.json()["detail"]
    assert detail["error"] == "map_generation_unavailable"
    assert detail["generator"] == "fixture"
    assert "asset_id" not in response.json()
    assert silo_double.objects == {}
