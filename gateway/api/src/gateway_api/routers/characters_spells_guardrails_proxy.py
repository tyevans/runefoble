"""Character spell and stand-in guardrail routes proxied to character_sheet (TASK-0586).

The gateway keeps the public paths and the Zanzibar check on each route. It forwards the caller's
bearer token, so character_sheet verifies the caller again and applies the change. The gateway
holds no character state and returns no substitute value (see `upstream_errors.py`).

The guardrail PUT relays the raw body, so character_sheet validates the policy and its 422 reaches
the caller unchanged.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from gateway_api.auth import require_zanzibar_permission
from gateway_api.character_models import (
    CastSpellRequest,
    CharacterResponse,
    PrepareSpellRequest,
)
from gateway_api.character_view import (
    CHARACTER_SERVICE,
    character_path,
    forward_character_state,
    to_character_response,
)
from gateway_api.proxy import forward_bytes, forward_json

router = APIRouter(tags=["characters-subresources"])

EDIT = [Depends(require_zanzibar_permission("edit", "character", "character_id"))]
VIEW = [Depends(require_zanzibar_permission("view", "character", "character_id"))]


@router.post(
    "/api/v1/characters/{character_id}/spells/cast",
    response_model=CharacterResponse,
    dependencies=EDIT,
)
async def cast_spell(
    character_id: str, req: CastSpellRequest, request: Request
) -> CharacterResponse:
    """Cast a spell and deduct the slot tier. character_sheet checks `edit`."""
    return await forward_character_state(
        request,
        "POST",
        character_path(character_id, "/spells/cast"),
        req.model_dump(exclude_unset=True),
    )


@router.post(
    "/api/v1/characters/{character_id}/spells/prepare",
    response_model=CharacterResponse,
    dependencies=EDIT,
)
async def prepare_spell(
    character_id: str, req: PrepareSpellRequest, request: Request
) -> CharacterResponse:
    """Prepare or unprepare a spell. character_sheet checks `edit`."""
    return await forward_character_state(
        request,
        "POST",
        character_path(character_id, "/spells/prepare"),
        req.model_dump(exclude_unset=True),
    )


@router.put(
    "/api/v1/characters/{character_id}/guardrails",
    response_model=CharacterResponse,
    dependencies=EDIT,
)
async def update_guardrails(character_id: str, request: Request) -> CharacterResponse:
    """Store stand-in guardrails. The raw body reaches character_sheet, which validates it."""
    res = await forward_bytes(
        request,
        service=CHARACTER_SERVICE,
        method="PUT",
        path=character_path(character_id, "/guardrails"),
    )
    return to_character_response(json.loads(res.body), None)


@router.get("/api/v1/characters/{character_id}/guardrails", dependencies=VIEW)
async def get_guardrails(character_id: str, request: Request) -> dict[str, Any]:
    """Read the stand-in guardrails. character_sheet checks `view`."""
    return await forward_json(
        request,
        service=CHARACTER_SERVICE,
        method="GET",
        path=character_path(character_id, "/guardrails"),
    )
