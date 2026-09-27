"""Party Codex cross-referencing and redstring knowledge graph linking."""

import logging
import re
from typing import Any
from uuid import UUID

from campaign_lore.extraction import classify_entity_type, extract_proper_nouns
from campaign_lore.retrieval import LoreRetrievalEngine

logger = logging.getLogger(__name__)


class CodexCrossReferencer:
    """Detects entities in codex markdown and cross-references them against redstring graph."""

    def __init__(self, retrieval_engine: LoreRetrievalEngine) -> None:
        self.retrieval_engine = retrieval_engine

    async def cross_reference_content(
        self,
        campaign_id: UUID,
        content: str,
    ) -> dict[str, Any]:
        """Scan codex markdown content, identify entity references, and generate hyperlinked content."""
        # Query known entities in redstring graph for this campaign
        known_entities = await self.retrieval_engine.graph.find_entities(campaign_id)
        entity_map = {e.name.lower(): e for e in known_entities}

        detected_entities: list[dict[str, Any]] = []
        seen_entity_ids: set[str] = set()

        # Check known entities from the redstring graph
        for ent in entity_map.values():
            names_to_try = [ent.name]
            if ent.name.startswith("The ") and len(ent.name) > 6:
                names_to_try.append(ent.name[4:])
            for n in names_to_try:
                pattern = re.compile(r"\b" + re.escape(n) + r"\b", re.IGNORECASE)
                if pattern.search(content):
                    str_id = str(ent.id)
                    if str_id not in seen_entity_ids:
                        seen_entity_ids.add(str_id)
                        detected_entities.append(
                            {
                                "id": str_id,
                                "name": n,
                                "entity_type": ent.entity_type,
                                "source": "knowledge_graph",
                            }
                        )
                    break

        # Also extract any proper nouns not yet in the graph and classify them
        extracted_nouns = extract_proper_nouns(content)
        for noun in extracted_nouns:
            if noun.lower() not in entity_map:
                ent_type = classify_entity_type(noun)
                detected_entities.append(
                    {
                        "id": f"entity-{noun.lower().replace(' ', '-')}",
                        "name": noun,
                        "entity_type": ent_type,
                        "source": "heuristic_extraction",
                    }
                )

        # Generate illuminated content with markdown hyperlinks for known entities
        illuminated = content
        for ent in detected_entities:
            name = ent["name"]
            ent_id = ent["id"]
            # Replace unlinked occurrences with lore link
            pattern = re.compile(rf"(?<!\[)\b({re.escape(name)})\b(?!\])", re.IGNORECASE)
            illuminated = pattern.sub(rf"[\1](#lore/entity/{ent_id})", illuminated)

        return {
            "illuminated_content": illuminated,
            "linked_entities": detected_entities,
            "linked_entity_ids": [e["id"] for e in detected_entities],
        }
