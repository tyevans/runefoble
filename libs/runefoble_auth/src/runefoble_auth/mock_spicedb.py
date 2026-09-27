"""In-memory mock Zanzibar relationship store and models for tests and offline runs."""

from runefoble_auth.mock.client import MockSpiceDBClient, Relationship
from runefoble_auth.mock.evaluator import PermissionEvaluator
from runefoble_auth.mock.schema_parser import (
    ObjectDef,
    PermissionDef,
    RelationDef,
    SchemaGraph,
    load_default_schema,
    parse_zed_schema,
)

__all__ = [
    "MockSpiceDBClient",
    "ObjectDef",
    "PermissionDef",
    "PermissionEvaluator",
    "RelationDef",
    "Relationship",
    "SchemaGraph",
    "load_default_schema",
    "parse_zed_schema",
]
