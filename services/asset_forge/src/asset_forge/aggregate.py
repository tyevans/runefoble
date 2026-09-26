"""Event-sourced AssetForge aggregate powered by eventsource-py."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.asset import (
    BattlemapForged,
    PrintPdfForged,
    StlTokenForged,
    TokenAssetForged,
)


class AssetForgeState(BaseModel):
    """Internal state representation for asset forge aggregate."""

    forge_id: UUID
    forged_battlemaps: dict[str, dict[str, Any]] = Field(default_factory=dict)
    forged_tokens: dict[str, dict[str, Any]] = Field(default_factory=dict)
    forged_prints: dict[str, dict[str, Any]] = Field(default_factory=dict)
    forged_stls: dict[str, dict[str, Any]] = Field(default_factory=dict)


class AssetForgeAggregate(DeclarativeAggregate[AssetForgeState]):
    """Event-sourced aggregate managing procedurally generated maps and token portraits."""

    aggregate_type = "AssetForge"
    requires_creation_event = False

    def init_state(self) -> AssetForgeState:
        return AssetForgeState(forge_id=self.aggregate_id)

    def record_battlemap_forged(
        self,
        asset_id: str,
        creator_id: str,
        prompt: str,
        image_url: str,
        width_cells: int,
        height_cells: int,
        cell_size_px: int,
        wall_segments_count: int,
        hazard_cells_count: int,
        doors_count: int,
        theme: str,
        campaign_id: UUID | None = None,
        session_id: str | None = None,
    ) -> None:
        """Record domain state event for a forged battlemap."""
        self.create_event(
            BattlemapForged,
            aggregate_id=self.aggregate_id,
            asset_id=asset_id,
            campaign_id=campaign_id,
            session_id=session_id,
            creator_id=creator_id,
            prompt=prompt,
            image_url=image_url,
            width_cells=width_cells,
            height_cells=height_cells,
            cell_size_px=cell_size_px,
            wall_segments_count=wall_segments_count,
            hazard_cells_count=hazard_cells_count,
            doors_count=doors_count,
            theme=theme,
        )

    def record_token_forged(
        self,
        asset_id: str,
        creator_id: str,
        prompt: str,
        token_name: str,
        token_type: str,
        image_url: str,
        crop_style: str = "circular",
        transparent_background: bool = True,
        campaign_id: UUID | None = None,
    ) -> None:
        """Record domain state event for a forged character/monster token."""
        self.create_event(
            TokenAssetForged,
            aggregate_id=self.aggregate_id,
            asset_id=asset_id,
            campaign_id=campaign_id,
            creator_id=creator_id,
            prompt=prompt,
            token_name=token_name,
            token_type=token_type,
            image_url=image_url,
            crop_style=crop_style,
            transparent_background=transparent_background,
        )

    def record_print_pdf_forged(
        self,
        asset_id: str,
        creator_id: str,
        total_pages: int,
        page_size: str,
        grid_scale: str,
        download_url: str,
        campaign_id: UUID | None = None,
        session_id: str | None = None,
    ) -> None:
        """Record domain state event for a forged multi-page print PDF or standee sheet."""
        self.create_event(
            PrintPdfForged,
            aggregate_id=self.aggregate_id,
            asset_id=asset_id,
            campaign_id=campaign_id,
            session_id=session_id,
            creator_id=creator_id,
            total_pages=total_pages,
            page_size=page_size,
            grid_scale=grid_scale,
            download_url=download_url,
        )

    def record_stl_token_forged(
        self,
        asset_id: str,
        creator_id: str,
        diameter_mm: float,
        height_mm: float,
        facet_count: int,
        download_url: str,
        condition_label: str = "Poisoned",
        campaign_id: UUID | None = None,
    ) -> None:
        """Record domain state event for a forged 3D printable STL token base."""
        self.create_event(
            StlTokenForged,
            aggregate_id=self.aggregate_id,
            asset_id=asset_id,
            campaign_id=campaign_id,
            creator_id=creator_id,
            diameter_mm=diameter_mm,
            height_mm=height_mm,
            facet_count=facet_count,
            condition_label=condition_label,
            download_url=download_url,
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(BattlemapForged)
    def _on_battlemap_forged(self, event: BattlemapForged) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.forged_battlemaps[event.asset_id] = {
            "asset_id": event.asset_id,
            "campaign_id": str(event.campaign_id) if event.campaign_id else None,
            "session_id": event.session_id,
            "creator_id": event.creator_id,
            "prompt": event.prompt,
            "image_url": event.image_url,
            "width_cells": event.width_cells,
            "height_cells": event.height_cells,
            "cell_size_px": event.cell_size_px,
            "wall_segments_count": event.wall_segments_count,
            "hazard_cells_count": event.hazard_cells_count,
            "doors_count": event.doors_count,
            "theme": event.theme,
        }

    @handles(TokenAssetForged)
    def _on_token_forged(self, event: TokenAssetForged) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.forged_tokens[event.asset_id] = {
            "asset_id": event.asset_id,
            "campaign_id": str(event.campaign_id) if event.campaign_id else None,
            "creator_id": event.creator_id,
            "prompt": event.prompt,
            "token_name": event.token_name,
            "token_type": event.token_type,
            "image_url": event.image_url,
            "crop_style": event.crop_style,
            "transparent_background": event.transparent_background,
        }

    @handles(PrintPdfForged)
    def _on_print_pdf_forged(self, event: PrintPdfForged) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.forged_prints[event.asset_id] = {
            "asset_id": event.asset_id,
            "campaign_id": str(event.campaign_id) if event.campaign_id else None,
            "creator_id": event.creator_id,
            "total_pages": event.total_pages,
            "page_size": event.page_size,
            "grid_scale": event.grid_scale,
            "download_url": event.download_url,
        }

    @handles(StlTokenForged)
    def _on_stl_token_forged(self, event: StlTokenForged) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.forged_stls[event.asset_id] = {
            "asset_id": event.asset_id,
            "campaign_id": str(event.campaign_id) if event.campaign_id else None,
            "creator_id": event.creator_id,
            "diameter_mm": event.diameter_mm,
            "height_mm": event.height_mm,
            "facet_count": event.facet_count,
            "condition_label": event.condition_label,
            "download_url": event.download_url,
        }
