"""Blackbox verification for Mailpit email testing, mock SMTP, and user email signups.

Tests cover:
- MailpitClient SMTP transmission and REST API inspection
- Fallback in-memory behavior when Mailpit is offline
- Gateway API user registration endpoint (/api/v1/auth/register)
- Verification email dispatch, 6-digit OTP codes, and activation URLs
- Email verification via captured codes (/api/v1/auth/verify)
- Dev test email endpoint (/api/v1/auth/test-email)
- Mailpit health check and status reporting
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app
from gateway_api.routers.auth import (
    _pending_verifications,
    get_mailpit_client,
    set_mailpit_client,
)
from runefoble_platform.email_client import (
    MailpitClient,
)


@pytest.fixture(autouse=True)
def reset_mailpit_state():
    """Ensure clean Mailpit client and verification state before each test."""
    client = MailpitClient(fallback_in_memory=True)
    set_mailpit_client(client)
    _pending_verifications.clear()
    yield client
    client.sent_emails.clear()
    _pending_verifications.clear()


@pytest.mark.asyncio
async def test_mailpit_client_send_and_inspect_in_memory():
    """Verify MailpitClient sends emails and inspects messages via memory fallback."""
    client = MailpitClient(fallback_in_memory=True)

    outbound = await client.send_email(
        to="adventurer@runefoble.local",
        subject="Welcome to the Frontier",
        body_text="Your quest begins at dawn. Use verification code: 481516",
        body_html="<p>Your quest begins at dawn. Code: <strong>481516</strong></p>",
        from_addr="dm@runefoble.local",
    )

    assert outbound.subject == "Welcome to the Frontier"
    assert outbound.to == ["adventurer@runefoble.local"]
    assert outbound.from_addr == "dm@runefoble.local"

    # List messages
    messages = await client.list_messages()
    assert len(messages) == 1
    assert messages[0].subject == "Welcome to the Frontier"
    assert "adventurer@runefoble.local" in messages[0].to

    # Get single message details
    detail = await client.get_message(messages[0].id)
    assert detail is not None
    assert "481516" in detail.text
    assert "<strong>481516</strong>" in detail.html

    # Get latest message
    latest = await client.get_latest_message()
    assert latest is not None
    assert latest.id == messages[0].id

    # Search messages
    search_results = await client.search_messages("quest")
    assert len(search_results) == 1
    no_results = await client.search_messages("nonexistent")
    assert len(no_results) == 0

    # Extract verification code
    code = MailpitClient.extract_verification_code(detail.text)
    assert code == "481516"

    # Delete messages
    deleted = await client.delete_all_messages()
    assert deleted is True
    assert len(await client.list_messages()) == 0


@pytest.mark.asyncio
async def test_mailpit_verification_link_and_code_extraction():
    """Verify regex extraction of activation links and OTP codes from email content."""
    body_with_link = (
        "Welcome! Activate your account here: "
        "http://runefoble.local/auth/verify?token=xyz123abc456&email=test@runefoble.local "
        "before it expires."
    )
    link = MailpitClient.extract_verification_link(body_with_link)
    assert (
        link == "http://runefoble.local/auth/verify?token=xyz123abc456&email=test@runefoble.local"
    )

    body_with_otp = "Your Runefoble verification code is: 839201. Do not share this."
    code = MailpitClient.extract_verification_code(body_with_otp)
    assert code == "839201"

    body_standalone_digits = "Confirm signup with 654321."
    code2 = MailpitClient.extract_verification_code(body_standalone_digits)
    assert code2 == "654321"


@pytest.mark.asyncio
async def test_mailpit_live_socket_smtp_server_interaction():
    """Verify MailpitClient transmits actual RFC-822 email over TCP socket using standard SMTP protocol."""
    received_emails: list[bytes] = []

    async def handle_smtp_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        writer.write(b"220 mailpit.local ESMTP Mock\r\n")
        await writer.drain()

        while True:
            line = await reader.readline()
            if not line:
                break
            cmd = line.upper().strip()
            if cmd.startswith(b"EHLO") or cmd.startswith(b"HELO"):
                writer.write(b"250-mailpit.local\r\n250 HELP\r\n")
                await writer.drain()
            elif cmd.startswith(b"MAIL FROM:"):
                writer.write(b"250 2.1.0 Ok\r\n")
                await writer.drain()
            elif cmd.startswith(b"RCPT TO:"):
                writer.write(b"250 2.1.5 Ok\r\n")
                await writer.drain()
            elif cmd == b"DATA":
                writer.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                await writer.drain()
                buffer = bytearray()
                while True:
                    dline = await reader.readline()
                    if dline == b".\r\n":
                        break
                    buffer.extend(dline)
                received_emails.append(bytes(buffer))
                writer.write(b"250 2.0.0 Ok: queued\r\n")
                await writer.drain()
            elif cmd == b"QUIT":
                writer.write(b"221 2.0.0 Bye\r\n")
                await writer.drain()
                break

        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_smtp_client, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    try:
        live_client = MailpitClient(
            smtp_host="127.0.0.1",
            smtp_port=port,
            http_url="http://127.0.0.1:8025",
            fallback_in_memory=False,
        )

        outbound = await live_client.send_email(
            to="player1@runefoble.local",
            subject="Live SMTP Test",
            body_text="Testing SMTP wire protocol transmission",
            from_addr="noreply@runefoble.local",
        )
        assert outbound.subject == "Live SMTP Test"
        assert len(received_emails) == 1
        raw_email = received_emails[0].decode()
        assert "Subject: Live SMTP Test" in raw_email
        assert "player1@runefoble.local" in raw_email
    finally:
        server.close()
        await server.wait_closed()


def test_blackbox_gateway_registration_dispatches_email_to_mailpit():
    """Verify that registering via /api/v1/auth/register dispatches email to Mailpit."""
    client = TestClient(app)
    mailpit = get_mailpit_client()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "EldrinTheWizard",
            "email": "eldrin@runefoble.local",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "EldrinTheWizard"
    assert data["email"] == "eldrin@runefoble.local"
    assert data["user_id"] == "user-eldrinthewizard"
    assert "access_token" in data
    assert data["verification_required"] is True
    assert "http://localhost/mail/" in data["message"]

    # Verify that Mailpit received the verification email
    assert len(mailpit.sent_emails) == 1
    sent = mailpit.sent_emails[0]
    assert "Welcome to Runefoble!" in sent.subject
    assert sent.to == ["eldrin@runefoble.local"]

    # Verify email contents contain code and activation URL
    code = MailpitClient.extract_verification_code(sent.body_text)
    assert code is not None
    assert len(code) == 6

    link = MailpitClient.extract_verification_link(sent.body_text)
    assert link is not None
    assert "token=" in link
    assert "email=eldrin@runefoble.local" in link


def test_blackbox_gateway_verify_email_via_code_and_token():
    """Verify that user account can be verified with code or link extracted from Mailpit."""
    test_client = TestClient(app)
    mailpit = get_mailpit_client()

    # 1. Register user
    reg_res = test_client.post(
        "/api/v1/auth/register",
        json={
            "username": "KaelenRanger",
            "email": "kaelen@runefoble.local",
            "password": "SecretPassword123!",
        },
    )
    assert reg_res.status_code == 201

    # 2. Extract code from Mailpit email
    latest_email = mailpit.sent_emails[-1]
    otp_code = MailpitClient.extract_verification_code(latest_email.body_text)
    assert otp_code is not None

    # 3. Verify via 6-digit code
    verify_res = test_client.post(
        "/api/v1/auth/verify",
        json={"email": "kaelen@runefoble.local", "code": otp_code},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "verified"

    # 4. Bad code returns 400
    bad_res = test_client.post(
        "/api/v1/auth/verify",
        json={"email": "kaelen@runefoble.local", "code": "000000"},
    )
    assert bad_res.status_code == 400


def test_blackbox_gateway_auth_token_and_test_email():
    """Verify /api/v1/auth/token login and /api/v1/auth/test-email developer endpoint."""
    client = TestClient(app)
    mailpit = get_mailpit_client()

    # Test login for token
    token_res = client.post(
        "/api/v1/auth/token",
        json={"username": "DungeonMaster", "password": "Password123!"},
    )
    assert token_res.status_code == 200
    token_data = token_res.json()
    assert "access_token" in token_data
    assert "dm" in token_data["roles"]

    # Test sending dev test email to Mailpit
    test_email_res = client.post(
        "/api/v1/auth/test-email",
        json={
            "to": "dev-tester@runefoble.local",
            "subject": "Mailpit Integration Check",
            "body": "Verifying that dev emails show up in the Mailpit inbox.",
        },
    )
    assert test_email_res.status_code == 200
    assert test_email_res.json()["status"] == "sent"

    # Mailpit captured the test email
    assert any(e.subject == "Mailpit Integration Check" for e in mailpit.sent_emails)


def test_mailpit_status_endpoint():
    """Verify /api/v1/auth/mailpit/status returns structured connectivity details."""
    client = TestClient(app)
    res = client.get("/api/v1/auth/mailpit/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "http_available" in data
    assert "smtp_available" in data
    assert "message_count" in data
    assert "web_ui_url" in data


def test_blackbox_gateway_admin_seed_and_invite():
    """Verify /api/v1/auth/admin/seed and /api/v1/auth/admin/invite dispatch emails to Mailpit."""
    client = TestClient(app)
    mailpit = get_mailpit_client()

    # 1. Seed dev admin
    seed_res = client.post("/api/v1/auth/admin/seed")
    assert seed_res.status_code == 200
    seed_data = seed_res.json()
    assert seed_data["status"] == "seeded"
    assert seed_data["username"] == "admin"
    assert "admin" in seed_data["roles"]
    assert "dm" in seed_data["roles"]
    assert "http://localhost/mail/" in seed_data["mailpit_url"]

    # Verify credentials email captured in Mailpit
    admin_email = next((e for e in mailpit.sent_emails if e.to == ["admin@runefoble.local"]), None)
    assert admin_email is not None
    assert "Admin Credentials" in admin_email.subject
    assert "RunefobleAdminPassword123!" in admin_email.body_text

    # 2. Invite a new DM
    invite_res = client.post(
        "/api/v1/auth/admin/invite",
        json={
            "email": "archmage-elena@runefoble.local",
            "username": "Elena",
            "role": "dm",
        },
    )
    assert invite_res.status_code == 200
    invite_data = invite_res.json()
    assert invite_data["status"] == "invited"
    assert invite_data["email"] == "archmage-elena@runefoble.local"
    assert "dm" in invite_data["roles"]
    assert "invite_token" in invite_data
    assert "http://runefoble.local/auth/invite" in invite_data["invite_url"]

    # Verify invitation email captured in Mailpit
    invite_email = next(
        (e for e in mailpit.sent_emails if e.to == ["archmage-elena@runefoble.local"]),
        None,
    )
    assert invite_email is not None
    assert "Invitation" in invite_email.subject
    assert invite_data["invite_token"] in invite_email.body_text
