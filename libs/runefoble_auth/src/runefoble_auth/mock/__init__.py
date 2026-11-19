"""Mock SpiceDB Zanzibar engine package."""

from runefoble_auth.mock.client import MockSpiceDBClient
from runefoble_auth.mock.evaluator import PermissionEvaluator
from runefoble_auth.schema_graph import (
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
    "SchemaGraph",
    "load_default_schema",
    "parse_zed_schema",
]
