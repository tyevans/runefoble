"""Blackbox TDD tests for Character Sheet condition overlays and badge thresholds.

Governed by:
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines; suite module < 200 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_blackbox_condition_overlays_and_bloodied_threshold(char_client: TestClient):
    """Verify HP drop below 50% triggers bloodied badge and dynamic SVG condition overlay."""
    # 1. Create character via frontdoor POST /api/v1/characters
    create_res = char_client.post(
        "/api/v1/characters",
        json={
            "name": "Nadia the Expressive Bard",
            "character_class": "Bard",
            "max_hp": 40,
            "personality_traits": ["dramatic", "poetic"],
        },
    )
    assert create_res.status_code == 200
    char_data = create_res.json()
    char_id = char_data["character_id"]
    assert char_data["current_hp"] == 40
    assert "bloodied" not in char_data["condition_badges"]

    # 2. Inflict minor damage (30/40 HP = 75% HP) -> still healthy
    hp1_res = char_client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": -10, "source": "Goblin Dagger"},
    )
    assert hp1_res.status_code == 200
    hp1_data = hp1_res.json()
    assert hp1_data["current_hp"] == 30
    assert "bloodied" not in hp1_data["condition_badges"]

    # 3. Inflict injury crossing the 50% HP threshold (18/40 HP = 45% HP)
    hp2_res = char_client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": -12, "source": "Manticore Spike"},
    )
    assert hp2_res.status_code == 200
    hp2_data = hp2_res.json()
    assert hp2_data["current_hp"] == 18
    # DoD Requirement 1: Character sheet REST API returns bloodied badge and updated portrait URL
    assert "bloodied" in hp2_data["condition_badges"]
    assert "data:image/svg+xml" in hp2_data["active_portrait_url"]

    # 4. Frontdoor GET /api/v1/characters/{id}/portrait
    port_res = char_client.get(f"/api/v1/characters/{char_id}/portrait")
    assert port_res.status_code == 200
    port_data = port_res.json()
    assert "bloodied" in port_data["condition_badges"]
    assert port_data["current_hp"] == 18
    assert "bloodied-vignette" in port_data["svg_overlay"]
    assert "blood-scratches" in port_data["svg_overlay"]

    # 5. Healing back above 50% (28/40 HP = 70% HP) clears the bloodied badge
    heal_res = char_client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": 10, "source": "Cure Wounds"},
    )
    assert heal_res.status_code == 200
    heal_data = heal_res.json()
    assert heal_data["current_hp"] == 28
    assert "bloodied" not in heal_data["condition_badges"]


def test_blackbox_status_affliction_overlays(char_client: TestClient):
    """Verify condition affliction (poisoned, stunned) applies SVG auras and badges."""
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Valeros", "character_class": "Fighter", "max_hp": 50},
    )
    char_id = create_res.json()["character_id"]

    # 1. Apply Poisoned condition via frontdoor POST /api/v1/characters/{id}/conditions
    cond1_res = char_client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "poisoned", "duration_rounds": 5, "source": "Spider Venom"},
    )
    assert cond1_res.status_code == 200
    cond1_data = cond1_res.json()
    assert "poisoned" in cond1_data["condition_badges"]
    assert "data:image/svg+xml" in cond1_data["active_portrait_url"]

    port_res = char_client.get(f"/api/v1/characters/{char_id}/portrait")
    assert port_res.status_code == 200
    assert "poisoned-aura" in port_res.json()["svg_overlay"]
    assert "poison-bubbles" in port_res.json()["svg_overlay"]

    # 2. Apply Stunned condition
    cond2_res = char_client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "stunned", "duration_rounds": 2, "source": "Mind Blast"},
    )
    assert cond2_res.status_code == 200
    cond2_data = cond2_res.json()
    assert "stunned" in cond2_data["condition_badges"]
    assert "poisoned" in cond2_data["condition_badges"]

    port2_res = char_client.get(f"/api/v1/characters/{char_id}/portrait")
    assert "stunned-stars" in port2_res.json()["svg_overlay"]

    # 3. Remove Poisoned condition via frontdoor DELETE
    del_res = char_client.delete(f"/api/v1/characters/{char_id}/conditions/poisoned")
    assert del_res.status_code == 200
    assert "poisoned" not in del_res.json()["condition_badges"]
    assert "stunned" in del_res.json()["condition_badges"]
