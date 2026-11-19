"""Typed domain errors of the board aggregate (TASK-0752, TASK-0914).

The service maps them to HTTP status codes in one place, `main.py`.
"""

from __future__ import annotations

from runefoble_platform.domain_errors import DomainNotFoundError


class BoardElementNotFoundError(DomainNotFoundError):
    """Raised when a command names a token, trap or AoE template that is not on the board.

    The HTTP handler answers 404. The board socket answers `INVALID`.
    """
