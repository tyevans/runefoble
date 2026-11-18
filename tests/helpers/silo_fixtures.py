"""Shared fixtures and constants for Silo S3 Media Asset Bucket blackbox test suites.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python Bounded Contexts
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
"""

from __future__ import annotations

from collections.abc import Generator

import httpx
import pytest
from runefoble_platform.storage import SiloStorageService, get_storage_service, set_storage_service

# Sample 1x1 PNG bytes for testing image uploads
PNG_SAMPLE_BYTES: bytes = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02"
    b"\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Sample WAV audio bytes for testing audio uploads
WAV_SAMPLE_BYTES: bytes = (
    b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00"
    b"\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
)

SILO_TEST_ENDPOINT = "http://silo.test:9000"


class FakeSilo:
    """In-process stand-in for the Silo HTTP API.

    It sits at the HTTP boundary only. The platform SiloStorageService sends real
    PUT, GET and DELETE requests through this transport. Tests can simulate an
    outage (connection refused) or a fixed error status.
    """

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.outage: bool = False
        self.forced_status: int | None = None

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        if self.outage:
            raise httpx.ConnectError("Silo is unreachable", request=request)
        if self.forced_status is not None:
            return httpx.Response(self.forced_status, request=request)

        key = request.url.path.lstrip("/")
        if request.method == "PUT":
            content_type = request.headers.get("Content-Type", "application/octet-stream")
            self.objects[key] = (request.content, content_type)
            return httpx.Response(200, request=request)
        if request.method == "GET":
            if key not in self.objects:
                return httpx.Response(404, request=request)
            data, content_type = self.objects[key]
            return httpx.Response(200, content=data, headers={"Content-Type": content_type})
        if request.method == "DELETE":
            if self.objects.pop(key, None) is None:
                return httpx.Response(404, request=request)
            return httpx.Response(204, request=request)
        return httpx.Response(405, request=request)


@pytest.fixture(autouse=True)
def silo_double() -> Generator[FakeSilo]:
    """Route the platform Silo client to a FakeSilo for every test."""
    fake = FakeSilo()
    previous = get_storage_service()
    set_storage_service(
        SiloStorageService(
            endpoint=SILO_TEST_ENDPOINT,
            secure=False,
            bucket_assets="runefoble-assets",
            transport=fake.transport(),
        )
    )
    yield fake
    set_storage_service(previous)
