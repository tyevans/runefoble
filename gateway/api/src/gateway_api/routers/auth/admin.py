"""Local development administrator account provisioning and invitation endpoints."""

import contextlib
import secrets
from typing import Any

from fastapi import APIRouter, HTTPException
from gateway_api.routers.auth.dev_mail import get_mailpit_client
from gateway_api.routers.auth.schemas import InviteAdminRequest, SeedAdminRequest
from gateway_api.routers.auth.tokens import _generate_mock_jwt
from runefoble_auth.spicedb import SpiceDBClient

router = APIRouter()


async def _write_system_relation(user_id: str, relation: str) -> None:
    with contextlib.suppress(Exception):
        await SpiceDBClient().write_relationship("system", "runefoble", relation, "user", user_id)


@router.post("/admin/seed")
async def seed_dev_admin(payload: SeedAdminRequest | None = None) -> dict[str, Any]:
    """Seed default local dev administrator in Zanzibar and dispatch credentials to Mailpit."""
    req = payload or SeedAdminRequest()
    user_id = f"user-{req.username.lower()}"
    roles = ["admin", "dm", "player"]
    await _write_system_relation(user_id, "admin")

    body_text = (
        f"Hail Administrator {req.username}!\n\nYour local development admin account has been provisioned:\n"
        f"Username: {req.username}\nEmail: {req.email}\nPassword: {req.password}\nRoles: {', '.join(roles)}\n\n"
        f"Login at: http://localhost/#/login or http://localhost/auth\nInspect in Mailpit: http://localhost/mail/\n"
    )
    body_html = (
        f"<div style='font-family: sans-serif; max-width: 600px; margin: 0 auto;'>"
        f"<h2>🛡️ Runefoble Admin Provisioned</h2><p>User: {req.username}<br/>Pass: <code>{req.password}</code></p>"
        f"<p><a href='http://localhost/auth'>Log In</a></p></div>"
    )
    await get_mailpit_client().send_email(
        to=req.email,
        subject="Runefoble Local Dev Admin Credentials",
        body_text=body_text,
        body_html=body_html,
        from_addr="system@runefoble.local",
    )
    return {
        "status": "seeded",
        "user_id": user_id,
        "username": req.username,
        "email": req.email,
        "roles": roles,
        "access_token": _generate_mock_jwt(user_id, req.username, req.email, roles),
        "mailpit_url": "http://localhost/mail/",
        "message": f"Admin seeded. Credentials dispatched to {req.email} in Mailpit.",
    }


@router.post("/admin/invite")
async def invite_admin_or_dm(payload: InviteAdminRequest) -> dict[str, Any]:
    """Invite an administrator or DM to local dev environment via Mailpit email."""
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

    rel = "admin" if "admin" in roles else "game_master" if "dm" in roles else "player"
    await _write_system_relation(user_id, rel)

    body_text = (
        f"Greetings {username},\n\nYou have been invited to join Runefoble as a {role.upper()}.\n\n"
        f"Claim your invite and set your password here:\n{invite_url}\n\nInvite Token: {invite_token}\n\n"
        f"May your adventures be legendary!\n- The Watcher"
    )
    body_html = (
        f"<div style='font-family: sans-serif; max-width: 600px; margin: 0 auto;'>"
        f"<h2>⚔️ Invited to Runefoble as {role.upper()}!</h2>"
        f"<p><a href='{invite_url}'>Accept Invitation</a></p><p>Token: <code>{invite_token}</code></p></div>"
    )
    await get_mailpit_client().send_email(
        to=email,
        subject=f"Invitation: Join Runefoble as {role.upper()}",
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


__all__ = ["invite_admin_or_dm", "router", "seed_dev_admin"]
