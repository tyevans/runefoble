"""API routes for Generative Diegetic Handouts, Parchment Textures, and Breakable Wax Seals."""

from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.event_sourcing import AggregateRepository

from campaign_lore.dependencies import (
    check_user_can_interact_handout,
    check_user_can_view_campaign,
    get_current_user_id,
    get_handout_repo,
    get_spicedb_client,
)
from campaign_lore.handouts import HandoutSynthesizer
from campaign_lore.handouts_aggregate import DiegeticHandoutAggregate

router = APIRouter(prefix="/api/v1/lore/handouts", tags=["Diegetic Handouts"])


class GenerateHandoutRequest(BaseModel):
    """Payload to synthesize and forge a diegetic in-world handout."""

    campaign_id: UUID
    title: str
    content: str
    handout_type: str = "letter"
    paper_texture: str = "weathered_parchment"
    calligraphy_font: str = "royal_chancery"
    seal_color: str = "crimson"
    seal_stamp: str = "raven_crest"
    secret_ink_text: str | None = None
    has_wax_seal: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class BreakSealRequest(BaseModel):
    """Payload to crack/break a wax seal on a handout."""

    broken_by: str = "player"
    break_force: float = 12.5


class RevealInvisibleInkRequest(BaseModel):
    """Payload to shine simulated UV torchlight over invisible ink runes."""

    revealed_by: str = "player"
    uv_intensity: float = 1.0


@router.post("/generate", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def generate_handout(
    payload: GenerateHandoutRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)] = None,
    repo: Annotated[
        AggregateRepository[DiegeticHandoutAggregate], Depends(get_handout_repo)
    ] = None,
) -> dict[str, Any]:
    """Generate a weathered diegetic handout with wax seal and optional UV invisible ink."""
    can_view = await check_user_can_view_campaign(user_id, payload.campaign_id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User lacks campaign view permission",
        )

    spec = HandoutSynthesizer.generate_handout_spec(
        title=payload.title,
        content=payload.content,
        handout_type=payload.handout_type,
        paper_texture=payload.paper_texture,
        calligraphy_font=payload.calligraphy_font,
        seal_color=payload.seal_color,
        seal_stamp=payload.seal_stamp,
        secret_ink_text=payload.secret_ink_text,
    )

    handout_id = uuid4()
    handout = DiegeticHandoutAggregate(aggregate_id=handout_id)
    handout.generate(
        campaign_id=payload.campaign_id,
        title=payload.title,
        content=payload.content,
        handout_type=payload.handout_type,
        paper_texture=payload.paper_texture,
        calligraphy_font=payload.calligraphy_font,
        has_wax_seal=payload.has_wax_seal,
        wax_seal=spec["wax_seal"],
        has_invisible_ink=spec["has_invisible_ink"],
        invisible_ink=spec["invisible_ink"],
        created_by=user_id,
        metadata={**payload.metadata, "spec": spec},
    )

    await repo.save(handout)
    return {
        "handout_id": str(handout_id),
        "campaign_id": str(payload.campaign_id),
        "title": payload.title,
        "handout_type": payload.handout_type,
        "paper_texture": payload.paper_texture,
        "calligraphy_font": payload.calligraphy_font,
        "has_wax_seal": payload.has_wax_seal,
        "wax_seal": spec["wax_seal"],
        "has_invisible_ink": spec["has_invisible_ink"],
        "invisible_ink": spec["invisible_ink"],
        "spec": spec,
        "status": "forged",
    }


@router.get("/{handout_id}", response_model=dict[str, Any])
async def get_handout(
    handout_id: UUID,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)] = None,
    repo: Annotated[
        AggregateRepository[DiegeticHandoutAggregate], Depends(get_handout_repo)
    ] = None,
) -> dict[str, Any]:
    """Retrieve diegetic handout state and visual styling spec."""
    try:
        handout = await repo.load(handout_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Handout {handout_id} not found",
        ) from None

    can_view = await check_user_can_view_campaign(user_id, handout.state.campaign_id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User lacks campaign view permission",
        )

    return {
        "handout_id": str(handout.state.handout_id),
        "campaign_id": str(handout.state.campaign_id),
        "title": handout.state.title,
        "handout_type": handout.state.handout_type,
        "paper_texture": handout.state.paper_texture,
        "calligraphy_font": handout.state.calligraphy_font,
        "content": handout.state.content,
        "has_wax_seal": handout.state.has_wax_seal,
        "wax_seal": handout.state.wax_seal,
        "has_invisible_ink": handout.state.has_invisible_ink,
        "invisible_ink": handout.state.invisible_ink,
        "metadata": handout.state.metadata,
        "reveals": handout.state.reveals,
    }


@router.post("/{handout_id}/break-seal", response_model=dict[str, Any])
async def break_seal(
    handout_id: UUID,
    payload: BreakSealRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)] = None,
    repo: Annotated[
        AggregateRepository[DiegeticHandoutAggregate], Depends(get_handout_repo)
    ] = None,
) -> dict[str, Any]:
    """Crack/break the wax seal on a handout with dynamic acoustic feedback."""
    try:
        handout = await repo.load(handout_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Handout {handout_id} not found",
        ) from None

    can_interact = await check_user_can_interact_handout(
        user_id, handout.state.campaign_id, spicedb
    )
    if not can_interact:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User lacks permission to break seal",
        )

    if handout.state.wax_seal.get("state") == "broken":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Wax seal is already broken",
        )

    audio = "wax_fracture_heavy.wav" if payload.break_force > 15.0 else "wax_crack_crisp_01.wav"

    handout.break_seal(
        broken_by=payload.broken_by or user_id or "player",
        break_force=payload.break_force,
        audio_cue=audio,
    )
    await repo.save(handout)

    return {
        "handout_id": str(handout_id),
        "seal_state": "broken",
        "broken_by": payload.broken_by or user_id or "player",
        "break_force": payload.break_force,
        "haptic_audio_effect": audio,
        "revealed_content": handout.state.content,
    }


@router.post("/{handout_id}/reveal-invisible-ink", response_model=dict[str, Any])
async def reveal_invisible_ink(
    handout_id: UUID,
    payload: RevealInvisibleInkRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)] = None,
    repo: Annotated[
        AggregateRepository[DiegeticHandoutAggregate], Depends(get_handout_repo)
    ] = None,
) -> dict[str, Any]:
    """Inspect invisible ink runes using simulated UV torchlight."""
    try:
        handout = await repo.load(handout_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Handout {handout_id} not found",
        ) from None

    can_interact = await check_user_can_interact_handout(
        user_id, handout.state.campaign_id, spicedb
    )
    if not can_interact:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User lacks permission to inspect handout",
        )

    if not handout.state.has_invisible_ink or not handout.state.invisible_ink:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Handout has no invisible ink layer",
        )

    handout.reveal_invisible_ink(
        revealed_by=payload.revealed_by or user_id or "player",
        uv_intensity=payload.uv_intensity,
    )
    await repo.save(handout)

    return {
        "handout_id": str(handout_id),
        "secret_text": handout.state.invisible_ink.get("secret_text", ""),
        "revealed": True,
        "luminescence_color": handout.state.invisible_ink.get("luminescence_color", "#00ffcc"),
        "uv_intensity": payload.uv_intensity,
    }
