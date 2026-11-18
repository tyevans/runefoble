"""Gateway proxy for the asset forge routes owned by asset_forge (TASK-0595).

Each route relays the request body and the caller's bearer token to asset_forge. asset_forge
verifies the token and checks `campaign.play` or `forged_asset.view` itself (ADR-0001, ADR-0015 c).
The gateway keeps no forge state, adds no permission check, and does not parse the payload.
Binary replies (PNG, PDF, STL) pass through with their content type and body bytes.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from gateway_api.proxy import forward_bytes
from runefoble_platform.service_client import path

router = APIRouter(tags=["Asset Forge"])

FORGE_SERVICE = "asset_forge"
# Procedural generation and PDF or STL export can take longer than a plain CRUD call.
FORGE_TIMEOUT_S = 60.0


@router.post("/api/v1/forge/battlemap")
async def forge_battlemap(request: Request) -> Response:
    """Generate a procedural battlemap. asset_forge checks `campaign.play`."""
    return await _forward(request, "POST", path("api", "v1", "forge", "battlemap"))


@router.get("/api/v1/forge/battlemap/{asset_id}")
async def read_battlemap(asset_id: str, request: Request) -> Response:
    """Read a forged battlemap. asset_forge checks `forged_asset.view`."""
    return await _forward(request, "GET", path("api", "v1", "forge", "battlemap", asset_id))


@router.post("/api/v1/forge/token")
async def forge_token(request: Request) -> Response:
    """Generate a circular token portrait. asset_forge checks `campaign.play`."""
    return await _forward(request, "POST", path("api", "v1", "forge", "token"))


@router.get("/api/v1/forge/token/{asset_id}")
async def read_token(asset_id: str, request: Request) -> Response:
    """Read a forged token. asset_forge checks `forged_asset.view`."""
    return await _forward(request, "GET", path("api", "v1", "forge", "token", asset_id))


@router.post("/api/v1/forge/wardrobe")
async def forge_wardrobe(request: Request) -> Response:
    """Generate a wardrobe variant. asset_forge checks `campaign.play`."""
    return await _forward(request, "POST", path("api", "v1", "forge", "wardrobe"))


@router.get("/api/v1/forge/wardrobe/{variant_id}")
async def read_wardrobe(variant_id: str, request: Request) -> Response:
    """Read a wardrobe variant. asset_forge checks `forged_asset.view`."""
    return await _forward(request, "GET", path("api", "v1", "forge", "wardrobe", variant_id))


@router.post("/api/v1/forge/print-pdf")
async def forge_print_pdf(request: Request) -> Response:
    """Export a 1-inch grid print PDF. asset_forge checks `campaign.play`."""
    return await _forward(request, "POST", path("api", "v1", "forge", "print-pdf"))


@router.post("/api/v1/forge/standees")
async def forge_standees(request: Request) -> Response:
    """Export folding papercraft standee sheets. asset_forge checks `campaign.play`."""
    return await _forward(request, "POST", path("api", "v1", "forge", "standees"))


@router.post("/api/v1/forge/stl-token")
async def forge_stl_token(request: Request) -> Response:
    """Export a watertight STL token ring. asset_forge checks `campaign.play`."""
    return await _forward(request, "POST", path("api", "v1", "forge", "stl-token"))


async def _forward(request: Request, method: str, owner_path: str) -> Response:
    return await forward_bytes(
        request,
        service=FORGE_SERVICE,
        method=method,
        path=owner_path,
        timeout=FORGE_TIMEOUT_S,
    )


__all__ = ["router"]
