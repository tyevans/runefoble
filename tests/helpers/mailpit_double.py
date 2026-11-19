"""Mailpit test double: a TCP SMTP sink and a Mailpit-style HTTP API.

The SMTP sink accepts messages over a real socket and keeps the raw RFC-822 bytes.
The HTTP API serves those stored messages in the shape that Mailpit uses. Production
code reads them only through the public Mailpit HTTP API, never through a Python list.
"""

from __future__ import annotations

import asyncio
import email.policy
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from email import message_from_bytes
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Any
from urllib.parse import parse_qs, urlsplit

from tests.helpers.local_http_server import Handler, RecordedRequest, Reply


@dataclass
class MailpitStore:
    """Raw messages that the SMTP sink received, in arrival order."""

    raw: list[bytes] = field(default_factory=list)


async def _read_data(reader: asyncio.StreamReader) -> bytes:
    buffer = bytearray()
    while True:
        line = await reader.readline()
        if line in (b".\r\n", b""):
            return bytes(buffer)
        buffer.extend(line)


async def _smtp_session(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, store: MailpitStore
) -> None:
    writer.write(b"220 mailpit.local ESMTP Double\r\n")
    await writer.drain()
    while True:
        line = await reader.readline()
        if not line:
            break
        command = line.strip().upper()
        if command.startswith((b"EHLO", b"HELO")):
            reply = b"250 mailpit.local\r\n"
        elif command.startswith((b"MAIL FROM:", b"RCPT TO:", b"NOOP")):
            reply = b"250 2.0.0 Ok\r\n"
        elif command == b"DATA":
            writer.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
            await writer.drain()
            store.raw.append(await _read_data(reader))
            reply = b"250 2.0.0 Ok: queued\r\n"
        elif command == b"QUIT":
            writer.write(b"221 2.0.0 Bye\r\n")
            await writer.drain()
            break
        else:
            reply = b"502 5.5.2 Command not implemented\r\n"
        writer.write(reply)
        await writer.drain()
    writer.close()
    await writer.wait_closed()


@asynccontextmanager
async def smtp_sink(store: MailpitStore) -> AsyncIterator[int]:
    """Listen on 127.0.0.1 with a random port and store every received message."""

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await _smtp_session(reader, writer, store)

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    try:
        yield int(server.sockets[0].getsockname()[1])
    finally:
        server.close()
        await server.wait_closed()


def _message_json(message_id: str, raw: bytes) -> dict[str, Any]:
    parsed = message_from_bytes(raw, policy=email.policy.default)
    assert isinstance(parsed, EmailMessage)
    text_part = parsed.get_body(preferencelist=("plain",))
    html_part = parsed.get_body(preferencelist=("html",))
    from_address = parseaddr(str(parsed.get("From", "")))[1]
    to_addresses = [parseaddr(part)[1] for part in str(parsed.get("To", "")).split(",")]
    return {
        "ID": message_id,
        "Subject": str(parsed.get("Subject", "")),
        "From": {"Address": from_address},
        "To": [{"Address": address} for address in to_addresses],
        "Created": "2026-11-18T00:00:00Z",
        "Size": len(raw),
        "Text": text_part.get_content() if text_part else "",
        "HTML": html_part.get_content() if html_part else "",
    }


def _searchable_text(raw: bytes) -> str:
    parsed = message_from_bytes(raw, policy=email.policy.default)
    parts = [str(parsed.get("Subject", "")), str(parsed.get("To", ""))]
    parts.extend(
        str(part.get_content()) for part in parsed.walk() if part.get_content_maintype() == "text"
    )
    return " ".join(parts).lower()


def mailpit_api(store: MailpitStore) -> Handler:
    """Return a handler that serves the stored messages through the Mailpit REST routes."""

    def handle(request: RecordedRequest) -> Reply:
        if request.method == "DELETE" and request.path == "/api/v1/messages":
            store.raw.clear()
            return 200, {}
        if request.method == "GET" and request.path.startswith("/api/v1/messages"):
            newest_first = [
                _message_json(str(index), raw)
                for index, raw in reversed(list(enumerate(store.raw)))
            ]
            return 200, {"total": len(newest_first), "messages": newest_first}
        if request.method == "GET" and request.path.startswith("/api/v1/search"):
            needle = parse_qs(urlsplit(request.path).query).get("query", [""])[0].lower()
            matches = [
                _message_json(str(index), raw)
                for index, raw in reversed(list(enumerate(store.raw)))
                if needle in _searchable_text(raw)
            ]
            return 200, {"total": len(matches), "messages": matches}
        if request.method == "GET" and request.path.startswith("/api/v1/message/"):
            message_id = request.path.rsplit("/", 1)[-1]
            if message_id.isdigit() and int(message_id) < len(store.raw):
                return 200, _message_json(message_id, store.raw[int(message_id)])
            return 404, {"error": "message not found"}
        return 404, {"error": f"no route for {request.method} {request.path}"}

    return handle
