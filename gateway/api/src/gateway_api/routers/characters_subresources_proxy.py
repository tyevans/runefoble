"""Character health, equipment, inventory and condition routes proxied to character_sheet (TASK-0586).

The gateway keeps the public paths and verifies the caller's bearer token on each route. It forwards
that token, so character_sheet checks `edit` on the character and applies the change. The gateway
holds no character state and returns no substitute value. A failed upstream call returns the
mapping in `upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.

Spells and guardrails are in `characters_spells_guardrails_proxy.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from gateway_api.auth import get_principal
from gateway_api.character_models import (
    AddInventoryItemRequest,
    ApplyConditionRequest,
    CharacterResponse,
    EquipItemRequest,
    HealthChangeRequest,
)
from gateway_api.character_view import forward_character_state
from gateway_api.proxy import owner_route
from runefoble_platform.service_client import owner_routes

router = APIRouter(tags=["characters-subresources"])

_VERIFIED = [Depends(get_principal)]


@router.post(
    "/api/v1/characters/{character_id}/health",
    response_model=CharacterResponse,
    dependencies=_VERIFIED,
)
async def modify_health(
    character_id: str, req: HealthChangeRequest, request: Request
) -> CharacterResponse:
    """Change HP. character_sheet checks `edit` (or the service credential) and stabilizes at 0 HP."""
    route = owner_route(owner_routes.change_health, character_id)
    return await forward_character_state(
        request, route.method, route.path, req.model_dump(exclude_unset=True)
    )


@router.post(
    "/api/v1/characters/{character_id}/equipment",
    response_model=CharacterResponse,
    dependencies=_VERIFIED,
)
async def equip_item(
    character_id: str, req: EquipItemRequest, request: Request
) -> CharacterResponse:
    """Equip an item into a slot. character_sheet checks `edit`."""
    route = owner_route(owner_routes.equip_item, character_id)
    return await forward_character_state(
        request, route.method, route.path, req.model_dump(exclude_unset=True)
    )


@router.delete(
    "/api/v1/characters/{character_id}/equipment/{slot}",
    response_model=CharacterResponse,
    dependencies=_VERIFIED,
)
async def unequip_item(character_id: str, slot: str, request: Request) -> CharacterResponse:
    """Clear an equipment slot. character_sheet checks `edit`."""
    route = owner_route(owner_routes.unequip_item, character_id, slot)
    return await forward_character_state(request, route.method, route.path)


@router.post(
    "/api/v1/characters/{character_id}/inventory",
    response_model=CharacterResponse,
    dependencies=_VERIFIED,
)
async def add_inventory(
    character_id: str, req: AddInventoryItemRequest, request: Request
) -> CharacterResponse:
    """Add an item to the inventory. character_sheet checks `edit`."""
    route = owner_route(owner_routes.add_inventory_item, character_id)
    return await forward_character_state(
        request, route.method, route.path, req.model_dump(exclude_unset=True)
    )


@router.delete(
    "/api/v1/characters/{character_id}/inventory/{item_id}",
    response_model=CharacterResponse,
    dependencies=_VERIFIED,
)
async def remove_inventory(
    character_id: str, item_id: str, request: Request, quantity: int = 1
) -> CharacterResponse:
    """Remove or decrement an inventory item. character_sheet checks `edit`."""
    route = owner_route(owner_routes.remove_inventory_item, character_id, item_id)
    return await forward_character_state(
        request, route.method, route.path, params={"quantity": str(quantity)}
    )


@router.post(
    "/api/v1/characters/{character_id}/conditions",
    response_model=CharacterResponse,
    dependencies=_VERIFIED,
)
async def apply_condition(
    character_id: str, req: ApplyConditionRequest, request: Request
) -> CharacterResponse:
    """Apply a tactical condition. character_sheet checks `edit` (or the service credential)."""
    route = owner_route(owner_routes.apply_condition, character_id)
    return await forward_character_state(
        request, route.method, route.path, req.model_dump(exclude_unset=True)
    )


@router.delete(
    "/api/v1/characters/{character_id}/conditions/{condition}",
    response_model=CharacterResponse,
    dependencies=_VERIFIED,
)
async def remove_condition(
    character_id: str, condition: str, request: Request
) -> CharacterResponse:
    """Clear a tactical condition. character_sheet checks `edit`."""
    route = owner_route(owner_routes.remove_condition, character_id, condition)
    return await forward_character_state(request, route.method, route.path)
