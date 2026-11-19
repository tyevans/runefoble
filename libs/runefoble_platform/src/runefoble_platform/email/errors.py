"""Errors raised by the email transport when SMTP or Mailpit cannot complete a request."""

from runefoble_platform.errors import ServiceUnavailableError


class EmailTransportError(ServiceUnavailableError):
    """Raised when the SMTP server or the Mailpit HTTP API fails. Maps to HTTP 503."""
