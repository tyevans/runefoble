"""Gateway proxy for media asset routes owned by asset_forge (TASK-0595).

The gateway relays the upload body (multipart, JSON, or raw bytes), the query string, and
the caller's bearer token. asset_forge verifies the token, checks `campaign.play` and
`forged_asset.manage` through SpiceDB, stores bytes in Silo, and publishes the events. The
gateway keeps no asset index and writes no ownership tuple. Paths match the owner's public paths.
Each route is a row in `ROUTES` (TASK-0822).
"""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes

ASSET_SERVICE = "asset_forge"
# An upload carries the whole image or audio file, so it gets more time than a read.
ASSET_TIMEOUT_S = 60.0

router = APIRouter(tags=["Assets"])

ROUTES = (
    ProxyRoute(
        "POST",
        "/api/v1/assets/upload",
        ("api", "v1", "assets", "upload"),
        ASSET_SERVICE,
        name="upload_asset",
        doc="Store a media asset in Silo. asset_forge checks `campaign.play` when a campaign is named.",
        reply="bytes",
        returns="response",
        body="raw",
        query_all=True,
        timeout=ASSET_TIMEOUT_S,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/assets/{asset_id}",
        ("api", "v1", "assets", "{asset_id}"),
        ASSET_SERVICE,
        name="get_asset",
        doc="Return asset metadata, or the raw bytes with `stream=true` or `download=true`.",
        reply="bytes",
        returns="response",
        query_all=True,
        timeout=ASSET_TIMEOUT_S,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/assets/{asset_id}/stream",
        ("api", "v1", "assets", "{asset_id}", "stream"),
        ASSET_SERVICE,
        name="stream_asset",
        doc="Stream the raw bytes of an asset inline.",
        reply="bytes",
        returns="response",
        query_all=True,
        timeout=ASSET_TIMEOUT_S,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/assets/{asset_id}/download",
        ("api", "v1", "assets", "{asset_id}", "download"),
        ASSET_SERVICE,
        name="download_asset",
        doc="Download the raw bytes of an asset as an attachment.",
        reply="bytes",
        returns="response",
        query_all=True,
        timeout=ASSET_TIMEOUT_S,
    ),
    ProxyRoute(
        "DELETE",
        "/api/v1/assets/{asset_id}",
        ("api", "v1", "assets", "{asset_id}"),
        ASSET_SERVICE,
        name="delete_asset",
        doc="Delete an asset. asset_forge checks `forged_asset.manage` and refuses a missing bearer.",
        reply="bytes",
        returns="response",
        query_all=True,
        timeout=ASSET_TIMEOUT_S,
    ),
)

register_proxy_routes(router, ROUTES)
