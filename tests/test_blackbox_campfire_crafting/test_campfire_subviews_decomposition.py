"""Blackbox tests for Campfire Crafting Subviews Modular Decomposition.

TASK-0199: Campfire Crafting Subviews Modular Decomposition
Governed by ADR-0004, ADR-0007, ADR-0012, ADR-0013, and Hard Invariants 6 & 7.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from game_session.dependencies import STREAM_SESSION, STREAM_STRONGHOLD

from .conftest import REPO_ROOT


def test_campfire_crafting_subviews_file_length_invariants() -> None:
    """Verify component controller and subview templates comply with line limits."""
    ui_src = REPO_ROOT / "services/game_session/ui/src"
    campfire_dir = ui_src / "campfire"
    controller_file = ui_src / "runefoble-campfire-crafting.ts"

    assert controller_file.is_file() and campfire_dir.is_dir()
    c_lines = len(controller_file.read_text(encoding="utf-8").splitlines())
    assert c_lines < 110 and c_lines < 100, f"runefoble-campfire-crafting.ts has {c_lines} lines"

    submodules = [
        (campfire_dir / "crafting-bench.template.ts", 120, 110),
        (campfire_dir / "boons-display.template.ts", 120, 90),
        (campfire_dir / "stronghold-status.template.ts", 120, 90),
        (campfire_dir / "types.ts", 60, 55),
        (campfire_dir / "index.ts", 30, 20),
    ]

    for path, max_limit, target_limit in submodules:
        assert path.is_file(), f"{path} must exist"
        lines = len(path.read_text(encoding="utf-8").splitlines())
        assert lines < max_limit and lines < target_limit, f"{path.name}: {lines} lines"


def test_campfire_subviews_exports_and_template_signatures() -> None:
    """Verify aggregator index and templates export expected functions and DOM structures."""
    campfire_dir = REPO_ROOT / "services/game_session/ui/src/campfire"
    index_content = (campfire_dir / "index.ts").read_text(encoding="utf-8")

    for sym in ["renderCraftingBench", "renderBoonsDisplay", "renderStrongholdStatus"]:
        assert sym in index_content, f"Expected {sym} in campfire/index.ts"

    bench_content = (campfire_dir / "crafting-bench.template.ts").read_text(encoding="utf-8")
    assert "Alchemical Crucible Workbench" in bench_content
    assert "Volatile Mishap Probability" in bench_content

    boons_content = (campfire_dir / "boons-display.template.ts").read_text(encoding="utf-8")
    assert "Campfire Rest Interlude" in boons_content
    assert "Active Party Rest Boons" in boons_content

    stronghold_content = (campfire_dir / "stronghold-status.template.ts").read_text(
        encoding="utf-8"
    )
    assert "Campsite Fortifications" in stronghold_content
    assert "Watchtower" in stronghold_content


def test_blackbox_campfire_crafting_frontdoor_integration(
    session_client: TestClient, char_client: TestClient, mock_bus
) -> None:
    """Verify campfire rest and alchemical crafting workflows via public frontdoors."""
    camp_id = uuid4()
    session_res = session_client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": str(camp_id), "title": "Campfire Haven Session", "dm_id": "dm_bram"},
    )
    assert session_res.status_code == 200
    session_id = session_res.json()["session_id"]

    upg_res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 100},
    )
    assert upg_res.status_code == 200 and upg_res.json()["new_tier"] == 1

    rest_res = session_client.post(
        f"/api/v1/sessions/{session_id}/rest/campfire",
        json={"rest_type": "long", "storytelling_prompt": "First monster that frightened you."},
    )
    assert rest_res.status_code == 200 and rest_res.json()["status"] == "completed"

    session_entries = mock_bus.streams.get(STREAM_SESSION, [])
    assert any("CampfireRestCompleted" in e[1].get("event_type", "") for e in session_entries)
    stronghold_entries = mock_bus.streams.get(STREAM_STRONGHOLD, [])
    assert any("StrongholdUpgraded" in e[1].get("event_type", "") for e in stronghold_entries)

    char_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Bram Master Alchemist", "character_class": "Artificer", "max_hp": 26},
    )
    assert char_res.status_code == 200
    char_id = char_res.json()["character_id"]

    combine_res = char_client.post(
        "/api/v1/crafting/recipes/combine",
        json={
            "character_id": char_id,
            "reagents": ["Glowmoss Extract", "Volcano Ash"],
            "catalyst": "purified_water",
        },
    )
    assert combine_res.status_code == 200
    data = combine_res.json()
    assert data["outcome"] == "success" and data["item_name"] == "Radiant Smoke Pellet"
