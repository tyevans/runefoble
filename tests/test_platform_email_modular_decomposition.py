"""Tests verifying the runefoble_platform.email package through its public imports."""

from __future__ import annotations

import asyncio

import pytest
from runefoble_platform.email import MailpitClient


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
