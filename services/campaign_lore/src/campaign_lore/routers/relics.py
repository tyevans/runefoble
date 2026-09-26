"""API routes for 3D Relic Inspector, WebGL Shaders, and Interactive Runic Inscriptions."""

from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.event_sourcing import AggregateRepository

from campaign_lore.dependencies import (
    check_user_can_inspect_relic,
    check_user_can_read_secrets,
    get_current_user_id,
    get_relic_repo,
    get_spicedb_client,
)
from campaign_lore.handouts import RelicSynthesizer
from campaign_lore.handouts_aggregate import RelicAggregate

router = APIRouter(prefix="/api/v1/lore/relics", tags=["3D Relics"])


class ForgeRelicRequest(BaseModel):
    """Payload to forge an interactive 3D relic or artifact."""

    campaign_id: UUID
    name: str
    relic_type: str = "amulet"
    model_geometry: str = "amulet_sunken_spire"
    shader_properties: dict[str, Any] | None = None
    runes: list[dict[str, Any]] | None = None
    is_secret: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class InspectRelicRequest(BaseModel):
    """Payload to record a player's 3D rotation and relic inspection."""

    inspected_by: str = "player"
    discovered_runes: list[dict[str, Any]] | None = None
    notes: str | None = None


class TranslateRuneRequest(BaseModel):
    """Payload to decipher or translate an inscription etched onto a relic."""

    rune_id: str
    translated_by: str = "player"
    translation: str | None = None


@router.post("/forge", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def forge_relic(
    payload: ForgeRelicRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)] = None,
    repo: Annotated[AggregateRepository[RelicAggregate], Depends(get_relic_repo)] = None,
) -> dict[str, Any]:
    """Forge a new 3D relic model with PBR shader attributes and etched runes."""
    can_inspect = await check_user_can_inspect_relic(user_id, payload.campaign_id, spicedb)
    if not can_inspect:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User lacks campaign view permission",
        )

    spec = RelicSynthesizer.generate_relic_spec(
        name=payload.name,
        relic_type=payload.relic_type,
        model_geometry=payload.model_geometry,
        custom_runes=payload.runes,
    )
    shaders = payload.shader_properties or spec["shader_properties"]
    runes = spec["runes"]

    relic_id = uuid4()
    relic = RelicAggregate(aggregate_id=relic_id)
    relic.forge(
        campaign_id=payload.campaign_id,
        name=payload.name,
        relic_type=payload.relic_type,
        model_geometry=payload.model_geometry,
        shader_properties=shaders,
        runes=runes,
        is_secret=payload.is_secret,
        created_by=user_id,
        metadata={**payload.metadata, "mesh_data": spec["mesh_data"]},
    )

    await repo.save(relic)
    return {
        "relic_id": str(relic_id),
        "campaign_id": str(payload.campaign_id),
        "name": payload.name,
        "relic_type": payload.relic_type,
        "model_geometry": payload.model_geometry,
        "shader_properties": shaders,
        "runes": runes,
        "mesh_data": spec["mesh_data"],
        "is_secret": payload.is_secret,
        "status": "forged",
    }


@router.get("/{relic_id}", response_model=dict[str, Any])
async def get_relic(
    relic_id: UUID,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)] = None,
    repo: Annotated[AggregateRepository[RelicAggregate], Depends(get_relic_repo)] = None,
) -> dict[str, Any]:
    """Retrieve 3D relic geometry, shader properties, and runes."""
    try:
        relic = await repo.load(relic_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relic {relic_id} not found",
        ) from None

    can_view = await check_user_can_inspect_relic(user_id, relic.state.campaign_id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User lacks campaign view permission",
        )

    if relic.state.is_secret:
        can_secret = await check_user_can_read_secrets(user_id, relic.state.campaign_id, spicedb)
        if not can_secret:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Relic is secret DM lore",
            )

    return {
        "relic_id": str(relic.state.relic_id),
        "campaign_id": str(relic.state.campaign_id),
        "name": relic.state.name,
        "relic_type": relic.state.relic_type,
        "model_geometry": relic.state.model_geometry,
        "shader_properties": relic.state.shader_properties,
        "runes": relic.state.runes,
        "is_secret": relic.state.is_secret,
        "metadata": relic.state.metadata,
        "inspections": relic.state.inspections,
    }


@router.post("/{relic_id}/inspect", response_model=dict[str, Any])
async def inspect_relic(
    relic_id: UUID,
    payload: InspectRelicRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)] = None,
    repo: Annotated[AggregateRepository[RelicAggregate], Depends(get_relic_repo)] = None,
) -> dict[str, Any]:
    """Record an interactive 3D inspection and discover engraved runes."""
    try:
        relic = await repo.load(relic_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relic {relic_id} not found",
        ) from None

    can_inspect = await check_user_can_inspect_relic(user_id, relic.state.campaign_id, spicedb)
    if not can_inspect:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User lacks relic inspection permission",
        )

    relic.inspect(
        inspected_by=payload.inspected_by or user_id or "player",
        discovered_runes=payload.discovered_runes,
        notes=payload.notes,
    )
    await repo.save(relic)

    return {
        "relic_id": str(relic_id),
        "inspected_by": payload.inspected_by or user_id or "player",
        "discovered_runes": relic.state.inspections[-1]["discovered_runes"],
        "status": "inspected",
    }


@router.post("/{relic_id}/translate-rune", response_model=dict[str, Any])
async def translate_rune(
    relic_id: UUID,
    payload: TranslateRuneRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)] = None,
    repo: Annotated[AggregateRepository[RelicAggregate], Depends(get_relic_repo)] = None,
) -> dict[str, Any]:
    """Translate an engraved rune inscription on the relic."""
    try:
        relic = await repo.load(relic_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relic {relic_id} not found",
        ) from None

    matched = next((r for r in relic.state.runes if r.get("id") == payload.rune_id), None)
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rune {payload.rune_id} not found on relic",
        )

    translation = payload.translation or matched.get("translated", "Ancient unknown dialect")
    relic.translate_rune(
        rune_id=payload.rune_id,
        translated_by=payload.translated_by or user_id or "player",
        translation=translation,
    )
    await repo.save(relic)

    return {
        "relic_id": str(relic_id),
        "rune_id": payload.rune_id,
        "original_inscription": matched.get("inscription", ""),
        "translation": translation,
        "translated_by": payload.translated_by or user_id or "player",
    }
