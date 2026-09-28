"""SMTP email transport, connection management, and MIME multipart composition."""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from runefoble_platform.config import PlatformSettings
from runefoble_platform.email.models import OutboundEmail

logger = logging.getLogger("runefoble.platform.email.smtp")


def build_mime_message(outbound: OutboundEmail) -> MIMEMultipart:
    """Compose an RFC-822 MIME multipart message from an OutboundEmail."""
    recipients = [outbound.to] if isinstance(outbound.to, str) else list(outbound.to)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = outbound.subject
    msg["From"] = outbound.from_addr
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(outbound.body_text, "plain", "utf-8"))
    if outbound.body_html:
        msg.attach(MIMEText(outbound.body_html, "html", "utf-8"))
    return msg


class SmtpTransport:
    """Manages synchronous and asynchronous SMTP connections and message delivery."""

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        timeout: float = 3.0,
        fallback_in_memory: bool = True,
    ) -> None:
        settings = PlatformSettings()
        self.smtp_host = smtp_host or settings.mailpit_smtp_host
        self.smtp_port = smtp_port or settings.mailpit_smtp_port
        self.timeout = timeout
        self.fallback_in_memory = fallback_in_memory
        self.sent_emails: list[OutboundEmail] = []

    def probe(self, timeout: float = 2.0) -> bool:
        """Probe SMTP server readiness via NOOP command."""
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=timeout) as server:
                return server.noop()[0] == 250
        except Exception:
            return False

    async def probe_async(self, timeout: float = 2.0) -> bool:
        """Asynchronously probe SMTP server availability."""
        return await asyncio.to_thread(self.probe, timeout)

    def send_email_sync(
        self,
        to: str | list[str],
        subject: str,
        body_text: str,
        body_html: str | None = None,
        from_addr: str = "noreply@runefoble.local",
    ) -> OutboundEmail:
        """Send email synchronously via SMTP with in-memory fallback buffer."""
        recipients = [to] if isinstance(to, str) else list(to)
        outbound = OutboundEmail(
            to=recipients,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            from_addr=from_addr,
        )
        msg = build_mime_message(outbound)
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                server.sendmail(from_addr, recipients, msg.as_string())
            logger.info("Sent email '%s' to %s via SMTP", subject, recipients)
        except Exception as exc:
            if self.fallback_in_memory:
                logger.warning(
                    "SMTP at %s:%s unreachable (%s); recorded in memory.",
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
        """Send email asynchronously via SMTP in a worker thread."""
        return await asyncio.to_thread(
            self.send_email_sync, to, subject, body_text, body_html, from_addr
        )
