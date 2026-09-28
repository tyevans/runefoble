"""Developer email testing and mock SMTP inspection handlers for Gateway API."""

from typing import Any

from fastapi import APIRouter
from gateway_api.routers.auth.schemas import DevSendEmailRequest
from runefoble_platform.email_client import MailpitClient

router = APIRouter()

_mailpit_client = MailpitClient()


def get_mailpit_client() -> MailpitClient:
    """Return the active MailpitClient instance."""
    return _mailpit_client


def set_mailpit_client(client: MailpitClient) -> None:
    """Inject a configured MailpitClient (e.g. in tests)."""
    global _mailpit_client
    _mailpit_client = client


@router.post("/dev/send-test")
@router.post("/test-email")
async def send_test_email(payload: DevSendEmailRequest) -> dict[str, Any]:
    """Send a test email to Mailpit SMTP to verify email delivery in development."""
    outbound = await _mailpit_client.send_email(
        to=payload.to,
        subject=payload.subject,
        body_text=payload.body,
        body_html=f"<p>{payload.body}</p>",
        from_addr="noreply@runefoble.local",
    )
    return {
        "status": "sent",
        "message_id": outbound.message_id,
        "to": outbound.to,
        "subject": outbound.subject,
        "mailpit_ui_url": "http://localhost/mail/",
    }


@router.get("/dev/emails")
async def list_dev_emails() -> list[dict[str, Any]]:
    """List captured messages via Mailpit REST API or local memory buffer."""
    messages = await _mailpit_client.list_messages()
    return [m.model_dump(by_alias=True) for m in messages]


@router.delete("/dev/emails")
async def clear_dev_emails() -> dict[str, str]:
    """Purge captured messages in Mailpit."""
    await _mailpit_client.delete_all_messages()
    return {"status": "cleared", "message": "Inbox purged"}


@router.get("/dev/stats")
@router.get("/mailpit/status")
async def mailpit_status() -> dict[str, Any]:
    """Inspect Mailpit SMTP and REST connectivity."""
    return await _mailpit_client.check_health()


__all__ = [
    "_mailpit_client",
    "clear_dev_emails",
    "get_mailpit_client",
    "list_dev_emails",
    "mailpit_status",
    "router",
    "send_test_email",
    "set_mailpit_client",
]
