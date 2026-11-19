"""Read the JSON body of an owner reply. Both gateways use these helpers.

A body that is not JSON raises ValueError. The caller maps that to its own error.
"""

from __future__ import annotations

import json
from typing import Any


def decode_json_body(body: bytes) -> Any:
    """Return the decoded JSON value of a reply body. Raise ValueError when it is not JSON."""
    return json.loads(body)


def error_detail(body: bytes) -> str:
    """Return the `detail` of an owner error body, or the decoded body when it has none.

    A body that is not JSON is returned as text. Owner errors are short, so no size limit applies.
    """
    try:
        decoded = decode_json_body(body)
    except ValueError:
        return body.decode("utf-8", errors="replace")
    if isinstance(decoded, dict) and "detail" in decoded:
        return str(decoded["detail"])
    return str(decoded)
