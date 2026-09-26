"""Compound action chaining and multi-clause decomposition engine for The Watcher."""

from __future__ import annotations

import re
from uuid import uuid4

from the_watcher.models import CompoundActionNode
from the_watcher.movement_parser import SpeechIntentParser


class CompoundActionEngine:
    """Decomposes compound voice commands into sequential action nodes and handles partial execution."""

    def __init__(self, parser: SpeechIntentParser | None = None) -> None:
        self._parser = parser or SpeechIntentParser()

        # Vault / jump obstacle patterns: e.g. "jump over the pit", "vault the table", "leap across the chasm"
        self._obstacle_pattern = re.compile(
            r"\b(jump\s+over|vault|leap\s+across|hop\s+over)\s+(?:the\s+|a\s+)?([a-zA-Z0-9_\-\s]+?)(?:$|\s+and|\s+then|\s*[,;])",
            re.IGNORECASE,
        )

    def split_clauses(self, transcript: str) -> list[str]:
        """Split a multi-clause utterance into distinct action clauses."""
        normalized = transcript.strip()
        # Protect coordinate pairs like '5, 7' or '(5, 8)' from comma splitting
        coords_placeholders: list[str] = []

        def save_coord(m: re.Match) -> str:
            coords_placeholders.append(m.group(0))
            return f"__COORD_PAIR_{len(coords_placeholders) - 1}__"

        protected = re.sub(r"\(?\s*\d+\s*,\s*\d+\s*\)?", save_coord, normalized)

        # Split on ' and then ', ' then ', ' and ', ';', or comma (outside coordinate pairs)
        delimiters = re.compile(r"\s+(?:and\s+then|then|and)\s+|[;,]\s*", re.IGNORECASE)
        parts = delimiters.split(protected)

        # Restore coordinate placeholders
        clauses: list[str] = []
        for p in parts:
            clause = p
            for idx, c_val in enumerate(coords_placeholders):
                clause = clause.replace(f"__COORD_PAIR_{idx}__", c_val)
            if clause.strip():
                clauses.append(clause.strip())
        return clauses

    def parse_clause(self, clause: str, speaker_name: str, order: int) -> CompoundActionNode:
        """Parse an individual clause into a CompoundActionNode."""
        node_id = f"node-{uuid4().hex[:8]}"

        # 1. Check obstacle / stunt check: "jump over the pit", "vault the table"
        obs_match = self._obstacle_pattern.search(clause)
        if obs_match:
            action_verb = obs_match.group(1).strip().lower()
            obstacle = obs_match.group(2).strip()
            # Obstacle acrobatics/athletics skill check
            skill = (
                "athletics"
                if "jump" in action_verb or "vault" in action_verb or "leap" in action_verb
                else "acrobatics"
            )
            return CompoundActionNode(
                node_id=node_id,
                order=order,
                action_type="skill_check",
                parameters={
                    "action": "skill_check",
                    "skill": skill,
                    "obstacle": obstacle,
                    "verb": action_verb,
                    "dc": 12,
                    "dice_notation": "1d20",
                },
                target=obstacle,
                description=f"{action_verb} {obstacle} ({skill} check)",
                status="pending",
            )

        # 2. Use base SpeechIntentParser for standard actions
        intent = self._parser.parse_speech_intent(clause, speaker_name)
        target = (
            intent.target
            or intent.parameters.get("target")
            or intent.parameters.get("target_token")
        )

        description = intent.details or f"{intent.action_type.capitalize()} action"

        return CompoundActionNode(
            node_id=node_id,
            order=order,
            action_type=intent.action_type,
            parameters=dict(intent.parameters),
            target=target,
            description=description,
            status="pending",
        )

    def decompose(
        self, transcript: str, speaker_name: str
    ) -> tuple[bool, list[CompoundActionNode]]:
        """Decompose a transcript into sequential compound action nodes.

        Returns (is_compound, nodes).
        """
        clauses = self.split_clauses(transcript)
        if len(clauses) <= 1:
            # Single action
            single_node = self.parse_clause(transcript, speaker_name, order=1)
            return False, [single_node]

        nodes: list[CompoundActionNode] = []
        for idx, clause in enumerate(clauses, start=1):
            node = self.parse_clause(clause, speaker_name, order=idx)
            nodes.append(node)

        return True, nodes

    def execute_plan(
        self,
        session_id: str,
        actions: list[CompoundActionNode],
        speaker_name: str = "Player",
        step_results: dict[str, bool] | None = None,
        rollback_on_failure: bool = True,
    ) -> tuple[str, list[CompoundActionNode], str, str | None]:
        """Execute or simulate execution of a compound action graph.

        Handles sequential execution, detects intermediate failures,
        and coordinates rollback or partial success.

        Returns (status, updated_actions, narrative_summary, failed_node_id).
        """
        step_results = step_results or {}
        failed_node_id: str | None = None
        has_failure = False

        for node in actions:
            if has_failure:
                # Subsequent nodes are aborted because intermediate action failed
                node.status = "aborted"
                continue

            # Check if this node fails
            result = step_results.get(node.node_id)
            # Also allow matching by order or action_type
            if result is None:
                result = step_results.get(str(node.order))
            if result is None:
                result = step_results.get(node.action_type)

            # If not specified in step_results, defaults to True (success)
            if result is False:
                node.status = "failed"
                failed_node_id = node.node_id
                has_failure = True
            else:
                node.status = "completed"

        if has_failure:
            if rollback_on_failure:
                # Mark preceding completed nodes as rolled back
                for node in actions:
                    if node.status == "completed":
                        node.status = "rolled_back"
                overall_status = "rolled_back"
                narrative = (
                    f"{speaker_name}'s action combo failed at step '{failed_node_id}'. "
                    f"Position and actions rolled back to prevent desynchronization."
                )
            else:
                overall_status = "partial_failure"
                narrative = (
                    f"{speaker_name}'s action combo suffered a partial failure at step '{failed_node_id}'. "
                    f"Completed steps stand, subsequent actions aborted."
                )
            return overall_status, actions, narrative, failed_node_id

        overall_status = "completed"
        narrative = f"{speaker_name} successfully resolved all combo actions: " + " -> ".join(
            n.description for n in actions
        )
        return overall_status, actions, narrative, None
