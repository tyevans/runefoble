"""FastAPI router for grid-calibrated PDFs, papercraft standees, and 3D STL tokens."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.asset import PrintPdfForged, StlTokenForged
from runefoble_platform.aggregate_loading import load_or_create
from runefoble_platform.event_sourcing import AggregateRepository
from runefoble_platform.storage import SiloStorageService

from asset_forge.aggregate import AssetForgeAggregate
from asset_forge.dependencies import (
    CallerId,
    get_forge_repo,
    get_principal,
    get_storage,
    publish_forge_event,
    record_asset_relations,
    require_forge_permission,
)
from asset_forge.map_generation_engine import get_map_generator
from asset_forge.models import (
    PrintPdfRequest,
    PrintPdfResponse,
    StandeesRequest,
    StandeesResponse,
    StlTokenRequest,
    StlTokenResponse,
)
from asset_forge.pdf_tiler import tile_battlemap_to_pdf
from asset_forge.silo_upload import store_forged_asset
from asset_forge.standees import generate_standees_pdf
from asset_forge.stl_generator import generate_stl_mesh

router = APIRouter(tags=["Print Forge"], dependencies=[Depends(get_principal)])


async def _record_aggregate(
    repo: AggregateRepository[AssetForgeAggregate],
    agg_id: UUID | None,
    record_fn: Callable[[AssetForgeAggregate], None],
) -> None:
    target_id = agg_id or uuid4()
    forge_agg = await load_or_create(repo, target_id, AssetForgeAggregate)
    record_fn(forge_agg)
    await repo.save(forge_agg)


@router.post("/api/v1/forge/print-pdf", response_model=None)
async def export_print_pdf(
    request: PrintPdfRequest,
    user_id: CallerId,
    storage: Annotated[SiloStorageService, Depends(get_storage)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[AssetForgeAggregate], Depends(get_forge_repo)],
) -> Any:
    """Generate multi-page print-ready PDF sliced to exact 1-inch tabletop grid."""
    creator_id = user_id
    campaign_id = await require_forge_permission(user_id, request.campaign_id, spicedb)

    grid, theme = request.grid, request.theme
    if not grid and request.prompt:
        layout = await get_map_generator().generate(
            prompt=request.prompt,
            width=request.width_cells,
            height=request.height_cells,
            seed=None,
            theme_override=request.theme,
        )
        theme, grid = layout.theme, layout.grid

    pdf_bytes, meta = tile_battlemap_to_pdf(
        width_cells=request.width_cells,
        height_cells=request.height_cells,
        grid=grid,
        page_size=request.page_size,
        theme=theme,
        title=request.title,
    )

    asset_id = f"pdf-{uuid4().hex[:12]}"
    # Authorization relations first. A failed write raises AuthzError (HTTP 503) before storage.
    await record_asset_relations(spicedb, asset_id, creator_id, campaign_id)
    upload_meta = await store_forged_asset(
        storage,
        object_key=f"prints/{asset_id}.pdf",
        data=pdf_bytes,
        content_type="application/pdf",
        owner_id=creator_id,
        asset_id=asset_id,
    )

    await _record_aggregate(
        repo,
        request.campaign_id,
        lambda agg: agg.record_print_pdf_forged(
            asset_id=asset_id,
            creator_id=creator_id,
            total_pages=meta["total_pages"],
            page_size=request.page_size,
            grid_scale="1-inch",
            download_url=upload_meta["download_url"],
            campaign_id=request.campaign_id,
            session_id=request.session_id,
        ),
    )

    await publish_forge_event(
        PrintPdfForged(
            asset_id=asset_id,
            campaign_id=request.campaign_id,
            session_id=request.session_id,
            creator_id=creator_id,
            total_pages=meta["total_pages"],
            page_size=request.page_size,
            grid_scale="1-inch",
            download_url=upload_meta["download_url"],
        )
    )

    if request.format == "json":
        return PrintPdfResponse(
            asset_id=asset_id,
            download_url=upload_meta["download_url"],
            total_pages=meta["total_pages"],
            rows=meta["rows"],
            cols=meta["cols"],
            page_size=request.page_size,
            grid_calibration=meta["grid_calibration"],
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="battlemap-{asset_id}.pdf"',
            "X-Asset-Id": asset_id,
            "X-Page-Count": str(meta["total_pages"]),
            "X-Grid-Scale": "1-inch",
            "X-Download-Url": upload_meta["download_url"],
        },
    )


@router.post("/api/v1/forge/standees", response_model=None)
async def export_standees(
    request: StandeesRequest,
    user_id: CallerId,
    storage: Annotated[SiloStorageService, Depends(get_storage)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[AssetForgeAggregate], Depends(get_forge_repo)],
) -> Any:
    """Generate folding papercraft miniature standee sheets."""
    creator_id = user_id
    campaign_id = await require_forge_permission(user_id, request.campaign_id, spicedb)

    raw_items = [item.model_dump() for item in request.standees]
    pdf_bytes, meta = generate_standees_pdf(
        standees=raw_items,
        page_size=request.page_size,
        sheet_title=request.sheet_title,
    )

    asset_id = f"std-{uuid4().hex[:12]}"
    # Authorization relations first. A failed write raises AuthzError (HTTP 503) before storage.
    await record_asset_relations(spicedb, asset_id, creator_id, campaign_id)
    upload_meta = await store_forged_asset(
        storage,
        object_key=f"standees/{asset_id}.pdf",
        data=pdf_bytes,
        content_type="application/pdf",
        owner_id=creator_id,
        asset_id=asset_id,
    )

    await _record_aggregate(
        repo,
        request.campaign_id,
        lambda agg: agg.record_print_pdf_forged(
            asset_id=asset_id,
            creator_id=creator_id,
            total_pages=meta["pages"],
            page_size=request.page_size,
            grid_scale="standee-sheet",
            download_url=upload_meta["download_url"],
            campaign_id=request.campaign_id,
        ),
    )

    await publish_forge_event(
        PrintPdfForged(
            asset_id=asset_id,
            campaign_id=request.campaign_id,
            creator_id=creator_id,
            total_pages=meta["pages"],
            page_size=request.page_size,
            grid_scale="standee-sheet",
            download_url=upload_meta["download_url"],
        )
    )

    if request.format == "json":
        return StandeesResponse(
            asset_id=asset_id,
            download_url=upload_meta["download_url"],
            standee_count=meta["standee_count"],
            pages=meta["pages"],
            page_size=request.page_size,
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="standees-{asset_id}.pdf"',
            "X-Asset-Id": asset_id,
            "X-Standee-Count": str(meta["standee_count"]),
            "X-Download-Url": upload_meta["download_url"],
        },
    )


@router.post("/api/v1/forge/stl-token", response_model=None)
async def export_stl_token(
    request: StlTokenRequest,
    user_id: CallerId,
    storage: Annotated[SiloStorageService, Depends(get_storage)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[AssetForgeAggregate], Depends(get_forge_repo)],
) -> Any:
    """Generate watertight 3D printable STL miniature base with status condition clips."""
    creator_id = user_id
    campaign_id = await require_forge_permission(user_id, request.campaign_id, spicedb)

    stl_bytes, meta = generate_stl_mesh(
        diameter_mm=request.diameter_mm,
        height_mm=request.height_mm,
        num_slots=request.num_slots,
        slot_depth_mm=request.slot_depth_mm,
        condition_label=request.condition_label,
        binary=request.binary,
    )

    asset_id = f"stl-{uuid4().hex[:12]}"
    # Authorization relations first. A failed write raises AuthzError (HTTP 503) before storage.
    await record_asset_relations(spicedb, asset_id, creator_id, campaign_id)
    upload_meta = await store_forged_asset(
        storage,
        object_key=f"stls/{asset_id}.stl",
        data=stl_bytes,
        content_type="model/stl",
        owner_id=creator_id,
        asset_id=asset_id,
    )

    await _record_aggregate(
        repo,
        request.campaign_id,
        lambda agg: agg.record_stl_token_forged(
            asset_id=asset_id,
            creator_id=creator_id,
            diameter_mm=request.diameter_mm,
            height_mm=request.height_mm,
            facet_count=meta["facet_count"],
            condition_label=request.condition_label,
            download_url=upload_meta["download_url"],
            campaign_id=request.campaign_id,
        ),
    )

    await publish_forge_event(
        StlTokenForged(
            asset_id=asset_id,
            campaign_id=request.campaign_id,
            creator_id=creator_id,
            diameter_mm=request.diameter_mm,
            height_mm=request.height_mm,
            facet_count=meta["facet_count"],
            condition_label=request.condition_label,
            download_url=upload_meta["download_url"],
        )
    )

    if request.format == "json":
        return StlTokenResponse(
            asset_id=asset_id,
            download_url=upload_meta["download_url"],
            diameter_mm=request.diameter_mm,
            height_mm=request.height_mm,
            facet_count=meta["facet_count"],
            is_watertight=True,
            condition_label=request.condition_label,
        )

    return Response(
        content=stl_bytes,
        media_type="model/stl",
        headers={
            "Content-Disposition": f'attachment; filename="token-base-{asset_id}.stl"',
            "X-Asset-Id": asset_id,
            "X-Facet-Count": str(meta["facet_count"]),
            "X-Is-Watertight": "true",
            "X-Download-Url": upload_meta["download_url"],
        },
    )
