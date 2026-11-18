"""Gateway proxy for media asset routes owned by asset_forge (TASK-0595).

The gateway relays the upload body (multipart, JSON, or raw bytes), the query string, and
the caller's bearer token. asset_forge verifies the token, checks `campaign.play` and
`forged_asset.manage` through SpiceDB, stores bytes in Silo, and publishes the events. The
gateway keeps no asset index and writes no ownership tuple. Paths match the owner's public paths.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from gateway_api.proxy import forward_bytes
from runefoble_platform.service_client import path

router = APIRouter(tags=["Assets"])

ASSET_SERVICE = "asset_forge"
# An upload carries the whole image or audio file, so it gets more time than a read.
ASSET_TIMEOUT_S = 60.0


@router.post("/api/v1/assets/upload")
async def upload_asset(request: Request) -> Response:
    """Store a media asset in Silo. asset_forge checks `campaign.play` when a campaign is named."""
    return await _forward(request, "POST", path("api", "v1", "assets", "upload"))


@router.get("/api/v1/assets/{asset_id}")
async def get_asset(asset_id: str, request: Request) -> Response:
    """Return asset metadata, or the raw bytes with `stream=true` or `download=true`."""
    return await _forward(request, "GET", path("api", "v1", "assets", asset_id))


@router.get("/api/v1/assets/{asset_id}/stream")
async def stream_asset(asset_id: str, request: Request) -> Response:
    """Stream the raw bytes of an asset inline."""
    return await _forward(request, "GET", path("api", "v1", "assets", asset_id, "stream"))


@router.get("/api/v1/assets/{asset_id}/download")
async def download_asset(asset_id: str, request: Request) -> Response:
    """Download the raw bytes of an asset as an attachment."""
    return await _forward(request, "GET", path("api", "v1", "assets", asset_id, "download"))


@router.delete("/api/v1/assets/{asset_id}")
async def delete_asset(asset_id: str, request: Request) -> Response:
    """Delete an asset. asset_forge checks `forged_asset.manage` and refuses a missing bearer."""
    return await _forward(request, "DELETE", path("api", "v1", "assets", asset_id))


async def _forward(request: Request, method: str, owner_path: str) -> Response:
    return await forward_bytes(
        request,
        service=ASSET_SERVICE,
        method=method,
        path=owner_path,
        params=dict(request.query_params),
        timeout=ASSET_TIMEOUT_S,
    )


__all__ = ["router"]
