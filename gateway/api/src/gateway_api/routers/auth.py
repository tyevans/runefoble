"""Authentication and Email Registration router for Runefoble Gateway API.

Handles user signup/registration, verification emails sent via Mailpit (mock SMTP),
token exchange, and dev email testing endpoints.
"""

import base64
import json
import logging
import secrets
import time
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.email_client import MailpitClient

logger = logging.getLogger("runefoble.gateway.auth_router")

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Signups"])

# Global Mailpit client instance for gateway email delivery
_mailpit_client = MailpitClient()

# In-memory store for pending verifications (in dev mode)
_pending_verifications: dict[str, dict[str, Any]] = {}


def get_mailpit_client() -> MailpitClient:
    return _mailpit_client


def set_mailpit_client(client: MailpitClient) -> None:
    global _mailpit_client
    _mailpit_client = client


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50, description="Desired username")
    email: str = Field(description="User email address")
    password: str = Field(min_length=6, description="User password")


class TokenRequest(BaseModel):
    username: str
    password: str
    grant_type: str = "password"


class RefreshRequest(BaseModel):
    refresh_token: str
    grant_type: str = "refresh_token"


class VerifyEmailRequest(BaseModel):
    email: str
    token: str | None = None
    code: str | None = None


class TestEmailRequest(BaseModel):
    to: str = Field(description="Recipient email address")
    subject: str = Field(default="Runefoble Dev Email Test", description="Email subject")
    body: str = Field(
        default="This is a test email sent to Mailpit to verify SMTP dev delivery.",
        description="Email text body",
    )


class SeedAdminRequest(BaseModel):
    username: str = Field(default="admin", description="Admin username")
    email: str = Field(default="admin@runefoble.local", description="Admin email")
    password: str = Field(default="RunefobleAdminPassword123!", description="Admin password")


class InviteAdminRequest(BaseModel):
    email: str = Field(description="Invited admin/DM email address")
    username: str = Field(default="", description="Invited username or display name")
    role: str = Field(default="admin", description="Assigned role: admin, dm, or player")


def _generate_mock_jwt(user_id: str, username: str, email: str, roles: list[str]) -> str:
    """Generate a lightweight HS256-like dev JWT token for client testing."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
    now = int(time.time())
    payload_data = {
        "sub": user_id,
        "preferred_username": username,
        "email": email,
        "urn:zitadel:iam:org:project:roles": roles,
        "roles": roles,
        "iat": now,
        "exp": now + 3600,
    }
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(b"runefoble-dev-signature").decode().rstrip("=")
    return f"{header}.{payload}.{signature}"


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest) -> dict[str, Any]:
    """Register a new user account, dispatch a verification email via Mailpit SMTP, and return auth tokens."""
    username = payload.username.strip()
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address format")

    user_id = f"user-{username.lower().replace(' ', '-')}"
    roles = ["dm", "player"] if "dm" in username.lower() else ["player"]

    # Generate verification token and 6-digit verification code
    verification_token = secrets.token_urlsafe(24)
    verification_code = f"{secrets.randbelow(900000) + 100000}"

    _pending_verifications[email] = {
        "user_id": user_id,
        "username": username,
        "token": verification_token,
        "code": verification_code,
        "verified": False,
        "created_at": time.time(),
    }

    # Dispatch welcome & verification email via Mailpit (SMTP)
    subject = "Welcome to Runefoble! Confirm your adventurer account"
    verify_url = f"http://runefoble.local/auth/verify?token={verification_token}&email={email}"
    text_content = (
        f"Hail {username}!\n\n"
        f"Welcome to Runefoble, the collaborative AI tabletop roleplaying platform.\n\n"
        f"Your verification code is: {verification_code}\n\n"
        f"Or click here to activate your account:\n{verify_url}\n\n"
        f"May your dice roll true!\n- The Watcher"
    )
    html_content = (
        f"<div style='font-family: sans-serif; max-width: 600px; margin: 0 auto;'>"
        f"<h2 style='color: #1a1a2e;'>Hail {username}!</h2>"
        f"<p>Welcome to <strong>Runefoble</strong>, the collaborative AI tabletop roleplaying platform.</p>"
        f"<p>Your 6-digit verification code is:</p>"
        f"<div style='background: #eef2ff; padding: 12px; font-size: 24px; font-weight: bold; letter-spacing: 4px; text-align: center;'>{verification_code}</div>"
        f"<p style='margin-top: 20px;'><a href='{verify_url}' style='background: #4f46e5; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;'>Confirm Account</a></p>"
        f"<p style='color: #6b7280; font-size: 12px; margin-top: 30px;'>May your dice roll true!<br/>The Watcher</p>"
        f"</div>"
    )

    try:
        await _mailpit_client.send_email(
            to=email,
            subject=subject,
            body_text=text_content,
            body_html=html_content,
            from_addr="noreply@runefoble.local",
        )
    except Exception as exc:
        logger.warning("Could not dispatch email via Mailpit SMTP: %s", exc)

    # Automatically sync user to SpiceDB Zanzibar permissions if client available
    try:
        spicedb = SpiceDBClient()
        await spicedb.write_relationship(
            resource_type="campaign",
            resource_id="public",
            relation="viewer",
            subject_type="user",
            subject_id=user_id,
        )
    except Exception:
        pass

    access_token = _generate_mock_jwt(user_id, username, email, roles)
    return {
        "user_id": user_id,
        "username": username,
        "email": email,
        "roles": roles,
        "access_token": access_token,
        "refresh_token": f"refresh-{secrets.token_hex(16)}",
        "token_type": "Bearer",
        "expires_in": 3600,
        "verification_required": True,
        "message": f"Verification email dispatched to {email}. View email in Mailpit at http://localhost/mail/",
    }


@router.post("/verify")
async def verify_email(payload: VerifyEmailRequest) -> dict[str, Any]:
    """Verify user email via token or 6-digit OTP code captured in Mailpit."""
    email = payload.email.strip().lower()
    record = _pending_verifications.get(email)
    if not record:
        raise HTTPException(status_code=404, detail="No pending registration found for this email")

    if payload.code and payload.code == record.get("code"):
        record["verified"] = True
        return {"status": "verified", "email": email, "message": "Email successfully verified!"}

    if payload.token and payload.token == record.get("token"):
        record["verified"] = True
        return {"status": "verified", "email": email, "message": "Email successfully verified!"}

    raise HTTPException(status_code=400, detail="Invalid verification code or token")


@router.post("/token")
async def login_for_token(payload: TokenRequest) -> dict[str, Any]:
    """Exchange username and password for JWT authentication tokens."""
    username = payload.username.strip()
    user_id = f"user-{username.lower().replace(' ', '-')}"
    roles = (
        ["dm", "player"]
        if any(term in username.lower() for term in ("dm", "master", "dungeon"))
        else ["player"]
    )
    email = f"{username.lower()}@runefoble.local"
    access_token = _generate_mock_jwt(user_id, username, email, roles)

    return {
        "access_token": access_token,
        "refresh_token": f"refresh-{secrets.token_hex(16)}",
        "token_type": "Bearer",
        "expires_in": 3600,
        "user_id": user_id,
        "username": username,
        "roles": roles,
    }


@router.post("/refresh")
async def refresh_token(payload: RefreshRequest) -> dict[str, Any]:
    """Refresh an access token using a valid refresh token."""
    if not payload.refresh_token:
        raise HTTPException(status_code=400, detail="Missing refresh token")
    access_token = _generate_mock_jwt(
        "user-refreshed", "adventurer", "adventurer@runefoble.local", ["player"]
    )
    return {
        "access_token": access_token,
        "refresh_token": f"refresh-{secrets.token_hex(16)}",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


@router.post("/test-email")
async def send_test_email(payload: TestEmailRequest) -> dict[str, Any]:
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


@router.get("/mailpit/status")
async def mailpit_status() -> dict[str, Any]:
    """Inspect Mailpit SMTP and REST connectivity."""
    return await _mailpit_client.check_health()


@router.post("/admin/seed")
async def seed_dev_admin(payload: SeedAdminRequest | None = None) -> dict[str, Any]:
    """Seed the default local development administrator account in Zanzibar and dispatch credentials to Mailpit."""
    req = payload or SeedAdminRequest()
    user_id = f"user-{req.username.lower()}"
    roles = ["admin", "dm", "player"]

    # Register in Zanzibar
    try:
        spicedb = SpiceDBClient()
        await spicedb.write_relationship(
            resource_type="system",
            resource_id="runefoble",
            relation="admin",
            subject_type="user",
            subject_id=user_id,
        )
    except Exception:
        pass

    subject = "Runefoble Local Dev Admin Credentials"
    body_text = (
        f"Hail Administrator {req.username}!\n\n"
        f"Your local development admin account has been provisioned:\n"
        f"Username: {req.username}\n"
        f"Email: {req.email}\n"
        f"Password: {req.password}\n"
        f"Roles: {', '.join(roles)}\n\n"
        f"Login at: http://localhost/#/login or http://localhost/auth\n"
        f"Inspect this email in Mailpit at: http://localhost/mail/\n"
    )
    body_html = (
        f"<div style='font-family: sans-serif; max-width: 600px; margin: 0 auto;'>"
        f"<h2 style='color: #1a1a2e;'>🛡️ Runefoble Local Admin Provisioned</h2>"
        f"<p>Your local development admin credentials have been seeded:</p>"
        f"<ul>"
        f"<li><strong>Username:</strong> {req.username}</li>"
        f"<li><strong>Email:</strong> {req.email}</li>"
        f"<li><strong>Password:</strong> <code>{req.password}</code></li>"
        f"<li><strong>Roles:</strong> {', '.join(roles)}</li>"
        f"</ul>"
        f"<p><a href='http://localhost/auth' style='background: #4f46e5; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;'>Log In to Zitadel Console</a></p>"
        f"<p style='color: #6b7280; font-size: 12px;'>Runefoble Dev Environment</p>"
        f"</div>"
    )

    await _mailpit_client.send_email(
        to=req.email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        from_addr="system@runefoble.local",
    )

    access_token = _generate_mock_jwt(user_id, req.username, req.email, roles)
    return {
        "status": "seeded",
        "user_id": user_id,
        "username": req.username,
        "email": req.email,
        "roles": roles,
        "access_token": access_token,
        "mailpit_url": "http://localhost/mail/",
        "message": f"Admin seeded. Credentials dispatched to {req.email} in Mailpit.",
    }


@router.post("/admin/invite")
async def invite_admin_or_dm(payload: InviteAdminRequest) -> dict[str, Any]:
    """Invite an administrator or DM to the local development environment via Mailpit email."""
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address format")

    username = payload.username.strip() or email.split("@")[0]
    user_id = f"user-{username.lower().replace(' ', '-')}"
    role = payload.role.lower().strip()
    roles = (
        ["admin", "dm", "player"]
        if role == "admin"
        else ["dm", "player"]
        if role == "dm"
        else ["player"]
    )

    invite_token = secrets.token_urlsafe(32)
    invite_url = (
        f"http://runefoble.local/auth/invite?token={invite_token}&email={email}&role={role}"
    )

    # Grant Zanzibar permissions
    try:
        spicedb = SpiceDBClient()
        rel = "admin" if "admin" in roles else "game_master" if "dm" in roles else "player"
        await spicedb.write_relationship(
            resource_type="system",
            resource_id="runefoble",
            relation=rel,
            subject_type="user",
            subject_id=user_id,
        )
    except Exception:
        pass

    subject = f"Invitation: Join Runefoble as {role.upper()}"
    body_text = (
        f"Greetings {username},\n\n"
        f"You have been invited to join Runefoble as a {role.upper()}.\n\n"
        f"Claim your invite and set your password here:\n{invite_url}\n\n"
        f"Invite Token: {invite_token}\n\n"
        f"May your adventures be legendary!\n- The Watcher"
    )
    body_html = (
        f"<div style='font-family: sans-serif; max-width: 600px; margin: 0 auto;'>"
        f"<h2 style='color: #1a1a2e;'>⚔️ You're Invited to Runefoble as {role.upper()}!</h2>"
        f"<p>Hail <strong>{username}</strong>,</p>"
        f"<p>An administrator has invited you to join the realm with <strong>{role.upper()}</strong> privileges.</p>"
        f"<p><a href='{invite_url}' style='background: #4f46e5; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;'>Accept Invitation & Set Password</a></p>"
        f"<p>Or use token: <code>{invite_token}</code></p>"
        f"<p style='color: #6b7280; font-size: 12px; margin-top: 30px;'>- The Watcher</p>"
        f"</div>"
    )

    await _mailpit_client.send_email(
        to=email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        from_addr="admin-invite@runefoble.local",
    )

    return {
        "status": "invited",
        "email": email,
        "username": username,
        "roles": roles,
        "invite_token": invite_token,
        "invite_url": invite_url,
        "mailpit_url": "http://localhost/mail/",
        "message": f"Invitation email dispatched to {email}. View email in Mailpit at http://localhost/mail/",
    }
