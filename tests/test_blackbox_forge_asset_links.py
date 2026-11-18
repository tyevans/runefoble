"""Blackbox frontdoor tests for forged asset links (TASK-0785).

Governed by Hard Invariant 7, ADR-0001 and ADR-0015 (c).

- Forge outputs go through the public forge routes with signed bearer tokens.
- Forged bytes are read only through the public asset route `/api/v1/assets/{id}`.
- Campaign roles are written on the shared SpiceDB mock (the SpiceDB process boundary).
- No response body and no response header may hold an unsigned Silo object URL.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from asset_forge.main import app
from fastapi.testclient import TestClient

from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES, SILO_TEST_ENDPOINT
from tests.helpers.ws_identity import SIGNING_ISSUER

DM = "dm-evelyn"
PLAYER = "player-marcus"
STRANGER = "stranger-mallory"

FORGE_ROUTES = {
    "print-pdf": "/api/v1/forge/print-pdf",
    "standees": "/api/v1/forge/standees",
    "stl-token": "/api/v1/forge/stl-token",
    "battlemap": "/api/v1/forge/battlemap",
    "token": "/api/v1/forge/token",
}

FORGE_BODIES = {
    "print-pdf": {
        "prompt": "Dwarven forge",
        "width_cells": 10,
        "height_cells": 10,
        "format": "json",
    },
    "standees": {
        "sheet_title": "Goblin Pack",
        "standees": [{"name": "Goblin", "type": "monster", "hp": 7, "color": "#e76f51"}],
        "format": "json",
    },
    "stl-token": {"diameter_mm": 28.0, "height_mm": 6.0, "format": "json"},
    "battlemap": {
        "prompt": "Flooded crypt with sunken altars",
        "width_cells": 10,
        "format": "json",
    },
    "token": {"token_name": "Ghoul", "prompt": "Gaunt ghoul with rusted claws"},
}


def bearer(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def campaign(spicedb) -> str:
    """A campaign with a DM and a player. The stranger holds no role in it."""
    campaign_id = str(uuid4())
    for relation, user in (("dungeon_master", DM), ("player", PLAYER)):
        asyncio.run(
            spicedb.write_relationship(
                resource_type="campaign",
                resource_id=campaign_id,
                relation=relation,
                subject_type="user",
                subject_id=user,
            )
        )
    return campaign_id


def _forge(client: TestClient, kind: str, campaign: str, sub: str):
    body = {**FORGE_BODIES[kind], "campaign_id": campaign}
    return client.post(FORGE_ROUTES[kind], json=body, headers=bearer(sub))


@pytest.mark.parametrize("kind", ["print-pdf", "standees", "stl-token", "battlemap", "token"])
def test_forged_output_is_read_by_creator_and_refused_to_stranger(
    client: TestClient, campaign: str, kind: str
):
    """The forge reply names an authorized asset path. The creator reads it, a stranger gets 403."""
    created = _forge(client, kind, campaign, PLAYER)
    assert created.status_code == 200, created.text
    data = created.json()
    asset_id = data["asset_id"]
    download_url = data.get("download_url") or data["image_url"]
    assert download_url == f"/api/v1/assets/{asset_id}?stream=true"

    read = client.get(download_url, headers=bearer(PLAYER))
    assert read.status_code == 200, read.text
    assert read.content

    refused = client.get(download_url, headers=bearer(STRANGER))
    assert refused.status_code == 403, refused.text


def test_stranger_cannot_read_a_forged_pdf_as_an_attachment(client: TestClient, campaign: str):
    """The attachment download is also gated by `forged_asset.view`."""
    created = _forge(client, "print-pdf", campaign, PLAYER)
    asset_id = created.json()["asset_id"]

    refused = client.get(f"/api/v1/assets/{asset_id}/download", headers=bearer(STRANGER))
    assert refused.status_code == 403, refused.text

    allowed = client.get(f"/api/v1/assets/{asset_id}/download", headers=bearer(PLAYER))
    assert allowed.status_code == 200, allowed.text
    assert allowed.headers["content-type"] == "application/pdf"


def test_binary_print_pdf_reply_has_no_unsigned_silo_url(client: TestClient, campaign: str):
    """A binary forge reply carries the asset path in its headers, never a Silo object URL."""
    response = client.post(
        FORGE_ROUTES["print-pdf"],
        json={"campaign_id": campaign, "width_cells": 10, "height_cells": 10},
        headers=bearer(PLAYER),
    )
    assert response.status_code == 200, response.text
    asset_id = response.headers["x-asset-id"]

    assert response.headers["x-download-url"] == f"/api/v1/assets/{asset_id}?stream=true"
    assert SILO_TEST_ENDPOINT not in response.text
    assert "expires=" not in str(dict(response.headers))


@pytest.mark.parametrize("kind", ["battlemap", "token"])
def test_forge_preview_url_is_the_authorized_asset_read_path(
    client: TestClient, campaign: str, kind: str
):
    """The preview URL names the gateway read path for the forged asset, so the App Shell can fetch it with a bearer."""
    response = _forge(client, kind, campaign, DM)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["image_url"] == f"/api/v1/assets/{body['asset_id']}?stream=true"


@pytest.mark.parametrize("kind", list(FORGE_ROUTES))
def test_no_forge_reply_holds_an_unsigned_silo_url(client: TestClient, campaign: str, kind: str):
    """No forge response body or header names the Silo endpoint or an `expires` query."""
    response = _forge(client, kind, campaign, PLAYER)
    assert response.status_code == 200, response.text

    assert SILO_TEST_ENDPOINT not in response.text
    assert "expires=" not in response.text
    assert SILO_TEST_ENDPOINT not in str(dict(response.headers))


def test_asset_upload_reply_holds_no_unsigned_silo_url(client: TestClient):
    """An avatar upload returns the authorized asset path and no Silo object URL."""
    response = client.post(
        "/api/v1/assets/upload",
        data={"asset_type": "avatar", "owner_id": PLAYER},
        files={"file": ("hero.png", PNG_SAMPLE_BYTES, "image/png")},
        headers=bearer(PLAYER),
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert "url" not in data
    assert SILO_TEST_ENDPOINT not in response.text
    assert "expires=" not in response.text
    assert data["download_url"] == f"/api/v1/assets/{data['asset_id']}?stream=true"


def test_asset_metadata_read_holds_no_unsigned_silo_url(client: TestClient, campaign: str):
    """A metadata read of a forged asset returns no Silo object URL."""
    created = _forge(client, "stl-token", campaign, PLAYER)
    asset_id = created.json()["asset_id"]

    read = client.get(f"/api/v1/assets/{asset_id}", headers=bearer(PLAYER))
    assert read.status_code == 200, read.text
    assert "url" not in read.json()
    assert SILO_TEST_ENDPOINT not in read.text
