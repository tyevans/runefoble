"""Worldbuilding entity and alias extraction using regex patterns (no model call)."""

import logging
import re
from uuid import UUID, uuid5

import redstring

logger = logging.getLogger(__name__)

ALIAS_PATTERNS = [
    r"([A-Z][a-zA-Z\s]+?)\s+is\s+also\s+known\s+as\s+([A-Z][a-zA-Z\s]+?)(?:\.|\,|$)",
    r"([A-Z][a-zA-Z\s]+?)\s+known\s+as\s+([A-Z][a-zA-Z\s]+?)(?:\.|\,|$)",
    r"([A-Z][a-zA-Z\s]+?)\s+\(also\s+called\s+([A-Z][a-zA-Z\s]+?)\)",
]
PROPER_NOUN_REGEX = re.compile(
    r"\b(?:The\s+)?(?:Sir\s+|Lady\s+|Lord\s+|Archmage\s+|King\s+|Queen\s+)?[A-Z][a-z]+(?:\s+(?:of\s+(?:the\s+)?)?[A-Z][a-z]+)*\b"
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
        if clean.startswith("The ") and len(clean) > 6:
            without_the = clean[4:].strip()
            if without_the not in seen:
                seen.add(without_the)
                found.append(without_the)
    return found


def extract_relationships(text: str) -> list[tuple[str, str, str]]:
    """Extract heuristic relational connections from text."""
    return [
        (m.group(1).strip(), m.group(2).strip(), m.group(3).strip())
        for m in RELATIONSHIP_REGEX.finditer(text)
    ]


ENTITY_NAMESPACE = uuid5(UUID(int=0), "runefoble.campaign_lore.entity")


def lore_entity_id(campaign_id: UUID, source_id: str, name: str, entity_type: str) -> UUID:
    """Deterministic entity id: the same name and type in the same document keep one id."""
    return uuid5(ENTITY_NAMESPACE, f"{campaign_id}:{source_id}:{name}:{entity_type}")


async def get_or_create_entity(
    graph: redstring.GraphStore,
    campaign_id: UUID,
    name: str,
    source_id: str,
    prov: redstring.Provenance,
    entity_type: str = "npc",
) -> UUID:
    """Find an entity by name, or create it with a deterministic id for the source document."""
    ents = await graph.find_entities(campaign_id, name=name.lower().strip())
    if ents:
        return ents[0].id
    new_id = lore_entity_id(campaign_id, source_id, name, entity_type)
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


def extract_pattern_graph(
    text: str,
) -> tuple[list[redstring.ExtractedEntity], list[redstring.ExtractedRelationship]]:
    """Extract entities, aliases, and relationships from lore text with regex patterns.

    The result is recorded with ExtractionMethod.PATTERN. No model is called.
    """
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

    return entities, relationships


__all__ = [
    "ALIAS_PATTERNS",
    "FACTION_KEYWORDS",
    "LOCATION_KEYWORDS",
    "NPC_TITLES",
    "PROPER_NOUN_REGEX",
    "RELATIONSHIP_REGEX",
    "classify_entity_type",
    "extract_alias_pairs",
    "extract_pattern_graph",
    "extract_proper_nouns",
    "extract_relationships",
    "get_or_create_entity",
    "lore_entity_id",
]
