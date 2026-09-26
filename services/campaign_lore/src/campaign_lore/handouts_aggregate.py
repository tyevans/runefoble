"""Event-sourced aggregates for Diegetic Handouts and 3D Relics using eventsource-py."""

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import (
    HandoutGenerated,
    InvisibleInkRevealed,
    RelicForged,
    RelicInspected,
    RelicRuneTranslated,
    WaxSealBroken,
)


class DiegeticHandoutState(BaseModel):
    """Internal state for a diegetic handout."""

    handout_id: UUID
    campaign_id: UUID
    title: str
    handout_type: str = "letter"
    paper_texture: str = "weathered_parchment"
    calligraphy_font: str = "royal_chancery"
    content: str
    has_wax_seal: bool = True
    wax_seal: dict[str, Any] = Field(default_factory=dict)
    has_invisible_ink: bool = False
    invisible_ink: dict[str, Any] | None = None
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    reveals: list[dict[str, Any]] = Field(default_factory=list)


class DiegeticHandoutAggregate(DeclarativeAggregate[DiegeticHandoutState]):
    """Event-sourced aggregate managing diegetic handout lifecycle, seal cracking, and UV reveals."""

    aggregate_type = "DiegeticHandout"
    requires_creation_event = True

    def generate(
        self,
        campaign_id: UUID,
        title: str,
        content: str,
        handout_type: str = "letter",
        paper_texture: str = "weathered_parchment",
        calligraphy_font: str = "royal_chancery",
        has_wax_seal: bool = True,
        wax_seal: dict[str, Any] | None = None,
        has_invisible_ink: bool = False,
        invisible_ink: dict[str, Any] | None = None,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Synthesize and publish a new diegetic handout."""
        seal_data = wax_seal or {
            "state": "intact",
            "color": "crimson",
            "stamp_symbol": "raven_crest",
            "physics": {"stiffness": 0.8, "brittleness": 0.95},
        }
        self.create_event(
            HandoutGenerated,
            aggregate_id=self.aggregate_id,
            handout_id=self.aggregate_id,
            campaign_id=campaign_id,
            title=title,
            handout_type=handout_type,
            paper_texture=paper_texture,
            calligraphy_font=calligraphy_font,
            content=content,
            has_wax_seal=has_wax_seal,
            wax_seal=seal_data,
            has_invisible_ink=has_invisible_ink,
            invisible_ink=invisible_ink,
            created_by=created_by,
            metadata=metadata or {},
        )

    def break_seal(
        self,
        broken_by: str,
        break_force: float = 1.0,
        audio_cue: str = "wax_crack_crisp_01.wav",
    ) -> None:
        """Break the wax seal on this handout."""
        if not self.state.has_wax_seal:
            raise ValueError("Handout does not possess a wax seal")
        if self.state.wax_seal.get("state") == "broken":
            raise ValueError("Wax seal is already broken")

        preview = (
            self.state.content[:60] + "..." if len(self.state.content) > 60 else self.state.content
        )
        self.create_event(
            WaxSealBroken,
            aggregate_id=self.aggregate_id,
            handout_id=self.aggregate_id,
            campaign_id=self.state.campaign_id,
            broken_by=broken_by,
            break_force=break_force,
            haptic_audio_effect=audio_cue,
            revealed_content_preview=preview,
        )

    def reveal_invisible_ink(self, revealed_by: str, uv_intensity: float = 1.0) -> None:
        """Reveal secret runes under UV torchlight."""
        if not self.state.has_invisible_ink or not self.state.invisible_ink:
            raise ValueError("Handout does not contain invisible ink")

        secret_text = self.state.invisible_ink.get("secret_text", "")
        self.create_event(
            InvisibleInkRevealed,
            aggregate_id=self.aggregate_id,
            handout_id=self.aggregate_id,
            campaign_id=self.state.campaign_id,
            revealed_by=revealed_by,
            secret_text=secret_text,
            uv_intensity=uv_intensity,
        )

    # Event Handlers (@handles)
    @handles(HandoutGenerated)
    def _on_generated(self, event: HandoutGenerated) -> None:
        self._state = DiegeticHandoutState(
            handout_id=event.handout_id,
            campaign_id=event.campaign_id,
            title=event.title,
            handout_type=event.handout_type,
            paper_texture=event.paper_texture,
            calligraphy_font=event.calligraphy_font,
            content=event.content,
            has_wax_seal=event.has_wax_seal,
            wax_seal=event.wax_seal,
            has_invisible_ink=event.has_invisible_ink,
            invisible_ink=event.invisible_ink,
            created_by=event.created_by,
            metadata=event.metadata,
        )

    @handles(WaxSealBroken)
    def _on_seal_broken(self, event: WaxSealBroken) -> None:
        self.state.wax_seal["state"] = "broken"
        self.state.wax_seal["broken_by"] = event.broken_by
        self.state.wax_seal["break_force"] = event.break_force
        self.state.wax_seal["haptic_audio_effect"] = event.haptic_audio_effect

    @handles(InvisibleInkRevealed)
    def _on_invisible_ink_revealed(self, event: InvisibleInkRevealed) -> None:
        if self.state.invisible_ink:
            self.state.invisible_ink["revealed"] = True
        self.state.reveals.append(
            {
                "revealed_by": event.revealed_by,
                "secret_text": event.secret_text,
                "uv_intensity": event.uv_intensity,
            }
        )


class RelicState(BaseModel):
    """Internal state for an interactive 3D relic."""

    relic_id: UUID
    campaign_id: UUID
    name: str
    relic_type: str = "amulet"
    model_geometry: str = "amulet_sunken_spire"
    shader_properties: dict[str, Any] = Field(default_factory=dict)
    runes: list[dict[str, Any]] = Field(default_factory=list)
    is_secret: bool = False
    created_by: str | None = None
    inspections: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelicAggregate(DeclarativeAggregate[RelicState]):
    """Event-sourced aggregate managing 3D interactive relics, inspection, and rune translation."""

    aggregate_type = "Relic"
    requires_creation_event = True

    def forge(
        self,
        campaign_id: UUID,
        name: str,
        relic_type: str = "amulet",
        model_geometry: str = "amulet_sunken_spire",
        shader_properties: dict[str, Any] | None = None,
        runes: list[dict[str, Any]] | None = None,
        is_secret: bool = False,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Forge a new 3D relic artifact."""
        shaders = shader_properties or {
            "metallic": 0.85,
            "roughness": 0.25,
            "emissive_color": "#00ffcc",
            "emissive_intensity": 1.2,
        }
        self.create_event(
            RelicForged,
            aggregate_id=self.aggregate_id,
            relic_id=self.aggregate_id,
            campaign_id=campaign_id,
            name=name,
            relic_type=relic_type,
            model_geometry=model_geometry,
            shader_properties=shaders,
            runes=runes or [],
            is_secret=is_secret,
            created_by=created_by,
            metadata=metadata or {},
        )

    def inspect(
        self,
        inspected_by: str,
        discovered_runes: list[dict[str, Any]] | None = None,
        notes: str | None = None,
    ) -> None:
        """Record an inspection event with discovered runes."""
        discovered = discovered_runes or [r for r in self.state.runes if not r.get("secret", False)]
        self.create_event(
            RelicInspected,
            aggregate_id=self.aggregate_id,
            relic_id=self.aggregate_id,
            campaign_id=self.state.campaign_id,
            inspected_by=inspected_by,
            name=self.state.name,
            model_geometry=self.state.model_geometry,
            shader_properties=self.state.shader_properties,
            discovered_runes=discovered,
            inspection_notes=notes,
        )

    def translate_rune(
        self,
        rune_id: str,
        translated_by: str,
        translation: str,
    ) -> None:
        """Translate a discovered rune on the relic."""
        matched_rune = next((r for r in self.state.runes if r.get("id") == rune_id), None)
        original = matched_rune.get("inscription", "Unknown") if matched_rune else "Unknown"

        self.create_event(
            RelicRuneTranslated,
            aggregate_id=self.aggregate_id,
            relic_id=self.aggregate_id,
            campaign_id=self.state.campaign_id,
            rune_id=rune_id,
            translated_by=translated_by,
            original_inscription=original,
            translation=translation,
        )

    # Event Handlers (@handles)
    @handles(RelicForged)
    def _on_forged(self, event: RelicForged) -> None:
        self._state = RelicState(
            relic_id=event.relic_id,
            campaign_id=event.campaign_id,
            name=event.name,
            relic_type=event.relic_type,
            model_geometry=event.model_geometry,
            shader_properties=event.shader_properties,
            runes=event.runes,
            is_secret=event.is_secret,
            created_by=event.created_by,
            metadata=event.metadata,
        )

    @handles(RelicInspected)
    def _on_inspected(self, event: RelicInspected) -> None:
        self.state.inspections.append(
            {
                "inspected_by": event.inspected_by,
                "discovered_runes": event.discovered_runes,
                "inspection_notes": event.inspection_notes,
            }
        )

    @handles(RelicRuneTranslated)
    def _on_rune_translated(self, event: RelicRuneTranslated) -> None:
        for rune in self.state.runes:
            if rune.get("id") == event.rune_id:
                rune["translated"] = event.translation
                rune["translated_by"] = event.translated_by
