"""Blackbox tests for user registration, Mailpit verification dispatch, and activation."""

from fastapi.testclient import TestClient
from runefoble_platform.email_client import MailpitClient


def test_registration_dispatches_email_to_mailpit(
    client: TestClient, mailpit: MailpitClient
) -> None:
    """Verify that registering via /api/v1/auth/register dispatches email to Mailpit."""
    payload = {
        "username": "EldrinTheWizard",
        "email": "eldrin@runefoble.local",
        "password": "SecurePassword123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "EldrinTheWizard"
    assert data["email"] == "eldrin@runefoble.local"
    assert data["user_id"] == "user-eldrinthewizard"
    assert "access_token" in data
    assert data["verification_required"] is True
    assert "http://localhost/mail/" in data["message"]

    assert len(mailpit.sent_emails) == 1
    sent = mailpit.sent_emails[0]
    assert "Welcome to Runefoble!" in sent.subject
    assert sent.to == ["eldrin@runefoble.local"]

    code = MailpitClient.extract_verification_code(sent.body_text)
    assert code is not None and len(code) == 6
    link = MailpitClient.extract_verification_link(sent.body_text)
    assert link is not None and "token=" in link and "email=eldrin@runefoble.local" in link


def test_verify_email_via_code_and_link(client: TestClient, mailpit: MailpitClient) -> None:
    """Verify that user account can be verified with code or link extracted from Mailpit."""
    reg = {
        "username": "KaelenRanger",
        "email": "kaelen@runefoble.local",
        "password": "SecretPassword123!",
    }
    assert client.post("/api/v1/auth/register", json=reg).status_code == 201

    latest_email = mailpit.sent_emails[-1]
    otp_code = MailpitClient.extract_verification_code(latest_email.body_text)
    assert otp_code is not None

    verify_res = client.post(
        "/api/v1/auth/verify",
        json={"email": "kaelen@runefoble.local", "code": otp_code},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "verified"

    bad_res = client.post(
        "/api/v1/auth/verify",
        json={"email": "kaelen@runefoble.local", "code": "000000"},
    )
    assert bad_res.status_code == 400

    not_found = client.post(
        "/api/v1/auth/verify",
        json={"email": "ghost@runefoble.local", "code": "123456"},
    )
    assert not_found.status_code == 404


def test_registration_validation_and_resend(client: TestClient, mailpit: MailpitClient) -> None:
    """Verify validation on invalid email and resend verification code flow."""
    bad_req = {"username": "InvalidUser", "email": "notanemail", "password": "Password123!"}
    assert client.post("/api/v1/auth/register", json=bad_req).status_code == 400

    good_req = {"username": "Gimli", "email": "gimli@runefoble.local", "password": "Pass123!"}
    assert client.post("/api/v1/auth/register", json=good_req).status_code == 201

    resend_res = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "gimli@runefoble.local"},
    )
    assert resend_res.status_code == 200
    assert resend_res.json()["status"] == "resent"

    missing_res = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "nobody@runefoble.local"},
    )
    assert missing_res.status_code == 404


def test_mailpit_verification_link_and_code_regex() -> None:
    """Verify regex extraction of activation links and OTP codes from email content."""
    body_with_link = (
        "Welcome! Activate: "
        "http://runefoble.local/auth/verify?token=xyz123abc456&email=test@runefoble.local"
    )
    assert (
        MailpitClient.extract_verification_link(body_with_link)
        == "http://runefoble.local/auth/verify?token=xyz123abc456&email=test@runefoble.local"
    )

    body_with_otp = "Your Runefoble verification code is: 839201. Do not share this."
    assert MailpitClient.extract_verification_code(body_with_otp) == "839201"

    body_standalone_digits = "Confirm signup with 654321."
    assert MailpitClient.extract_verification_code(body_standalone_digits) == "654321"
