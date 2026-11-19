"""Shared-world routes for caravan contracts, proxied to game_session (TASK-0807).

The gateway verifies the bearer token, then forwards the request with that same token.
game_session checks every object permission (ADR-0001, ADR-0015). The gateway holds no
contract, ledger, or outpost state. It returns no canned payloads.

Reads use `forward_json`. Writes use `forward_bytes`. The owner validates each request body,
and the gateway does not import the owner's request models (import-linter contract).
Each route is a row in `ROUTES` (TASK-0822).
"""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes

GAME_SESSION = "game_session"
CONTRACTS_PREFIX = ("api", "v1", "shared-worlds")
CONTRACTS = (*CONTRACTS_PREFIX, "{shared_world_id}", "caravans", "contracts")

router = APIRouter(tags=["Caravan Contracts"])

ROUTES = (
    ProxyRoute(
        "POST",
        "/api/v1/shared-worlds",
        CONTRACTS_PREFIX,
        GAME_SESSION,
        name="create_shared_world_gateway",
        doc="Found a shared world in game_session. The caller becomes its guild officer there.",
        reply="bytes",
        body="raw",
        returns="response",
        principal=True,
        status_code=201,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts",
        CONTRACTS,
        GAME_SESSION,
        name="list_caravan_contracts_gateway",
        doc=(
            "List notice board contracts in game_session (owner checks `view` on the shared world)."
        ),
        query_all=True,
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts",
        CONTRACTS,
        GAME_SESSION,
        name="post_caravan_contract_gateway",
        doc="Post a contract to the notice board in game_session (owner checks `trade`).",
        reply="bytes",
        body="raw",
        returns="response",
        principal=True,
        status_code=201,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}",
        (*CONTRACTS, "{contract_id}"),
        GAME_SESSION,
        name="get_caravan_contract_gateway",
        doc="Read one contract in game_session (owner checks `view` on the contract).",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/accept",
        (*CONTRACTS, "{contract_id}", "accept"),
        GAME_SESSION,
        name="accept_caravan_contract_gateway",
        doc="Accept an open contract for a party in game_session (owner checks `claim`).",
        reply="bytes",
        body="raw",
        returns="response",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/dispatch",
        (*CONTRACTS, "{contract_id}", "dispatch"),
        GAME_SESSION,
        name="dispatch_caravan_contract_gateway",
        doc="Dispatch the caravan of an accepted contract in game_session (owner checks `claim`).",
        reply="bytes",
        body="raw",
        returns="response",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/ambush",
        (*CONTRACTS, "{contract_id}", "ambush"),
        GAME_SESSION,
        name="report_caravan_ambush_gateway",
        doc="Report an ambush outcome in transit in game_session (owner checks `claim`).",
        reply="bytes",
        body="raw",
        returns="response",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/fulfill",
        (*CONTRACTS, "{contract_id}", "fulfill"),
        GAME_SESSION,
        name="fulfill_caravan_contract_gateway",
        doc="Deliver cargo and pay the reward in game_session (owner checks `fulfill`).",
        reply="bytes",
        body="raw",
        returns="response",
        principal=True,
    ),
)

register_proxy_routes(router, ROUTES)
