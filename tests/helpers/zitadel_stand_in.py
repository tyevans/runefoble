"""Loopback stand-in for Zitadel discovery and JWKS (ADR-0015 c).

A verifier built from settings reads discovery and JWKS over HTTP. This server plays the
process boundary. It answers each issuer by its `Host` header, as Zitadel does, and it
refuses every other host. Tokens are checked for real: signature, `iss`, `aud`, and `exp`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import urlsplit

from tests.helpers.local_http_server import LocalHttpServer, RecordedRequest
from tests.helpers.signing_test_issuer import SigningTestIssuer


@contextmanager
def zitadel_stand_in(*issuers: SigningTestIssuer) -> Iterator[LocalHttpServer]:
    """Serve discovery and the JWK set of each issuer on one loopback origin.

    Set `RUNEFOBLE_ZITADEL_INTERNAL_URL` to the yielded URL. The issuer stays the external one.
    """
    by_host = {urlsplit(issuer.issuer).netloc: issuer for issuer in issuers}

    def handle(request: RecordedRequest) -> tuple[int, object]:
        issuer = by_host.get(request.headers.get("Host", ""))
        if issuer is None:
            return 404, {"message": "Instance not found"}
        if request.path == "/.well-known/openid-configuration":
            return 200, {
                "issuer": issuer.issuer,
                "jwks_uri": f"{issuer.issuer}/.well-known/jwks.json",
            }
        if request.path == "/.well-known/jwks.json":
            return 200, issuer.jwks()
        return 404, {"message": "not found"}

    server = LocalHttpServer(handle).start()
    try:
        yield server
    finally:
        server.stop()
