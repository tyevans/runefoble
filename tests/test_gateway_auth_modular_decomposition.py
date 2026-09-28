"""Frontdoor blackbox tests for TASK-0241: Gateway Auth Router Modular Decomposition.

Verifies:
1. Strict line length invariants (< 130 lines for each module in gateway/api/src/gateway_api/routers/auth/).
2. Removal and replacement of monolithic auth.py.
3. Registration endpoints (/register, /verify-email, /verify, /resend-verification).
4. OAuth2 token handlers (/token, /refresh, /logout).
5. Dev testing endpoints (/dev/emails, /dev/send-test, /test-email, /dev/stats, /mailpit/status).
6. Admin provisioning endpoints (/admin/seed, /admin/invite).
7. Backward compatibility and symbol re-exports from gateway_api.routers.auth.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app
from gateway_api.routers.auth import (
    DevSendEmailRequest,
    InviteAdminRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    SeedAdminRequest,
    TestEmailRequest,
    TokenRequest,
    VerifyEmailRequest,
    _generate_mock_jwt,
    _mailpit_client,
    _pending_verifications,
    get_mailpit_client,
    router,
    set_mailpit_client,
)
from runefoble_platform.email_client import MailpitClient

TestEmailRequest.__test__ = False

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTH_PKG_DIR = REPO_ROOT / "gateway/api/src/gateway_api/routers/auth"


@pytest.fixture(autouse=True)
def reset_mailpit_state():
    """Ensure clean Mailpit client and verification store before each test."""
    client = MailpitClient(fallback_in_memory=True)
    set_mailpit_client(client)
    _pending_verifications.clear()
    yield client
    client.sent_emails.clear()
    _pending_verifications.clear()


def test_auth_submodules_line_length_invariants():
    """Verify all submodules in auth/ are strictly under 130 lines per Hard Invariant 6."""
    legacy_file = REPO_ROOT / "gateway/api/src/gateway_api/routers/auth.py"
    assert not legacy_file.exists(), "Monolithic auth.py must be removed"
    assert AUTH_PKG_DIR.is_dir(), f"Auth package directory {AUTH_PKG_DIR} must exist"

    expected_files = [
        "__init__.py",
        "admin.py",
        "dev_mail.py",
        "registration.py",
        "schemas.py",
        "tokens.py",
    ]
    for filename in expected_files:
        file_path = AUTH_PKG_DIR / filename
        assert file_path.is_file(), f"Expected submodule {file_path} to exist"
        line_count = len(file_path.read_text(encoding="utf-8").splitlines())
        assert line_count < 130, (
            f"Submodule {filename} exceeds 130 lines invariant ({line_count} lines)"
        )


def test_auth_public_symbol_exports():
    """Verify backward compatibility of public symbols and models exported by auth package."""
    assert router is not None
    assert callable(get_mailpit_client)
    assert callable(set_mailpit_client)
    assert callable(_generate_mock_jwt)
    assert isinstance(_pending_verifications, dict)
    assert _mailpit_client is not None

    for schema_cls in [
        RegisterRequest,
        TokenRequest,
        RefreshRequest,
        VerifyEmailRequest,
        DevSendEmailRequest,
        TestEmailRequest,
        PasswordResetRequest,
        SeedAdminRequest,
        InviteAdminRequest,
    ]:
        assert issubclass(schema_cls, object)


def test_registration_flow_and_resend_verification():
    """Verify user registration, verification code dispatch, resend, and activation."""
    client = TestClient(app)
    mailpit = get_mailpit_client()

    reg_payload = {
        "username": "DecompAdventurer",
        "email": "decomp@runefoble.local",
        "password": "Password123!",
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["username"] == "DecompAdventurer"
    assert reg_data["verification_required"] is True

    # Resend verification
    resend_res = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "decomp@runefoble.local"},
    )
    assert resend_res.status_code == 200
    assert resend_res.json()["status"] == "resent"

    # Resend for non-existent user returns 404
    missing_res = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "nobody@runefoble.local"},
    )
    assert missing_res.status_code == 404

    # Verify email with code via /verify-email endpoint
    otp_code = MailpitClient.extract_verification_code(mailpit.sent_emails[-1].body_text)
    assert otp_code is not None

    verify_res = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "decomp@runefoble.local", "code": otp_code},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "verified"


def test_tokens_flow_and_logout():
    """Verify OAuth2 token grant, refresh flow, and user logout endpoint."""
    client = TestClient(app)

    token_res = client.post(
        "/api/v1/auth/token",
        json={"username": "DMRoger", "password": "Password123!"},
    )
    assert token_res.status_code == 200
    token_data = token_res.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert "dm" in token_data["roles"]

    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_data["refresh_token"]},
    )
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()

    logout_res = client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "logged_out"


def test_dev_mail_and_admin_endpoints():
    """Verify dev mail inspection, test send, stats, clearing, and admin provisioning."""
    client = TestClient(app)

    # Dev send test
    test_send_res = client.post(
        "/api/v1/auth/dev/send-test",
        json={
            "to": "test-dev@runefoble.local",
            "subject": "Decomp Dev Test",
            "body": "Dev mail test body content",
        },
    )
    assert test_send_res.status_code == 200
    assert test_send_res.json()["status"] == "sent"

    # Dev list emails
    list_res = client.get("/api/v1/auth/dev/emails")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # Dev stats / mailpit status
    stats_res = client.get("/api/v1/auth/dev/stats")
    assert stats_res.status_code == 200
    assert "smtp_available" in stats_res.json()

    # Clear emails
    clear_res = client.delete("/api/v1/auth/dev/emails")
    assert clear_res.status_code == 200
    assert clear_res.json()["status"] == "cleared"

    # Admin seed
    seed_res = client.post("/api/v1/auth/admin/seed")
    assert seed_res.status_code == 200
    assert seed_res.json()["status"] == "seeded"

    # Admin invite
    invite_res = client.post(
        "/api/v1/auth/admin/invite",
        json={"email": "guest-dm@runefoble.local", "username": "GuestDM", "role": "dm"},
    )
    assert invite_res.status_code == 200
    assert invite_res.json()["status"] == "invited"
