"""Turn pattern-extracted lore into redstring graph records (PATTERN provenance)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid5

import redstring

from campaign_lore.extraction import classify_entity_type, extract_pattern_graph, lore_entity_id

RELATIONSHIP_NAMESPACE = uuid5(UUID(int=0), "runefoble.campaign_lore.relationship")


@dataclass(frozen=True)
class PatternGraphRecords:
    """Entities and relationships one document contributes, keyed for graph writes."""

    entities: list[redstring.Entity]
    relationships: list[redstring.Relationship]


def build_pattern_graph(
    campaign_id: UUID,
    document_id: UUID,
    content: str,
    observed_at: datetime,
) -> PatternGraphRecords:
    """Extract entities and relationships from text, recorded as ExtractionMethod.PATTERN."""
    source_id = str(document_id)
    extracted_entities, extracted_relationships = extract_pattern_graph(content)
    entities: dict[str, redstring.Entity] = {}

    def add_entity(name: str, etype: str, description: str | None, confidence: float) -> None:
        if name in entities:
            return
        entities[name] = redstring.Entity(
            id=lore_entity_id(campaign_id, source_id, name, etype),
            tenant_id=campaign_id,
            name=name,
            normalized_name=name.lower().strip(),
            entity_type=etype,
            description=description,
            provenance=redstring.Provenance(
                observed_at=observed_at,
                extraction_method=redstring.ExtractionMethod.PATTERN,
                confidence=confidence,
                source_id=source_id,
            ),
        )

    for ext in extracted_entities:
        add_entity(ext.name, ext.entity_type, ext.description, ext.confidence)
    for rel in extracted_relationships:
        for name in (rel.source_name, rel.target_name):
            add_entity(name, classify_entity_type(name), None, rel.confidence)

    relationships: list[redstring.Relationship] = []
    for rel in extracted_relationships:
        src, tgt = entities[rel.source_name], entities[rel.target_name]
        if src.id == tgt.id:
            continue
        relationships.append(
            redstring.Relationship(
                id=uuid5(
                    RELATIONSHIP_NAMESPACE,
                    f"{campaign_id}:{source_id}:{src.id}:{rel.relationship_type}:{tgt.id}",
                ),
                tenant_id=campaign_id,
                source_entity_id=src.id,
                target_entity_id=tgt.id,
                relationship_type=rel.relationship_type,
                source_id=source_id,
                confidence=rel.confidence,
            )
        )
    return PatternGraphRecords(entities=list(entities.values()), relationships=relationships)
