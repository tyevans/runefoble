"""Typed domain errors that a service maps to HTTP status codes (TASK-0914, ADR-0015).

An aggregate or a domain module raises these when it refuses a command:

- `DomainRefusedError`: the command breaks a domain rule (HTTP 400).
- `DomainNotFoundError`: the command names an entity that does not exist (HTTP 404).

They do not subclass `ValueError`. A `ValueError` from a programming error, or a
`pydantic.ValidationError` raised inside service code, is therefore never a client error.
This module has no web dependency, so domain code can import it.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class of the errors that a domain raises to refuse a command."""


class DomainRefusedError(DomainError):
    """The command breaks a domain rule. Nothing is applied."""


class DomainNotFoundError(DomainError):
    """The command names an entity that does not exist."""


__all__ = ["DomainError", "DomainNotFoundError", "DomainRefusedError"]
