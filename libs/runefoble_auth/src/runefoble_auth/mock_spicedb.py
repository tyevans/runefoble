"""In-memory mock Zanzibar relationship store and models for tests and offline runs."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Relationship:
    resource_type: str
    resource_id: str
    relation: str
    subject_type: str
    subject_id: str

    def to_tuple_key(self) -> str:
        return f"{self.resource_type}:{self.resource_id}#{self.relation}@{self.subject_type}:{self.subject_id}"

    @classmethod
    def from_tuple_key(cls, key: str) -> "Relationship":
        res, rest = key.split("#", 1)
        res_type, res_id = res.split(":", 1)
        rel, subj = rest.split("@", 1)
        subj_type, subj_id = subj.split(":", 1)
        return cls(res_type, res_id, rel, subj_type, subj_id)


class MockSpiceDBClient:
    """In-memory mock Zanzibar relationship tuple store for tests and offline runs."""

    def __init__(self, endpoint: str = "localhost:50051", token: str = "secret"):
        self.endpoint = endpoint
        self.token = token
        self._tuples: set[str] = set()
        self._schema: str = ""

    def _tuple_key(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> str:
        return f"{resource_type}:{resource_id}#{relation}@{subject_type}:{subject_id}"

    def _find_subjects(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
    ) -> list[tuple[str, str]]:
        prefix = f"{resource_type}:{resource_id}#{relation}@"
        results: list[tuple[str, str]] = []
        for key in self._tuples:
            if key.startswith(prefix):
                subject_part = key[len(prefix) :]
                if ":" in subject_part:
                    s_type, s_id = subject_part.split(":", 1)
                    results.append((s_type, s_id))
        return results

    async def write_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        """Create a relationship tuple in Zanzibar."""
        key = self._tuple_key(resource_type, resource_id, relation, subject_type, subject_id)
        self._tuples.add(key)
        logger.info("SpiceDB tuple written: %s", key)

    async def delete_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        """Remove a relationship tuple."""
        key = self._tuple_key(resource_type, resource_id, relation, subject_type, subject_id)
        self._tuples.discard(key)
        logger.info("SpiceDB tuple deleted: %s", key)

    async def read_relationships(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        relation: str | None = None,
    ) -> list[Relationship]:
        """Query stored relationship tuples matching optional filters."""
        results: list[Relationship] = []
        for key in sorted(self._tuples):
            rel = Relationship.from_tuple_key(key)
            if resource_type and rel.resource_type != resource_type:
                continue
            if resource_id and rel.resource_id != resource_id:
                continue
            if relation and rel.relation != relation:
                continue
            results.append(rel)
        return results

    async def write_schema(self, schema_text: str) -> None:
        """Store mock schema definition."""
        self._schema = schema_text

    async def read_schema(self) -> str:
        """Return mock schema definition."""
        return getattr(self, "_schema", "")

    async def check_permission(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        """Check whether a subject has a specific permission on a resource.

        Evaluates direct relations, owner bypass, and Zanzibar graph hierarchy.
        """
        # 1. Direct relationship check
        direct = self._tuple_key(resource_type, resource_id, permission, subject_type, subject_id)
        if direct in self._tuples:
            return True

        # 2. Campaign evaluation
        if resource_type == "campaign":
            # Owner bypass / supreme hierarchy
            if (
                self._tuple_key("campaign", resource_id, "owner", subject_type, subject_id)
                in self._tuples
            ):
                return True

            # DM / GM hierarchy
            is_dm = (
                self._tuple_key("campaign", resource_id, "dungeon_master", subject_type, subject_id)
                in self._tuples
                or self._tuple_key("campaign", resource_id, "game_master", subject_type, subject_id)
                in self._tuples
                or self._tuple_key("campaign", resource_id, "gm", subject_type, subject_id)
                in self._tuples
            )
            if is_dm and permission in (
                "dungeon_master",
                "game_master",
                "gm",
                "run_session",
                "play",
                "view",
                "read",
                "edit",
                "move",
                "move_token",
                "modify_hp",
                "apply_condition",
                "spawn_monster",
                "set_scene",
                "control",
                "participate",
                "observe",
                "inspect",
            ):
                return True

            # Player inheritance
            if self._tuple_key(
                "campaign", resource_id, "player", subject_type, subject_id
            ) in self._tuples and permission in (
                "player",
                "play",
                "view",
                "read",
                "participate",
                "observe",
                "inspect",
            ):
                return True

            # Spectator inheritance
            if self._tuple_key(
                "campaign", resource_id, "spectator", subject_type, subject_id
            ) in self._tuples and permission in ("spectator", "view", "read", "observe", "inspect"):
                return True

            if self._tuple_key(
                "campaign", resource_id, "view", subject_type, subject_id
            ) in self._tuples and permission in ("view", "read", "observe", "inspect"):
                return True

        # 3. Session evaluation (session->campaign)
        if resource_type in ("session", "game_session"):
            parents = self._find_subjects(resource_type, resource_id, "campaign")
            if not parents:
                parents = [("campaign", resource_id)]
            for p_type, p_id in parents:
                if permission in ("control", "run_session") and await self.check_permission(
                    p_type, p_id, "run_session", subject_type, subject_id
                ):
                    return True
                if permission in ("participate", "play") and await self.check_permission(
                    p_type, p_id, "play", subject_type, subject_id
                ):
                    return True
                if permission in (
                    "observe",
                    "view",
                    "read",
                    "inspect",
                ) and await self.check_permission(p_type, p_id, "view", subject_type, subject_id):
                    return True

        # 4. Character evaluation (owner + campaign->run_session, view = edit + campaign->view)
        if resource_type == "character":
            char_owner = self._tuple_key(
                "character", resource_id, "owner", subject_type, subject_id
            )
            if char_owner in self._tuples and permission in ("owner", "edit", "view", "read"):
                return True

            parents = self._find_subjects("character", resource_id, "campaign")
            for p_type, p_id in parents:
                if permission in ("edit", "view", "read") and await self.check_permission(
                    p_type, p_id, "run_session", subject_type, subject_id
                ):
                    return True
                if permission in ("view", "read") and await self.check_permission(
                    p_type, p_id, "view", subject_type, subject_id
                ):
                    return True

        # 5. Board token evaluation (character->edit + campaign->run_session)
        if resource_type == "board_token":
            token_move = self._tuple_key(
                "board_token", resource_id, "move", subject_type, subject_id
            )
            if token_move in self._tuples and permission in ("move", "move_token"):
                return True

            linked_chars = self._find_subjects("board_token", resource_id, "character")
            for c_type, c_id in linked_chars:
                if permission in (
                    "move",
                    "move_token",
                    "inspect",
                    "view",
                    "read",
                ) and await self.check_permission(c_type, c_id, "edit", subject_type, subject_id):
                    return True

            parents = self._find_subjects("board_token", resource_id, "campaign")
            for p_type, p_id in parents:
                if permission in (
                    "move",
                    "move_token",
                    "inspect",
                    "view",
                    "read",
                ) and await self.check_permission(
                    p_type, p_id, "run_session", subject_type, subject_id
                ):
                    return True
                if permission in ("inspect", "view", "read") and await self.check_permission(
                    p_type, p_id, "view", subject_type, subject_id
                ):
                    return True

        # 6. Lore document evaluation (read_public = campaign->view, read_secret/manage = campaign->run_session)
        if resource_type == "lore_document":
            parents = self._find_subjects("lore_document", resource_id, "campaign")
            if not parents:
                parents = [("campaign", resource_id)]
            for p_type, p_id in parents:
                if permission in ("read_secret", "manage") and await self.check_permission(
                    p_type, p_id, "run_session", subject_type, subject_id
                ):
                    return True
                if permission in ("read_public", "view", "read") and await self.check_permission(
                    p_type, p_id, "view", subject_type, subject_id
                ):
                    return True

        # 7. Audience poll evaluation
        if resource_type == "audience_poll":
            parents = self._find_subjects("audience_poll", resource_id, "campaign")
            if not parents:
                parents = [("campaign", resource_id)]
            for p_type, p_id in parents:
                if permission in ("moderate", "approve", "veto") and await self.check_permission(
                    p_type, p_id, "run_session", subject_type, subject_id
                ):
                    return True
                if permission in ("vote", "view", "read") and await self.check_permission(
                    p_type, p_id, "view", subject_type, subject_id
                ):
                    return True

        # 8. Atlas evaluation (view = campaign->view, edit = campaign->run_session, place_pin = campaign->play)
        if resource_type == "atlas":
            parents = self._find_subjects("atlas", resource_id, "campaign")
            if not parents:
                parents = [("campaign", resource_id)]
            for p_type, p_id in parents:
                if permission in ("edit", "manage") and await self.check_permission(
                    p_type, p_id, "run_session", subject_type, subject_id
                ):
                    return True
                if permission in ("place_pin",) and (
                    await self.check_permission(p_type, p_id, "play", subject_type, subject_id)
                    or await self.check_permission(
                        p_type, p_id, "run_session", subject_type, subject_id
                    )
                ):
                    return True
                if permission in ("view", "read") and await self.check_permission(
                    p_type, p_id, "view", subject_type, subject_id
                ):
                    return True

        # 9. Codex entry evaluation (author + editor + reader; party_shared; public)
        if resource_type == "codex_entry":
            # Author or editor direct access
            if (
                self._tuple_key("codex_entry", resource_id, "author", subject_type, subject_id)
                in self._tuples
                or self._tuple_key("codex_entry", resource_id, "editor", subject_type, subject_id)
                in self._tuples
            ):
                return True
            if (
                permission in ("view", "read")
                and self._tuple_key("codex_entry", resource_id, "reader", subject_type, subject_id)
                in self._tuples
            ):
                return True

            parents = self._find_subjects("codex_entry", resource_id, "campaign")
            if not parents:
                parents = [("campaign", resource_id)]
            for p_type, p_id in parents:
                if permission in ("manage", "edit") and await self.check_permission(
                    p_type, p_id, "run_session", subject_type, subject_id
                ):
                    return True
                if permission in ("view", "read"):
                    # Check party_shared visibility
                    if (
                        self._tuple_key(
                            "codex_entry", resource_id, "party_shared", "campaign", p_id
                        )
                        in self._tuples
                        or self._tuple_key("codex_entry", resource_id, "shared", "campaign", p_id)
                        in self._tuples
                    ) and (
                        await self.check_permission(p_type, p_id, "play", subject_type, subject_id)
                        or await self.check_permission(
                            p_type, p_id, "run_session", subject_type, subject_id
                        )
                    ):
                        return True
                    # Check public visibility
                    if (
                        self._tuple_key("codex_entry", resource_id, "public", "campaign", p_id)
                        in self._tuples
                    ) and await self.check_permission(
                        p_type, p_id, "view", subject_type, subject_id
                    ):
                        return True

        return False
