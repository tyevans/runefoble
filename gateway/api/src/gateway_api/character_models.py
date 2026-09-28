"""Pydantic schemas and serialization models for character management."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateCharacterRequest(BaseModel):
    id: str | None = None
    name: str = Field(..., min_length=1, max_length=100)
    character_class: str = Field(default="Fighter", alias="characterClass")
    subclass: str | None = None
    level: int = Field(default=1, ge=1, le=20)
    current_hp: int | None = Field(default=None, alias="currentHp")
    max_hp: int = Field(default=10, ge=1, alias="maxHp")
    armor_class: int = Field(default=10, ge=1, alias="armorClass")
    speed: int = Field(default=30, ge=0)
    campaign_id: str | None = Field(default=None, alias="campaignId")
    portrait_url: str | None = Field(default=None, alias="portraitUrl")

    model_config = ConfigDict(populate_by_name=True)


class AssignCampaignRequest(BaseModel):
    campaign_id: str | None = Field(default=None, alias="campaignId")
    campaign_title: str | None = Field(default=None, alias="campaignTitle")

    model_config = ConfigDict(populate_by_name=True)


class CharacterResponse(BaseModel):
    id: str
    name: str
    character_class: str
    subclass: str | None = None
    level: int
    current_hp: int
    max_hp: int
    armor_class: int
    speed: int = 30
    campaign_id: str | None = None
    campaign_title: str | None = None
    owner_id: str = ""
    portrait_url: str | None = None

    # CamelCase mirrors for frontend compatibility
    characterClass: str | None = None
    currentHp: int | None = None
    maxHp: int | None = None
    armorClass: int | None = None
    campaignId: str | None = None
    campaignTitle: str | None = None
    ownerId: str | None = None
    portraitUrl: str | None = None

    model_config = ConfigDict(populate_by_name=True)

    def model_post_init(self, __context: Any) -> None:
        if self.characterClass is None:
            self.characterClass = self.character_class
        if self.currentHp is None:
            self.currentHp = self.current_hp
        if self.maxHp is None:
            self.maxHp = self.max_hp
        if self.armorClass is None:
            self.armorClass = self.armor_class
        if self.campaignId is None:
            self.campaignId = self.campaign_id
        if self.campaignTitle is None:
            self.campaignTitle = self.campaign_title
        if self.ownerId is None:
            self.ownerId = self.owner_id
        if self.portraitUrl is None:
            self.portraitUrl = self.portrait_url


__all__ = [
    "AssignCampaignRequest",
    "CharacterResponse",
    "CreateCharacterRequest",
]
