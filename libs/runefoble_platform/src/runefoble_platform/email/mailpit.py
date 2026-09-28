"""Mailpit REST API client and mock email inbox inspection."""

from typing import Any

import httpx

from runefoble_platform.config import PlatformSettings
from runefoble_platform.email.models import (
    MailpitMessage,
    MailpitMessageSummary,
    OutboundEmail,
    extract_verification_code,
    extract_verification_link,
)
from runefoble_platform.email.smtp import SmtpTransport


def _to_msg(item: dict[str, Any] | OutboundEmail, detail: bool = False, def_id: str = "") -> Any:
    if isinstance(item, OutboundEmail):
        mid, subj, addr = item.message_id, item.subject, item.from_addr
        to = item.to if isinstance(item.to, list) else [item.to]
        created, txt, html = item.created_at, item.body_text, item.body_html or ""
        size = len(txt)
    else:
        src = item.get("From", "")
        addr = src.get("Address", "") if isinstance(src, dict) else str(src or "")
        to = [t.get("Address", "") if isinstance(t, dict) else str(t) for t in item.get("To", [])]
        mid, subj = item.get("ID", def_id), item.get("Subject", "")
        created, txt, html = item.get("Created", ""), item.get("Text", ""), item.get("HTML", "")
        size = item.get("Size", len(txt))
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
    return MailpitMessageSummary(**kw, size=size)


class MailpitClient(SmtpTransport):
    """Client for sending emails to Mailpit and querying captured emails via REST."""

    extract_verification_link = staticmethod(extract_verification_link)
    extract_verification_code = staticmethod(extract_verification_code)

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        http_url: str | None = None,
        fallback_in_memory: bool = True,
    ) -> None:
        super().__init__(smtp_host, smtp_port, fallback_in_memory=fallback_in_memory)
        self.http_url = (http_url or PlatformSettings().mailpit_http_url).rstrip("/")

    async def _get(self, path: str, **params: Any) -> Any:
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                query = {k: v for k, v in params.items() if v is not None}
                res = await c.get(f"{self.http_url}{path}", params=query)
                return res.json() if res.status_code == 200 else None
        except Exception:
            return None

    async def list_messages(self, start: int = 0, limit: int = 50) -> list[MailpitMessageSummary]:
        """List captured messages via Mailpit REST API, falling back to local memory."""
        res = await self._get("/api/v1/messages", start=start, limit=limit)
        if res and "messages" in res:
            return [_to_msg(m) for m in res["messages"]]
        return [_to_msg(e) for e in reversed(self.sent_emails[start : start + limit])]

    async def get_message(self, message_id: str) -> MailpitMessage | None:
        """Get full message details by ID from Mailpit REST API or local memory."""
        res = await self._get(f"/api/v1/message/{message_id}")
        if res:
            return _to_msg(res, detail=True, def_id=message_id)
        return next(
            (_to_msg(e, detail=True) for e in self.sent_emails if e.message_id == message_id), None
        )

    async def get_latest_message(self) -> MailpitMessage | None:
        """Fetch the most recent captured message."""
        msgs = await self.list_messages(start=0, limit=1)
        return await self.get_message(msgs[0].id) if msgs else None

    async def search_messages(self, query: str) -> list[MailpitMessageSummary]:
        """Search messages by subject, recipient, or content."""
        res = await self._get("/api/v1/search", query=query)
        if res and "messages" in res:
            return [_to_msg(m) for m in res["messages"]]
        q = query.lower()
        return [
            _to_msg(e)
            for e in reversed(self.sent_emails)
            if q in f"{e.subject} {e.to} {e.body_text} {e.body_html or ''}".lower()
        ]

    async def delete_all_messages(self) -> bool:
        """Purge all captured messages."""
        self.sent_emails.clear()
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                return (await c.delete(f"{self.http_url}/api/v1/messages")).status_code in (
                    200,
                    204,
                )
        except Exception:
            return True

    async def check_health(self) -> dict[str, Any]:
        """Check SMTP and HTTP connectivity to Mailpit."""
        d = await self._get("/api/v1/messages", limit=1)
        cnt = d.get("total", len(self.sent_emails)) if d else len(self.sent_emails)
        smtp = await self.probe_async(timeout=2.0)
        st = "healthy" if (d and smtp) else ("degraded" if (d or smtp) else "offline")
        return {
            "status": st,
            "http_available": d is not None,
            "smtp_available": smtp,
            "message_count": cnt,
            "web_ui_url": f"{self.http_url}/mail/",
        }
