"""Shared fixtures and configuration for wardrobe gallery blackbox tests.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public frontdoors:
- Public HTTP REST API endpoints in character_sheet and asset_forge
- Silo S3 object storage validation
- Published standard CloudEvents over Redis Streams
- Object-level Zanzibar authorization via SpiceDB schema
"""

from __future__ import annotations

from pathlib import Path

import pytest
from asset_forge.main import app as asset_forge_app
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import bearer

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def char_client() -> TestClient:
    return TestClient(character_app, headers=bearer("character-owner"))


@pytest.fixture
def forge_client() -> TestClient:
    return TestClient(asset_forge_app, headers=bearer("character-owner"))
