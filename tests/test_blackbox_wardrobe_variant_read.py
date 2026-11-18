"""Blackbox TDD test: a wardrobe variant that is created is read back through the public route (TASK-0703).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup). Setup and assertions use
only the public character sheet HTTP routes. No private aggregate state is read.
"""

from character_sheet.main import app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import SIGNING_ISSUER


def _client() -> TestClient:
    return TestClient(
        app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('character-owner')}"}
    )


def test_blackbox_created_wardrobe_variant_appears_in_character_wardrobe_read():
    """Create a character, add a wardrobe variant, then read the character wardrobe."""
    client = _client()
    created = client.post(
        "/api/v1/characters",
        json={"name": "Nadia", "character_class": "Cleric", "max_hp": 10},
    )
    assert created.status_code == 200, created.text
    character_id = created.json()["character_id"]

    added = client.post(
        f"/api/v1/characters/{character_id}/wardrobe",
        json={
            "variant_id": "variant-arctic-cloak",
            "variant_name": "Arctic Cloak",
            "attire_type": "arctic_tundra",
            "image_url": "https://silo.example/wardrobe/variant-arctic-cloak.png",
            "prompt": "a fur-lined cloak over chainmail",
            "set_active": False,
        },
    )
    assert added.status_code == 200, added.text

    read = client.get(f"/api/v1/characters/{character_id}/wardrobe")
    assert read.status_code == 200, read.text
    wardrobe = read.json()
    assert "variant-arctic-cloak" in wardrobe
    variant = wardrobe["variant-arctic-cloak"]
    assert variant["variant_name"] == "Arctic Cloak"
    assert variant["attire_type"] == "arctic_tundra"
    assert variant["image_url"] == "https://silo.example/wardrobe/variant-arctic-cloak.png"
