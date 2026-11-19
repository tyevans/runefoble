"""Mailpit REST API client and mock email inbox inspection."""

from typing import Any

import httpx

from runefoble_platform.config import PlatformSettings
from runefoble_platform.email.errors import EmailTransportError
from runefoble_platform.email.models import (
    MailpitMessage,
    MailpitMessageSummary,
    extract_verification_code,
    extract_verification_link,
)
from runefoble_platform.email.smtp import SmtpTransport


def _to_msg(item: dict[str, Any], detail: bool = False, def_id: str = "") -> Any:
    src = item.get("From", "")
    addr = src.get("Address", "") if isinstance(src, dict) else str(src or "")
    to = [t.get("Address", "") if isinstance(t, dict) else str(t) for t in item.get("To", [])]
    mid, subj = item.get("ID", def_id), item.get("Subject", "")
    created, txt, html = item.get("Created", ""), item.get("Text", ""), item.get("HTML", "")
    kw = {
        "id": mid,
        "subject": subj,
        "from_addr": addr,
        "to": to,
        "created": created,
        "snippet": txt[:100],
    }
    if detail:
        return MailpitMessage(**kw, text=txt, html=html)
    return MailpitMessageSummary(**kw, size=item.get("Size", len(txt)))


class MailpitClient(SmtpTransport):
    """Client for sending emails to Mailpit and querying captured emails via REST."""

    extract_verification_link = staticmethod(extract_verification_link)
    extract_verification_code = staticmethod(extract_verification_code)

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        http_url: str | None = None,
    ) -> None:
        super().__init__(smtp_host, smtp_port)
        self.http_url = (http_url or PlatformSettings().mailpit_http_url).rstrip("/")

    async def _get(self, path: str, missing_ok: bool = False, **params: Any) -> Any:
        """GET a Mailpit route. Raises EmailTransportError on transport failure or HTTP error.

        With missing_ok, an HTTP 404 returns None instead of raising.
        """
        query = {k: v for k, v in params.items() if v is not None}
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                res = await c.get(f"{self.http_url}{path}", params=query)
        except httpx.HTTPError as exc:
            raise EmailTransportError(f"Mailpit at {self.http_url} unreachable: {exc}") from exc
        if missing_ok and res.status_code == 404:
            return None
        if res.status_code != 200:
            raise EmailTransportError(
                f"Mailpit GET {path} at {self.http_url} returned HTTP {res.status_code}"
            )
        return res.json()

    async def list_messages(self, start: int = 0, limit: int = 50) -> list[MailpitMessageSummary]:
        """List captured messages via the Mailpit REST API."""
        res = await self._get("/api/v1/messages", start=start, limit=limit)
        return [_to_msg(m) for m in res["messages"] or []]

    async def get_message(self, message_id: str) -> MailpitMessage | None:
        """Get full message details by ID. Returns None when Mailpit has no such message."""
        res = await self._get(f"/api/v1/message/{message_id}", missing_ok=True)
        return None if res is None else _to_msg(res, detail=True, def_id=message_id)

    async def get_latest_message(self) -> MailpitMessage | None:
        """Fetch the most recent captured message."""
        msgs = await self.list_messages(start=0, limit=1)
        return await self.get_message(msgs[0].id) if msgs else None

    async def search_messages(self, query: str) -> list[MailpitMessageSummary]:
        """Search messages by subject, recipient, or content."""
        res = await self._get("/api/v1/search", query=query)
        return [_to_msg(m) for m in res["messages"] or []]

    async def delete_all_messages(self) -> None:
        """Purge all captured messages. Raises EmailTransportError when the purge fails."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                res = await c.delete(f"{self.http_url}/api/v1/messages")
        except httpx.HTTPError as exc:
            raise EmailTransportError(f"Mailpit at {self.http_url} unreachable: {exc}") from exc
        if res.status_code not in (200, 204):
            raise EmailTransportError(
                f"Mailpit purge at {self.http_url} returned HTTP {res.status_code}"
            )

    async def check_health(self) -> dict[str, Any]:
        """Check SMTP and HTTP connectivity to Mailpit. Failure causes are reported as text."""
        http_error: str | None = None
        smtp_error: str | None = None
        count: int | None = None
        try:
            count = int((await self._get("/api/v1/messages", limit=1))["total"])
        except EmailTransportError as exc:
            http_error = str(exc)
        try:
            await self.probe_async(timeout=2.0)
        except EmailTransportError as exc:
            smtp_error = str(exc)
        http_ok, smtp_ok = http_error is None, smtp_error is None
        if http_ok and smtp_ok:
            status = "healthy"
        elif http_ok or smtp_ok:
            status = "degraded"
        else:
            status = "offline"
        return {
            "status": status,
            "http_available": http_ok,
            "smtp_available": smtp_ok,
            "http_error": http_error,
            "smtp_error": smtp_error,
            "message_count": count,
            "web_ui_url": f"{self.http_url}/mail/",
        }
