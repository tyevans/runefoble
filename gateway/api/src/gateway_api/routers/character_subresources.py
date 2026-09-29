"""Sub-resource APIRouter for character health, equipment, inventory, conditions, and spells."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from gateway_api.auth import require_zanzibar_permission
from gateway_api.character_models import (
    AddInventoryItemRequest,
    ApplyConditionRequest,
    CastSpellRequest,
    CharacterResponse,
    EquipItemRequest,
    HealthChangeRequest,
    PrepareSpellRequest,
)
from gateway_api.character_store import character_store

router = APIRouter(tags=["characters-subresources"])

CHARACTER_SHEET_URL = os.getenv("CHARACTER_SHEET_URL")


async def proxy_or_fallback(
    method: str,
    path: str,
    fallback_fn: Callable[[], Any],
    json_body: Any = None,
    params: Any = None,
) -> Any:
    if CHARACTER_SHEET_URL:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.request(
                    method,
                    f"{CHARACTER_SHEET_URL}{path}",
                    json=json_body,
                    params=params,
                )
                if res.status_code == 200:
                    return res.json()
        except Exception:
            pass
    return await fallback_fn()


@router.post(
    "/api/v1/characters/{character_id}/health",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def modify_health(
    character_id: str,
    req: HealthChangeRequest,
) -> CharacterResponse:
    """Mutate character HP, verify stand-in stabilization (requires 'edit')."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    async def fallback():
        updated = await character_store.modify_health(
            character_id, req.delta, req.source, req.is_stand_in
        )
        return updated.to_response()

    res = await proxy_or_fallback(
        "POST",
        f"/api/v1/characters/{character_id}/health",
        fallback,
        json_body=req.model_dump(exclude_unset=True),
    )
    return res if isinstance(res, CharacterResponse) else CharacterResponse(**res)


@router.post(
    "/api/v1/characters/{character_id}/equipment",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def equip_item(
    character_id: str,
    req: EquipItemRequest,
) -> CharacterResponse:
    """Equip item to slot (requires 'edit')."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    async def fallback():
        updated = await character_store.equip_item(character_id, req.slot, req.item_name)
        return updated.to_response()

    res = await proxy_or_fallback(
        "POST",
        f"/api/v1/characters/{character_id}/equipment",
        fallback,
        json_body=req.model_dump(exclude_unset=True),
    )
    return res if isinstance(res, CharacterResponse) else CharacterResponse(**res)


@router.delete(
    "/api/v1/characters/{character_id}/equipment/{slot}",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def unequip_item(
    character_id: str,
    slot: str,
) -> CharacterResponse:
    """Unequip item from slot (requires 'edit')."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    async def fallback():
        updated = await character_store.unequip_item(character_id, slot)
        return updated.to_response()

    res = await proxy_or_fallback(
        "DELETE",
        f"/api/v1/characters/{character_id}/equipment/{slot}",
        fallback,
    )
    return res if isinstance(res, CharacterResponse) else CharacterResponse(**res)


@router.post(
    "/api/v1/characters/{character_id}/inventory",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def add_inventory(
    character_id: str,
    req: AddInventoryItemRequest,
) -> CharacterResponse:
    """Add item to inventory (requires 'edit')."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    async def fallback():
        updated = await character_store.add_inventory_item(
            character_id,
            req.name,
            req.quantity,
            req.weight_lbs,
            item_id=req.item_id,
        )
        return updated.to_response()

    res = await proxy_or_fallback(
        "POST",
        f"/api/v1/characters/{character_id}/inventory",
        fallback,
        json_body=req.model_dump(exclude_unset=True),
    )
    return res if isinstance(res, CharacterResponse) else CharacterResponse(**res)


@router.delete(
    "/api/v1/characters/{character_id}/inventory/{item_id}",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def remove_inventory(
    character_id: str,
    item_id: str,
    quantity: int = 1,
) -> CharacterResponse:
    """Remove item from inventory (requires 'edit')."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    async def fallback():
        updated = await character_store.remove_inventory_item(character_id, item_id, quantity)
        return updated.to_response()

    res = await proxy_or_fallback(
        "DELETE",
        f"/api/v1/characters/{character_id}/inventory/{item_id}",
        fallback,
        params={"quantity": quantity},
    )
    return res if isinstance(res, CharacterResponse) else CharacterResponse(**res)


@router.post(
    "/api/v1/characters/{character_id}/conditions",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def apply_condition(
    character_id: str,
    req: ApplyConditionRequest,
) -> CharacterResponse:
    """Apply tactical condition (requires 'edit')."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    async def fallback():
        updated = await character_store.apply_condition(
            character_id, req.condition, req.duration_rounds, req.source
        )
        return updated.to_response()

    res = await proxy_or_fallback(
        "POST",
        f"/api/v1/characters/{character_id}/conditions",
        fallback,
        json_body=req.model_dump(exclude_unset=True),
    )
    return res if isinstance(res, CharacterResponse) else CharacterResponse(**res)


@router.delete(
    "/api/v1/characters/{character_id}/conditions/{condition}",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def remove_condition(
    character_id: str,
    condition: str,
) -> CharacterResponse:
    """Remove tactical condition (requires 'edit')."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    async def fallback():
        updated = await character_store.remove_condition(character_id, condition)
        return updated.to_response()

    res = await proxy_or_fallback(
        "DELETE",
        f"/api/v1/characters/{character_id}/conditions/{condition}",
        fallback,
    )
    return res if isinstance(res, CharacterResponse) else CharacterResponse(**res)


@router.post(
    "/api/v1/characters/{character_id}/spells/cast",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def cast_spell(
    character_id: str,
    req: CastSpellRequest,
) -> CharacterResponse:
    """Cast spell, deducting slot tier (requires 'edit')."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    async def fallback():
        try:
            updated = await character_store.cast_spell(character_id, req.spell_name, req.slot_level)
            return updated.to_response()
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err

    res = await proxy_or_fallback(
        "POST",
        f"/api/v1/characters/{character_id}/spells/cast",
        fallback,
        json_body=req.model_dump(exclude_unset=True),
    )
    return res if isinstance(res, CharacterResponse) else CharacterResponse(**res)


@router.post(
    "/api/v1/characters/{character_id}/spells/prepare",
    response_model=CharacterResponse,
    dependencies=[Depends(require_zanzibar_permission("edit", "character", "character_id"))],
)
async def prepare_spell(
    character_id: str,
    req: PrepareSpellRequest,
) -> CharacterResponse:
    """Prepare or unprepare spell (requires 'edit')."""
    char = character_store.get_character(character_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    async def fallback():
        updated = await character_store.prepare_spell(character_id, req.spell_name, req.is_prepared)
        return updated.to_response()

    res = await proxy_or_fallback(
        "POST",
        f"/api/v1/characters/{character_id}/spells/prepare",
        fallback,
        json_body=req.model_dump(exclude_unset=True),
    )
    return res if isinstance(res, CharacterResponse) else CharacterResponse(**res)
