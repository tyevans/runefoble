"""Blackbox TDD test: a papercraft standee export is published as PrintPdfForged.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Setup and assertions use only the public Asset Forge standees route and the
Redis Streams entries that the route publishes.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from asset_forge.main import app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import bearer


@pytest.mark.asyncio
async def test_standee_export_publishes_print_pdf_forged(spicedb, mock_bus):
    """Exporting standees through the public route writes one PrintPdfForged entry."""
    client = TestClient(app, headers=bearer("crafter-rowan"))
    campaign_id = str(uuid4())
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id="crafter-rowan",
    )

    response = client.post(
        "/api/v1/forge/standees",
        json={
            "campaign_id": campaign_id,
            "sheet_title": "Goblin Ambush Pack",
            "standees": [{"name": "Goblin Scout", "type": "monster", "hp": 7, "color": "#e76f51"}],
            "format": "json",
        },
    )
    assert response.status_code == 200, response.text
    asset_id = response.json()["asset_id"]

    entries = [
        payload
        for _, payload in mock_bus.streams.get("runefoble.events.asset", [])
        if payload["event_type"] == "runefoble.events.asset.print_pdf_forged"
    ]
    assert len(entries) == 1
    assert asset_id in entries[0]["payload"]
    assert "standee-sheet" in entries[0]["payload"]
