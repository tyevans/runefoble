"""Sub-resource APIRouter for character health, equipment, inventory, conditions, and spells."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from gateway_api.auth import require_zanzibar_permission
from gateway_api.character_models import (
    AddInventoryItemRequest,
    ApplyConditionRequest,
    CastSpellRequest,
    CharacterResponse,
    EquipItemRequest,
    HealthChangeRequest,
    PrepareSpellRequest,
    StandInGuardrailsRequest,
)
from gateway_api.character_view import to_character_response
from gateway_api.proxy import forward_json

router = APIRouter(tags=["characters-subresources"])


async def _forward(
    request: Request,
    method: str,
    path: str,
    json_body: Any = None,
    params: dict[str, str] | None = None,
) -> Any:
    return await forward_json(
        request,
        method=method,
        service="character_sheet",
        path=path,
        json_body=json_body,
        params=params,
    )


@router.post(
    "/api/v1/characters/{character_id}/health",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def modify_health(
    character_id: str,
    req: HealthChangeRequest,
    request: Request,
) -> CharacterResponse:
    """Mutate character HP, verify stand-in stabilization (requires 'edit')."""
    res = await _forward(
        request,
        "POST",
        f"/api/v1/characters/{character_id}/health",
        json_body=req.model_dump(exclude_unset=True),
    )
    return to_character_response(res, None)


@router.post(
    "/api/v1/characters/{character_id}/equipment",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def equip_item(
    character_id: str,
    req: EquipItemRequest,
    request: Request,
) -> CharacterResponse:
    """Equip item to slot (requires 'edit')."""
    res = await _forward(
        request,
        "POST",
        f"/api/v1/characters/{character_id}/equipment",
        json_body=req.model_dump(exclude_unset=True),
    )
    return to_character_response(res, None)


@router.delete(
    "/api/v1/characters/{character_id}/equipment/{slot}",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def unequip_item(
    character_id: str,
    slot: str,
    request: Request,
) -> CharacterResponse:
    """Unequip item from slot (requires 'edit')."""
    res = await _forward(request, "DELETE", f"/api/v1/characters/{character_id}/equipment/{slot}")
    return to_character_response(res, None)


@router.post(
    "/api/v1/characters/{character_id}/inventory",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def add_inventory(
    character_id: str,
    req: AddInventoryItemRequest,
    request: Request,
) -> CharacterResponse:
    """Add item to inventory (requires 'edit')."""
    res = await _forward(
        request,
        "POST",
        f"/api/v1/characters/{character_id}/inventory",
        json_body=req.model_dump(exclude_unset=True),
    )
    return to_character_response(res, None)


@router.delete(
    "/api/v1/characters/{character_id}/inventory/{item_id}",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def remove_inventory(
    character_id: str,
    item_id: str,
    request: Request,
    quantity: int = 1,
) -> CharacterResponse:
    """Remove item from inventory (requires 'edit')."""
    res = await _forward(
        request,
        "DELETE",
        f"/api/v1/characters/{character_id}/inventory/{item_id}",
        params={"quantity": str(quantity)},
    )
    return to_character_response(res, None)


@router.post(
    "/api/v1/characters/{character_id}/conditions",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def apply_condition(
    character_id: str,
    req: ApplyConditionRequest,
    request: Request,
) -> CharacterResponse:
    """Apply tactical condition (requires 'edit')."""
    res = await _forward(
        request,
        "POST",
        f"/api/v1/characters/{character_id}/conditions",
        json_body=req.model_dump(exclude_unset=True),
    )
    return to_character_response(res, None)


@router.delete(
    "/api/v1/characters/{character_id}/conditions/{condition}",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def remove_condition(
    character_id: str,
    condition: str,
    request: Request,
) -> CharacterResponse:
    """Remove tactical condition (requires 'edit')."""
    res = await _forward(
        request, "DELETE", f"/api/v1/characters/{character_id}/conditions/{condition}"
    )
    return to_character_response(res, None)


@router.post(
    "/api/v1/characters/{character_id}/spells/cast",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def cast_spell(
    character_id: str,
    req: CastSpellRequest,
    request: Request,
) -> CharacterResponse:
    """Cast spell, deducting slot tier (requires 'edit')."""
    res = await _forward(
        request,
        "POST",
        f"/api/v1/characters/{character_id}/spells/cast",
        json_body=req.model_dump(exclude_unset=True),
    )
    return to_character_response(res, None)


@router.post(
    "/api/v1/characters/{character_id}/spells/prepare",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def prepare_spell(
    character_id: str,
    req: PrepareSpellRequest,
    request: Request,
) -> CharacterResponse:
    """Prepare or unprepare spell (requires 'edit')."""
    res = await _forward(
        request,
        "POST",
        f"/api/v1/characters/{character_id}/spells/prepare",
        json_body=req.model_dump(exclude_unset=True),
    )
    return to_character_response(res, None)


@router.put(
    "/api/v1/characters/{character_id}/guardrails",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def update_guardrails(
    character_id: str,
    req: StandInGuardrailsRequest,
    request: Request,
) -> CharacterResponse:
    """Update stand-in policy guardrails (requires 'edit')."""
    res = await _forward(
        request,
        "PUT",
        f"/api/v1/characters/{character_id}/guardrails",
        json_body=req.model_dump(by_alias=False),
    )
    return to_character_response(res, None)


@router.get(
    "/api/v1/characters/{character_id}/guardrails",
    dependencies=[Depends(require_zanzibar_permission("view", "character", "character_id"))],
)
async def get_guardrails(
    character_id: str,
    request: Request,
) -> dict[str, Any]:
    """Retrieve stand-in policy guardrails (requires 'view')."""
    res = await _forward(request, "GET", f"/api/v1/characters/{character_id}/guardrails")
    return dict(res)
