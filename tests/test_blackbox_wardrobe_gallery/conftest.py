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
from asset_forge.dependencies import get_storage as get_asset_storage
from asset_forge.dependencies import set_event_bus as set_forge_bus
from asset_forge.main import app as asset_forge_app
from character_sheet.dependencies import (
    set_event_bus as set_char_bus,
)
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean storage and bus states before and after each test."""
    storage = get_asset_storage()
    storage.clear()
    set_char_bus(None)
    set_forge_bus(None)
    yield
    storage.clear()
    set_char_bus(None)
    set_forge_bus(None)


@pytest.fixture
def char_client() -> TestClient:
    return TestClient(character_app)


@pytest.fixture
def forge_client() -> TestClient:
    return TestClient(asset_forge_app)
