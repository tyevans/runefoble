"""API routes for Generative Diegetic Handouts, Parchment Textures, and Breakable Wax Seals."""

from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.port import SpiceDBPort
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.event_sourcing import AggregateRepository

from campaign_lore.dependencies import (
    get_handout_repo,
)
from campaign_lore.handouts import HandoutSynthesizer
from campaign_lore.handouts_aggregate import DiegeticHandoutAggregate
from campaign_lore.identity import CallerId, get_principal
from campaign_lore.permissions import (
    check_user_can_interact_handout,
    check_user_can_run_session,
    check_user_can_view_campaign,
)

router = APIRouter(
    prefix="/api/v1/lore/handouts",
    tags=["Diegetic Handouts"],
    dependencies=[Depends(get_principal)],
)


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
    """Payload to crack/break a wax seal on a handout. The breaker is the verified caller."""

    model_config = ConfigDict(extra="forbid")

    break_force: float = 12.5


class RevealInvisibleInkRequest(BaseModel):
    """Payload to shine simulated UV torchlight over invisible ink runes. The revealer is the verified caller."""

    model_config = ConfigDict(extra="forbid")

    uv_intensity: float = 1.0


@router.post("/generate", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def generate_handout(
    payload: GenerateHandoutRequest,
    user_id: CallerId,
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)] = None,
    repo: Annotated[
        AggregateRepository[DiegeticHandoutAggregate], Depends(get_handout_repo)
    ] = None,
) -> dict[str, Any]:
    """Generate a weathered diegetic handout with wax seal and optional UV invisible ink."""
    can_generate = await check_user_can_run_session(user_id, payload.campaign_id, spicedb)
    if not can_generate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only campaign run_session members can generate handouts.",
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
    user_id: CallerId,
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)] = None,
    repo: Annotated[
        AggregateRepository[DiegeticHandoutAggregate], Depends(get_handout_repo)
    ] = None,
) -> dict[str, Any]:
    """Retrieve diegetic handout state and visual styling spec."""
    handout = await load_if_exists(repo, handout_id)
    if handout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Handout {handout_id} not found",
        )

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
    user_id: CallerId,
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)] = None,
    repo: Annotated[
        AggregateRepository[DiegeticHandoutAggregate], Depends(get_handout_repo)
    ] = None,
) -> dict[str, Any]:
    """Crack/break the wax seal on a handout with dynamic acoustic feedback."""
    handout = await load_if_exists(repo, handout_id)
    if handout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Handout {handout_id} not found",
        )

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
        broken_by=user_id,
        break_force=payload.break_force,
        audio_cue=audio,
    )
    await repo.save(handout)

    return {
        "handout_id": str(handout_id),
        "seal_state": "broken",
        "broken_by": user_id,
        "break_force": payload.break_force,
        "haptic_audio_effect": audio,
        "revealed_content": handout.state.content,
    }


@router.post("/{handout_id}/reveal-invisible-ink", response_model=dict[str, Any])
async def reveal_invisible_ink(
    handout_id: UUID,
    payload: RevealInvisibleInkRequest,
    user_id: CallerId,
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)] = None,
    repo: Annotated[
        AggregateRepository[DiegeticHandoutAggregate], Depends(get_handout_repo)
    ] = None,
) -> dict[str, Any]:
    """Inspect invisible ink runes using simulated UV torchlight."""
    handout = await load_if_exists(repo, handout_id)
    if handout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Handout {handout_id} not found",
        )

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
        revealed_by=user_id,
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
