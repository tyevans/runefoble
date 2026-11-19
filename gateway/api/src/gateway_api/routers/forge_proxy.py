"""Gateway proxy for the asset forge routes owned by asset_forge (TASK-0595).

Each route relays the request body and the caller's bearer token to asset_forge. asset_forge
verifies the token and checks `campaign.play` or `forged_asset.view` itself (ADR-0001, ADR-0015 c).
The gateway keeps no forge state, adds no permission check, and does not parse the payload.
Binary replies (PNG, PDF, STL) pass through with their content type and body bytes.
Each route is a row in `ROUTES` (TASK-0822).
"""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes

FORGE_SERVICE = "asset_forge"
# Procedural generation and PDF or STL export can take longer than a plain CRUD call.
FORGE_TIMEOUT_S = 60.0

router = APIRouter(tags=["Asset Forge"])

ROUTES = (
    ProxyRoute(
        "POST",
        "/api/v1/forge/battlemap",
        ("api", "v1", "forge", "battlemap"),
        FORGE_SERVICE,
        name="forge_battlemap",
        doc="Generate a procedural battlemap. asset_forge checks `campaign.play`.",
        reply="bytes",
        returns="response",
        body="raw",
        timeout=FORGE_TIMEOUT_S,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/forge/battlemap/{asset_id}",
        ("api", "v1", "forge", "battlemap", "{asset_id}"),
        FORGE_SERVICE,
        name="read_battlemap",
        doc="Read a forged battlemap. asset_forge checks `forged_asset.view`.",
        reply="bytes",
        returns="response",
        timeout=FORGE_TIMEOUT_S,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/forge/token",
        ("api", "v1", "forge", "token"),
        FORGE_SERVICE,
        name="forge_token",
        doc="Generate a circular token portrait. asset_forge checks `campaign.play`.",
        reply="bytes",
        returns="response",
        body="raw",
        timeout=FORGE_TIMEOUT_S,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/forge/token/{asset_id}",
        ("api", "v1", "forge", "token", "{asset_id}"),
        FORGE_SERVICE,
        name="read_token",
        doc="Read a forged token. asset_forge checks `forged_asset.view`.",
        reply="bytes",
        returns="response",
        timeout=FORGE_TIMEOUT_S,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/forge/wardrobe",
        ("api", "v1", "forge", "wardrobe"),
        FORGE_SERVICE,
        name="forge_wardrobe",
        doc="Generate a wardrobe variant. asset_forge checks `campaign.play`.",
        reply="bytes",
        returns="response",
        body="raw",
        timeout=FORGE_TIMEOUT_S,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/forge/wardrobe/{variant_id}",
        ("api", "v1", "forge", "wardrobe", "{variant_id}"),
        FORGE_SERVICE,
        name="read_wardrobe",
        doc="Read a wardrobe variant. asset_forge checks `forged_asset.view`.",
        reply="bytes",
        returns="response",
        timeout=FORGE_TIMEOUT_S,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/forge/print-pdf",
        ("api", "v1", "forge", "print-pdf"),
        FORGE_SERVICE,
        name="forge_print_pdf",
        doc="Export a 1-inch grid print PDF. asset_forge checks `campaign.play`.",
        reply="bytes",
        returns="response",
        body="raw",
        timeout=FORGE_TIMEOUT_S,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/forge/standees",
        ("api", "v1", "forge", "standees"),
        FORGE_SERVICE,
        name="forge_standees",
        doc="Export folding papercraft standee sheets. asset_forge checks `campaign.play`.",
        reply="bytes",
        returns="response",
        body="raw",
        timeout=FORGE_TIMEOUT_S,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/forge/stl-token",
        ("api", "v1", "forge", "stl-token"),
        FORGE_SERVICE,
        name="forge_stl_token",
        doc="Export a watertight STL token ring. asset_forge checks `campaign.play`.",
        reply="bytes",
        returns="response",
        body="raw",
        timeout=FORGE_TIMEOUT_S,
    ),
)

register_proxy_routes(router, ROUTES)
