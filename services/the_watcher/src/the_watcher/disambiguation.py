"""Target disambiguation engine for resolving ambiguous speech intents."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import uuid4

from the_watcher.models import CandidateTarget, CompoundActionNode, EntityTarget


@dataclass
class PendingDisambiguation:
    disambiguation_id: str
    session_id: str
    campaign_id: str | None
    speaker_id: str
    speaker_name: str
    transcript: str
    action_type: str
    ambiguous_target: str
    candidates: list[CandidateTarget]
    clarification_prompt: str
    actions: list[CompoundActionNode] = field(default_factory=list)


class DisambiguationEngine:
    """Detects ambiguous targets from board entities and manages clarification workflows."""

    def __init__(self) -> None:
        self._pending: dict[str, PendingDisambiguation] = {}

    def extract_target_words(self, target_phrase: str) -> list[str]:
        """Extract meaningful target keywords excluding articles and common fillers."""
        cleaned = re.sub(
            r"\b(the|a|an|at|towards|near|to|my|with|this|that)\b", " ", target_phrase, flags=re.I
        )
        words = [w.strip().lower() for w in re.findall(r"\b\w+\b", cleaned) if len(w.strip()) > 1]
        return words

    def find_candidates(
        self,
        target_phrase: str,
        entities: list[EntityTarget],
        from_x: int | None = None,
        from_y: int | None = None,
    ) -> list[CandidateTarget]:
        """Find matching entities for a target phrase.

        If target_phrase specifies a distinguishing descriptor (e.g. 'goblin archer'),
        only entities matching all specified keywords are selected.
        If target_phrase is generic (e.g. 'goblin') and matches multiple entities,
        all matching entities are returned as disambiguation candidates.
        """
        words = self.extract_target_words(target_phrase)
        if not words or not entities:
            return []

        scored_candidates: list[tuple[int, EntityTarget]] = []
        for entity in entities:
            entity_corpus = f"{entity.name} {entity.tag or ''} {entity.descriptor or ''}".lower()
            match_count = sum(1 for w in words if w in entity_corpus)
            if match_count > 0:
                scored_candidates.append((match_count, entity))

        if not scored_candidates:
            return []

        # Find the highest score (e.g. if 'goblin archer' matches 2 words, prefer that over 1 word)
        max_score = max(score for score, _ in scored_candidates)
        best_matches = [entity for score, entity in scored_candidates if score == max_score]

        candidates: list[CandidateTarget] = []
        for e in best_matches:
            # Build natural descriptor
            if e.descriptor:
                descriptor = e.descriptor
            elif e.tag:
                descriptor = f"{e.tag} at ({e.x}, {e.y})"
            else:
                descriptor = f"{e.name} at ({e.x}, {e.y})"

            distance_ft = None
            if from_x is not None and from_y is not None:
                distance_ft = max(abs(e.x - from_x), abs(e.y - from_y)) * 5

            candidates.append(
                CandidateTarget(
                    id=e.id,
                    name=e.name,
                    tag=e.tag,
                    descriptor=descriptor,
                    x=e.x,
                    y=e.y,
                    distance_ft=distance_ft,
                    preview_coordinates=(e.x, e.y),
                )
            )

        return candidates

    def generate_clarification_prompt(
        self, target_phrase: str, candidates: list[CandidateTarget]
    ) -> str:
        """Generate an immersive, audible clarification prompt.

        Example: 'Which goblin? The archer by the pillar or the shaman on the altar?'
        """
        words = self.extract_target_words(target_phrase)
        head_noun = words[0] if words else target_phrase.strip()

        descriptors: list[str] = []
        for c in candidates:
            desc = c.descriptor.strip()
            # Prefix with 'the' if not already present
            if not desc.lower().startswith("the "):
                desc = f"the {desc}"
            # Lowercase the leading article for joining
            descriptors.append(desc[0].upper() + desc[1:])

        if len(descriptors) == 2:
            options_text = f"{descriptors[0]} or {descriptors[1].lower()}?"
        elif len(descriptors) > 2:
            options_text = (
                ", ".join(d.lower() for d in descriptors[:-1]) + f", or {descriptors[-1].lower()}?"
            )
            options_text = options_text[0].upper() + options_text[1:]
        else:
            options_text = f"{descriptors[0]}?"

        return f"Which {head_noun}? {options_text}"

    def register_disambiguation(
        self,
        session_id: str,
        speaker_id: str,
        speaker_name: str,
        transcript: str,
        action_type: str,
        ambiguous_target: str,
        candidates: list[CandidateTarget],
        clarification_prompt: str,
        actions: list[CompoundActionNode],
        campaign_id: str | None = None,
    ) -> PendingDisambiguation:
        """Register a pending disambiguation request in memory."""
        d_id = f"disambig-{uuid4().hex[:12]}"
        pending = PendingDisambiguation(
            disambiguation_id=d_id,
            session_id=session_id,
            campaign_id=campaign_id,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            transcript=transcript,
            action_type=action_type,
            ambiguous_target=ambiguous_target,
            candidates=candidates,
            clarification_prompt=clarification_prompt,
            actions=actions,
        )
        self._pending[d_id] = pending
        return pending

    def get_pending(self, disambiguation_id: str) -> PendingDisambiguation | None:
        """Retrieve a pending disambiguation by ID."""
        return self._pending.get(disambiguation_id)

    def resolve(
        self,
        disambiguation_id: str,
        selected_candidate_id: str | None = None,
        selected_target: str | None = None,
    ) -> tuple[PendingDisambiguation, CandidateTarget]:
        """Resolve a pending disambiguation by matching candidate id or name."""
        pending = self._pending.get(disambiguation_id)
        if pending is None:
            raise KeyError(
                f"Disambiguation ID '{disambiguation_id}' not found or already resolved."
            )

        matched_candidate: CandidateTarget | None = None

        if selected_candidate_id:
            for c in pending.candidates:
                if c.id == selected_candidate_id:
                    matched_candidate = c
                    break

        if matched_candidate is None and selected_target:
            target_norm = selected_target.strip().lower()
            for c in pending.candidates:
                if (
                    target_norm in c.id.lower()
                    or target_norm in c.name.lower()
                    or target_norm in c.descriptor.lower()
                    or (c.tag and target_norm in c.tag.lower())
                ):
                    matched_candidate = c
                    break

        # Fallback to first candidate if not precisely matched
        if matched_candidate is None:
            matched_candidate = pending.candidates[0]

        # Update action nodes
        for node in pending.actions:
            if node.requires_disambiguation or node.target in (pending.ambiguous_target, None):
                node.target = matched_candidate.descriptor or matched_candidate.name
                node.parameters["target"] = matched_candidate.descriptor or matched_candidate.name
                node.parameters["target_id"] = matched_candidate.id
                node.parameters["target_x"] = matched_candidate.x
                node.parameters["target_y"] = matched_candidate.y
                node.requires_disambiguation = False
                node.candidates = []

        # Remove from pending once resolved
        self._pending.pop(disambiguation_id, None)

        return pending, matched_candidate
