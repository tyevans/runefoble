"""Tests verifying modular decomposition and backward compatibility of runefoble_platform.email."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from runefoble_platform.email import MailpitClient


def test_import_from_subpackage_facade() -> None:
    """Verify that importing from runefoble_platform.email exposes all public symbols."""
    from runefoble_platform.email import (
        EmailMessage,
        EmailRecipient,
        EmailVerificationPayload,
        MailpitClient,
        MailpitMessage,
        MailpitMessageSummary,
        OutboundEmail,
        SmtpTransport,
        build_mime_message,
        extract_verification_code,
        extract_verification_link,
    )

    assert MailpitClient is not None
    assert SmtpTransport is not None
    assert OutboundEmail is not None
    assert MailpitMessage is not None
    assert MailpitMessageSummary is not None
    assert EmailRecipient is not None
    assert EmailMessage is not None
    assert EmailVerificationPayload is not None
    assert callable(build_mime_message)
    assert callable(extract_verification_link)
    assert callable(extract_verification_code)


def test_import_from_modular_submodules() -> None:
    """Verify that importing directly from modular submodules works as expected."""
    from runefoble_platform.email.mailpit import MailpitClient
    from runefoble_platform.email.models import (
        EmailMessage,
        EmailRecipient,
        EmailVerificationPayload,
        MailpitMessage,
        MailpitMessageSummary,
        OutboundEmail,
        extract_verification_code,
        extract_verification_link,
    )
    from runefoble_platform.email.smtp import SmtpTransport, build_mime_message

    assert MailpitClient is not None
    assert SmtpTransport is not None
    assert OutboundEmail is not None
    assert MailpitMessage is not None
    assert MailpitMessageSummary is not None
    assert EmailRecipient is not None
    assert EmailMessage is not None
    assert EmailVerificationPayload is not None
    assert callable(build_mime_message)
    assert callable(extract_verification_link)
    assert callable(extract_verification_code)


def test_import_from_backward_compatibility_shim() -> None:
    """Verify backward compatibility shim email_client.py re-exports identical symbols."""
    from runefoble_platform.email import (
        EmailMessage as FacadeMessage,
    )
    from runefoble_platform.email import (
        EmailRecipient as FacadeRecipient,
    )
    from runefoble_platform.email import (
        EmailVerificationPayload as FacadePayload,
    )
    from runefoble_platform.email import (
        MailpitClient as FacadeClient,
    )
    from runefoble_platform.email import (
        MailpitMessage as FacadeMailpitMessage,
    )
    from runefoble_platform.email import (
        MailpitMessageSummary as FacadeSummary,
    )
    from runefoble_platform.email import (
        OutboundEmail as FacadeOutbound,
    )
    from runefoble_platform.email import (
        SmtpTransport as FacadeTransport,
    )
    from runefoble_platform.email_client import (
        EmailMessage as ShimMessage,
    )
    from runefoble_platform.email_client import (
        EmailRecipient as ShimRecipient,
    )
    from runefoble_platform.email_client import (
        EmailVerificationPayload as ShimPayload,
    )
    from runefoble_platform.email_client import (
        MailpitClient as ShimClient,
    )
    from runefoble_platform.email_client import (
        MailpitMessage as ShimMailpitMessage,
    )
    from runefoble_platform.email_client import (
        MailpitMessageSummary as ShimSummary,
    )
    from runefoble_platform.email_client import (
        OutboundEmail as ShimOutbound,
    )
    from runefoble_platform.email_client import (
        SmtpTransport as ShimTransport,
    )
    from runefoble_platform.email_client import (
        build_mime_message,
        extract_verification_code,
        extract_verification_link,
    )

    assert ShimClient is FacadeClient
    assert ShimTransport is FacadeTransport
    assert ShimOutbound is FacadeOutbound
    assert ShimMailpitMessage is FacadeMailpitMessage
    assert ShimSummary is FacadeSummary
    assert ShimMessage is FacadeMessage
    assert ShimRecipient is FacadeRecipient
    assert ShimPayload is FacadePayload
    assert callable(build_mime_message)
    assert callable(extract_verification_link)
    assert callable(extract_verification_code)


def test_submodules_line_counts_strictly_under_limit() -> None:
    """Verify Hard Invariant 6: all submodules are strictly < 130 lines each."""
    email_pkg = (
        Path(__file__).resolve().parent.parent
        / "libs"
        / "runefoble_platform"
        / "src"
        / "runefoble_platform"
        / "email"
    )
    shim_file = (
        Path(__file__).resolve().parent.parent
        / "libs"
        / "runefoble_platform"
        / "src"
        / "runefoble_platform"
        / "email_client.py"
    )

    py_files = list(email_pkg.glob("*.py")) + [shim_file]
    assert len(py_files) >= 4

    for f in py_files:
        lines = len(f.read_text().splitlines())
        assert lines < 130, f"{f.name} has {lines} lines, exceeding the 130 line limit"


@pytest.mark.asyncio
async def test_mailpit_client_send_and_inspect_in_memory() -> None:
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

    messages = await client.list_messages()
    assert len(messages) == 1
    assert messages[0].subject == "Welcome to the Frontier"
    assert "adventurer@runefoble.local" in messages[0].to

    detail = await client.get_message(messages[0].id)
    assert detail is not None
    assert "481516" in detail.text
    assert "<strong>481516</strong>" in detail.html

    latest = await client.get_latest_message()
    assert latest is not None
    assert latest.id == messages[0].id

    search_results = await client.search_messages("quest")
    assert len(search_results) == 1
    assert len(await client.search_messages("nonexistent")) == 0

    assert MailpitClient.extract_verification_code(detail.text) == "481516"

    deleted = await client.delete_all_messages()
    assert deleted is True
    assert len(await client.list_messages()) == 0


@pytest.mark.asyncio
async def test_mailpit_live_socket_smtp_server_interaction() -> None:
    """Verify MailpitClient transmits actual RFC-822 email over TCP socket."""
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
