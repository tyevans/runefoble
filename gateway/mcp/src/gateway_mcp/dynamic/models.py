"""Domain models and schema validation for dynamic FastMCP tools."""

from __future__ import annotations

from typing import Any

from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError
from pydantic import BaseModel, Field

TYPE_MAP: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


class DynamicToolDefinition(BaseModel):
    """Declarative specification for dynamically registered FastMCP tools."""

    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(default="", description="Functional description for LLM planning")
    parameters: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}},
        description="JSON Schema for input parameters",
    )
    handler_code: str | None = Field(
        default=None, description="Optional sandboxed Python handler implementation"
    )
    sandbox_policy: dict[str, Any] = Field(
        default_factory=dict, description="Custom sandbox execution constraints"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata tags, author, and version info"
    )
    author_id: str | None = Field(default=None, description="Author user ID for SpiceDB checks")
    campaign_id: str | None = Field(default=None, description="Campaign ID for scoped permissions")


class DynamicToolExecutionRequest(BaseModel):
    """Payload for invoking a dynamic tool directly via administrative frontdoor."""

    arguments: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = Field(default=None, description="Optional caller user ID")
    session_id: str | None = Field(default=None, description="Optional caller session ID")


def validate_parameter_schema(schema: dict[str, Any]) -> None:
    """Validate that parameters conform to valid JSON Schema Draft-07."""
    if not isinstance(schema, dict):
        raise ValueError("Tool parameters must be a JSON Schema dictionary")
    if schema.get("type") != "object":
        raise ValueError("Top-level parameters schema must have type 'object'")
    try:
        Draft7Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError(f"Invalid JSON schema: {exc.message}") from exc
