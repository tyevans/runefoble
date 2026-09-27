"""API routes for Collaborative Campaign World Atlas and Deep-Zoom Geography."""

from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.event_sourcing import AggregateRepository

from campaign_lore.atlas import (
    CoordinateProjection,
    detect_contested_zones,
    filter_features_by_era,
    find_containing_territory,
)
from campaign_lore.atlas_aggregate import AtlasAggregate, AtlasState
from campaign_lore.dependencies import (
    check_user_can_view_campaign,
    get_atlas_repo,
    get_current_user_id,
    get_spicedb_client,
)

router = APIRouter(prefix="/api/v1/campaigns/{campaign_id}/atlas", tags=["Campaign Atlas"])


class CreatePinRequest(BaseModel):
    """Payload to place a geographical milestone pin."""

    title: str = Field(description="Title or label of the milestone pin")
    coordinates: dict[str, float] = Field(description="Spatial coordinates {x, y}")
    layer: str = Field(
        default="continental", description="Target layer (continental, regional, municipal)"
    )
    description: str = Field(default="", description="Detailed narrative lore or milestone summary")
    era: str | None = Field(default=None, description="Campaign era or chronological tag")
    session_id: str | None = Field(default=None, description="Linked session identifier")
    linked_entity_ids: list[str] = Field(
        default_factory=list, description="Referenced redstring entities"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Visual icons and flags")


class ToggleLayerRequest(BaseModel):
    """Payload to toggle visibility for a map layer."""

    layer: str = Field(
        description="Layer identifier (continental, regional, municipal, contested_boundaries)"
    )
    is_visible: bool = Field(description="Layer active state")


class UpdateTerritoryRequest(BaseModel):
    """Payload to define geopolitical territory boundaries."""

    name: str = Field(description="Territory or realm name")
    polygon_coordinates: list[list[float]] = Field(description="Polygon [x, y] coordinates")
    layer: str = Field(default="continental", description="Layer scope")
    owner_faction: str = Field(default="Neutral", description="Ruling faction name")
    is_contested: bool = Field(default=False, description="Whether border is actively disputed")
    era: str | None = Field(default=None, description="Era or chronological milestone")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Styling attributes")


class AtlasViewResponse(BaseModel):
    """Aggregated atlas view matching query layer and chronological era filters."""

    campaign_id: UUID
    active_layers: dict[str, bool]
    current_layer: str
    current_era: str | None
    pins: list[dict[str, Any]]
    territories: list[dict[str, Any]]
    contested_zones: list[dict[str, Any]]
    layer_extent: float


@router.get("", response_model=AtlasViewResponse)
async def get_campaign_atlas(
    campaign_id: UUID,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    repo: Annotated[AggregateRepository[AtlasAggregate], Depends(get_atlas_repo)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    layer: str = Query(default="continental", description="Active deep-zoom layer"),
    era: str | None = Query(default=None, description="Chronological era filter"),
    session_id: str | None = Query(default=None, description="Session milestone filter"),
) -> AtlasViewResponse:
    """Retrieve the multi-layered interactive campaign atlas, applying era and zoom projections."""
    # Check campaign view permission
    can_view = await check_user_can_view_campaign(user_id, campaign_id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: SpiceDB Zanzibar policy denies view access to this campaign atlas.",
        )

    try:
        aggregate = await repo.load(campaign_id)
        state = aggregate.state
    except Exception:
        state = AtlasState(campaign_id=campaign_id)

    # Filter pins and territories by era / session
    filtered_pins = filter_features_by_era(state.pins, target_era=era, session_id=session_id)
    # Filter pins matching the current layer or continental base
    layer_pins = [
        p for p in filtered_pins if p.get("layer") == layer or p.get("layer") == "continental"
    ]

    filtered_territories = filter_features_by_era(
        state.territories, target_era=era, session_id=session_id
    )
    layer_territories = [
        t
        for t in filtered_territories
        if t.get("layer") == layer or t.get("layer") == "continental"
    ]

    contested_zones = detect_contested_zones(layer_territories)
    extent = CoordinateProjection.get_layer_extent(layer)

    return AtlasViewResponse(
        campaign_id=campaign_id,
        active_layers=state.active_layers,
        current_layer=layer,
        current_era=era,
        pins=layer_pins,
        territories=layer_territories,
        contested_zones=contested_zones,
        layer_extent=extent,
    )


@router.post("/pins", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_pin(
    campaign_id: UUID,
    payload: CreatePinRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    repo: Annotated[AggregateRepository[AtlasAggregate], Depends(get_atlas_repo)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> dict[str, Any]:
    """Place a geographical milestone pin onto the campaign world atlas."""
    can_view = await check_user_can_view_campaign(user_id, campaign_id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User cannot interact with campaign atlas.",
        )

    try:
        aggregate = await repo.load(campaign_id)
    except Exception:
        aggregate = AtlasAggregate(campaign_id)

    pin_id = uuid4()
    meta = dict(payload.metadata)

    # Automatically identify if coordinate falls inside an existing territory
    containing = find_containing_territory(payload.coordinates, aggregate.state.territories)
    if containing:
        meta["territory_id"] = str(containing.get("territory_id"))
        meta["territory_name"] = containing.get("name")
        meta["territory_faction"] = containing.get("owner_faction")

    # Add normalized coordinates for cross-layer projection
    norm_x, norm_y = CoordinateProjection.normalize(
        payload.coordinates.get("x", 0.0),
        payload.coordinates.get("y", 0.0),
        layer=payload.layer,
    )
    meta["normalized_coordinates"] = {"x": round(norm_x, 4), "y": round(norm_y, 4)}

    aggregate.add_pin(
        pin_id=pin_id,
        campaign_id=campaign_id,
        title=payload.title,
        coordinates=payload.coordinates,
        layer=payload.layer,
        description=payload.description,
        era=payload.era,
        session_id=payload.session_id,
        linked_entity_ids=payload.linked_entity_ids,
        created_by=user_id,
        metadata=meta,
    )
    await repo.save(aggregate)

    return {
        "pin_id": str(pin_id),
        "campaign_id": str(campaign_id),
        "title": payload.title,
        "layer": payload.layer,
        "coordinates": payload.coordinates,
        "description": payload.description,
        "era": payload.era,
        "session_id": payload.session_id,
        "linked_entity_ids": payload.linked_entity_ids,
        "metadata": meta,
        "status": "placed",
    }


@router.get("/pins/{pin_id}", response_model=dict[str, Any])
async def get_pin(
    campaign_id: UUID,
    pin_id: UUID,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    repo: Annotated[AggregateRepository[AtlasAggregate], Depends(get_atlas_repo)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> dict[str, Any]:
    """Retrieve details for a specific atlas milestone pin."""
    can_view = await check_user_can_view_campaign(user_id, campaign_id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view atlas.",
        )

    try:
        aggregate = await repo.load(campaign_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Atlas not found") from exc

    for pin in aggregate.state.pins:
        if pin.get("pin_id") == str(pin_id):
            return pin

    raise HTTPException(status_code=404, detail="Atlas pin not found")


@router.post("/layers/toggle", response_model=dict[str, Any])
async def toggle_layer(
    campaign_id: UUID,
    payload: ToggleLayerRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    repo: Annotated[AggregateRepository[AtlasAggregate], Depends(get_atlas_repo)],
) -> dict[str, Any]:
    """Toggle visibility for a map layer or geopolitical boundary overlay."""
    try:
        aggregate = await repo.load(campaign_id)
    except Exception:
        aggregate = AtlasAggregate(campaign_id)

    aggregate.toggle_layer(
        layer=payload.layer,
        is_visible=payload.is_visible,
        toggled_by=user_id,
    )
    await repo.save(aggregate)

    return {
        "campaign_id": str(campaign_id),
        "layer": payload.layer,
        "is_visible": payload.is_visible,
        "status": "updated",
    }


@router.post("/territories", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def update_territory(
    campaign_id: UUID,
    payload: UpdateTerritoryRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    repo: Annotated[AggregateRepository[AtlasAggregate], Depends(get_atlas_repo)],
) -> dict[str, Any]:
    """Define or update geopolitical boundaries, ownership factions, and contested statuses."""
    try:
        aggregate = await repo.load(campaign_id)
    except Exception:
        aggregate = AtlasAggregate(campaign_id)

    territory_id = uuid4()
    aggregate.update_territory(
        territory_id=territory_id,
        campaign_id=campaign_id,
        name=payload.name,
        polygon_coordinates=payload.polygon_coordinates,
        layer=payload.layer,
        owner_faction=payload.owner_faction,
        is_contested=payload.is_contested,
        era=payload.era,
        metadata=payload.metadata,
    )
    await repo.save(aggregate)

    return {
        "territory_id": str(territory_id),
        "campaign_id": str(campaign_id),
        "name": payload.name,
        "layer": payload.layer,
        "polygon_coordinates": payload.polygon_coordinates,
        "owner_faction": payload.owner_faction,
        "is_contested": payload.is_contested,
        "era": payload.era,
        "status": "persisted",
    }
