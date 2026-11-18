"""Signed identity for voice_agent blackbox tests (TASK-0530, ADR-0015 c).

Tests mint RS256 tokens from one SigningTestIssuer. The `trusted_voice_issuer`
fixture makes the voice_agent verifier trust that issuer for one test. Requests
then carry `Authorization: Bearer <token>`, and WebSockets offer the bearer subprotocol.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
from voice_agent.auth import set_voice_verifier

from tests.helpers.ws_identity import SIGNING_ISSUER

# One shared test issuer. The gateway mounts the voice room routes, so both verifiers must trust it.
VOICE_SIGNING_ISSUER = SIGNING_ISSUER


def voice_auth_headers(sub: str = "user-dm") -> dict[str, str]:
    """Return an Authorization header with a fresh token for `sub`."""
    return {"Authorization": f"Bearer {VOICE_SIGNING_ISSUER.mint(sub)}"}


def voice_ws_subprotocols(sub: str = "user-dm") -> list[str]:
    """Return the subprotocols that carry a fresh voice token for `sub`."""
    return ["runefoble.v1", f"runefoble.bearer.{VOICE_SIGNING_ISSUER.mint(sub)}"]


@pytest.fixture
def trusted_voice_issuer() -> Iterator[SigningTestIssuer]:
    """Trust the voice test issuer in voice_agent for one test."""
    set_voice_verifier(VOICE_SIGNING_ISSUER.verifier())
    yield VOICE_SIGNING_ISSUER
    set_voice_verifier(None)
