"""Lore domain events for Runefoble worldbuilding and redstring knowledge graph indexing."""

from typing import Any
from uuid import UUID

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class LoreDocumentIngested(BaseRunefobleEvent):
    """Emitted when a new campaign lore markdown/text document is ingested into the knowledge base."""

    event_type: str = "LoreDocumentIngested"
    document_id: UUID = Field(description="Unique document aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the lore belongs")
    title: str = Field(description="Title or heading of the lore document")
    content: str = Field(description="Raw markdown/text content of the worldbuilding document")
    is_secret: bool = Field(default=False, description="Whether this lore is restricted to DMs/GMs")
    author_id: str | None = Field(default=None, description="User ID of author or DM")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata attributes"
    )


@register_event
class EntitiesExtracted(BaseRunefobleEvent):
    """Emitted when entities and relationships are extracted from a lore document via redstring."""

    event_type: str = "EntitiesExtracted"
    document_id: UUID = Field(description="Source document aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the lore belongs")
    entities: list[dict[str, Any]] = Field(
        default_factory=list, description="Extracted entity dictionaries"
    )
    relationships: list[dict[str, Any]] = Field(
        default_factory=list, description="Extracted relationship dictionaries"
    )


@register_event
class AliasesConsolidated(BaseRunefobleEvent):
    """Emitted when synonymous entity titles and aliases are consolidated into canonical nodes."""

    event_type: str = "AliasesConsolidated"
    campaign_id: UUID = Field(description="Campaign to which the lore belongs")
    canonical_entity_id: UUID = Field(description="Canonical entity UUID")
    canonical_name: str = Field(description="Canonical name of the entity")
    alias_entity_id: UUID = Field(description="Alias entity UUID merged into canonical")
    alias_name: str = Field(description="Alias name or title")
    document_id: UUID | None = Field(
        default=None, description="Optional document that triggered consolidation"
    )
    reason: str = Field(
        default="alias consolidation", description="Rationale for entity consolidation"
    )


@register_event
class HandoutGenerated(BaseRunefobleEvent):
    """Emitted when a diegetic handout (letter, decree, bounty, scroll) is forged."""

    aggregate_type: str = "DiegeticHandout"
    handout_id: UUID = Field(description="Unique handout aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the handout belongs")
    title: str = Field(description="Title or subject of the handout")
    handout_type: str = Field(
        default="letter",
        description="Type of document (letter, decree, bounty, crypt_map, scroll)",
    )
    paper_texture: str = Field(default="weathered_parchment", description="Texture style")
    calligraphy_font: str = Field(default="royal_chancery", description="Calligraphy typeface")
    content: str = Field(description="Visible content body of the document")
    has_wax_seal: bool = Field(default=True, description="Whether the document is sealed with wax")
    wax_seal: dict[str, Any] = Field(
        default_factory=dict,
        description="Wax seal configuration, color, stamp symbol, and physics",
    )
    has_invisible_ink: bool = Field(
        default=False, description="Whether invisible ink layer is present"
    )
    invisible_ink: dict[str, Any] | None = Field(
        default=None, description="Invisible ink secret text and properties"
    )
    created_by: str | None = Field(default=None, description="User ID of creator")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata attributes"
    )


@register_event
class WaxSealBroken(BaseRunefobleEvent):
    """Emitted when a player or DM breaks the wax seal on a diegetic handout."""

    aggregate_type: str = "DiegeticHandout"
    handout_id: UUID = Field(description="Unique handout aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the handout belongs")
    broken_by: str = Field(description="User or character identifier who cracked the seal")
    break_force: float = Field(default=1.0, description="Force applied to break seal")
    haptic_audio_effect: str = Field(
        default="wax_crack_crisp_01.wav",
        description="Synthesized audio soundscape asset",
    )
    revealed_content_preview: str = Field(default="", description="Snippet of revealed text")


@register_event
class InvisibleInkRevealed(BaseRunefobleEvent):
    """Emitted when hidden runes or text are revealed via UV torchlight cursor."""

    aggregate_type: str = "DiegeticHandout"
    handout_id: UUID = Field(description="Unique handout aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the handout belongs")
    revealed_by: str = Field(description="User ID who shined the torchlight")
    secret_text: str = Field(description="The hidden runes or message revealed")
    uv_intensity: float = Field(default=1.0, description="UV intensity ratio")


@register_event
class RelicForged(BaseRunefobleEvent):
    """Emitted when a 3D interactive relic is forged or added to the campaign lore."""

    aggregate_type: str = "Relic"
    relic_id: UUID = Field(description="Unique relic aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the relic belongs")
    name: str = Field(description="Name of the magical relic or artifact")
    relic_type: str = Field(
        default="amulet",
        description="Type of relic (amulet, dagger, puzzle_box, ring, chalice)",
    )
    model_geometry: str = Field(
        default="amulet_sunken_spire", description="Geometry identifier for 3D mesh"
    )
    shader_properties: dict[str, Any] = Field(
        default_factory=dict,
        description="PBR shader parameters (metallic, roughness, emissive)",
    )
    runes: list[dict[str, Any]] = Field(
        default_factory=list, description="Engraved runes, 3D positions, and translations"
    )
    is_secret: bool = Field(default=False, description="Whether secret/unidentified DM lore")
    created_by: str | None = Field(default=None, description="User ID who created or placed relic")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata attributes"
    )


@register_event
class RelicInspected(BaseRunefobleEvent):
    """Emitted when a player rotates, examines, and inspects an interactive 3D relic."""

    aggregate_type: str = "Relic"
    relic_id: UUID = Field(description="Unique relic aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the relic belongs")
    inspected_by: str = Field(description="User ID or character who inspected the relic")
    name: str = Field(description="Name of the relic")
    model_geometry: str = Field(description="Geometry identifier")
    shader_properties: dict[str, Any] = Field(
        default_factory=dict, description="Active shader parameters"
    )
    discovered_runes: list[dict[str, Any]] = Field(
        default_factory=list, description="Runes inspected during this session"
    )
    inspection_notes: str | None = Field(default=None, description="Observations or lore recorded")


@register_event
class RelicRuneTranslated(BaseRunefobleEvent):
    """Emitted when an ancient rune on a relic is translated or deciphered."""

    aggregate_type: str = "Relic"
    relic_id: UUID = Field(description="Unique relic aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the relic belongs")
    rune_id: str = Field(description="Identifier of the rune")
    translated_by: str = Field(description="User ID or character translating")
    original_inscription: str = Field(description="Original rune glyph or text")
    translation: str = Field(description="Deciphered meaning or spell incantation")


@register_event
class AtlasPinCreated(BaseRunefobleEvent):
    """Emitted when a geographical milestone pin is placed on the campaign world atlas."""

    aggregate_type: str = "Atlas"
    event_type: str = "AtlasPinCreated"
    pin_id: UUID = Field(description="Unique identifier for the atlas pin")
    campaign_id: UUID = Field(description="Campaign to which the atlas belongs")
    title: str = Field(description="Title or label of the milestone pin")
    layer: str = Field(
        default="continental", description="Map layer (continental, regional, municipal)"
    )
    coordinates: dict[str, float] = Field(description="Projected spatial coordinates {x, y}")
    description: str = Field(default="", description="Detailed narrative description or recap")
    era: str | None = Field(default=None, description="Campaign era or chronological milestone tag")
    session_id: str | None = Field(default=None, description="Linked session identifier")
    linked_entity_ids: list[str] = Field(
        default_factory=list, description="Linked redstring lore entity IDs"
    )
    created_by: str | None = Field(default=None, description="User or character who placed the pin")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary visual or thematic metadata"
    )


@register_event
class AtlasPinUpdated(BaseRunefobleEvent):
    """Emitted when an atlas milestone pin properties are updated."""

    aggregate_type: str = "Atlas"
    event_type: str = "AtlasPinUpdated"
    pin_id: UUID = Field(description="Unique identifier for the atlas pin")
    campaign_id: UUID = Field(description="Campaign to which the atlas belongs")
    title: str | None = None
    coordinates: dict[str, float] | None = None
    description: str | None = None
    era: str | None = None
    linked_entity_ids: list[str] | None = None
    metadata: dict[str, Any] | None = None


@register_event
class AtlasLayerToggled(BaseRunefobleEvent):
    """Emitted when an atlas map layer visibility or active level is toggled."""

    aggregate_type: str = "Atlas"
    event_type: str = "AtlasLayerToggled"
    campaign_id: UUID = Field(description="Campaign to which the atlas belongs")
    layer: str = Field(
        description="Layer toggled (continental, regional, municipal, contested_boundaries)"
    )
    is_visible: bool = Field(description="Whether the layer is enabled/visible")
    toggled_by: str | None = Field(default=None, description="User who toggled the layer")


@register_event
class AtlasTerritoryUpdated(BaseRunefobleEvent):
    """Emitted when a geopolitical territory boundary polygon or ownership is created or updated."""

    aggregate_type: str = "Atlas"
    event_type: str = "AtlasTerritoryUpdated"
    territory_id: UUID = Field(description="Unique territory identifier")
    campaign_id: UUID = Field(description="Campaign to which the territory belongs")
    name: str = Field(description="Territory or realm name")
    layer: str = Field(default="continental", description="Layer scope")
    polygon_coordinates: list[list[float]] = Field(
        description="List of [x, y] coordinates defining the polygon"
    )
    owner_faction: str = Field(default="Neutral", description="Ruling faction or entity")
    is_contested: bool = Field(default=False, description="Whether border is contested / disputed")
    era: str | None = Field(
        default=None, description="Era or chronological epoch for this boundary"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Visual styling and banner attributes"
    )


@register_event
class CodexEntryPublished(BaseRunefobleEvent):
    """Emitted when a collaborative party codex entry is drafted, published, or revised."""

    aggregate_type: str = "Codex"
    event_type: str = "CodexEntryPublished"
    entry_id: UUID = Field(description="Unique codex entry aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the codex entry belongs")
    title: str = Field(description="Codex entry title")
    content: str = Field(description="Markdown body of the journal or lore note")
    privacy: str = Field(
        default="private", description="Privacy level: private, party_shared, or public"
    )
    author_id: str = Field(description="Author user identifier")
    era: str | None = Field(default=None, description="Campaign era or chronological tag")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    linked_entity_ids: list[str] = Field(
        default_factory=list, description="Cross-referenced redstring entities"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata attributes"
    )


@register_event
class CodexEntryUpdated(BaseRunefobleEvent):
    """Emitted when an existing codex entry content or privacy status is updated."""

    aggregate_type: str = "Codex"
    event_type: str = "CodexEntryUpdated"
    entry_id: UUID = Field(description="Unique codex entry aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the codex entry belongs")
    title: str | None = None
    content: str | None = None
    privacy: str | None = None
    era: str | None = None
    tags: list[str] | None = None
    linked_entity_ids: list[str] | None = None
    updated_by: str | None = None
    metadata: dict[str, Any] | None = None
