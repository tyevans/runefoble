"""Shared fixtures and constants for Silo S3 Media Asset Bucket blackbox test suites.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python Bounded Contexts
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from gateway_api.main import set_event_bus
from runefoble_platform.storage import get_storage_service

# Sample 1x1 PNG bytes for testing image uploads
PNG_SAMPLE_BYTES: bytes = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02"
    b"\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Sample WAV audio bytes for testing audio uploads
WAV_SAMPLE_BYTES: bytes = (
    b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00"
    b"\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
)


@pytest.fixture
def clean_storage_and_bus() -> Generator[None]:
    """Ensure isolated storage and bus states for each blackbox test."""
    storage = get_storage_service()
    storage.clear()
    set_event_bus(None)
    yield
    storage.clear()
    set_event_bus(None)
