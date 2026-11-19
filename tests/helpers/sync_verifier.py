"""A Zitadel verifier for tests of the identity sync service.

The sync paths under test write SpiceDB tuples and never call Zitadel, so the verifier only
fills the required constructor argument.
"""

from __future__ import annotations

from runefoble_auth.zitadel import ZitadelAuthService


def sync_test_verifier() -> ZitadelAuthService:
    return ZitadelAuthService(
        issuer="http://zitadel.test", audience="runefoble-api", internal_url=None
    )
