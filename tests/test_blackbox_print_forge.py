"""Blackbox TDD test suite for Printable Tabletop Forge (TASK-0105).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public frontdoors:
- Public HTTP REST API endpoints in asset_forge.main (/assets/print-pdf, /assets/stl-token, /assets/standees)
- Multi-page PDF geometry scaling and exact 1-inch tabletop grid calibration
- Watertight 3D printable STL mesh validity (2-manifold topological check)
- Silo S3 storage persistence and domain event validation
"""

from __future__ import annotations

import struct
from uuid import uuid4

import pytest
from asset_forge.dependencies import get_storage, set_event_bus
from asset_forge.main import app
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient


class MockEventBus:
    def __init__(self):
        self.events: list[tuple[str, any]] = []

    async def publish_event(self, channel: str, event: any) -> None:
        self.events.append((channel, event))


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean storage and bus states before and after each test."""
    storage = get_storage()
    storage.clear()
    bus = MockEventBus()
    set_event_bus(bus)
    yield bus
    storage.clear()
    set_event_bus(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_blackbox_tiled_pdf_battlemap_letter_and_a4(
    client: TestClient, clean_environment: MockEventBus
):
    """Verify POST /assets/print-pdf generates multi-page 1-inch grid calibrated PDF."""
    response = client.post(
        "/assets/print-pdf",
        json={
            "prompt": "Dwarven forge with molten rivers",
            "width_cells": 16,
            "height_cells": 16,
            "page_size": "letter",
            "theme": "dwarven_forge",
            "title": "Molten Caverns",
        },
        headers={"X-User-Id": "crafter-rowan"},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-grid-scale"] == "1-inch"
    assert int(response.headers["x-page-count"]) > 1

    pdf_bytes = response.content
    # 1. PDF signature validation
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_bytes

    # 2. Check alignment crosshairs and 1-inch grid markers in PDF stream
    assert b"Molten Caverns" in pdf_bytes
    assert b"1-inch Grid (300 DPI calibrated)" in pdf_bytes

    # 3. Silo S3 persistence verification
    asset_id = response.headers["x-asset-id"]
    storage = get_storage()
    stored_bytes, ct = storage.get_asset("runefoble-assets", f"prints/{asset_id}.pdf")
    assert ct == "application/pdf"
    assert stored_bytes == pdf_bytes

    # 4. Domain event publication
    assert len(clean_environment.events) == 1
    channel, event = clean_environment.events[0]
    assert channel == "runefoble.events.asset"
    assert event.asset_id == asset_id
    assert event.grid_scale == "1-inch"


def test_blackbox_tiled_pdf_json_format_and_alias(client: TestClient):
    """Verify POST /api/v1/forge/print-pdf with format='json' returns metadata response."""
    response = client.post(
        "/api/v1/forge/print-pdf",
        json={
            "width_cells": 14,
            "height_cells": 18,
            "page_size": "a4",
            "format": "json",
            "title": "A4 Crypt",
        },
        headers={"X-User-Id": "crafter-rowan"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "forged"
    assert data["grid_calibration"] == "1-inch (72pt)"
    assert data["page_size"] == "a4"
    assert data["total_pages"] >= 4
    assert data["download_url"].startswith("http")


def test_blackbox_papercraft_standees_generation(client: TestClient):
    """Verify POST /assets/standees produces foldable paper miniatures with mirrored artwork."""
    response = client.post(
        "/assets/standees",
        json={
            "sheet_title": "Goblin Ambush Pack",
            "standees": [
                {"name": "Goblin Scout", "type": "monster", "hp": 7, "color": "#e76f51"},
                {"name": "Goblin Boss", "type": "monster", "hp": 21, "color": "#d62828"},
                {"name": "Valeros Fighter", "type": "pc", "hp": 28, "color": "#2a9d8f"},
            ],
            "page_size": "letter",
        },
        headers={"X-User-Id": "crafter-rowan"},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-standee-count"] == "3"

    pdf_bytes = response.content
    assert pdf_bytes.startswith(b"%PDF-1.4")
    # Verify mirrored back face and fold tab labels
    assert b"Goblin Scout - BACK" in pdf_bytes
    assert b"Valeros Fighter - BACK" in pdf_bytes
    assert b"FOLD BASE TAB" in pdf_bytes


def test_blackbox_stl_token_watertight_mesh(client: TestClient, clean_environment: MockEventBus):
    """Verify POST /assets/stl-token outputs mathematically watertight 3D STL mesh."""
    response = client.post(
        "/assets/stl-token",
        json={
            "diameter_mm": 28.0,
            "height_mm": 3.5,
            "num_slots": 4,
            "slot_depth_mm": 1.5,
            "condition_label": "Poisoned",
            "binary": True,
        },
        headers={"X-User-Id": "crafter-rowan"},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "model/stl"
    assert response.headers["x-is-watertight"] == "true"

    stl_bytes = response.content
    assert len(stl_bytes) >= 84
    facet_count = struct.unpack("<I", stl_bytes[80:84])[0]
    assert facet_count == int(response.headers["x-facet-count"])
    assert len(stl_bytes) == 80 + 4 + (facet_count * 50)

    # Topological 2-Manifold watertight mesh verification
    # Every triangle edge must be shared by exactly two adjacent triangles
    edges: dict[tuple[tuple[float, float, float], tuple[float, float, float]], int] = {}
    vertices: set[tuple[float, float, float]] = set()

    for i in range(facet_count):
        offset = 84 + i * 50
        floats = struct.unpack("<12fH", stl_bytes[offset : offset + 50])
        v1 = (round(floats[3], 3), round(floats[4], 3), round(floats[5], 3))
        v2 = (round(floats[6], 3), round(floats[7], 3), round(floats[8], 3))
        v3 = (round(floats[9], 3), round(floats[10], 3), round(floats[11], 3))

        vertices.add(v1)
        vertices.add(v2)
        vertices.add(v3)

        for a, b in [(v1, v2), (v2, v3), (v3, v1)]:
            edge_key = tuple(sorted([a, b]))
            edges[edge_key] = edges.get(edge_key, 0) + 1

    # Assert exactly 2 triangles share every edge (zero open boundaries or non-manifold edges)
    non_manifold_edges = [e for e, count in edges.items() if count != 2]
    assert len(non_manifold_edges) == 0, f"Found {len(non_manifold_edges)} non-manifold edges!"

    # Assert Euler-Poincaré formula for closed orientable surface (genus 0 sphere): V - E + F = 2
    v_count = len(vertices)
    e_count = len(edges)
    f_count = facet_count
    assert v_count - e_count + f_count == 2, (
        f"Euler characteristic != 2: V={v_count}, E={e_count}, F={f_count}"
    )

    # Silo S3 storage check
    asset_id = response.headers["x-asset-id"]
    storage = get_storage()
    stored_bytes, ct = storage.get_asset("runefoble-assets", f"stls/{asset_id}.stl")
    assert ct == "model/stl"
    assert stored_bytes == stl_bytes

    # Domain event publication
    assert len(clean_environment.events) == 1
    channel, event = clean_environment.events[0]
    assert event.facet_count == facet_count
    assert event.condition_label == "Poisoned"


def test_blackbox_stl_token_ascii_format(client: TestClient):
    """Verify POST /api/v1/forge/stl-token with format='json' and ASCII mesh option."""
    response = client.post(
        "/api/v1/forge/stl-token",
        json={
            "diameter_mm": 50.0,
            "height_mm": 4.0,
            "num_slots": 6,
            "condition_label": "Stunned",
            "binary": False,
            "format": "json",
        },
        headers={"X-User-Id": "crafter-rowan"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "forged"
    assert data["diameter_mm"] == 50.0
    assert data["is_watertight"] is True
    assert data["condition_label"] == "Stunned"


@pytest.mark.asyncio
async def test_blackbox_print_forge_spicedb_authorization(client: TestClient, monkeypatch):
    """Verify campaign Zanzibar permission check blocks unauthorized users."""
    camp_id = uuid4()

    async def mock_check_permission(*args, **kwargs):
        return False

    monkeypatch.setattr(SpiceDBClient, "check_permission", mock_check_permission)

    response = client.post(
        "/assets/print-pdf",
        json={"campaign_id": str(camp_id), "width_cells": 10, "height_cells": 10},
        headers={"X-User-Id": "unauthorized-user"},
    )
    assert response.status_code == 403
    assert "Forbidden" in response.text
