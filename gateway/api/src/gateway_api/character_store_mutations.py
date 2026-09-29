"""Character sub-resource mutation handlers and event-sourced persistence mixin."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gateway_api.character_record import CharacterRecord


def to_uuid(val: str) -> uuid.UUID:
    try:
        return uuid.UUID(val)
    except Exception:
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


class CharacterMutationsMixin:
    """Mixin providing sub-resource mutations (health, equipment, inventory, conditions, spells)."""

    def get_character(self, character_id: str) -> CharacterRecord | None:
        raise NotImplementedError

    async def _sync_aggregate(
        self, char_rec: CharacterRecord, mutation_fn: Callable[[Any], Any]
    ) -> None:
        try:
            from character_sheet import dependencies as cs_deps
            from character_sheet.aggregate import CharacterAggregate

            cid = to_uuid(char_rec.id)
            try:
                agg = await cs_deps.repo.load(cid)
            except Exception:
                agg = CharacterAggregate(cid)
                agg.create(
                    name=char_rec.name,
                    character_class=char_rec.character_class,
                    max_hp=char_rec.max_hp,
                    subclass=char_rec.subclass,
                    armor_class=char_rec.armor_class,
                    speed_ft=char_rec.speed,
                    campaign_id=char_rec.campaign_id,
                )
            mutation_fn(agg)
            await cs_deps.repo.save(agg)
        except Exception:
            pass

    async def modify_health(
        self,
        character_id: str,
        delta: int,
        source: str = "damage",
        is_stand_in: bool | None = None,
    ) -> CharacterRecord:
        char = self.get_character(character_id)
        if not char:
            raise KeyError(f"Character '{character_id}' not found")
        effective_stand_in = is_stand_in if is_stand_in is not None else char.is_stand_in_active
        if (
            delta < 0
            and (char.current_hp + delta <= 0)
            and effective_stand_in
            and char.stand_in_guardrails.get("permadeath_safeguard", True)
        ):
            char.current_hp = 0
            char.is_stabilized = True
            char.conditions["unconscious_stabilized"] = {
                "condition": "unconscious_stabilized",
                "duration_rounds": None,
                "source": "permadeath_safeguard",
            }
        else:
            char.current_hp = max(0, min(char.max_hp, char.current_hp + delta))

        await self._sync_aggregate(
            char,
            lambda agg: agg.modify_health(delta, source=source, is_stand_in=effective_stand_in),
        )
        return char

    async def equip_item(
        self,
        character_id: str,
        slot: str,
        item_name: str | None = None,
    ) -> CharacterRecord:
        char = self.get_character(character_id)
        if not char:
            raise KeyError(f"Character '{character_id}' not found")
        s = slot.lower()
        if item_name:
            char.equipment[s] = item_name
        elif s in char.equipment:
            del char.equipment[s]

        await self._sync_aggregate(char, lambda agg: agg.equip_item(s, item_name))
        return char

    async def unequip_item(
        self,
        character_id: str,
        slot: str,
    ) -> CharacterRecord:
        return await self.equip_item(character_id, slot, None)

    async def add_inventory_item(
        self,
        character_id: str,
        name: str,
        quantity: int = 1,
        weight_lbs: float = 0.0,
        item_id: str | None = None,
    ) -> CharacterRecord:
        char = self.get_character(character_id)
        if not char:
            raise KeyError(f"Character '{character_id}' not found")
        iid = str(item_id or uuid.uuid4())
        if iid in char.inventory:
            char.inventory[iid]["quantity"] = char.inventory[iid].get("quantity", 0) + quantity
        else:
            char.inventory[iid] = {
                "item_id": iid,
                "name": name,
                "quantity": quantity,
                "weight_lbs": weight_lbs,
            }

        await self._sync_aggregate(
            char, lambda agg: agg.add_inventory_item(iid, name, quantity, weight_lbs)
        )
        return char

    async def remove_inventory_item(
        self,
        character_id: str,
        item_id: str,
        quantity: int = 1,
    ) -> CharacterRecord:
        char = self.get_character(character_id)
        if not char:
            raise KeyError(f"Character '{character_id}' not found")
        iid = str(item_id)
        if iid not in char.inventory:
            raise ValueError(f"Item '{item_id}' not found in inventory")
        cur_qty = char.inventory[iid].get("quantity", 1)
        if cur_qty <= quantity:
            del char.inventory[iid]
        else:
            char.inventory[iid]["quantity"] = cur_qty - quantity

        await self._sync_aggregate(char, lambda agg: agg.remove_inventory_item(iid, quantity))
        return char

    async def apply_condition(
        self,
        character_id: str,
        condition: str,
        duration_rounds: int | None = None,
        source: str = "",
    ) -> CharacterRecord:
        char = self.get_character(character_id)
        if not char:
            raise KeyError(f"Character '{character_id}' not found")
        cond = condition.lower()
        char.conditions[cond] = {
            "condition": cond,
            "duration_rounds": duration_rounds,
            "source": source,
        }

        await self._sync_aggregate(
            char, lambda agg: agg.apply_condition(cond, duration_rounds, source)
        )
        return char

    async def remove_condition(
        self,
        character_id: str,
        condition: str,
    ) -> CharacterRecord:
        char = self.get_character(character_id)
        if not char:
            raise KeyError(f"Character '{character_id}' not found")
        cond = condition.lower()
        if cond not in char.conditions:
            raise ValueError(f"Condition '{condition}' is not active on this character")
        del char.conditions[cond]
        if cond in char.penalties:
            del char.penalties[cond]

        await self._sync_aggregate(char, lambda agg: agg.remove_condition(cond))
        return char

    async def cast_spell(
        self,
        character_id: str,
        spell_name: str,
        slot_level: int = 1,
        session_id: str = "",
    ) -> CharacterRecord:
        char = self.get_character(character_id)
        if not char:
            raise KeyError(f"Character '{character_id}' not found")
        avail = char.spell_slots.get(slot_level, 0)
        if avail <= 0:
            raise ValueError(
                f"INSUFFICIENT_SPELL_SLOTS: Character '{character_id}' has 0 level {slot_level} spell slots remaining to cast '{spell_name}'"
            )
        char.spell_slots[slot_level] = avail - 1

        await self._sync_aggregate(
            char, lambda agg: agg.cast_spell(spell_name, slot_level, session_id)
        )
        return char

    async def prepare_spell(
        self,
        character_id: str,
        spell_name: str,
        is_prepared: bool = True,
        spell_level: int | None = None,
        session_id: str = "",
    ) -> CharacterRecord:
        char = self.get_character(character_id)
        if not char:
            raise KeyError(f"Character '{character_id}' not found")
        if is_prepared:
            if spell_name not in char.prepared_spells:
                char.prepared_spells.append(spell_name)
            if spell_name not in char.spellbook:
                char.spellbook.append(spell_name)
            await self._sync_aggregate(
                char, lambda agg: agg.prepare_spell(spell_name, spell_level, session_id)
            )
        else:
            char.prepared_spells = [s for s in char.prepared_spells if s != spell_name]
            await self._sync_aggregate(
                char,
                lambda agg: (
                    agg.unprepare_spell(spell_name) if hasattr(agg, "unprepare_spell") else None
                ),
            )
        return char
