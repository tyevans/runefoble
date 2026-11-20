"""Rate limits for the invite account route (ADR-0023 d).

The gateway counts two keys: the client address and the invite. The client address comes from
`X-Forwarded-For` only when the peer is a trusted proxy (`runefoble_platform.client_address`).
The invite key is a SHA-256 digest of the token, so the raw token is not held in memory. Each limit is a fixed window of one
hour. A refused request returns 429 with `Retry-After`. The counts live in this process. A
shared limiter that uses the same port can replace them later.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from runefoble_platform.client_address import Network
from runefoble_platform.rate_limit import FixedWindowRateLimiter, RateLimiter

WINDOW_SECONDS = 3600.0
CLIENT_HITS_PER_WINDOW = 20
INVITE_HITS_PER_WINDOW = 30


@dataclass(frozen=True)
class AccountInviteLimits:
    client: RateLimiter
    invite: RateLimiter
    # Proxies whose X-Forwarded-For header names the client (see client_address).
    trusted_proxies: tuple[Network, ...]


def build_account_invite_limits(trusted_proxies: tuple[Network, ...]) -> AccountInviteLimits:
    return AccountInviteLimits(
        client=FixedWindowRateLimiter(limit=CLIENT_HITS_PER_WINDOW, window_seconds=WINDOW_SECONDS),
        invite=FixedWindowRateLimiter(limit=INVITE_HITS_PER_WINDOW, window_seconds=WINDOW_SECONDS),
        trusted_proxies=trusted_proxies,
    )


def invite_limit_key(token: str) -> str:
    return "invite:" + hashlib.sha256(token.encode("utf-8")).hexdigest()


def client_limit_key(address: str) -> str:
    return "client:" + address
