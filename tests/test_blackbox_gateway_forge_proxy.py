"""Blackbox tests: gateway forge and Silo asset routes proxy to asset_forge (TASK-0595).

The gateway is called through its public HTTP routes. asset_forge runs as a live loopback
upstream (tests/helpers/live_services.py). Setup uses the public routes, and the SpiceDB mock
holds the campaign roles. Governed by ADR-0001, ADR-0007 and ADR-0015 (b, c).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import closed_port_url, serve, unavailable_app
from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES
from tests.helpers.ws_identity import SIGNING_ISSUER

PLAYER = "player-marcus"
STRANGER = "stranger-mallory"


def bearer(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def campaign(spicedb) -> str:
    """A campaign whose player may forge and view assets. The stranger holds no role."""
    campaign_id = str(uuid4())
    asyncio.run(
        spicedb.write_relationship(
            resource_type="campaign",
            resource_id=campaign_id,
            relation="player",
            subject_type="user",
            subject_id=PLAYER,
        )
    )
    return campaign_id


@pytest.fixture
def gateway(asset_forge_upstream: str) -> Iterator[TestClient]:
    """Gateway client wired to a live asset_forge. The URL is set before the lifespan runs."""
    with TestClient(gateway_app) as client:
        yield client


def _token_body(campaign_id: str) -> dict:
    return {
        "token_name": "Ghoul",
        "prompt": "Gaunt ghoul with rusted claws",
        "campaign_id": campaign_id,
    }


def _print_body(campaign_id: str) -> dict:
    return {
        "prompt": "Dwarven forge",
        "width_cells": 10,
        "height_cells": 10,
        "campaign_id": campaign_id,
    }


# --- Forge routes ---------------------------------------------------------------------------


def test_token_forge_through_gateway_stores_a_png_that_the_gateway_streams(
    gateway: TestClient, campaign: str
) -> None:
    created = gateway.post(
        "/api/v1/forge/token", json=_token_body(campaign), headers=bearer(PLAYER)
    )
    assert created.status_code == 200, created.text
    asset_id = created.json()["asset_id"]

    image = gateway.get(f"/api/v1/assets/{asset_id}?stream=true", headers=bearer(PLAYER))

    assert image.status_code == 200, image.text
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(b"\x89PNG")


def test_print_pdf_through_gateway_returns_the_owner_pdf_bytes(
    gateway: TestClient, campaign: str
) -> None:
    res = gateway.post(
        "/api/v1/forge/print-pdf", json=_print_body(campaign), headers=bearer(PLAYER)
    )

    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("application/pdf")
    assert res.content.startswith(b"%PDF")


def test_forge_request_without_bearer_is_refused_by_the_owner_with_its_challenge(
    gateway: TestClient, campaign: str
) -> None:
    res = gateway.post("/api/v1/forge/token", json=_token_body(campaign))

    assert res.status_code == 401, res.text
    assert res.headers["www-authenticate"] == "Bearer"


def test_owner_4xx_body_passes_through_unchanged(gateway: TestClient) -> None:
    res = gateway.post(
        "/api/v1/forge/token",
        json={"token_name": "Ghoul", "prompt": "No campaign named"},
        headers=bearer(PLAYER),
    )

    assert res.status_code == 400, res.text
    assert "campaign_id" in res.json()["detail"]


def test_stranger_is_refused_forging_in_a_campaign_it_does_not_play(
    gateway: TestClient, campaign: str
) -> None:
    res = gateway.post("/api/v1/forge/token", json=_token_body(campaign), headers=bearer(STRANGER))

    assert res.status_code == 403, res.text


def test_forge_owner_unreachable_returns_503_with_upstream_name(monkeypatch) -> None:
    monkeypatch.setenv("RUNEFOBLE_ASSET_FORGE_URL", closed_port_url())
    with TestClient(gateway_app) as client:
        res = client.post(
            "/api/v1/forge/token",
            json=_token_body(str(uuid4())),
            headers=bearer(PLAYER),
        )

    assert res.status_code == 503, res.text
    assert res.json()["upstream"] == "asset_forge"


def test_forge_owner_5xx_returns_502_with_upstream_name(monkeypatch) -> None:
    with serve(unavailable_app(500)) as url:
        monkeypatch.setenv("RUNEFOBLE_ASSET_FORGE_URL", url)
        with TestClient(gateway_app) as client:
            res = client.post(
                "/api/v1/forge/print-pdf", json={"prompt": "x"}, headers=bearer(PLAYER)
            )

    assert res.status_code == 502, res.text
    assert res.json()["upstream"] == "asset_forge"


# --- Silo asset routes ----------------------------------------------------------------------


def test_asset_upload_then_read_through_the_gateway_returns_the_same_bytes(
    gateway: TestClient,
) -> None:
    uploaded = gateway.post(
        "/api/v1/assets/upload",
        files={"file": ("valeros_avatar.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"asset_type": "avatar"},
        headers=bearer(PLAYER),
    )
    assert uploaded.status_code == 200, uploaded.text
    asset_id = uploaded.json()["asset_id"]
    assert uploaded.json()["owner_id"] == PLAYER

    streamed = gateway.get(f"/api/v1/assets/{asset_id}/stream", headers=bearer(PLAYER))
    assert streamed.status_code == 200, streamed.text
    assert streamed.content == PNG_SAMPLE_BYTES
    assert streamed.headers["content-type"] == "image/png"

    downloaded = gateway.get(f"/api/v1/assets/{asset_id}/download", headers=bearer(PLAYER))
    assert downloaded.content == PNG_SAMPLE_BYTES
    assert downloaded.headers["content-disposition"].startswith("attachment")


@pytest.mark.parametrize("suffix", ["", "/stream", "/download"])
def test_asset_read_by_a_stranger_is_refused(gateway: TestClient, suffix: str) -> None:
    """A user with no `forged_asset.view` on the asset gets 403 and no bytes."""
    uploaded = gateway.post(
        "/api/v1/assets/upload",
        files={"file": ("valeros_avatar.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"asset_type": "avatar"},
        headers=bearer(PLAYER),
    )
    asset_id = uploaded.json()["asset_id"]

    res = gateway.get(f"/api/v1/assets/{asset_id}{suffix}", headers=bearer(STRANGER))

    assert res.status_code == 403, res.text
    assert PNG_SAMPLE_BYTES not in res.content


def test_asset_upload_to_a_campaign_the_caller_does_not_play_is_refused(
    gateway: TestClient, campaign: str
) -> None:
    res = gateway.post(
        "/api/v1/assets/upload",
        files={"file": ("map.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"campaign_id": campaign, "asset_type": "battlemap"},
        headers=bearer(STRANGER),
    )

    assert res.status_code == 403, res.text


def test_asset_delete_without_identity_returns_401_with_challenge(
    gateway: TestClient,
) -> None:
    uploaded = gateway.post(
        "/api/v1/assets/upload",
        files={"file": ("map.png", PNG_SAMPLE_BYTES, "image/png")},
        headers=bearer(PLAYER),
    )
    asset_id = uploaded.json()["asset_id"]

    res = gateway.delete(f"/api/v1/assets/{asset_id}")

    assert res.status_code == 401, res.text
    assert res.headers["www-authenticate"] == "Bearer"
    assert gateway.get(f"/api/v1/assets/{asset_id}", headers=bearer(PLAYER)).status_code == 200


def test_asset_delete_by_the_owner_removes_the_asset(gateway: TestClient) -> None:
    uploaded = gateway.post(
        "/api/v1/assets/upload",
        files={"file": ("map.png", PNG_SAMPLE_BYTES, "image/png")},
        headers=bearer(PLAYER),
    )
    asset_id = uploaded.json()["asset_id"]

    res = gateway.delete(f"/api/v1/assets/{asset_id}", headers=bearer(PLAYER))

    assert res.status_code == 200, res.text
    assert res.json()["deleted"] is True
    assert gateway.get(f"/api/v1/assets/{asset_id}", headers=bearer(PLAYER)).status_code == 404


def test_asset_owner_unreachable_returns_503(monkeypatch) -> None:
    monkeypatch.setenv("RUNEFOBLE_ASSET_FORGE_URL", closed_port_url())
    with TestClient(gateway_app) as client:
        res = client.get(f"/api/v1/assets/{uuid4()}")

    assert res.status_code == 503, res.text
    assert res.json()["upstream"] == "asset_forge"
