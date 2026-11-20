"""Blackbox frontdoor tests: a campaign invite creates the player account (ADR-0023, TASK-0967).

The tests drive only public routes through the gateway: campaign creation, invite issue, the
account route, and the join route. Zitadel is a loopback fake (`tests/helpers/fake_zitadel_server.py`).
It stands in for the external process, so the code under test makes real HTTP calls to it.
The fake records every call, so a test can check what Zitadel received and what it did not.

Hard rules that these tests hold:
- Runefoble sends no password and no init code to Zitadel.
- A new and an existing email get the same reply.
- A refused invite makes no Zitadel call.
- Zitadel unavailable: 503, and no invite use is recorded.
- SpiceDB gets the player relation only at the join, and a join never uses a second invite use.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from eventsource.adapters.memory.store import InMemoryEventStore
from fastapi.testclient import TestClient
from game_session.campaign import service_accounts
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app as gateway_app
from runefoble_platform.event_sourcing import get_event_store, set_event_store
from runefoble_platform.models import utc_now

from tests.helpers.fake_zitadel_server import FakeZitadel, fake_zitadel_server
from tests.helpers.game_session_app import app_with_container, session_event_bus
from tests.helpers.module_state import restored_seam
from tests.helpers.service_harness import live_upstream

pytestmark = pytest.mark.asyncio

SERVICE_TOKEN = "test-zitadel-service-token"
TRUSTED_PROXY_CIDR = "10.244.0.0/16"
ACCOUNT_PATH = "/api/v1/campaigns/invites/accounts"
TRUSTED_PEER = "10.244.0.9"
UNTRUSTED_PEER = "198.51.100.1"
DIRECT_PEER = "198.51.100.250"
OWNER = "dm-owner"
PLAYER_EMAIL = "new.player@example.com"
REPLY_KEYS = {"status", "message"}


@dataclass
class AccountStack:
    gateway: TestClient
    zitadel: FakeZitadel
    store: InMemoryEventStore
    issuer: Any


@pytest.fixture
def account_stack(monkeypatch, trusted_ws_issuer) -> Iterator[AccountStack]:
    """The gateway, a game_session app and a loopback Zitadel fake, wired by settings only."""
    from game_session.container import build_container

    with fake_zitadel_server(SERVICE_TOKEN) as zitadel:
        monkeypatch.setenv("RUNEFOBLE_ZITADEL_API_URL", zitadel.base_url)
        monkeypatch.setenv("RUNEFOBLE_ZITADEL_SERVICE_TOKEN", SERVICE_TOKEN)
        monkeypatch.setenv("RUNEFOBLE_TRUSTED_PROXY_CIDRS", TRUSTED_PROXY_CIDR)
        store = InMemoryEventStore()
        with restored_seam(get_event_store, set_event_store, store, replace=True):
            session = app_with_container(build_container(event_bus=session_event_bus))
            with (
                live_upstream(session, "RUNEFOBLE_GAME_SESSION_URL"),
                TestClient(_PeerAddress(gateway_app)) as gateway,
            ):
                yield AccountStack(gateway, zitadel, store, trusted_ws_issuer)


def _headers(stack: AccountStack, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {stack.issuer.mint(sub)}"}


def _campaign_with_invite(
    stack: AccountStack, *, max_uses: int | None = None, expires_in_hours: int | None = 72
) -> tuple[str, str]:
    """The owner creates a campaign and one player invite. Return (campaign_id, token)."""
    created = stack.gateway.post(
        "/api/v1/campaigns", json={"title": "Invite Campaign"}, headers=_headers(stack, OWNER)
    )
    assert created.status_code == 201, created.text
    campaign_id = created.json()["id"]
    invite = stack.gateway.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player", "max_uses": max_uses, "expires_in_hours": expires_in_hours},
        headers=_headers(stack, OWNER),
    )
    assert invite.status_code == 201, invite.text
    return campaign_id, invite.json()["token"]


def _request_account(
    stack: AccountStack, token: str, email: str, display_name: str = "Ada Lovelace"
) -> Any:
    """The account route. It takes no bearer token. The invite token travels in the body."""
    return stack.gateway.post(
        ACCOUNT_PATH,
        json={"invite_token": token, "email": email, "display_name": display_name},
    )


class _PeerAddress:
    """Stands in for the TCP peer that the ASGI server reports for each request.

    The test sets the `x-test-peer` header. The wrapper removes it and sets the scope client to
    that address, as uvicorn does for a real connection. Every other request passes unchanged.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            incoming = dict(scope["headers"])
            peer = incoming.get(b"x-test-peer", DIRECT_PEER.encode()).decode()
            headers = [(k, v) for k, v in scope["headers"] if k != b"x-test-peer"]
            scope = {**scope, "headers": headers, "client": (peer, 50000)}
        await self.app(scope, receive, send)


def _account_from(stack: AccountStack, token: str, peer: str, forwarded_for: str | None) -> int:
    headers = {"x-test-peer": peer}
    if forwarded_for is not None:
        headers["X-Forwarded-For"] = forwarded_for
    res = stack.gateway.post(
        ACCOUNT_PATH,
        json={
            "invite_token": token,
            "email": f"{uuid4().hex[:10]}@example.com",
            "display_name": "Peer Player",
        },
        headers=headers,
    )
    return res.status_code


async def _account_events(store: InMemoryEventStore) -> list[str]:
    """The invite events that an account or a join writes: pending joins and use records."""
    names = []
    async for envelope in store.read_category("CampaignInvite"):
        name = envelope.event.event_type
        if name.endswith(("pending_join_recorded", "pending_join_completed", "redeemed")):
            names.append(name)
    return names


def _mentions(value: Any, word: str) -> bool:
    return word.lower() in str(value).lower()


def _user_id(stack: AccountStack, email: str) -> str:
    return stack.zitadel.users[email.lower()]


async def test_new_email_creates_account_without_password_and_answers_202(account_stack):
    stack = account_stack
    _, token = _campaign_with_invite(stack, max_uses=2)

    res = _request_account(stack, token, PLAYER_EMAIL)

    assert res.status_code == 202, res.text
    assert set(res.json()) == REPLY_KEYS
    creates = stack.zitadel.create_calls()
    assert len(creates) == 1
    sent = creates[0].body
    assert creates[0].authorized
    assert not _mentions(sent, "password")
    assert sent["email"] == {"email": PLAYER_EMAIL, "sendCode": {}}
    assert sent["profile"]["displayName"] == "Ada Lovelace"
    names = await _account_events(stack.store)
    assert names == [
        "runefoble.events.game_session.campaign_invite_redeemed",
        "runefoble.events.game_session.pending_join_recorded",
    ]


async def test_existing_email_gets_the_same_reply_and_no_create_call(account_stack):
    stack = account_stack
    _, token = _campaign_with_invite(stack, max_uses=2)
    known_id = stack.zitadel.add_existing_user("known.player@example.com")

    existing = _request_account(stack, token, "known.player@example.com")
    fresh = _request_account(stack, token, PLAYER_EMAIL)

    assert existing.status_code == fresh.status_code == 202
    assert existing.json() == fresh.json()
    assert stack.zitadel.create_calls()[0].body["email"]["email"] == PLAYER_EMAIL
    assert len(stack.zitadel.create_calls()) == 1
    resets = stack.zitadel.reset_calls()
    assert [call.path for call in resets] == [f"/v2beta/users/{known_id}/password_reset"]
    assert resets[0].body == {"sendLink": {"notificationType": "NOTIFICATION_TYPE_EMAIL"}}
    assert not _mentions(existing.json(), known_id)


async def test_existing_email_records_no_use_and_no_pending_join(account_stack):
    stack = account_stack
    _, token = _campaign_with_invite(stack, max_uses=1)
    stack.zitadel.add_existing_user("known.player@example.com")

    assert _request_account(stack, token, "known.player@example.com").status_code == 202

    # The use is still free, so a new person can still take the single use.
    assert _request_account(stack, token, PLAYER_EMAIL).status_code == 202
    assert len(stack.zitadel.create_calls()) == 1


async def test_unknown_invite_answers_404_without_a_provider_call(account_stack):
    stack = account_stack

    res = _request_account(stack, "no-such-token", PLAYER_EMAIL)

    assert res.status_code == 404
    assert stack.zitadel.calls == []


async def test_malformed_email_answers_422_without_a_provider_call(account_stack):
    stack = account_stack
    _, token = _campaign_with_invite(stack)

    res = _request_account(stack, token, "not-an-email")

    assert res.status_code == 422
    assert stack.zitadel.calls == []


async def test_used_up_invite_answers_410_without_a_second_provider_call(account_stack):
    stack = account_stack
    _, token = _campaign_with_invite(stack, max_uses=1)
    assert _request_account(stack, token, PLAYER_EMAIL).status_code == 202

    res = _request_account(stack, token, "second.player@example.com")

    assert res.status_code == 410
    assert res.json()["detail"]["error"] == "invite_exhausted"
    assert len(stack.zitadel.create_calls()) == 1
    assert not [call for call in stack.zitadel.calls if "second.player" in str(call.body)]


async def test_expired_invite_answers_410_without_a_provider_call(account_stack, monkeypatch):
    stack = account_stack
    _, token = _campaign_with_invite(stack, expires_in_hours=1)
    later = utc_now() + timedelta(days=2)
    monkeypatch.setattr(service_accounts, "utc_now", lambda: later)

    res = _request_account(stack, token, PLAYER_EMAIL)

    assert res.status_code == 410
    assert res.json()["detail"]["error"] == "invite_expired"
    assert stack.zitadel.calls == []


async def test_zitadel_unavailable_answers_503_and_records_no_use(account_stack):
    stack = account_stack
    _, token = _campaign_with_invite(stack, max_uses=1)
    stack.zitadel.fail_status = 503

    failed = _request_account(stack, token, PLAYER_EMAIL)

    assert failed.status_code == 503
    assert failed.json()["upstream"] == "game_session"
    assert await _account_events(stack.store) == []

    # No use was recorded, so the single use is still free once Zitadel answers again.
    stack.zitadel.fail_status = None
    assert _request_account(stack, token, PLAYER_EMAIL).status_code == 202
    assert _request_account(stack, token, "second.player@example.com").status_code == 410


async def test_account_route_is_rate_limited_per_client_with_retry_after(account_stack):
    stack = account_stack
    _, token = _campaign_with_invite(stack)
    for index in range(20):
        res = _request_account(stack, token, f"player{index}@example.com")
        assert res.status_code == 202, res.text

    limited = _request_account(stack, token, "player-over@example.com")

    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1
    assert len(stack.zitadel.create_calls()) == 20


async def test_pending_join_completes_at_sign_in_without_a_second_use(account_stack):
    stack = account_stack
    campaign_id, token = _campaign_with_invite(stack, max_uses=2)
    first = _request_account(stack, token, PLAYER_EMAIL)
    second = _request_account(stack, token, "second.player@example.com")
    assert first.status_code == second.status_code == 202
    assert _request_account(stack, token, "third.player@example.com").status_code == 410
    first_user = _user_id(stack, PLAYER_EMAIL)
    second_user = _user_id(stack, "second.player@example.com")
    spicedb = get_spicedb_client()

    assert not await spicedb.check_permission("campaign", campaign_id, "play", "user", first_user)

    joined = stack.gateway.post(
        "/api/v1/campaigns/join", json={"invite_token": token}, headers=_headers(stack, first_user)
    )
    assert joined.status_code == 200, joined.text
    assert joined.json()["role"] == "player"
    assert await spicedb.check_permission("campaign", campaign_id, "play", "user", first_user)

    # A second join by the same person repeats the grant and uses nothing. The invite is still
    # exhausted by the two accounts, so a join that used a use would fail here.
    again = stack.gateway.post(
        "/api/v1/campaigns/join", json={"invite_token": token}, headers=_headers(stack, first_user)
    )
    assert again.status_code == 200, again.text

    other = stack.gateway.post(
        "/api/v1/campaigns/join", json={"invite_token": token}, headers=_headers(stack, second_user)
    )
    assert other.status_code == 200, other.text

    stranger = stack.gateway.post(
        "/api/v1/campaigns/join", json={"invite_token": token}, headers=_headers(stack, "stranger")
    )
    assert stranger.status_code == 410
    assert not await spicedb.check_permission("campaign", campaign_id, "play", "user", "stranger")


async def test_invite_token_never_reaches_a_log_line(account_stack, caplog):
    """The token is a bearer credential. No log record of a request may carry it."""
    stack = account_stack
    _, token = _campaign_with_invite(stack, max_uses=1)
    caplog.set_level(logging.DEBUG)

    assert _request_account(stack, token, PLAYER_EMAIL).status_code == 202
    assert _request_account(stack, token, "second.player@example.com").status_code == 410
    assert _request_account(stack, "no-such-token", PLAYER_EMAIL).status_code == 404

    for record in caplog.records:
        rendered = f"{record.getMessage()} {record.args!r} {record.exc_info!r}"
        assert token not in rendered, record.name


async def test_trusted_peer_limits_each_forwarded_client_separately(account_stack):
    """Traefik (a trusted peer) appends the real client. The limit follows that address."""
    stack = account_stack
    _, token = _campaign_with_invite(stack)
    for _ in range(20):
        assert _account_from(stack, token, TRUSTED_PEER, "203.0.113.7") == 202

    assert _account_from(stack, token, TRUSTED_PEER, "203.0.113.7") == 429
    assert _account_from(stack, token, TRUSTED_PEER, "203.0.113.8") == 202


async def test_untrusted_peer_ignores_the_forwarded_header(account_stack):
    """A client that reaches the gateway directly cannot choose its own bucket."""
    stack = account_stack
    _, token = _campaign_with_invite(stack)
    for index in range(20):
        assert _account_from(stack, token, UNTRUSTED_PEER, f"192.0.2.{index + 1}") == 202

    assert _account_from(stack, token, UNTRUSTED_PEER, "192.0.2.250") == 429


async def test_trusted_peer_uses_the_rightmost_untrusted_address(account_stack):
    """A client can prepend anything. The address that the proxy appended is the one that counts."""
    stack = account_stack
    _, token = _campaign_with_invite(stack)
    for index in range(20):
        forged = f"198.51.100.{index + 1}, 203.0.113.7"
        assert _account_from(stack, token, TRUSTED_PEER, forged) == 202

    assert _account_from(stack, token, TRUSTED_PEER, "198.51.100.99, 203.0.113.7") == 429
