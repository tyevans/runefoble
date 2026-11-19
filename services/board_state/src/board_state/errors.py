"""Typed domain errors of the board aggregate (TASK-0752).

The service maps them to HTTP status codes in one place, `main.py`.
"""

from __future__ import annotations


class BoardElementNotFoundError(ValueError):
    """Raised when a command names a token, trap or AoE template that is not on the board.

    It is a `ValueError`, so socket handlers that refuse bad input also refuse it. The HTTP
    handler is more specific and answers 404.
    """
