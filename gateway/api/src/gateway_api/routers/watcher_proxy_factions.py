"""Faction, world tick, and region routes proxied to The Watcher (TASK-0596).

The gateway verifies the bearer token and forwards each request with that token. The owner
checks `campaign.run_session`, `campaign.view`, and faction permissions (ADR-0001). The world
tick takes an optional JSON body. The gateway forwards a request that has none, as the owner
expects. Each route is a row in `ROUTES` (TASK-0822).
"""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes

SERVICE = "the_watcher"

router = APIRouter(tags=["The Watcher"])

ROUTES = (
    ProxyRoute(
        "POST",
        "/api/v1/campaigns/{campaign_id}/world-tick",
        ("api", "v1", "campaigns", "{campaign_id}", "world-tick"),
        SERVICE,
        name="watcher_world_tick",
        doc="Advance the campaign's NPC factions and issue the DM bulletin (The Watcher).",
        body="json",
        body_optional=True,
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/campaigns/{campaign_id}/factions",
        ("api", "v1", "campaigns", "{campaign_id}", "factions"),
        SERVICE,
        name="watcher_create_faction",
        doc="Register an autonomous NPC faction in a campaign (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/campaigns/{campaign_id}/factions",
        ("api", "v1", "campaigns", "{campaign_id}", "factions"),
        SERVICE,
        name="watcher_list_factions",
        doc="List the NPC factions of a campaign (The Watcher).",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/campaigns/{campaign_id}/factions/{faction_id}",
        ("api", "v1", "campaigns", "{campaign_id}", "factions", "{faction_id}"),
        SERVICE,
        name="watcher_get_faction",
        doc="Read the state of one NPC faction (The Watcher).",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/campaigns/{campaign_id}/world-ticks/latest",
        ("api", "v1", "campaigns", "{campaign_id}", "world-ticks", "latest"),
        SERVICE,
        name="watcher_latest_world_tick",
        doc="Read the latest DM bulletin and geopolitical state (The Watcher).",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/factions/{faction_id}/resources/adjust",
        ("api", "v1", "factions", "{faction_id}", "resources", "adjust"),
        SERVICE,
        name="watcher_adjust_faction_resources",
        doc="Adjust a faction's treasury or contraband (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/factions/{faction_id}/bribery/resolve",
        ("api", "v1", "factions", "{faction_id}", "bribery", "resolve"),
        SERVICE,
        name="watcher_resolve_bribery",
        doc="Resolve a bribery attempt against a target faction (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/factions/{faction_id}/mercenaries/recruit",
        ("api", "v1", "factions", "{faction_id}", "mercenaries", "recruit"),
        SERVICE,
        name="watcher_recruit_mercenaries",
        doc="Recruit mercenaries against a faction's treasury (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/factions/{faction_id}/resources",
        ("api", "v1", "factions", "{faction_id}", "resources"),
        SERVICE,
        name="watcher_get_faction_resources",
        doc="Read a faction's treasury, contraband, and mercenaries (The Watcher).",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/factions/skirmish/simulate",
        ("api", "v1", "factions", "skirmish", "simulate"),
        SERVICE,
        name="watcher_simulate_skirmish",
        doc="Simulate a skirmish on a faction boundary and update territory (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/regions/{region_id}/unrest",
        ("api", "v1", "regions", "{region_id}", "unrest"),
        SERVICE,
        name="watcher_get_region_unrest",
        doc="Read a region's unrest score and security posture (The Watcher).",
        principal=True,
    ),
)

register_proxy_routes(router, ROUTES)
