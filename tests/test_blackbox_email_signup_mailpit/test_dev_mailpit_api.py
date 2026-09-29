"""Blackbox tests for developer Mailpit endpoints, inbox management, and admin seeding."""

from pathlib import Path

from fastapi.testclient import TestClient
from runefoble_platform.email_client import MailpitClient


def test_dev_send_and_list_emails(client: TestClient, mailpit: MailpitClient) -> None:
    """Verify /dev/send-test and /test-email dispatch emails and /dev/emails lists them."""
    send_res = client.post(
        "/api/v1/auth/dev/send-test",
        json={
            "to": "tester@runefoble.local",
            "subject": "Dev Test Email",
            "body": "Testing dev endpoints.",
        },
    )
    assert send_res.status_code == 200
    assert send_res.json()["status"] == "sent"

    legacy_res = client.post(
        "/api/v1/auth/test-email",
        json={"to": "legacy@runefoble.local", "subject": "Legacy Check", "body": "Checking."},
    )
    assert legacy_res.status_code == 200

    list_res = client.get("/api/v1/auth/dev/emails")
    assert list_res.status_code == 200
    emails = list_res.json()
    assert len(emails) >= 2


def test_dev_emails_clear(client: TestClient, mailpit: MailpitClient) -> None:
    """Verify DELETE /dev/emails purges all messages from the Mailpit inbox."""
    client.post(
        "/api/v1/auth/dev/send-test",
        json={"to": "purge@runefoble.local", "subject": "Purge Me", "body": "Disposable."},
    )
    clear_res = client.delete("/api/v1/auth/dev/emails")
    assert clear_res.status_code == 200
    assert clear_res.json()["status"] == "cleared"

    list_res = client.get("/api/v1/auth/dev/emails")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 0


def test_mailpit_status_and_stats(client: TestClient) -> None:
    """Verify /mailpit/status and /dev/stats report structured connectivity."""
    for path in ("/api/v1/auth/mailpit/status", "/api/v1/auth/dev/stats"):
        res = client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "http_available" in data
        assert "smtp_available" in data
        assert "message_count" in data


def test_admin_seed_and_invite(client: TestClient, mailpit: MailpitClient) -> None:
    """Verify /admin/seed and /admin/invite dispatch emails to Mailpit."""
    seed_res = client.post("/api/v1/auth/admin/seed")
    assert seed_res.status_code == 200
    assert seed_res.json()["status"] == "seeded"
    assert any(e.to == ["admin@runefoble.local"] for e in mailpit.sent_emails)

    invite_res = client.post(
        "/api/v1/auth/admin/invite",
        json={"email": "newdm@runefoble.local", "username": "NewDM", "role": "dm"},
    )
    assert invite_res.status_code == 200
    assert invite_res.json()["status"] == "invited"
    assert any(e.to == ["newdm@runefoble.local"] for e in mailpit.sent_emails)

    bad_invite = client.post("/api/v1/auth/admin/invite", json={"email": "bademail", "role": "dm"})
    assert bad_invite.status_code == 400


def test_submodule_line_invariants() -> None:
    """Verify Hard Invariant 6: all test submodules in this suite are strictly < 150 lines."""
    suite_dir = Path(__file__).resolve().parent
    for py_file in suite_dir.glob("*.py"):
        lines = len(py_file.read_text(encoding="utf-8").splitlines())
        assert lines < 150, f"{py_file.name} has {lines} lines (exceeds 150-line limit)"
