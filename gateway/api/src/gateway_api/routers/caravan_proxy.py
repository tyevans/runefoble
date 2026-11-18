"""Shared-world routes for caravan contracts, proxied to game_session (TASK-0807).

The gateway verifies the bearer token, then forwards the request with that same token.
game_session checks every object permission (ADR-0001, ADR-0015). The gateway holds no
contract, ledger, or outpost state. It returns no canned payloads.

Reads use `forward_json`. Writes use `forward_bytes`. The owner validates each request body,
and the gateway does not import the owner's request models (import-linter contract).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response
from gateway_api.auth import CallerPrincipal
from gateway_api.proxy import forward_bytes, forward_json
from runefoble_platform.service_client import path

GAME_SESSION = "game_session"
CONTRACTS_PREFIX = ("api", "v1", "shared-worlds")

router = APIRouter(tags=["Caravan Contracts"])


@router.post("/api/v1/shared-worlds", status_code=201)
async def create_shared_world_gateway(request: Request, user: CallerPrincipal) -> Response:
    """Found a shared world in game_session. The caller becomes its guild officer there."""
    return await forward_bytes(
        request,
        service=GAME_SESSION,
        method="POST",
        path=path(*CONTRACTS_PREFIX),
    )


@router.get("/api/v1/shared-worlds/{shared_world_id}/caravans/contracts")
async def list_caravan_contracts_gateway(
    shared_world_id: str, request: Request, user: CallerPrincipal
) -> Any:
    """List notice board contracts in game_session (owner checks `view` on the shared world)."""
    return await forward_json(
        request,
        service=GAME_SESSION,
        method="GET",
        path=path(*CONTRACTS_PREFIX, shared_world_id, "caravans", "contracts"),
        params=dict(request.query_params),
    )


@router.post("/api/v1/shared-worlds/{shared_world_id}/caravans/contracts", status_code=201)
async def post_caravan_contract_gateway(
    shared_world_id: str, request: Request, user: CallerPrincipal
) -> Response:
    """Post a contract to the notice board in game_session (owner checks `trade`)."""
    return await forward_bytes(
        request,
        service=GAME_SESSION,
        method="POST",
        path=path(*CONTRACTS_PREFIX, shared_world_id, "caravans", "contracts"),
    )


@router.get("/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}")
async def get_caravan_contract_gateway(
    shared_world_id: str, contract_id: str, request: Request, user: CallerPrincipal
) -> Any:
    """Read one contract in game_session (owner checks `view` on the contract)."""
    return await forward_json(
        request,
        service=GAME_SESSION,
        method="GET",
        path=path(*CONTRACTS_PREFIX, shared_world_id, "caravans", "contracts", contract_id),
    )


@router.post("/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/accept")
async def accept_caravan_contract_gateway(
    shared_world_id: str, contract_id: str, request: Request, user: CallerPrincipal
) -> Response:
    """Accept an open contract for a party in game_session (owner checks `claim`)."""
    return await _post_contract_action(shared_world_id, contract_id, "accept", request)


@router.post("/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/dispatch")
async def dispatch_caravan_contract_gateway(
    shared_world_id: str, contract_id: str, request: Request, user: CallerPrincipal
) -> Response:
    """Dispatch the caravan of an accepted contract in game_session (owner checks `claim`)."""
    return await _post_contract_action(shared_world_id, contract_id, "dispatch", request)


@router.post("/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/ambush")
async def report_caravan_ambush_gateway(
    shared_world_id: str, contract_id: str, request: Request, user: CallerPrincipal
) -> Response:
    """Report an ambush outcome in transit in game_session (owner checks `claim`)."""
    return await _post_contract_action(shared_world_id, contract_id, "ambush", request)


@router.post("/api/v1/shared-worlds/{shared_world_id}/caravans/contracts/{contract_id}/fulfill")
async def fulfill_caravan_contract_gateway(
    shared_world_id: str, contract_id: str, request: Request, user: CallerPrincipal
) -> Response:
    """Deliver cargo and pay the reward in game_session (owner checks `fulfill`)."""
    return await _post_contract_action(shared_world_id, contract_id, "fulfill", request)


async def _post_contract_action(
    shared_world_id: str, contract_id: str, action: str, request: Request
) -> Response:
    return await forward_bytes(
        request,
        service=GAME_SESSION,
        method="POST",
        path=path(*CONTRACTS_PREFIX, shared_world_id, "caravans", "contracts", contract_id, action),
    )
