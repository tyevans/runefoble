"""Rules compendium routes proxied to rules_compendium, which owns rules, encounters and homebrew (TASK-0594).

The gateway verifies the bearer token, then forwards the request with that same token. The owner
validates each body and checks every permission (SpiceDB Zanzibar, ADR-0001). The gateway writes
no tuple and keeps no rule, encounter or homebrew state. A failed upstream call returns the mapping
in `upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.

Each route is a row in `ROUTES` (TASK-0822).
"""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes
from runefoble_platform.service_client import owner_routes

COMPENDIUM_SERVICE = "rules_compendium"

router = APIRouter(tags=["Rules Compendium"])

ROUTES = (
    ProxyRoute(
        "GET",
        "/api/v1/compendium/rules/search",
        ("api", "v1", "compendium", "rules", "search"),
        COMPENDIUM_SERVICE,
        name="search_rules",
        doc="Hybrid rule search. The query string reaches the owner unchanged.",
        query_all=True,
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/compendium/monsters/{name}",
        (),
        COMPENDIUM_SERVICE,
        name="get_monster",
        doc="Monster stat block by name. A `campaign_id` query value reaches the owner unchanged.",
        owner=owner_routes.get_monster,
        query_all=True,
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/compendium/spells/{name}",
        ("api", "v1", "compendium", "spells", "{name}"),
        COMPENDIUM_SERVICE,
        name="get_spell",
        doc="Spell definition by name.",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/compendium/conditions/{name}",
        ("api", "v1", "compendium", "conditions", "{name}"),
        COMPENDIUM_SERVICE,
        name="get_condition",
        doc="Condition mechanics by name.",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/compendium/encounters/balance",
        (),
        COMPENDIUM_SERVICE,
        name="balance_encounter",
        doc="Balance an encounter for a party roster. A campaign-scoped call needs `campaign.play`.",
        owner=owner_routes.balance_encounter,
        reply="bytes",
        body="raw",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/compendium/homebrew",
        ("api", "v1", "compendium", "homebrew"),
        COMPENDIUM_SERVICE,
        name="register_homebrew",
        doc="Register a campaign homebrew rule. The owner checks `manage` or `run_session`.",
        reply="bytes",
        body="raw",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/compendium/homebrew/{campaign_id}",
        ("api", "v1", "compendium", "homebrew", "{campaign_id}"),
        COMPENDIUM_SERVICE,
        name="list_homebrew",
        doc="List the campaign homebrew rules the caller may view. The owner filters them.",
        principal=True,
    ),
)

register_proxy_routes(router, ROUTES)
