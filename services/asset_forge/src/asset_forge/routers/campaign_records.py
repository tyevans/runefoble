"""FastAPI router that lists the forge records of one campaign (TASK-0902).

The campaign id is the id of the campaign forge aggregate. Every forge route requires a
campaign id and saves its record there, so this list shows each forged asset of the campaign.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.port import SpiceDBPort
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.event_sourcing import AggregateRepository

from asset_forge.aggregate import AssetForgeAggregate, AssetForgeState
from asset_forge.dependencies import (
    CallerId,
    get_forge_repo,
    get_principal,
    require_campaign_view,
)
from asset_forge.models import CampaignForgeRecord, CampaignForgeRecordsResponse

router = APIRouter(
    prefix="/api/v1/forge/campaigns",
    tags=["Campaign Forge Records"],
    dependencies=[Depends(get_principal)],
)

_BASE_FIELDS = ("asset_id", "campaign_id", "creator_id")


def _record(kind: str, entry: dict[str, Any]) -> CampaignForgeRecord:
    details = {key: value for key, value in entry.items() if key not in _BASE_FIELDS}
    return CampaignForgeRecord(
        kind=kind,
        asset_id=entry["asset_id"],
        campaign_id=entry["campaign_id"],
        creator_id=entry["creator_id"],
        details=details,
    )


def _print_kind(entry: dict[str, Any]) -> str:
    return "standees" if entry.get("grid_scale") == "standee-sheet" else "print_pdf"


def _records(state: AssetForgeState) -> list[CampaignForgeRecord]:
    records = [_record("battlemap", e) for e in state.forged_battlemaps.values()]
    records += [_record("token", e) for e in state.forged_tokens.values()]
    records += [_record(_print_kind(e), e) for e in state.forged_prints.values()]
    records += [_record("stl_token", e) for e in state.forged_stls.values()]
    return records


@router.get("/{campaign_id}/records", response_model=CampaignForgeRecordsResponse)
async def list_campaign_forge_records(
    campaign_id: UUID,
    user_id: CallerId,
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[AssetForgeAggregate], Depends(get_forge_repo)],
) -> CampaignForgeRecordsResponse:
    """List the forge records of a campaign. Requires `campaign.view`.

    A campaign with no forge request answers an empty list.
    """
    await require_campaign_view(spicedb, campaign_id, user_id)
    forge_agg = await load_if_exists(repo, campaign_id)
    records = _records(forge_agg.state) if forge_agg is not None else []
    return CampaignForgeRecordsResponse(campaign_id=str(campaign_id), records=records)
