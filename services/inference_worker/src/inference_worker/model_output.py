"""Helpers for reading JSON objects out of model output."""

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from inference_worker.ports import backend_unavailable


def parse_json_object(content: str) -> dict[str, Any]:
    """Extract the first JSON object from model output. Return an empty dict if none parses."""
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def require_field(data: dict[str, Any], key: str, backend: str) -> Any:
    """Return `data[key]`. Raise EngineUnavailableError when the model omitted it or left it empty.

    The worker has no substitute for a field that the model did not produce (ADR-0015 Context item 4).
    """
    value = data.get(key)
    if not value:
        raise backend_unavailable(backend, f"model output had no {key}")
    return value


def validate_fields[M: BaseModel](data: dict[str, Any], schema: type[M], backend: str) -> M:
    """Check the types of the model fields. Raise EngineUnavailableError when one is wrong.

    The worker does not convert a wrong value into a right one (ADR-0015). The error names the field.
    """
    try:
        return schema.model_validate(data)
    except ValidationError as e:
        fields = ", ".join(".".join(str(p) for p in err["loc"]) for err in e.errors())
        raise backend_unavailable(backend, f"model output has wrong types in: {fields}") from e
