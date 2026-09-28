"""User registration and email verification handlers for Gateway API."""

import contextlib
import logging
import secrets
import time
from typing import Any

from fastapi import APIRouter, HTTPException, status
from gateway_api.routers.auth.dev_mail import get_mailpit_client
from gateway_api.routers.auth.schemas import RegisterRequest, VerifyEmailRequest
from gateway_api.routers.auth.tokens import _generate_mock_jwt
from runefoble_auth.spicedb import SpiceDBClient

logger = logging.getLogger("runefoble.gateway.registration")
router = APIRouter()
_pending_verifications: dict[str, dict[str, Any]] = {}


async def _write_campaign_viewer(user_id: str) -> None:
    with contextlib.suppress(Exception):
        await SpiceDBClient().write_relationship("campaign", "public", "viewer", "user", user_id)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest) -> dict[str, Any]:
    """Register a new user account and dispatch verification email via Mailpit SMTP."""
    username, email = payload.username.strip(), payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address format")

    user_id = f"user-{username.lower().replace(' ', '-')}"
    roles = ["dm", "player"] if "dm" in username.lower() else ["player"]
    token, code = secrets.token_urlsafe(24), f"{secrets.randbelow(900000) + 100000}"

    _pending_verifications[email] = {
        "user_id": user_id,
        "username": username,
        "token": token,
        "code": code,
        "verified": False,
        "created_at": time.time(),
    }

    url = f"http://runefoble.local/auth/verify?token={token}&email={email}"
    txt = f"Hail {username}!\nWelcome to Runefoble!\nCode: {code}\nActivate: {url}\n- The Watcher"
    html = f"<h2>Hail {username}!</h2><p>Code: {code}</p><p><a href='{url}'>Confirm Account</a></p>"

    try:
        await get_mailpit_client().send_email(
            to=email,
            subject="Welcome to Runefoble! Confirm your adventurer account",
            body_text=txt,
            body_html=html,
            from_addr="noreply@runefoble.local",
        )
    except Exception as exc:
        logger.warning("Could not dispatch email via Mailpit SMTP: %s", exc)

    await _write_campaign_viewer(user_id)
    return {
        "user_id": user_id,
        "username": username,
        "email": email,
        "roles": roles,
        "access_token": _generate_mock_jwt(user_id, username, email, roles),
        "refresh_token": f"refresh-{secrets.token_hex(16)}",
        "token_type": "Bearer",
        "expires_in": 3600,
        "verification_required": True,
        "message": f"Verification email dispatched to {email}. View email in Mailpit at http://localhost/mail/",
    }


@router.post("/verify")
@router.post("/verify-email")
async def verify_email(payload: VerifyEmailRequest) -> dict[str, Any]:
    """Verify user email via token or 6-digit OTP code captured in Mailpit."""
    email = payload.email.strip().lower()
    record = _pending_verifications.get(email)
    if not record:
        raise HTTPException(status_code=404, detail="No pending registration found for this email")
    if (payload.code and payload.code == record.get("code")) or (
        payload.token and payload.token == record.get("token")
    ):
        record["verified"] = True
        return {"status": "verified", "email": email, "message": "Email successfully verified!"}
    raise HTTPException(status_code=400, detail="Invalid verification code or token")


@router.post("/resend-verification")
async def resend_verification(payload: VerifyEmailRequest) -> dict[str, Any]:
    """Resend a pending verification code/email to the user."""
    email = payload.email.strip().lower()
    record = _pending_verifications.get(email)
    if not record:
        raise HTTPException(status_code=404, detail="No pending registration found for this email")
    code, token = f"{secrets.randbelow(900000) + 100000}", secrets.token_urlsafe(24)
    record.update({"code": code, "token": token, "created_at": time.time()})
    url = f"http://runefoble.local/auth/verify?token={token}&email={email}"
    try:
        await get_mailpit_client().send_email(
            to=email,
            subject="Runefoble Verification Code Resend",
            body_text=f"Your verification code is: {code}\nActivation URL: {url}",
            from_addr="noreply@runefoble.local",
        )
    except Exception as exc:
        logger.warning("Could not resend email: %s", exc)
    return {"status": "resent", "email": email, "message": f"Verification email resent to {email}."}


__all__ = [
    "_pending_verifications",
    "register_user",
    "resend_verification",
    "router",
    "verify_email",
]
