"""Errors raised when a call to an owning bounded context fails.

A downstream failure is an error, never data. Callers map these errors to HTTP
responses. The client never substitutes a canned value.
"""

from __future__ import annotations


class UpstreamError(Exception):
    """Base class for a failed call to an owning service. Carries the service name."""

    def __init__(self, service: str, message: str) -> None:
        super().__init__(message)
        self.service = service


class UpstreamUnavailableError(UpstreamError):
    """The owning service could not be reached: connect failure, timeout, or no URL configured."""

    def __init__(self, service: str, reason: str) -> None:
        super().__init__(service, f"Upstream {service} is unavailable: {reason}")
        self.reason = reason


class UpstreamFailureError(UpstreamError):
    """The owning service answered with an HTTP 5xx status."""

    def __init__(self, service: str, status_code: int, body: bytes) -> None:
        super().__init__(service, f"Upstream {service} failed with HTTP {status_code}")
        self.status_code = status_code
        self.body = body
