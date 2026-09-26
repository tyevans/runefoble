"""SpiceDB Zanzibar client integration for fine-grained object-level authorization."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Relationship:
    resource_type: str
    resource_id: str
    relation: str
    subject_type: str
    subject_id: str


class SpiceDBClient:
    """Client for querying and writing permissions to SpiceDB Zanzibar engine."""

    def __init__(self, endpoint: str = "localhost:50051", token: str = "secret"):
        self.endpoint = endpoint
        self.token = token
        # In-memory relationship tuple store for local/test execution
        self._tuples: set[str] = set()

    def _tuple_key(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> str:
        return f"{resource_type}:{resource_id}#{relation}@{subject_type}:{subject_id}"

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
        logger.info(f"SpiceDB tuple written: {key}")

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

    async def check_permission(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        """Check whether a subject has a specific permission on a resource.

        Evaluates direct relations or owner bypass.
        """
        # Direct relationship check
        direct = self._tuple_key(resource_type, resource_id, permission, subject_type, subject_id)
        if direct in self._tuples:
            return True

        # Owner / DM inheritance hierarchy checks
        owner = self._tuple_key(resource_type, resource_id, "owner", subject_type, subject_id)
        if owner in self._tuples:
            return True

        dm = self._tuple_key(resource_type, resource_id, "dungeon_master", subject_type, subject_id)
        if dm in self._tuples and permission in ("run_session", "play", "view", "edit", "move"):
            return True

        player = self._tuple_key(resource_type, resource_id, "player", subject_type, subject_id)
        return player in self._tuples and permission in ("play", "view")
