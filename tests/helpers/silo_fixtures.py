"""Shared fixtures and constants for Silo S3 Media Asset Bucket blackbox test suites.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python Bounded Contexts
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterator
from contextlib import ExitStack

import httpx
import pytest
from fastapi.testclient import TestClient
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
SILO_TEST_ACCESS_KEY = "silo-test-access"
SILO_TEST_SECRET_KEY = "silo-test-secret"
SILO_UNSIGNED_STATUS = 403


class FakeSilo:
    """In-process stand-in for the Silo HTTP API.

    It sits at the HTTP boundary only. The platform SiloStorageService sends real
    PUT, GET, DELETE and bucket HEAD requests through this transport. Tests can simulate an
    outage (connection refused) or a fixed error status.

    Like the real Silo, it refuses a request without an AWS Signature Version 4
    `Authorization` header for the test access key with 403 (TASK-0926).
    """

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.outage: bool = False
        self.forced_status: int | None = None
        self.buckets: set[str] = {"runefoble-assets"}

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        if self.outage:
            raise httpx.ConnectError("Silo is unreachable", request=request)
        if not _is_sigv4_signed(request):
            return httpx.Response(SILO_UNSIGNED_STATUS, request=request)
        if self.forced_status is not None:
            return httpx.Response(self.forced_status, request=request)

        key = request.url.path.lstrip("/")
        if request.method == "HEAD":
            return httpx.Response(200 if key.rstrip("/") in self.buckets else 404, request=request)
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


def _is_sigv4_signed(request: httpx.Request) -> bool:
    """True when the request carries a SigV4 S3 signature for the test access key."""
    authorization = request.headers.get("Authorization", "")
    return (
        authorization.startswith(f"AWS4-HMAC-SHA256 Credential={SILO_TEST_ACCESS_KEY}/")
        and "/s3/aws4_request" in authorization
        and "Signature=" in authorization
        and "x-amz-date" in request.headers
        and "x-amz-content-sha256" in request.headers
    )


@pytest.fixture(autouse=True)
def silo_double() -> Generator[FakeSilo]:
    """Route the platform Silo client to a FakeSilo for every test."""
    fake = FakeSilo()
    previous = get_storage_service()
    set_storage_service(
        SiloStorageService(
            endpoint=SILO_TEST_ENDPOINT,
            access_key=SILO_TEST_ACCESS_KEY,
            secret_key=SILO_TEST_SECRET_KEY,
            secure=False,
            bucket_assets="runefoble-assets",
            transport=fake.transport(),
        )
    )
    yield fake
    set_storage_service(previous)


@pytest.fixture
def gateway_for(asset_forge_upstream: str) -> Iterator[Callable[..., TestClient]]:
    """Return gateway clients wired to a live asset_forge (TASK-0595).

    Each client enters the gateway lifespan, which builds the upstream clients. Pass an issuer
    and a subject for a bearer token. Call with no arguments for an anonymous client.
    """
    from gateway_api.main import app as gateway_app

    with ExitStack() as stack:

        def make(issuer=None, sub: str | None = None) -> TestClient:
            headers = {"Authorization": f"Bearer {issuer.mint(sub)}"} if issuer else None
            return stack.enter_context(TestClient(gateway_app, headers=headers))

        yield make
