"""Rules compendium routes proxied to rules_compendium, which owns rules, encounters and homebrew (TASK-0594).

The gateway verifies the bearer token, then forwards the request with that same token. The owner
validates each body and checks every permission (SpiceDB Zanzibar, ADR-0001). The gateway writes
no tuple and keeps no rule, encounter or homebrew state. A failed upstream call returns the mapping
in `upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from gateway_api.auth import CurrentPrincipal
from gateway_api.proxy import forward_bytes, forward_json
from runefoble_platform.service_client import path

COMPENDIUM_SERVICE = "rules_compendium"

router = APIRouter(tags=["Rules Compendium"])


@router.get("/api/v1/compendium/rules/search")
async def search_rules(request: Request, user: CurrentPrincipal) -> Any:
    """Hybrid rule search. The query string reaches the owner unchanged."""
    return await forward_json(
        request,
        service=COMPENDIUM_SERVICE,
        method="GET",
        path=path("api", "v1", "compendium", "rules", "search"),
        params=dict(request.query_params),
    )


@router.get("/api/v1/compendium/monsters/{name}")
async def get_monster(name: str, request: Request, user: CurrentPrincipal) -> Any:
    """Monster stat block by name. A `campaign_id` query value reaches the owner unchanged."""
    return await forward_json(
        request,
        service=COMPENDIUM_SERVICE,
        method="GET",
        path=path("api", "v1", "compendium", "monsters", name),
        params=dict(request.query_params),
    )


@router.get("/api/v1/compendium/spells/{name}")
async def get_spell(name: str, request: Request, user: CurrentPrincipal) -> Any:
    """Spell definition by name."""
    return await forward_json(
        request,
        service=COMPENDIUM_SERVICE,
        method="GET",
        path=path("api", "v1", "compendium", "spells", name),
    )


@router.get("/api/v1/compendium/conditions/{name}")
async def get_condition(name: str, request: Request, user: CurrentPrincipal) -> Any:
    """Condition mechanics by name."""
    return await forward_json(
        request,
        service=COMPENDIUM_SERVICE,
        method="GET",
        path=path("api", "v1", "compendium", "conditions", name),
    )


@router.post("/api/v1/compendium/encounters/balance")
async def balance_encounter(request: Request, user: CurrentPrincipal) -> Any:
    """Balance an encounter for a party roster. A campaign-scoped call needs `campaign.play`."""
    return await forward_bytes(
        request,
        service=COMPENDIUM_SERVICE,
        method="POST",
        path=path("api", "v1", "compendium", "encounters", "balance"),
    )


@router.post("/api/v1/compendium/homebrew")
async def register_homebrew(request: Request, user: CurrentPrincipal) -> Any:
    """Register a campaign homebrew rule. The owner checks `manage` or `run_session`."""
    return await forward_bytes(
        request,
        service=COMPENDIUM_SERVICE,
        method="POST",
        path=path("api", "v1", "compendium", "homebrew"),
    )


@router.get("/api/v1/compendium/homebrew/{campaign_id}")
async def list_homebrew(campaign_id: str, request: Request, user: CurrentPrincipal) -> Any:
    """List the campaign homebrew rules the caller may view. The owner filters them."""
    return await forward_json(
        request,
        service=COMPENDIUM_SERVICE,
        method="GET",
        path=path("api", "v1", "compendium", "homebrew", campaign_id),
    )
