"""Gateway proxy for the wardrobe and active-portrait routes owned by character_sheet (TASK-0444).

Each route relays the caller's bearer token to character_sheet. character_sheet verifies the
token and checks `view` (reads) or `edit` (writes) on the character itself (ADR-0001, ADR-0015 c).
The gateway keeps no wardrobe or portrait state and adds no permission check. The owner's 401,
403, 404 and 4xx answers pass through. An unreachable owner returns 503, and an owner 5xx returns
502 (ADR-0015 b).

Decision: kept in owner. The gateway does not check SpiceDB for these routes.
Each route is a row in `ROUTES` (TASK-0822).
"""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.character_models import AddWardrobeVariantRequest, UpdatePortraitRequest
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes

CHARACTER_SHEET_SERVICE = "character_sheet"

router = APIRouter(tags=["characters-wardrobe"])

ROUTES = (
    ProxyRoute(
        "GET",
        "/api/v1/characters/{character_id}/wardrobe",
        ("api", "v1", "characters", "{character_id}", "wardrobe"),
        CHARACTER_SHEET_SERVICE,
        name="get_character_wardrobe",
        doc="List the unlocked wardrobe variants of a character. character_sheet checks `view`.",
    ),
    ProxyRoute(
        "POST",
        "/api/v1/characters/{character_id}/wardrobe",
        ("api", "v1", "characters", "{character_id}", "wardrobe"),
        CHARACTER_SHEET_SERVICE,
        name="add_character_wardrobe_variant",
        doc="Add a synthesized or unlocked wardrobe variant. character_sheet checks `edit`.",
        body="json",
        body_model=AddWardrobeVariantRequest,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/characters/{character_id}/portrait/active",
        ("api", "v1", "characters", "{character_id}", "portrait", "active"),
        CHARACTER_SHEET_SERVICE,
        name="set_character_active_portrait",
        doc="Switch the active portrait to a wardrobe variant or a custom image. Checks `edit`.",
        body="json",
        body_model=UpdatePortraitRequest,
    ),
)

register_proxy_routes(router, ROUTES)
