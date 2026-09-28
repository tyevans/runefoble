#!/usr/bin/env python3
"""CLI utility to seed default administrator or invite new admins/DMs in local development.

Dispatches credentials and invite links via Mailpit (mock SMTP) and writes
fine-grained Zanzibar permissions into SpiceDB.

Usage:
  python3 scripts/invite_admin.py --seed
  python3 scripts/invite_admin.py --email elena@runefoble.local --name Elena --role dm
  python3 scripts/invite_admin.py --email admin2@runefoble.local --role admin
"""

import argparse
import asyncio
import contextlib
import json
import secrets
import sys
from pathlib import Path

# Ensure local libs are discoverable when executed directly via python3
REPO_ROOT = Path(__file__).resolve().parents[1]
for lib_dir in [
    REPO_ROOT / "libs" / "runefoble_platform" / "src",
    REPO_ROOT / "libs" / "runefoble_auth" / "src",
    REPO_ROOT / "libs" / "runefoble_events" / "src",
]:
    if str(lib_dir) not in sys.path:
        sys.path.insert(0, str(lib_dir))

import httpx  # noqa: E402
from runefoble_auth.spicedb import SpiceDBClient  # noqa: E402
from runefoble_platform.email_client import MailpitClient  # noqa: E402


async def seed_default_admin(gateway_url: str = "http://localhost", json_output: bool = False):
    """Seed the default local development administrator account."""
    # Attempt through Gateway API first if reachable
    with contextlib.suppress(Exception):
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.post(
                f"{gateway_url}/api/v1/auth/admin/seed",
                json={
                    "username": "admin",
                    "email": "admin@runefoble.local",
                    "password": "RunefobleAdminPassword123!",
                },
            )
            if res.status_code in (200, 201):
                data = res.json()
                if json_output:
                    print(json.dumps(data, indent=2))
                else:
                    _print_banner("Default Local Administrator Seeded")
                    print(f"  Username  : {data.get('username')}")
                    print(f"  Email     : {data.get('email')}")
                    print("  Password  : RunefobleAdminPassword123!")
                    print(f"  Roles     : {', '.join(data.get('roles', []))}")
                    print("  SpiceDB   : system:runefoble#admin@user:user-admin")
                    print(f"  Mailpit UI: {data.get('mailpit_url', 'http://localhost/mail/')}")
                    print("\nCredentials dispatched to Mailpit. Open the UI to view the email.")
                return 0

    # Direct offline fallback
    mailpit = MailpitClient()
    spicedb = SpiceDBClient()

    with contextlib.suppress(Exception):
        await spicedb.write_relationship(
            resource_type="system",
            resource_id="runefoble",
            relation="admin",
            subject_type="user",
            subject_id="user-admin",
        )

    await mailpit.send_email(
        to="admin@runefoble.local",
        subject="Runefoble Local Dev Admin Credentials",
        body_text=(
            "Hail Administrator admin!\n\n"
            "Your local development admin account has been provisioned:\n"
            "Username: admin\n"
            "Email: admin@runefoble.local\n"
            "Password: RunefobleAdminPassword123!\n"
            "Roles: admin, dm, player\n\n"
            "Login at: http://localhost/#/login or http://localhost/auth\n"
            "Inspect in Mailpit: http://localhost/mail/\n"
        ),
        from_addr="system@runefoble.local",
    )

    if json_output:
        print(
            json.dumps(
                {
                    "status": "seeded",
                    "username": "admin",
                    "email": "admin@runefoble.local",
                    "roles": ["admin", "dm", "player"],
                    "mailpit_url": "http://localhost/mail/",
                },
                indent=2,
            )
        )
    else:
        _print_banner("Default Local Administrator Seeded (Standalone)")
        print("  Username  : admin")
        print("  Email     : admin@runefoble.local")
        print("  Password  : RunefobleAdminPassword123!")
        print("  Roles     : admin, dm, player")
        print("  SpiceDB   : system:runefoble#admin@user:user-admin")
        print("  Mailpit UI: http://localhost/mail/")
        print("\nCredentials dispatched to Mailpit. Open the UI to view the email.")
    return 0


async def invite_admin_or_dm(
    email: str,
    name: str = "",
    role: str = "admin",
    gateway_url: str = "http://localhost",
    json_output: bool = False,
):
    """Invite an administrator or DM and dispatch invite email to Mailpit."""
    role = role.lower().strip()
    if role not in ("admin", "dm", "player"):
        role = "admin"

    username = name or email.split("@")[0]

    # Attempt via Gateway API if online
    with contextlib.suppress(Exception):
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.post(
                f"{gateway_url}/api/v1/auth/admin/invite",
                json={"email": email, "username": username, "role": role},
            )
            if res.status_code in (200, 201):
                data = res.json()
                if json_output:
                    print(json.dumps(data, indent=2))
                else:
                    _print_banner(f"Invited {role.upper()} to Runefoble")
                    print(f"  Username   : {data.get('username')}")
                    print(f"  Email      : {data.get('email')}")
                    print(f"  Role       : {role}")
                    print(f"  Invite URL : {data.get('invite_url')}")
                    print(f"  Token      : {data.get('invite_token')}")
                    print(f"  Mailpit UI : {data.get('mailpit_url', 'http://localhost/mail/')}")
                    print(
                        "\nInvitation dispatched to Mailpit! Open http://localhost/mail/ to accept."
                    )
                return 0

    # Direct offline fallback
    mailpit = MailpitClient()
    spicedb = SpiceDBClient()
    token = secrets.token_urlsafe(32)
    user_id = f"user-{username.lower().replace(' ', '-')}"
    invite_url = f"http://runefoble.local/auth/invite?token={token}&email={email}&role={role}"

    with contextlib.suppress(Exception):
        rel = "admin" if role == "admin" else "game_master" if role == "dm" else "player"
        await spicedb.write_relationship(
            resource_type="system",
            resource_id="runefoble",
            relation=rel,
            subject_type="user",
            subject_id=user_id,
        )

    await mailpit.send_email(
        to=email,
        subject=f"Invitation: Join Runefoble as {role.upper()}",
        body_text=(
            f"Greetings {username},\n\n"
            f"You have been invited to join Runefoble as a {role.upper()}.\n\n"
            f"Claim your invite and set your password here:\n{invite_url}\n\n"
            f"Invite Token: {token}\n\n"
            f"May your adventures be legendary!\n- The Watcher"
        ),
        from_addr="admin-invite@runefoble.local",
    )

    if json_output:
        print(
            json.dumps(
                {
                    "status": "invited",
                    "email": email,
                    "username": username,
                    "role": role,
                    "invite_token": token,
                    "invite_url": invite_url,
                    "mailpit_url": "http://localhost/mail/",
                },
                indent=2,
            )
        )
    else:
        _print_banner(f"Invited {role.upper()} to Runefoble (Standalone)")
        print(f"  Username   : {username}")
        print(f"  Email      : {email}")
        print(f"  Role       : {role}")
        print(f"  Invite URL : {invite_url}")
        print(f"  Token      : {token}")
        print("  Mailpit UI : http://localhost/mail/")
        print("\nInvitation dispatched to Mailpit! Open http://localhost/mail/ to accept.")
    return 0


def _print_banner(title: str):
    print("\n" + "=" * 60)
    print(f"  🛡️  {title}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Seed local admin or invite admin/DM users via Mailpit."
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed default local admin (admin / admin@runefoble.local)",
    )
    parser.add_argument("--email", type=str, help="Email address to invite")
    parser.add_argument("--name", type=str, default="", help="Username or display name")
    parser.add_argument(
        "--role",
        type=str,
        default="admin",
        choices=["admin", "dm", "player"],
        help="Role to grant (admin, dm, or player)",
    )
    parser.add_argument(
        "--gateway",
        type=str,
        default="http://localhost",
        help="Base gateway URL (default: http://localhost)",
    )
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()

    if args.email:
        ret = asyncio.run(
            invite_admin_or_dm(
                email=args.email,
                name=args.name,
                role=args.role,
                gateway_url=args.gateway,
                json_output=args.json,
            )
        )
        sys.exit(ret)

    # Default action is seed admin
    ret = asyncio.run(seed_default_admin(gateway_url=args.gateway, json_output=args.json))
    sys.exit(ret)


if __name__ == "__main__":
    main()
