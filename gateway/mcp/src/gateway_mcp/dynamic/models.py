"""Domain models and schema validation for dynamic FastMCP tools."""

from __future__ import annotations

from typing import Any

from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError
from pydantic import BaseModel, Field, field_validator

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
    handler: dict[str, Any] = Field(
        ...,
        description="Declarative result template (ADR-0020): ${name} placeholders, $expr, $dice",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata tags, author, and version info"
    )
    campaign_id: str | None = Field(default=None, description="Campaign ID for scoped permissions")

    @field_validator("handler")
    @classmethod
    def _require_handler(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("handler must be a non-empty declarative result template")
        return value


class DynamicToolRecord(DynamicToolDefinition):
    """A registered tool. The gateway sets `author_id` from the verified caller (TASK-0532)."""

    author_id: str | None = Field(default=None, description="Verified author user ID")


class DynamicToolExecutionRequest(BaseModel):
    """Payload for invoking a dynamic tool directly via administrative frontdoor."""

    arguments: dict[str, Any] = Field(default_factory=dict)
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
