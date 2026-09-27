"""Portrait and wardrobe handler mixin for event-sourced CharacterSheet aggregate."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from character_sheet.models import CharacterState, WardrobeVariant
from eventsource.domain.decorators import handles
from runefoble_events import events as ev


class PortraitHandlerMixin:
    """Mixin managing character wardrobe variant generation and active portrait assignment."""

    _state: CharacterState | None
    state: CharacterState
    create_event: Any
    aggregate_id: Any

    def add_wardrobe_variant(
        self,
        variant_name: str,
        attire_type: str = "base",
        image_url: str = "",
        prompt: str = "",
        variant_id: str | None = None,
        set_active: bool = False,
    ) -> str:
        """Register a synthesized or custom wardrobe variant for this character."""
        vid = variant_id or f"var-{uuid4().hex[:10]}"
        self.create_event(
            ev.PortraitVariantGenerated,
            character_id=str(self.aggregate_id),
            variant_id=vid,
            variant_name=variant_name,
            attire_type=attire_type,
            image_url=image_url,
            prompt=prompt,
            is_active=set_active,
        )
        if set_active:
            self.create_event(
                ev.CharacterPortraitUpdated,
                character_id=str(self.aggregate_id),
                active_portrait_url=image_url,
                variant_id=vid,
            )
        return vid

    def set_active_portrait(
        self,
        variant_id: str | None = None,
        custom_url: str | None = None,
    ) -> None:
        """Assign active token portrait either from an unlocked wardrobe variant or custom URL."""
        target_url = custom_url or ""
        if variant_id:
            if variant_id not in self.state.wardrobe_variants:
                raise ValueError(
                    f"Wardrobe variant '{variant_id}' does not exist on this character"
                )
            target_url = self.state.wardrobe_variants[variant_id].image_url
        elif not custom_url:
            target_url = self.state.base_portrait_url

        self.create_event(
            ev.CharacterPortraitUpdated,
            character_id=str(self.aggregate_id),
            active_portrait_url=target_url,
            variant_id=variant_id,
        )

    @handles(ev.PortraitVariantGenerated)
    def _on_portrait_variant_generated(self, event: ev.PortraitVariantGenerated) -> None:
        variant = WardrobeVariant(
            variant_id=event.variant_id,
            variant_name=event.variant_name,
            attire_type=event.attire_type,
            image_url=event.image_url,
            prompt=event.prompt,
        )
        self._state = self.state.with_wardrobe_variant(variant)
        if event.is_active:
            self._state = self.state.with_active_portrait(
                variant_id=event.variant_id, custom_url=event.image_url
            )

    @handles(ev.CharacterPortraitUpdated)
    def _on_portrait_updated(self, event: ev.CharacterPortraitUpdated) -> None:
        self._state = self.state.with_active_portrait(
            variant_id=event.variant_id, custom_url=event.active_portrait_url
        )

    @handles(ev.CharacterDamaged)
    def _on_character_damaged(self, event: ev.CharacterDamaged) -> None:
        pass
