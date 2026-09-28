"""Mailpit Email Testing & Mock SMTP Client.

Provides synchronous and asynchronous SMTP email sending and Mailpit REST API
inspection for developer testing, automated verification, and CI/CD pipelines.
"""

import asyncio
import logging
import re
import smtplib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx
from pydantic import BaseModel, Field

from runefoble_platform.config import PlatformSettings

logger = logging.getLogger("runefoble.platform.email")


class MailpitMessageSummary(BaseModel):
    """Summary of a message captured by Mailpit."""

    id: str = Field(description="Mailpit internal message ID")
    subject: str = Field(default="", description="Email subject")
    from_addr: str = Field(default="", alias="from", description="Sender address")
    to: list[str] = Field(default_factory=list, description="Recipient addresses")
    created: str = Field(default="", description="Creation timestamp")
    size: int = Field(default=0, description="Message size in bytes")
    snippet: str = Field(default="", description="Snippet of message body")

    model_config = {"populate_by_name": True}


class MailpitMessage(BaseModel):
    """Full detail of a message captured by Mailpit."""

    id: str = Field(description="Mailpit internal message ID")
    subject: str = Field(default="", description="Email subject")
    from_addr: str = Field(default="", alias="from", description="Sender address")
    to: list[str] = Field(default_factory=list, description="Recipient addresses")
    created: str = Field(default="", description="Creation timestamp")
    text: str = Field(default="", description="Plain text content")
    html: str = Field(default="", description="HTML content")
    snippet: str = Field(default="", description="Snippet of message body")

    model_config = {"populate_by_name": True}


@dataclass
class OutboundEmail:
    """Outbound email payload."""

    to: str | list[str]
    subject: str
    body_text: str
    body_html: str | None = None
    from_addr: str = "noreply@runefoble.local"
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class MailpitClient:
    """Client for sending emails to Mailpit via SMTP and querying captured emails via REST."""

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        http_url: str | None = None,
        fallback_in_memory: bool = True,
    ) -> None:
        settings = PlatformSettings()
        self.smtp_host = smtp_host or settings.mailpit_smtp_host
        self.smtp_port = smtp_port or settings.mailpit_smtp_port
        self.http_url = (http_url or settings.mailpit_http_url).rstrip("/")
        self.fallback_in_memory = fallback_in_memory
        self.sent_emails: list[OutboundEmail] = []

    def send_email_sync(
        self,
        to: str | list[str],
        subject: str,
        body_text: str,
        body_html: str | None = None,
        from_addr: str = "noreply@runefoble.local",
    ) -> OutboundEmail:
        """Send an email synchronously via SMTP with in-memory fallback on connection failure."""
        recipients = [to] if isinstance(to, str) else list(to)
        outbound = OutboundEmail(
            to=recipients,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            from_addr=from_addr,
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=3.0) as server:
                server.sendmail(from_addr, recipients, msg.as_string())
            logger.info("Sent email '%s' to %s via Mailpit SMTP", subject, recipients)
        except Exception as exc:
            if self.fallback_in_memory:
                logger.warning(
                    "Mailpit SMTP at %s:%s unreachable (%s); recorded email in memory buffer.",
                    self.smtp_host,
                    self.smtp_port,
                    exc,
                )
            else:
                raise

        self.sent_emails.append(outbound)
        return outbound

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        body_text: str,
        body_html: str | None = None,
        from_addr: str = "noreply@runefoble.local",
    ) -> OutboundEmail:
        """Send an email asynchronously via SMTP in a background thread."""
        return await asyncio.to_thread(
            self.send_email_sync,
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            from_addr=from_addr,
        )

    async def list_messages(self, start: int = 0, limit: int = 50) -> list[MailpitMessageSummary]:
        """List captured messages via Mailpit REST API, falling back to local memory."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(
                    f"{self.http_url}/api/v1/messages",
                    params={"start": start, "limit": limit},
                )
                if res.status_code == 200:
                    data = res.json()
                    messages = data.get("messages", [])
                    return [
                        MailpitMessageSummary(
                            id=m.get("ID", ""),
                            subject=m.get("Subject", ""),
                            from_addr=m.get("From", {}).get("Address", "")
                            if isinstance(m.get("From"), dict)
                            else str(m.get("From", "")),
                            to=[
                                t.get("Address", "") if isinstance(t, dict) else str(t)
                                for t in m.get("To", [])
                            ],
                            created=m.get("Created", ""),
                            size=m.get("Size", 0),
                            snippet=m.get("Snippet", ""),
                        )
                        for m in messages
                    ]
        except Exception as exc:
            logger.debug("Mailpit API unreachable (%s), checking in-memory buffer", exc)

        # Fallback to local memory buffer
        return [
            MailpitMessageSummary(
                id=e.message_id,
                subject=e.subject,
                from_addr=e.from_addr,
                to=e.to if isinstance(e.to, list) else [e.to],
                created=e.created_at,
                size=len(e.body_text),
                snippet=e.body_text[:100],
            )
            for e in reversed(self.sent_emails[start : start + limit])
        ]

    async def get_message(self, message_id: str) -> MailpitMessage | None:
        """Get full message details by ID from Mailpit REST API or local memory."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.http_url}/api/v1/message/{message_id}")
                if res.status_code == 200:
                    m = res.json()
                    return MailpitMessage(
                        id=m.get("ID", message_id),
                        subject=m.get("Subject", ""),
                        from_addr=m.get("From", {}).get("Address", "")
                        if isinstance(m.get("From"), dict)
                        else str(m.get("From", "")),
                        to=[
                            t.get("Address", "") if isinstance(t, dict) else str(t)
                            for t in m.get("To", [])
                        ],
                        created=m.get("Created", ""),
                        text=m.get("Text", ""),
                        html=m.get("HTML", ""),
                        snippet=m.get("Snippet", ""),
                    )
        except Exception as exc:
            logger.debug("Mailpit API unreachable (%s), querying memory buffer", exc)

        for e in self.sent_emails:
            if e.message_id == message_id:
                return MailpitMessage(
                    id=e.message_id,
                    subject=e.subject,
                    from_addr=e.from_addr,
                    to=e.to if isinstance(e.to, list) else [e.to],
                    created=e.created_at,
                    text=e.body_text,
                    html=e.body_html or "",
                    snippet=e.body_text[:100],
                )
        return None

    async def get_latest_message(self) -> MailpitMessage | None:
        """Fetch the most recent captured message."""
        messages = await self.list_messages(start=0, limit=1)
        if not messages:
            return None
        return await self.get_message(messages[0].id)

    async def search_messages(self, query: str) -> list[MailpitMessageSummary]:
        """Search messages by subject, recipient, or content."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.http_url}/api/v1/search", params={"query": query})
                if res.status_code == 200:
                    data = res.json()
                    messages = data.get("messages", [])
                    return [
                        MailpitMessageSummary(
                            id=m.get("ID", ""),
                            subject=m.get("Subject", ""),
                            from_addr=m.get("From", {}).get("Address", "")
                            if isinstance(m.get("From"), dict)
                            else str(m.get("From", "")),
                            to=[
                                t.get("Address", "") if isinstance(t, dict) else str(t)
                                for t in m.get("To", [])
                            ],
                            created=m.get("Created", ""),
                            size=m.get("Size", 0),
                            snippet=m.get("Snippet", ""),
                        )
                        for m in messages
                    ]
        except Exception:
            pass

        # In-memory search fallback
        q = query.lower()
        results: list[MailpitMessageSummary] = []
        for e in reversed(self.sent_emails):
            recipients = " ".join(e.to) if isinstance(e.to, list) else e.to
            if (
                q in e.subject.lower()
                or q in recipients.lower()
                or q in e.body_text.lower()
                or (e.body_html and q in e.body_html.lower())
            ):
                results.append(
                    MailpitMessageSummary(
                        id=e.message_id,
                        subject=e.subject,
                        from_addr=e.from_addr,
                        to=e.to if isinstance(e.to, list) else [e.to],
                        created=e.created_at,
                        size=len(e.body_text),
                        snippet=e.body_text[:100],
                    )
                )
        return results

    async def delete_all_messages(self) -> bool:
        """Purge all captured messages (useful for test isolation)."""
        self.sent_emails.clear()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.delete(f"{self.http_url}/api/v1/messages")
                return res.status_code in (200, 204)
        except Exception:
            return True

    async def check_health(self) -> dict[str, Any]:
        """Check SMTP and HTTP connectivity to Mailpit."""
        http_ok = False
        smtp_ok = False
        count = len(self.sent_emails)

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.http_url}/api/v1/messages?limit=1")
                if res.status_code == 200:
                    http_ok = True
                    count = res.json().get("total", 0)
        except Exception:
            pass

        try:

            def _probe_smtp():
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=2.0) as s:
                    return s.noop()[0] == 250

            smtp_ok = await asyncio.to_thread(_probe_smtp)
        except Exception:
            pass

        return {
            "status": "healthy"
            if (http_ok and smtp_ok)
            else "degraded"
            if (http_ok or smtp_ok)
            else "offline",
            "http_available": http_ok,
            "smtp_available": smtp_ok,
            "message_count": count,
            "web_ui_url": f"{self.http_url}/mail/",
        }

    @staticmethod
    def extract_verification_link(content: str) -> str | None:
        """Extract verification or activation URL from email body content."""
        match = re.search(
            r'https?://[^\s<>"\']+(?:verify|token|activate|confirm|code)[^\s<>"\']*',
            content,
            re.IGNORECASE,
        )
        return match.group(0) if match else None

    @staticmethod
    def extract_verification_code(content: str) -> str | None:
        """Extract numeric or alphanumeric OTP verification code (4 to 8 characters)."""
        match = re.search(
            r"(?:code|pin|otp|token|code is)[:\s]+([A-Z0-9]{4,8})\b",
            content,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)
        match_digits = re.search(r"\b\d{6}\b", content)
        return match_digits.group(0) if match_digits else None
