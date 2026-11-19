"""Blackbox checks for the shared `/ui/manifest` router factory (ADR-0013, ADR-0015 (4)).

The tests build a FastAPI app with the router and call it over HTTP. A missing or
invalid manifest must fail when the app is built, not when a client calls the route.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from runefoble_platform.ui_manifest import UIManifestError, ui_manifest_router

MANIFEST = {
    "service": "example",
    "package": "@runefoble/example-ui",
    "components": ["runefoble-example"],
}


def _write_manifest(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(content, encoding="utf-8")
    return path


def test_router_serves_the_manifest_file(tmp_path: Path) -> None:
    """GET /ui/manifest returns the JSON object in the manifest file."""
    app = FastAPI()
    path = _write_manifest(tmp_path, json.dumps(MANIFEST))
    app.include_router(ui_manifest_router(path, summary="Example manifest"))

    response = TestClient(app).get("/ui/manifest")

    assert response.status_code == 200
    assert response.json() == MANIFEST


def test_router_reads_the_manifest_once_at_build(tmp_path: Path) -> None:
    """A change to the file after the build does not change the response."""
    app = FastAPI()
    path = _write_manifest(tmp_path, json.dumps(MANIFEST))
    app.include_router(ui_manifest_router(path, summary="Example manifest"))
    path.unlink()

    response = TestClient(app).get("/ui/manifest")

    assert response.status_code == 200
    assert response.json() == MANIFEST


def test_router_publishes_the_manifest_operation_in_openapi(tmp_path: Path) -> None:
    """The OpenAPI spec lists GET /ui/manifest with the given summary."""
    app = FastAPI()
    path = _write_manifest(tmp_path, json.dumps(MANIFEST))
    app.include_router(ui_manifest_router(path, summary="Example manifest"))

    spec = TestClient(app).get("/openapi.json").json()

    operation = spec["paths"]["/ui/manifest"]["get"]
    assert operation["summary"] == "Example manifest"
    assert operation["tags"] == ["Microfrontends"]


def test_router_build_fails_when_the_manifest_is_missing(tmp_path: Path) -> None:
    """A missing manifest raises when the router is built."""
    with pytest.raises(UIManifestError, match="UI manifest not found"):
        ui_manifest_router(tmp_path / "missing.json", summary="Example manifest")


def test_router_build_fails_when_the_manifest_is_invalid(tmp_path: Path) -> None:
    """A manifest that is not a JSON object raises when the router is built."""
    path = _write_manifest(tmp_path, "[1, 2]")

    with pytest.raises(UIManifestError, match="must be a JSON object"):
        ui_manifest_router(path, summary="Example manifest")
