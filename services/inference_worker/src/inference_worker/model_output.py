"""Helpers for reading JSON objects out of model output."""

import json
import re
from typing import Any


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
