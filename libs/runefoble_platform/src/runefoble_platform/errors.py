"""Runefoble platform exceptions hierarchy."""

from typing import Optional, Dict, Any


class RunefobleError(Exception):
    """Base error for all Runefoble platform operations."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundError(RunefobleError):
    """Raised when a requested resource does not exist."""

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(f"{entity_type} with ID '{entity_id}' not found.", {
            "entity_type": entity_type,
            "entity_id": entity_id,
        })


class AuthorizationError(RunefobleError):
    """Raised when Zanzibar / SpiceDB permission check fails."""

    def __init__(self, user_id: str, action: str, resource: str):
        super().__init__(f"User '{user_id}' is not authorized to '{action}' on '{resource}'.", {
            "user_id": user_id,
            "action": action,
            "resource": resource,
        })


class GameRuleViolationError(RunefobleError):
    """Raised when an action violates tactical rules or board physics."""

    def __init__(self, rule: str, reason: str):
        super().__init__(f"Game rule violation: {rule} - {reason}", {
            "rule": rule,
            "reason": reason,
        })
