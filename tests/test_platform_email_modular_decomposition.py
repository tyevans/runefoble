"""Blackbox tests for the runefoble_platform.email transport through its public API.

The SMTP sink and the Mailpit HTTP API are real sockets on 127.0.0.1. A failed dependency
raises EmailTransportError. Nothing is recorded in memory as sent mail.
"""

from __future__ import annotations

import socket
from typing import Any

import pytest
from runefoble_platform.email import EmailTransportError, MailpitClient

from tests.helpers.local_http_server import LocalHttpServer, RecordedRequest
from tests.helpers.mailpit_double import MailpitStore, mailpit_api, smtp_sink


def _closed_port() -> int:
    """Return a loopback port with no listener."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _closed_url() -> str:
    return f"http://127.0.0.1:{_closed_port()}"


@pytest.mark.asyncio
async def test_sent_mail_is_visible_through_mailpit_http_api_and_purge_clears_it() -> None:
    store = MailpitStore()
    async with smtp_sink(store) as smtp_port:
        with LocalHttpServer(mailpit_api(store)) as http:
            client = MailpitClient(smtp_host="127.0.0.1", smtp_port=smtp_port, http_url=http.url)

            outbound = await client.send_email(
                to="adventurer@runefoble.local",
                subject="Welcome to the Frontier",
                body_text="Your quest begins at dawn. Use verification code: 481516",
                body_html="<p>Code: <strong>481516</strong></p>",
                from_addr="dm@runefoble.local",
            )

            assert outbound.subject == "Welcome to the Frontier"
            assert outbound.to == ["adventurer@runefoble.local"]
            assert len(store.raw) == 1
            assert b"Subject: Welcome to the Frontier" in store.raw[0]

            messages = await client.list_messages()
            assert len(messages) == 1
            assert messages[0].subject == "Welcome to the Frontier"
            assert "adventurer@runefoble.local" in messages[0].to

            detail = await client.get_message(messages[0].id)
            assert detail is not None
            assert "481516" in detail.text
            assert "<strong>481516</strong>" in detail.html
            assert MailpitClient.extract_verification_code(detail.text) == "481516"

            latest = await client.get_latest_message()
            assert latest is not None
            assert latest.id == messages[0].id

            search_results = await client.search_messages("Frontier")
            assert len(search_results) == 1

            await client.delete_all_messages()
            assert await client.list_messages() == []


@pytest.mark.asyncio
async def test_send_raises_typed_error_when_smtp_server_is_down() -> None:
    client = MailpitClient(smtp_host="127.0.0.1", smtp_port=_closed_port(), http_url=_closed_url())

    with pytest.raises(EmailTransportError, match="unreachable"):
        await client.send_email(to="player@runefoble.local", subject="Lost", body_text="x")


@pytest.mark.asyncio
async def test_failed_send_leaves_no_fake_sent_mail_behind() -> None:
    store = MailpitStore()
    with LocalHttpServer(mailpit_api(store)) as http:
        client = MailpitClient(smtp_host="127.0.0.1", smtp_port=_closed_port(), http_url=http.url)

        with pytest.raises(EmailTransportError):
            await client.send_email(to="player@runefoble.local", subject="Lost", body_text="x")

        assert await client.list_messages() == []
        assert await client.search_messages("Lost") == []


@pytest.mark.asyncio
async def test_delete_all_messages_raises_when_purge_fails() -> None:
    def purge_fails(_request: RecordedRequest) -> tuple[int, dict[str, Any]]:
        return 500, {"error": "purge failed"}

    with LocalHttpServer(purge_fails) as http:
        client = MailpitClient(smtp_host="127.0.0.1", smtp_port=_closed_port(), http_url=http.url)

        with pytest.raises(EmailTransportError, match="500"):
            await client.delete_all_messages()


@pytest.mark.asyncio
async def test_list_messages_raises_when_mailpit_is_down() -> None:
    client = MailpitClient(smtp_host="127.0.0.1", smtp_port=_closed_port(), http_url=_closed_url())

    with pytest.raises(EmailTransportError, match="unreachable"):
        await client.list_messages()


@pytest.mark.asyncio
async def test_get_message_returns_none_for_unknown_id() -> None:
    store = MailpitStore()
    with LocalHttpServer(mailpit_api(store)) as http:
        client = MailpitClient(smtp_host="127.0.0.1", smtp_port=_closed_port(), http_url=http.url)

        assert await client.get_message("999") is None


@pytest.mark.asyncio
async def test_check_health_reports_offline_with_the_cause_when_both_services_are_down() -> None:
    client = MailpitClient(smtp_host="127.0.0.1", smtp_port=_closed_port(), http_url=_closed_url())

    health = await client.check_health()

    assert health["status"] == "offline"
    assert health["http_available"] is False
    assert health["smtp_available"] is False
    assert "unreachable" in health["http_error"]
    assert "unreachable" in health["smtp_error"]


@pytest.mark.asyncio
async def test_check_health_reports_degraded_when_only_smtp_is_down() -> None:
    store = MailpitStore()
    with LocalHttpServer(mailpit_api(store)) as http:
        client = MailpitClient(smtp_host="127.0.0.1", smtp_port=_closed_port(), http_url=http.url)

        health = await client.check_health()

        assert health["status"] == "degraded"
        assert health["http_available"] is True
        assert health["smtp_available"] is False
        assert health["http_error"] is None
        assert "unreachable" in health["smtp_error"]


@pytest.mark.asyncio
async def test_check_health_reports_healthy_when_both_services_answer() -> None:
    store = MailpitStore()
    async with smtp_sink(store) as smtp_port:
        with LocalHttpServer(mailpit_api(store)) as http:
            client = MailpitClient(smtp_host="127.0.0.1", smtp_port=smtp_port, http_url=http.url)

            health = await client.check_health()

            assert health["status"] == "healthy"
            assert health["smtp_available"] is True
            assert health["message_count"] == 0
            assert health["smtp_error"] is None
