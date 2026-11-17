"""Blackbox TDD frontdoor tests for Mobile Companion UI Decomposition (TASK-0151).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Theming System and Accessibility Contrast Invariants
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines, all sub-files < 180 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from voice_agent.main import app as voice_app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def voice_client() -> TestClient:
    return TestClient(voice_app)


def test_voice_agent_manifest_exposes_decomposed_companion(voice_client: TestClient) -> None:
    """Verify GET /ui/manifest advertises mobile companion sub-components and styles."""
    resp = voice_client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "voice_agent"
    assert data["package"] == "@runefoble/voice-agent-ui"

    for comp in [
        "runefoble-mobile-companion",
        "audio-stream-controller",
        "haptic-ping-panel",
        "connection-status-badge",
    ]:
        assert comp in data["components"]
        assert comp in data["tags"]

    assert any("mobile_companion/styles" in s for s in data["styles"])

    # Manifest file matches runtime endpoint
    manifest_path = REPO_ROOT / "services/voice_agent/ui/manifest.json"
    assert manifest_path.is_file()
    file_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert file_data["components"] == data["components"]
    assert file_data["tags"] == data["tags"]
