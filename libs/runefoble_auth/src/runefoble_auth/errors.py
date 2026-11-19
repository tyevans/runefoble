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


class AuthzWriteUnavailableError(AuthzWriteError, AuthzUnavailableError):
    """A write did not apply because SpiceDB was unreachable or did not answer in time.

    It is an `AuthzWriteError` for callers that handle write failures, and an
    `AuthzUnavailableError` for the retry policy, which retries transient outages.
    """


class SchemaContractError(AuthzSchemaError):
    """A name is not defined in runefoble.zed (type, relation, subject, or permission).

    Raised by the strict mock. Live SpiceDB raises AuthzSchemaError for the same call.
    """
