"""Worldbuilding Entity & Alias Extraction powered by redstring."""

import logging
import re
from uuid import UUID, uuid4

import redstring
from pydantic import BaseModel

logger = logging.getLogger(__name__)

ALIAS_PATTERNS = [
    r"([A-Z][a-zA-Z\s]+?)\s+is\s+also\s+known\s+as\s+([A-Z][a-zA-Z\s]+?)(?:\.|\,|$)",
    r"([A-Z][a-zA-Z\s]+?)\s+known\s+as\s+([A-Z][a-zA-Z\s]+?)(?:\.|\,|$)",
    r"([A-Z][a-zA-Z\s]+?)\s+\(also\s+called\s+([A-Z][a-zA-Z\s]+?)\)",
]
PROPER_NOUN_REGEX = re.compile(
    r"\b(?:The\s+)?(?:Sir\s+|Lady\s+|Lord\s+|Archmage\s+|King\s+|Queen\s+)?[A-Z][a-z]+(?:\s+(?:of\s+)?[A-Z][a-z]+)*\b"
)
RELATIONSHIP_REGEX = re.compile(
    r"([A-Z][a-zA-Z\s]+?)\s+(guards|rules|located in|allied with|serves)\s+([A-Z][a-zA-Z\s]+?)(?:\.|\,|$)"
)
NPC_TITLES = ("sir", "lady", "lord", "knight", "king", "queen", "mage")
LOCATION_KEYWORDS = ("citadel", "keep", "forest", "castle", "city", "tower", "mount", "lake")
FACTION_KEYWORDS = ("order", "guild", "cult", "cabal", "clan", "alliance")


def classify_entity_type(name: str) -> str:
    """Classify an entity type based on lexical keywords and titles."""
    lower_name = name.lower()
    if any(t in lower_name for t in NPC_TITLES):
        return "npc"
    if any(loc in lower_name for loc in LOCATION_KEYWORDS):
        return "location"
    if any(fac in lower_name for fac in FACTION_KEYWORDS):
        return "faction"
    return "entity"


def extract_alias_pairs(text: str) -> list[tuple[str, str]]:
    """Extract canonical and alias pairs from text using heuristic regex patterns."""
    pairs = []
    for pat in ALIAS_PATTERNS:
        for m in re.finditer(pat, text):
            pairs.append((m.group(1).strip(), m.group(2).strip()))
    return pairs


def extract_proper_nouns(text: str) -> list[str]:
    """Extract unique proper nouns matching worldbuilding entity heuristics."""
    found: list[str] = []
    seen: set[str] = set()
    for name in PROPER_NOUN_REGEX.findall(text):
        clean = name.strip()
        if len(clean) >= 3 and clean not in seen:
            seen.add(clean)
            found.append(clean)
    return found


def extract_relationships(text: str) -> list[tuple[str, str, str]]:
    """Extract heuristic relational connections from text."""
    return [
        (m.group(1).strip(), m.group(2).strip(), m.group(3).strip())
        for m in RELATIONSHIP_REGEX.finditer(text)
    ]


async def get_or_create_entity(
    graph: redstring.InMemoryGraphStore,
    campaign_id: UUID,
    name: str,
    prov: redstring.Provenance,
    entity_type: str = "npc",
) -> UUID:
    """Find existing entity by name or create a new entity in graph store."""
    ents = await graph.find_entities(campaign_id, name=name.lower().strip())
    if ents:
        return ents[0].id
    new_id = uuid4()
    await graph.upsert_entity(
        redstring.Entity(
            id=new_id,
            tenant_id=campaign_id,
            name=name,
            normalized_name=name.lower().strip(),
            entity_type=entity_type,
            provenance=prov,
        )
    )
    return new_id


class WorldbuildingLlmProvider:
    """Extraction provider extracting entities, relationships, and aliases from worldbuilding text."""

    def __init__(self, model: str = "runefoble/worldbuilding-ner-v1") -> None:
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def extract[S: BaseModel](
        self,
        text: str,
        schema: type[S],
        *,
        system_prompt: str | None = None,
    ) -> S:
        """Extract structured entities and relationships from worldbuilding lore text."""
        entities: list[redstring.ExtractedEntity] = []
        relationships: list[redstring.ExtractedRelationship] = []

        alias_pairs = extract_alias_pairs(text)
        proper_nouns = extract_proper_nouns(text)
        seen_names = set(proper_nouns)

        for name in proper_nouns:
            etype = classify_entity_type(name)
            entities.append(
                redstring.ExtractedEntity(
                    name=name,
                    entity_type=etype,
                    description=f"{etype.upper()} mentioned in campaign lore",
                    confidence=0.9,
                )
            )

        for canon, alias in alias_pairs:
            for n in (canon, alias):
                if n not in seen_names:
                    entities.append(
                        redstring.ExtractedEntity(name=n, entity_type="npc", confidence=0.95)
                    )
                    seen_names.add(n)
            relationships.append(
                redstring.ExtractedRelationship(
                    source_name=canon,
                    target_name=alias,
                    relationship_type="alias_of",
                    confidence=0.99,
                )
            )

        for src, rel, tgt in extract_relationships(text):
            relationships.append(
                redstring.ExtractedRelationship(
                    source_name=src,
                    target_name=tgt,
                    relationship_type=rel,
                    confidence=0.85,
                )
            )

        return schema.model_validate({"entities": entities, "relationships": relationships})


__all__ = [
    "ALIAS_PATTERNS",
    "FACTION_KEYWORDS",
    "LOCATION_KEYWORDS",
    "NPC_TITLES",
    "PROPER_NOUN_REGEX",
    "RELATIONSHIP_REGEX",
    "WorldbuildingLlmProvider",
    "classify_entity_type",
    "extract_alias_pairs",
    "extract_proper_nouns",
    "extract_relationships",
    "get_or_create_entity",
]
