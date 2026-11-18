"""Microfrontend manifest router for The Watcher service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from runefoble_platform.ui_manifest import load_ui_manifest

router = APIRouter(tags=["Microfrontends"])

# Start-up fails when the manifest is missing or invalid. No fallback manifest exists (ADR-0015 4).
UI_MANIFEST: dict[str, Any] = load_ui_manifest(
    Path(__file__).resolve().parents[3] / "ui" / "manifest.json"
)


@router.get("/ui/manifest")
@router.get("/the-watcher/ui/manifest")
def get_ui_manifest() -> dict[str, Any]:
    """Advertise vendored microfrontend components for The Watcher."""
    return UI_MANIFEST
