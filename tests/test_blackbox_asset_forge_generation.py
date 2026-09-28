"""Blackbox TDD test suite for Procedural Battlemap & Token Asset Forge Generation (TASK-0092).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public frontdoors:
- Public HTTP REST API endpoints in asset_forge.main
- Silo S3 storage retrieval and validation
- Procedural battlemap and token generation with geometry extraction and transparency
"""

from __future__ import annotations

import struct

import pytest
from asset_forge.dependencies import get_storage, set_event_bus
from asset_forge.main import app
from fastapi.testclient import TestClient

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean storage and bus states before and after each test."""
    storage = get_storage()
    storage.clear()
    set_event_bus(None)
    yield
    storage.clear()
    set_event_bus(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_blackbox_forge_battlemap_generation_and_storage(client: TestClient):
    """Verify POST /api/v1/forge/battlemap generates map, extracts geometry, and stores in Silo S3."""
    response = client.post(
        "/api/v1/forge/battlemap",
        json={
            "prompt": "Subterranean dwarven forge with lava canals and broken anvil statues",
            "width_cells": 16,
            "height_cells": 16,
            "cell_size_px": 64,
            "wall_density": 0.25,
            "hazard_density": 0.15,
        },
        headers={"X-User-Id": "dm-evelyn"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    # 1. Output model verification
    assert data["status"] == "forged"
    assert data["asset_id"].startswith("map-")
    assert data["theme"] == "dwarven_forge"
    assert data["width_cells"] == 16
    assert data["height_cells"] == 16
    assert data["cell_size_px"] == 64

    # 2. Spatial geometry analysis
    assert len(data["wall_segments"]) > 0
    assert len(data["doors"]) > 0
    assert len(data["hazard_cells"]) > 0

    # Verify dwarven forge theme produced lava hazards with 2d10 damage
    first_hazard = data["hazard_cells"][0]
    assert first_hazard["hazard_type"] == "lava"
    assert first_hazard["damage_dice"] == "2d10"
    assert first_hazard["terrain_type"] == "difficult"

    # 3. Board state pre-calculated payload
    geom = data["board_geometry_payload"]
    assert "terrain_mutations" in geom
    assert "obstacle_tokens" in geom
    assert "wall_segments" in geom
    assert "doors" in geom
    assert len(geom["terrain_mutations"]) == len(data["hazard_cells"])

    # 4. Storage verification directly from Silo S3
    storage = get_storage()
    asset_bytes, content_type = storage.get_asset(
        "runefoble-assets", f"battlemaps/{data['asset_id']}.png"
    )
    assert content_type == "image/png"
    assert asset_bytes.startswith(PNG_SIGNATURE)

    # Verify PNG dimensions match 16 * 64 = 1024 px
    w, h = struct.unpack(">II", asset_bytes[16:24])
    assert w == 16 * 64
    assert h == 16 * 64


def test_blackbox_forge_token_portrait_and_transparency(client: TestClient):
    """Verify POST /api/v1/forge/token creates circular transparent token portrait in Silo S3."""
    response = client.post(
        "/api/v1/forge/token",
        json={
            "token_name": "Thorin Ironbreaker",
            "prompt": "Dwarven paladin with glowing runic warhammer",
            "token_type": "pc",
            "size_px": 128,
            "crop_style": "circular",
            "border_color": "#e63946",
            "border_width": 6,
            "transparent_background": True,
        },
        headers={"X-User-Id": "player-marcus"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "forged"
    assert data["asset_id"].startswith("tok-")
    assert data["token_name"] == "Thorin Ironbreaker"
    assert data["token_type"] == "pc"
    assert data["crop_style"] == "circular"
    assert data["size_px"] == 128
    assert data["has_transparency"] is True

    # Storage verification
    storage = get_storage()
    asset_bytes, content_type = storage.get_asset(
        "runefoble-assets", f"tokens/{data['asset_id']}.png"
    )
    assert content_type == "image/png"
    assert asset_bytes.startswith(PNG_SIGNATURE)

    w, h = struct.unpack(">II", asset_bytes[16:24])
    assert w == 128
    assert h == 128


def test_raster_modular_decomposition_and_line_limits():
    """Verify TASK-0197 modular decomposition limits and facade re-exports."""
    from pathlib import Path

    import asset_forge.generator as gen_facade
    import asset_forge.raster as raster_pkg
    import asset_forge.raster.battlemap_raster as bm_mod
    import asset_forge.raster.png_codec as codec_mod
    import asset_forge.raster.token_raster as tok_mod
    import asset_forge.raster.wardrobe_raster as wd_mod

    # 1. Structural line limits verification
    gen_file = Path(gen_facade.__file__)
    raster_dir = Path(raster_pkg.__file__).parent

    gen_lines = len(gen_file.read_text().splitlines())
    assert gen_lines < 50, f"generator.py facade must be < 50 lines, got {gen_lines}"

    for py_file in raster_dir.glob("*.py"):
        lines = len(py_file.read_text().splitlines())
        assert lines < 120, (
            f"Submodule {py_file.name} must be < 120 lines per Hard Invariant 6, got {lines}"
        )

    # 2. Re-export parity between facade and submodules
    assert gen_facade.encode_png_rgba is codec_mod.encode_png_rgba
    assert gen_facade.parse_hex_color is codec_mod.parse_hex_color
    assert gen_facade.generate_battlemap_png is bm_mod.generate_battlemap_png
    assert gen_facade.generate_token_portrait_png is tok_mod.generate_token_portrait_png
    assert gen_facade.generate_token_png is tok_mod.generate_token_png
    assert gen_facade.generate_wardrobe_portrait_png is wd_mod.generate_wardrobe_portrait_png
    assert gen_facade.ATTIRE_PROMPTS is wd_mod.ATTIRE_PROMPTS
    assert gen_facade.ATTIRE_PALETTES is wd_mod.ATTIRE_PALETTES

    # 3. Direct functional generation test via submodules
    grid = [[0, 1], [2, 0]]
    map_png = bm_mod.generate_battlemap_png(grid, "dwarven_forge", cell_size_px=32)
    assert map_png.startswith(PNG_SIGNATURE)

    tok_png = tok_mod.generate_token_png("TestToken", "A brave warrior")
    assert tok_png.startswith(PNG_SIGNATURE)
