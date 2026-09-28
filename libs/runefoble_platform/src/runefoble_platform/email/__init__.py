"""Modular email subsystem for Runefoble platform.

Provides transactional email models, SMTP transport, and Mailpit testing integration.
"""

from runefoble_platform.email.mailpit import MailpitClient
from runefoble_platform.email.models import (
    EmailMessage,
    EmailRecipient,
    EmailVerificationPayload,
    MailpitMessage,
    MailpitMessageSummary,
    OutboundEmail,
    extract_verification_code,
    extract_verification_link,
)
from runefoble_platform.email.smtp import SmtpTransport, build_mime_message

__all__ = [
    "EmailMessage",
    "EmailRecipient",
    "EmailVerificationPayload",
    "MailpitClient",
    "MailpitMessage",
    "MailpitMessageSummary",
    "OutboundEmail",
    "SmtpTransport",
    "build_mime_message",
    "extract_verification_code",
    "extract_verification_link",
]
