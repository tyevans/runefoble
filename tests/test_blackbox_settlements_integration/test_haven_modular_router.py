"""Blackbox tests for haven router modular decomposition and backward compatibility.

Governed by ADR-0001, ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient


def test_haven_router_submodule_line_invariants():
    """Verify haven aggregator router is < 40 lines and all submodules are < 130 lines."""
    facade = Path("services/game_session/src/game_session/settlement/router.py")
    assert facade.exists()
    facade_lines = len(facade.read_text().splitlines())
    assert facade_lines < 40, f"router.py must be strictly < 40 lines, got {facade_lines}"

    haven_dir = Path("services/game_session/src/game_session/settlement/haven")
    submodules = list(haven_dir.glob("*.py"))
    assert len(submodules) >= 5, f"Expected at least 5 haven submodules, found {len(submodules)}"
    for mod in submodules:
        lines = len(mod.read_text().splitlines())
        assert lines < 130, f"{mod.name} must be strictly < 130 lines, got {lines}"


def test_haven_router_backwards_compatibility_exports():
    """Verify router and haven package backwards compatibility exports."""
    import game_session.settlement.haven as haven_pkg
    import game_session.settlement.router as router_mod

    expected_router_symbols = [
        "bulletin_router",
        "decrypt_cipher_notice",
        "establishments_router",
        "havens_router",
        "list_bulletin_notices",
        "pin_bulletin_notice",
        "remove_bulletin_notice",
        "router",
        "upgrades_router",
    ]
    for sym in expected_router_symbols:
        assert hasattr(router_mod, sym), f"Missing exported symbol {sym} in router.py"

    expected_haven_symbols = [
        "build_settlement_projection",
        "construct_establishment",
        "establishments_router",
        "found_settlement",
        "get_campaign_settlement_projection",
        "get_establishment",
        "havens_router",
        "list_campaign_settlements",
        "list_settlement_establishments",
        "load_establishment",
        "load_settlement",
        "save_and_publish",
        "to_uuid",
        "upgrade_establishment",
        "upgrade_settlement_tier",
        "upgrades_router",
    ]
    for sym in expected_haven_symbols:
        assert hasattr(haven_pkg, sym), f"Missing exported symbol {sym} in haven package"


@pytest.mark.asyncio
async def test_haven_modular_routes_frontdoor_journey(
    session_client: TestClient, spicedb: MockSpiceDBClient
):
    """Verify full haven lifecycle, establishment creation, and tier upgrading through frontdoor."""
    cid, dm_id = str(uuid4()), f"dm_{uuid4().hex[:6]}"
    await spicedb.write_relationship("campaign", cid, "dungeon_master", "user", dm_id)
    await spicedb.write_relationship("campaign", cid, "player", "user", dm_id)
    headers = {"x-user-id": dm_id}

    # 1. Haven creation via havens_router
    found_res = session_client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Havenwood", "scale": "hamlet", "districts": ["commons"], "prosperity": 120},
        headers=headers,
    )
    assert found_res.status_code == 201
    sid = found_res.json()["settlement_id"]
    assert found_res.json()["name"] == "Havenwood"

    # 2. Establishment construction via establishments_router
    est_res = session_client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "commons", "category": "hospitality", "name": "The Green Dragon"},
        headers=headers,
    )
    assert est_res.status_code == 201
    eid = est_res.json()["establishment_id"]

    # 3. Upgrade tier via upgrades_router
    upg_res = session_client.post(
        f"/api/v1/settlements/{sid}/upgrade-tier",
        json={"new_tier": 2, "prosperity": 120},
        headers=headers,
    )
    assert upg_res.status_code == 200
    assert upg_res.json()["tier"] == 2
    assert upg_res.json()["scale"] == "village"

    # 4. Upgrade establishment via upgrades_router
    est_upg = session_client.post(
        f"/api/v1/establishments/{eid}/upgrade",
        json={"tier": 2, "added_amenities": ["cellar"]},
        headers=headers,
    )
    assert est_upg.status_code == 200
    assert est_upg.json()["tier"] == 2
