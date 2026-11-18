"""In-memory mock Zanzibar relationship tuple store for tests and offline runs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from runefoble_auth.contract import require_permission, require_relation, require_subject_type
from runefoble_auth.errors import SchemaContractError
from runefoble_auth.mock.evaluator import PermissionEvaluator
from runefoble_auth.schema_graph import SchemaGraph, load_default_schema, parse_zed_schema

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
    def from_tuple_key(cls, key: str) -> Relationship:
        res, rest = key.split("#", 1)
        res_t, res_id = res.split(":", 1)
        rel, subj = rest.split("@", 1)
        sub_t, sub_id = subj.split(":", 1)
        return cls(res_t, res_id, rel, sub_t, sub_id)


class MockSpiceDBClient:
    """In-memory Zanzibar tuple store that enforces the schema name contract.

    A write to an undefined type, relation, or subject raises SchemaContractError. A check
    for an undefined permission raises it too. Live SpiceDB rejects the same calls.
    """

    def __init__(
        self,
        endpoint: str = "localhost:50051",
        token: str | None = None,
        schema_text: str | None = None,
    ):
        self.endpoint = endpoint
        self.token = token
        self._tuples: set[str] = set()
        self._schema_graph: SchemaGraph = (
            parse_zed_schema(schema_text) if schema_text else load_default_schema()
        )
        self._schema: str = schema_text or ""
        self._evaluator: PermissionEvaluator = PermissionEvaluator(schema=self._schema_graph)

    def _validate_tuple(self, resource_type: str, relation: str, subject_type: str) -> None:
        require_subject_type(resource_type, relation, subject_type, self._schema_graph)

    def _tuple_key(self, res_t: str, res_id: str, rel: str, sub_t: str, sub_id: str) -> str:
        return f"{res_t}:{res_id}#{rel}@{sub_t}:{sub_id}"

    def _find_subjects(self, res_type: str, res_id: str, rel: str) -> list[tuple[str, str]]:
        return self._evaluator.find_subjects(self._tuples, res_type, res_id, rel)

    async def write_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        """Create a relationship tuple in Zanzibar."""
        self._validate_tuple(resource_type, relation, subject_type)
        key = self._tuple_key(resource_type, resource_id, relation, subject_type, subject_id)
        self._tuples.add(key)
        logger.info("SpiceDB tuple written: %s", key)

    async def touch_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        """Touch / upsert a relationship tuple in Zanzibar."""
        await self.write_relationship(
            resource_type, resource_id, relation, subject_type, subject_id
        )

    async def delete_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        """Remove a relationship tuple."""
        self._validate_tuple(resource_type, relation, subject_type)
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
        if resource_type and relation:
            require_relation(resource_type, relation, self._schema_graph)
        results: list[Relationship] = []
        for key in sorted(self._tuples):
            rel = Relationship.from_tuple_key(key)
            if (
                (not resource_type or rel.resource_type == resource_type)
                and (not resource_id or rel.resource_id == resource_id)
                and (not relation or rel.relation == relation)
            ):
                results.append(rel)
        return results

    async def lookup_resources(
        self,
        resource_type: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> list[str]:
        """Return resource IDs of `resource_type` where the subject has `permission`.

        Candidates are the resources that hold at least one direct tuple.
        """
        require_permission(resource_type, permission, self._schema_graph)
        candidates = sorted(
            {rel.resource_id for rel in await self.read_relationships(resource_type=resource_type)}
        )
        found: list[str] = []
        for resource_id in candidates:
            if await self.check_permission(
                resource_type, resource_id, permission, subject_type, subject_id
            ):
                found.append(resource_id)
        return found

    async def write_schema(self, schema_text: str) -> None:
        """Store mock schema definition and update schema graph."""
        self._schema = schema_text
        self._schema_graph = parse_zed_schema(schema_text)
        self._evaluator = PermissionEvaluator(schema=self._schema_graph)

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
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Check whether a subject has a specific permission on a resource."""
        require_permission(resource_type, permission, self._schema_graph)
        if subject_type not in self._schema_graph.definitions:
            raise SchemaContractError(
                f"Subject type '{subject_type}' is not defined in runefoble.zed"
            )
        return await self._evaluator.evaluate(
            self._tuples, resource_type, resource_id, permission, subject_type, subject_id, context
        )
