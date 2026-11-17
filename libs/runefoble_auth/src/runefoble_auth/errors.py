"""Typed SpiceDB errors. A failed authorization call never looks like a denial.

Each message keeps the original gRPC status, so logs show the cause.
"""

from runefoble_platform.errors import RunefobleError


class AuthzError(RunefobleError):
    """Base error for every SpiceDB call that could not be answered or applied."""


class AuthzUnavailableError(AuthzError):
    """SpiceDB could not be reached or did not answer in time (transport failure)."""


class AuthzSchemaError(AuthzError):
    """SpiceDB rejected the call because a type, relation, or permission is not in the schema."""


class AuthzWriteError(AuthzError):
    """SpiceDB did not apply a relationship write, delete, or schema write."""
