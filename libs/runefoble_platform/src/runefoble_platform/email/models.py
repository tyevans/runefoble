"""Email data structures, recipient schemas, and Mailpit message models."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class EmailRecipient(BaseModel):
    """Schema representing an email recipient."""

    email: str
    name: str = ""


class EmailMessage(BaseModel):
    """General transactional email message representation."""

    to: list[str] | str
    subject: str
    body_text: str
    body_html: str | None = None
    from_addr: str = "noreply@runefoble.local"


class EmailVerificationPayload(BaseModel):
    """Envelope for email verification tokens and activation links."""

    email: str
    token: str
    code: str | None = None
    expires_at: str | None = None


class MailpitMessageSummary(BaseModel):
    """Summary of a message captured by Mailpit."""

    id: str = ""
    subject: str = ""
    from_addr: str = Field(default="", alias="from")
    to: list[str] = Field(default_factory=list)
    created: str = ""
    size: int = 0
    snippet: str = ""

    model_config = {"populate_by_name": True}


class MailpitMessage(BaseModel):
    """Full detail of a message captured by Mailpit."""

    id: str = ""
    subject: str = ""
    from_addr: str = Field(default="", alias="from")
    to: list[str] = Field(default_factory=list)
    created: str = ""
    text: str = ""
    html: str = ""
    snippet: str = ""

    model_config = {"populate_by_name": True}


@dataclass
class OutboundEmail:
    """Outbound email payload queued or delivered via SMTP."""

    to: str | list[str]
    subject: str
    body_text: str
    body_html: str | None = None
    from_addr: str = "noreply@runefoble.local"
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def extract_verification_link(content: str) -> str | None:
    """Extract verification or activation URL from email body content."""
    m = re.search(
        r'https?://[^\s<>"\']+(?:verify|token|activate|confirm|code)[^\s<>"\']*', content, re.I
    )
    return m.group(0) if m else None


def extract_verification_code(content: str) -> str | None:
    """Extract numeric or alphanumeric OTP verification code (4 to 8 characters)."""
    m = re.search(r"(?:code|pin|otp|token|code is)[:\s]+([A-Z0-9]{4,8})\b", content, re.I)
    return (
        m.group(1)
        if m
        else (
            re.search(r"\b\d{6}\b", content).group(0) if re.search(r"\b\d{6}\b", content) else None
        )
    )
