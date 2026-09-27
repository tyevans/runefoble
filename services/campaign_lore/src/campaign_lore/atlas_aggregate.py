"""Event-sourced AtlasAggregate using eventsource-py."""

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import (
    AtlasLayerToggled,
    AtlasPinCreated,
    AtlasPinUpdated,
    AtlasTerritoryUpdated,
)


class AtlasState(BaseModel):
    """Internal state representation for an interactive campaign world atlas."""

    campaign_id: UUID
    active_layers: dict[str, bool] = Field(
        default_factory=lambda: {
            "continental": True,
            "regional": True,
            "municipal": True,
            "contested_boundaries": True,
        }
    )
    pins: list[dict[str, Any]] = Field(default_factory=list)
    territories: list[dict[str, Any]] = Field(default_factory=list)


class AtlasAggregate(DeclarativeAggregate[AtlasState]):
    """Event-sourced aggregate managing multi-layered world atlas pins, layers, and territories."""

    aggregate_type = "Atlas"
    requires_creation_event = False

    @property
    def state(self) -> AtlasState:
        """Return state, initializing with default AtlasState if not yet set."""
        if self._state is None:
            self._state = AtlasState(campaign_id=self.aggregate_id)
        return self._state

    def add_pin(
        self,
        pin_id: UUID,
        campaign_id: UUID,
        title: str,
        coordinates: dict[str, float],
        layer: str = "continental",
        description: str = "",
        era: str | None = None,
        session_id: str | None = None,
        linked_entity_ids: list[str] | None = None,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Place a geographical milestone pin onto the atlas."""
        self.create_event(
            AtlasPinCreated,
            aggregate_id=self.aggregate_id,
            pin_id=pin_id,
            campaign_id=campaign_id,
            title=title,
            layer=layer,
            coordinates=coordinates,
            description=description,
            era=era,
            session_id=session_id,
            linked_entity_ids=linked_entity_ids or [],
            created_by=created_by,
            metadata=metadata or {},
        )

    def toggle_layer(
        self,
        layer: str,
        is_visible: bool,
        toggled_by: str | None = None,
    ) -> None:
        """Toggle visibility for a map layer or overlay."""
        campaign_id = self.state.campaign_id if self._state else self.aggregate_id
        self.create_event(
            AtlasLayerToggled,
            aggregate_id=self.aggregate_id,
            campaign_id=campaign_id,
            layer=layer,
            is_visible=is_visible,
            toggled_by=toggled_by,
        )

    def update_territory(
        self,
        territory_id: UUID,
        campaign_id: UUID,
        name: str,
        polygon_coordinates: list[list[float]],
        layer: str = "continental",
        owner_faction: str = "Neutral",
        is_contested: bool = False,
        era: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Define or update geopolitical boundaries and faction ownership."""
        self.create_event(
            AtlasTerritoryUpdated,
            aggregate_id=self.aggregate_id,
            territory_id=territory_id,
            campaign_id=campaign_id,
            name=name,
            layer=layer,
            polygon_coordinates=polygon_coordinates,
            owner_faction=owner_faction,
            is_contested=is_contested,
            era=era,
            metadata=metadata or {},
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    def _ensure_state(self, campaign_id: UUID) -> None:
        if self._state is None:
            self._state = AtlasState(campaign_id=campaign_id)

    @handles(AtlasPinCreated)
    def _on_pin_created(self, event: AtlasPinCreated) -> None:
        self._ensure_state(event.campaign_id)
        # Check if pin already exists
        self.state.pins = [p for p in self.state.pins if p.get("pin_id") != str(event.pin_id)]
        self.state.pins.append(
            {
                "pin_id": str(event.pin_id),
                "title": event.title,
                "layer": event.layer,
                "coordinates": event.coordinates,
                "description": event.description,
                "era": event.era,
                "session_id": event.session_id,
                "linked_entity_ids": event.linked_entity_ids,
                "created_by": event.created_by,
                "metadata": event.metadata,
            }
        )

    @handles(AtlasPinUpdated)
    def _on_pin_updated(self, event: AtlasPinUpdated) -> None:
        self._ensure_state(event.campaign_id)
        for pin in self.state.pins:
            if pin.get("pin_id") == str(event.pin_id):
                if event.title is not None:
                    pin["title"] = event.title
                if event.coordinates is not None:
                    pin["coordinates"] = event.coordinates
                if event.description is not None:
                    pin["description"] = event.description
                if event.era is not None:
                    pin["era"] = event.era
                if event.linked_entity_ids is not None:
                    pin["linked_entity_ids"] = event.linked_entity_ids
                if event.metadata is not None:
                    pin["metadata"] = event.metadata

    @handles(AtlasLayerToggled)
    def _on_layer_toggled(self, event: AtlasLayerToggled) -> None:
        self._ensure_state(event.campaign_id)
        self.state.active_layers[event.layer] = event.is_visible

    @handles(AtlasTerritoryUpdated)
    def _on_territory_updated(self, event: AtlasTerritoryUpdated) -> None:
        self._ensure_state(event.campaign_id)
        self.state.territories = [
            t for t in self.state.territories if t.get("territory_id") != str(event.territory_id)
        ]
        self.state.territories.append(
            {
                "territory_id": str(event.territory_id),
                "name": event.name,
                "layer": event.layer,
                "polygon_coordinates": event.polygon_coordinates,
                "owner_faction": event.owner_faction,
                "is_contested": event.is_contested,
                "era": event.era,
                "metadata": event.metadata,
            }
        )
