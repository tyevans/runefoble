"""Target disambiguation for ambiguous speech intents.

``DisambiguationEngine`` holds the pure matching rules. ``DisambiguationStore`` keeps the
open requests in the ``DisambiguationAggregate`` (TASK-0568), so they survive a restart.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from uuid import uuid4

from eventsource.application.aggregates.repository import AggregateRepository
from runefoble_platform.aggregate_loading import load_if_exists, load_or_create
from the_watcher.copilot_state.disambiguations import (
    DisambiguationAggregate,
    DisambiguationNotFoundError,
    PendingDisambiguation,
    disambiguation_board_id,
)
from the_watcher.models import CandidateTarget, CompoundActionNode, EntityTarget


class DisambiguationEngine:
    """Detects ambiguous targets from board entities and builds clarification prompts."""

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

    def select_candidate(
        self,
        pending: PendingDisambiguation,
        selected_candidate_id: str | None = None,
        selected_target: str | None = None,
    ) -> CandidateTarget:
        """Match the player's choice by candidate id, then by name. Fall back to the first."""
        if selected_candidate_id:
            for c in pending.candidates:
                if c.id == selected_candidate_id:
                    return c

        if selected_target:
            target_norm = selected_target.strip().lower()
            for c in pending.candidates:
                if (
                    target_norm in c.id.lower()
                    or target_norm in c.name.lower()
                    or target_norm in c.descriptor.lower()
                    or (c.tag and target_norm in c.tag.lower())
                ):
                    return c

        return pending.candidates[0]

    def apply_resolution(
        self, pending: PendingDisambiguation, chosen: CandidateTarget
    ) -> PendingDisambiguation:
        """Return a copy of the request whose ambiguous action nodes name the chosen target."""
        resolved = pending.model_copy(deep=True)
        for node in resolved.actions:
            if node.requires_disambiguation or node.target in (pending.ambiguous_target, None):
                _bind_node(node, chosen)
        return resolved


def _bind_node(node: CompoundActionNode, chosen: CandidateTarget) -> None:
    node.target = chosen.descriptor or chosen.name
    node.parameters["target"] = chosen.descriptor or chosen.name
    node.parameters["target_id"] = chosen.id
    node.parameters["target_x"] = chosen.x
    node.parameters["target_y"] = chosen.y
    node.requires_disambiguation = False
    node.candidates = []


class DisambiguationStore:
    """Opens and resolves disambiguation requests through the aggregate repository."""

    def __init__(
        self,
        repo: Callable[[], AggregateRepository[DisambiguationAggregate]],
        engine: DisambiguationEngine,
    ) -> None:
        self._repo = repo
        self._engine = engine

    async def register(
        self,
        *,
        session_id: str,
        campaign_id: str | None,
        speaker_id: str,
        speaker_name: str,
        transcript: str,
        action_type: str,
        ambiguous_target: str,
        candidates: list[CandidateTarget],
        clarification_prompt: str,
        actions: list[CompoundActionNode],
    ) -> PendingDisambiguation:
        """Record a new open request for the session and return it."""
        repo = self._repo()
        board = await load_or_create(repo, disambiguation_board_id(session_id), _new_board)
        pending = PendingDisambiguation(
            disambiguation_id=f"disambig-{uuid4().hex[:12]}",
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
        board.open_request(pending)
        await repo.save(board)
        return pending

    async def resolve(
        self,
        session_id: str,
        disambiguation_id: str,
        selected_candidate_id: str | None = None,
        selected_target: str | None = None,
    ) -> tuple[PendingDisambiguation, CandidateTarget]:
        """Close an open request. Return its resolved copy and the chosen candidate.

        Raise DisambiguationNotFoundError when the request is unknown or already resolved.
        """
        repo = self._repo()
        board = await load_if_exists(repo, disambiguation_board_id(session_id))
        pending = board.find(disambiguation_id) if board is not None else None
        if board is None or pending is None:
            raise DisambiguationNotFoundError(
                f"Disambiguation ID '{disambiguation_id}' not found or already resolved."
            )
        chosen = self._engine.select_candidate(pending, selected_candidate_id, selected_target)
        board.resolve(disambiguation_id, chosen.id)
        await repo.save(board)
        return self._engine.apply_resolution(pending, chosen), chosen


def _new_board(board_id) -> DisambiguationAggregate:
    return DisambiguationAggregate(aggregate_id=board_id)
