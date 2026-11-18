"""Blackbox TDD suite for the wardrobe generator port and honest face claims (TASK-0615).

Governed by:
- ADR-0014: BDD and Playwright E2E. Docs must match observable route behaviour.
- Hard Invariant 7: Blackbox TDD with frontdoor setup.

Setup and assertions use only public HTTP routes, FastAPI dependency overrides (the
generator port is the seam for an external image provider), the Silo storage read the
other wardrobe suites use, and the repository docs.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from asset_forge.dependencies import get_storage, get_wardrobe_generator
from asset_forge.main import app
from asset_forge.raster.png_codec import encode_png_rgba
from asset_forge.wardrobe_generator import WardrobePortrait, build_wardrobe_generator
from fastapi.testclient import TestClient
from pydantic import ValidationError
from runefoble_platform.config import WardrobeGeneratorSettings

from tests.helpers.ws_identity import SIGNING_ISSUER


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_PATHS = [
    REPO_ROOT / "docs/reference/ports-and-endpoints.md",
    REPO_ROOT / "docs/how-to/manage-generative-wardrobe-and-condition-portraits.md",
    REPO_ROOT / "docs/how-to/forge-procedural-battlemaps-and-tokens.md",
]
FALSE_CLAIM = "preserves face embeddings"


class RecordingFaceGenerator:
    """Fake of an external image provider behind the port. It records each call.

    It reports that it preserves the face. The image bytes depend on the attire prompt,
    so two different prompts give two different PNG files.
    """

    name = "recording-provider"
    preserves_face = True

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate(
        self,
        portrait: WardrobePortrait,
        attire_prompt: str,
        face_seed: str | None,
    ) -> bytes:
        self.calls.append(
            {"attire_prompt": attire_prompt, "face_seed": face_seed, "size": portrait.size_px}
        )
        digest = hashlib.sha256(attire_prompt.encode()).digest()
        pixel = bytes((digest[0], digest[1], digest[2], 255))
        return encode_png_rgba(16, 16, pixel * (16 * 16))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def recording_generator() -> Iterator[RecordingFaceGenerator]:
    fake = RecordingFaceGenerator()
    app.dependency_overrides[get_wardrobe_generator] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_wardrobe_generator, None)


def _forge(client: TestClient, prompt: str | None) -> dict:
    response = client.post(
        "/api/v1/forge/wardrobe",
        json={
            "character_id": str(uuid4()),
            "character_name": "Nadia the Bard",
            "attire_type": "ballroom_masquerade",
            "prompt": prompt,
            "face_embedding_seed": "nadia_face_v1",
            "size_px": 128,
        },
        headers=auth_headers("player-nadia"),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _stored_bytes(variant_id: str) -> bytes:
    storage = get_storage()
    data, content_type = storage.get_asset(storage.default_bucket, f"wardrobe/{variant_id}.png")
    assert content_type == "image/png"
    return data


def test_blackbox_default_placeholder_reports_no_face_preservation(client: TestClient):
    """The default generator is the placeholder. The response says it preserves no face."""
    data = _forge(client, prompt="Gilded Venetian mask")

    assert data["generator"] == "placeholder"
    assert data["preserves_face"] is False
    assert data["status"] == "forged"
    assert data["prompt"].startswith("Ornate royal masquerade ball attire")
    assert _stored_bytes(data["variant_id"]).startswith(PNG_SIGNATURE)


def test_blackbox_attire_prompt_reaches_configured_generator(
    client: TestClient, recording_generator: RecordingFaceGenerator
):
    """The attire prompt is passed to the configured generator. Its output follows the prompt."""
    first = _forge(client, prompt="Violet velvet gown")
    second = _forge(client, prompt="Snow leopard cloak")

    prompts = [call["attire_prompt"] for call in recording_generator.calls]
    assert any("Violet velvet gown" in p for p in prompts)
    assert any("Snow leopard cloak" in p for p in prompts)
    assert recording_generator.calls[0]["face_seed"] == "nadia_face_v1"

    assert first["generator"] == "recording-provider"
    assert first["preserves_face"] is True
    assert _stored_bytes(first["variant_id"]) != _stored_bytes(second["variant_id"])


def test_blackbox_docs_do_not_claim_face_embedding_preservation():
    """The reference and how-to docs no longer claim face-embedding preservation."""
    for path in DOC_PATHS:
        text = path.read_text(encoding="utf-8").lower()
        assert FALSE_CLAIM not in text, f"{path.name} still makes the false face claim"


def test_blackbox_docs_describe_placeholder_default_and_response_fields():
    """The wardrobe how-to names the placeholder default and the response fields."""
    how_to = (
        REPO_ROOT / "docs/how-to/manage-generative-wardrobe-and-condition-portraits.md"
    ).read_text(encoding="utf-8")
    assert "placeholder" in how_to
    assert "preserves_face" in how_to
    assert "generator" in how_to


def test_blackbox_unknown_generator_setting_fails_at_start_up(monkeypatch: pytest.MonkeyPatch):
    """An unknown generator name fails validation. It does not fall back to the placeholder."""
    monkeypatch.setenv("RUNEFOBLE_WARDROBE_GENERATOR", "unlisted-provider")
    with pytest.raises(ValidationError):
        WardrobeGeneratorSettings()


def test_blackbox_placeholder_is_the_default_setting(monkeypatch: pytest.MonkeyPatch):
    """With no setting, the configured generator is the placeholder."""
    monkeypatch.delenv("RUNEFOBLE_WARDROBE_GENERATOR", raising=False)
    generator = build_wardrobe_generator(WardrobeGeneratorSettings())
    assert generator.name == "placeholder"
    assert generator.preserves_face is False
