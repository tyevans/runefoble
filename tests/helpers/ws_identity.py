"""Signed WebSocket identity for blackbox tests.

Governed by TASK-0520 and TASK-0522 and ADR-0015 (c). Tests mint RS256 tokens
with one shared SigningTestIssuer and offer them in the bearer subprotocol.
The `trusted_ws_issuer` fixture in tests/conftest.py trusts that issuer in the
gateway and game_session verifiers for one test.
"""

from __future__ import annotations

from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

SIGNING_ISSUER = SigningTestIssuer()


def ws_subprotocols(sub: str) -> list[str]:
    """Return the subprotocols that carry a fresh token for `sub`."""
    return ["runefoble.v1", f"runefoble.bearer.{SIGNING_ISSUER.mint(sub)}"]
