"""Settlement haven, establishment, bulletin, and upgrade routes proxied to game_session (TASK-0592).

The gateway verifies the bearer token, then forwards the request with that same token.
game_session verifies the token again and checks every object permission. The gateway keeps
no settlement state and returns no substitute value. A failed upstream call returns the mapping
in `upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.

Only the `/api/v1` paths are proxied. Each route keeps its owner path and method. Each route is a
row in `ROUTES` (TASK-0822). A path segment the owner cannot encode returns 404.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes

SERVICE = "game_session"

router = APIRouter(tags=["Settlements & Establishments"])

ROUTES = (
    ProxyRoute(
        "POST",
        "/api/v1/campaigns/{campaign_id}/settlements",
        ("api", "v1", "campaigns", "{campaign_id}", "settlements"),
        SERVICE,
        name="found_settlement",
        doc="Found a settlement haven in a campaign (game_session checks campaign write).",
        body="json",
        principal=True,
        status_code=status.HTTP_201_CREATED,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/campaigns/{campaign_id}/settlements",
        ("api", "v1", "campaigns", "{campaign_id}", "settlements"),
        SERVICE,
        name="list_campaign_settlements",
        doc="List the settlements of a campaign (game_session checks view).",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/campaigns/{campaign_id}/settlements/{settlement_id}",
        ("api", "v1", "campaigns", "{campaign_id}", "settlements", "{settlement_id}"),
        SERVICE,
        name="get_campaign_settlement",
        doc="Read one settlement projection (game_session checks view).",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/settlements/{settlement_id}/establishments",
        ("api", "v1", "settlements", "{settlement_id}", "establishments"),
        SERVICE,
        name="construct_establishment",
        doc="Construct an establishment in a settlement district (game_session checks upgrade).",
        body="json",
        principal=True,
        status_code=status.HTTP_201_CREATED,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/settlements/{settlement_id}/establishments",
        ("api", "v1", "settlements", "{settlement_id}", "establishments"),
        SERVICE,
        name="list_settlement_establishments",
        doc="List the establishments of a settlement (game_session checks view).",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/establishments/{establishment_id}",
        ("api", "v1", "establishments", "{establishment_id}"),
        SERVICE,
        name="get_establishment",
        doc="Read one establishment (game_session checks view).",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/settlements/{settlement_id}/upgrade-tier",
        ("api", "v1", "settlements", "{settlement_id}", "upgrade-tier"),
        SERVICE,
        name="upgrade_settlement_tier",
        doc="Upgrade a settlement to a higher civic tier (game_session checks upgrade).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/establishments/{establishment_id}/upgrade",
        ("api", "v1", "establishments", "{establishment_id}", "upgrade"),
        SERVICE,
        name="upgrade_establishment",
        doc="Upgrade an establishment tier, amenity, or capacity (game_session checks edit).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/settlements/{settlement_id}/bulletin",
        ("api", "v1", "settlements", "{settlement_id}", "bulletin"),
        SERVICE,
        name="pin_bulletin_notice",
        doc="Pin a notice to the settlement bulletin board (game_session checks the board).",
        body="json",
        principal=True,
        status_code=status.HTTP_201_CREATED,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/settlements/{settlement_id}/bulletin",
        ("api", "v1", "settlements", "{settlement_id}", "bulletin"),
        SERVICE,
        name="list_bulletin_notices",
        doc="List the bulletin notices of a settlement (game_session checks view).",
        principal=True,
    ),
    ProxyRoute(
        "DELETE",
        "/api/v1/settlements/{settlement_id}/bulletin/{notice_id}",
        ("api", "v1", "settlements", "{settlement_id}", "bulletin", "{notice_id}"),
        SERVICE,
        name="remove_bulletin_notice",
        doc="Remove or fulfill a bulletin notice (game_session checks the board).",
        query_defaults=(("reason", "removed"),),
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/settlements/{settlement_id}/bulletin/{notice_id}/decrypt",
        ("api", "v1", "settlements", "{settlement_id}", "bulletin", "{notice_id}", "decrypt"),
        SERVICE,
        name="decrypt_cipher_notice",
        doc="Submit a cipher solution for a hidden bulletin notice (game_session checks the board).",
        body="json",
        principal=True,
    ),
)

register_proxy_routes(router, ROUTES)
