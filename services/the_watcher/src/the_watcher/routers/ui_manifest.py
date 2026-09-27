"""Microfrontend manifest router for The Watcher service."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["Microfrontends"])

UI_MANIFEST: dict[str, Any] = {
    "service": "the_watcher",
    "package": "@runefoble/the-watcher-ui",
    "version": "0.1.0",
    "components": [
        "runefoble-watcher-feed",
        "runefoble-autonomous-dm",
        "runefoble-dm-whisper-bar",
        "runefoble-faction-radar",
        "runefoble-faction-espionage",
    ],
    "tags": [
        "runefoble-watcher-feed",
        "runefoble-autonomous-dm",
        "runefoble-dm-whisper-bar",
        "runefoble-faction-radar",
        "runefoble-faction-espionage",
    ],
}


@router.get("/ui/manifest")
@router.get("/the-watcher/ui/manifest")
def get_ui_manifest() -> dict[str, Any]:
    """Advertise vendored microfrontend components for The Watcher."""
    return UI_MANIFEST
