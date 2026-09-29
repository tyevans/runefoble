"""In-memory character metadata store and SpiceDB Zanzibar query integration."""

from __future__ import annotations

import uuid
from typing import Any

from gateway_api.character_defaults import DEFAULT_CHARACTERS
from gateway_api.character_models import (
    AssignCampaignRequest,
    CharacterResponse,
    CreateCharacterRequest,
)
from gateway_api.character_record import CharacterRecord
from gateway_api.character_store_mutations import CharacterMutationsMixin


class CharacterStore(CharacterMutationsMixin):
    """In-memory character store with Zanzibar SpiceDB integration."""

    def __init__(self) -> None:
        self._characters: dict[str, CharacterRecord] = {}
        self.load_defaults()

    def load_defaults(self) -> None:
        for item in DEFAULT_CHARACTERS:
            self.create_character(**item)

    async def ensure_default_tuples(self, client: Any) -> None:
        for d in DEFAULT_CHARACTERS:
            try:
                await client.write_relationship(
                    "character", d["id"], "owner", "user", d["owner_id"]
                )
                if d.get("campaign_id"):
                    await client.write_relationship(
                        "character", d["id"], "campaign", "campaign", d["campaign_id"]
                    )
            except Exception:
                pass

    def create_character(
        self,
        id: str,
        name: str,
        character_class: str,
        subclass: str | None = None,
        level: int = 1,
        current_hp: int = 10,
        max_hp: int = 10,
        armor_class: int = 10,
        speed: int = 30,
        campaign_id: str | None = None,
        owner_id: str = "",
        portrait_url: str | None = None,
        **kwargs: Any,
    ) -> CharacterRecord:
        cid = id or kwargs.get("character_id") or f"char-{uuid.uuid4().hex[:8]}"
        rec = CharacterRecord(
            id=cid,
            name=name,
            character_class=character_class,
            subclass=subclass,
            level=level,
            current_hp=current_hp,
            max_hp=max_hp,
            armor_class=armor_class,
            speed=speed,
            campaign_id=campaign_id,
            owner_id=owner_id,
            portrait_url=portrait_url,
            is_stand_in_active=kwargs.get("is_stand_in_active", False),
        )
        self._characters[cid] = rec
        return rec

    def create_from_request(self, req: CreateCharacterRequest, owner_id: str) -> CharacterRecord:
        cid = req.id or f"char-{uuid.uuid4().hex[:8]}"
        cur_hp = req.current_hp if req.current_hp is not None else req.max_hp
        return self.create_character(
            id=cid,
            name=req.name,
            character_class=req.character_class,
            subclass=req.subclass,
            level=req.level,
            current_hp=cur_hp,
            max_hp=req.max_hp,
            armor_class=req.armor_class,
            speed=req.speed,
            campaign_id=req.campaign_id,
            owner_id=owner_id,
            portrait_url=req.portrait_url,
            is_stand_in_active=getattr(req, "is_stand_in_active", False),
        )

    def get_character(self, character_id: str) -> CharacterRecord | None:
        return self._characters.get(character_id)

    def list_characters(self) -> list[CharacterRecord]:
        return list(self._characters.values())

    async def list_characters_for_user(
        self, user_id: str, client: Any = None, owned_only: bool = False
    ) -> list[CharacterRecord]:
        if client is None:
            from gateway_api.auth import get_spicedb_client

            client = get_spicedb_client()

        await self.ensure_default_tuples(client)

        result: list[CharacterRecord] = []
        seen: set[str] = set()

        for char in list(self._characters.values()):
            if char.id in seen:
                continue
            if char.owner_id == user_id:
                result.append(char)
                seen.add(char.id)
                continue
            try:
                if await client.check_permission("character", char.id, "owner", "user", user_id):
                    result.append(char)
                    seen.add(char.id)
                    continue
                if not owned_only and await client.check_permission(
                    "character", char.id, "view", "user", user_id
                ):
                    result.append(char)
                    seen.add(char.id)
            except Exception:
                pass

        try:
            rels = await client.read_relationships(resource_type="character", relation="owner")
            for rel in rels:
                if rel.subject_id == user_id and rel.resource_id not in seen:
                    stub = self.create_character(
                        id=rel.resource_id,
                        name=f"Character {rel.resource_id}",
                        character_class="Adventurer",
                        owner_id=user_id,
                    )
                    result.append(stub)
                    seen.add(rel.resource_id)
        except Exception:
            pass

        return result

    def assign_campaign(self, character_id: str, campaign_id: str | None) -> CharacterRecord | None:
        char = self.get_character(character_id)
        if not char:
            return None
        char.campaign_id = campaign_id if campaign_id else None
        return char

    def delete_character(self, character_id: str) -> bool:
        if character_id in self._characters:
            del self._characters[character_id]
            return True
        return False

    def reset(self, load_defaults: bool = True) -> None:
        self._characters.clear()
        if load_defaults:
            self.load_defaults()


character_store = CharacterStore()

__all__ = [
    "DEFAULT_CHARACTERS",
    "AssignCampaignRequest",
    "CharacterRecord",
    "CharacterResponse",
    "CharacterStore",
    "CreateCharacterRequest",
    "character_store",
]
