"""Build URL paths from segments that may come from agent or client input.

Each segment is percent-encoded with `safe=""`, so a `/`, `?`, or `#` in a value
stays inside one segment. Empty and dot segments are refused, because they change
the target route.
"""

from __future__ import annotations

from urllib.parse import quote


def path(*segments: str) -> str:
    """Join segments into an absolute path such as `/api/v1/pins/a%2Fb`.

    Raises ValueError for an empty segment, or for a segment that is `.` or `..`.
    """
    quoted: list[str] = []
    for segment in segments:
        if segment in ("", ".", ".."):
            raise ValueError(f"Refusing unsafe path segment: {segment!r}")
        quoted.append(quote(segment, safe=""))
    return "/" + "/".join(quoted)
