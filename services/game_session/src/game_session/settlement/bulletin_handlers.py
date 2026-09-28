"""Bulletin board notice event handlers and mutation commands mixin for settlements.

Governed by ADR-0002, ADR-0007, ADR-0011, and Hard Invariant 2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from eventsource.domain.decorators import handles
from game_session.settlement.models import BulletinNoticeState
from runefoble_events.settlements import (
    BulletinNoticePinnedEvent,
    BulletinNoticeRemovedEvent,
    CipherNoticeDecryptedEvent,
)

if TYPE_CHECKING:
    from game_session.settlement.models import SettlementState


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception:
        return uuid4()


class BulletinHandlersMixin:
    """Event handlers and command methods for settlement bulletin boards and notices."""

    _state: SettlementState
    aggregate_id: Any
    create_event: Any

    @handles(BulletinNoticePinnedEvent)
    def handle_bulletin_notice_pinned(self, ev: BulletinNoticePinnedEvent) -> None:
        """Handle pinning a new bulletin notice or bounty to the settlement board."""
        d = ev.model_dump()
        d.update(decrypted_by=[], status="active", created_at=str(ev.occurred_at or ""))
        fields = set(BulletinNoticeState.model_fields)
        self._state.bulletin_notices[ev.notice_id] = BulletinNoticeState(
            **{k: v for k, v in d.items() if k in fields}
        )

    @handles(BulletinNoticeRemovedEvent)
    def handle_bulletin_notice_removed(self, ev: BulletinNoticeRemovedEvent) -> None:
        """Handle removing or fulfilling a bulletin notice."""
        if n := self._state.bulletin_notices.get(ev.notice_id):
            n.status = "removed"

    @handles(CipherNoticeDecryptedEvent)
    def handle_cipher_notice_decrypted(self, ev: CipherNoticeDecryptedEvent) -> None:
        """Handle unlocking cipher secret for a player."""
        if (
            (n := self._state.bulletin_notices.get(ev.notice_id))
            and ev.player_id
            and ev.player_id not in n.decrypted_by
        ):
            n.decrypted_by.append(ev.player_id)

    def pin_bulletin_notice(self, title: str, content: str, author_id: str, **kw: Any) -> str:
        """Pin a notice, rumor, bounty, or job to the settlement notice board."""
        if not self._state.is_founded:
            raise ValueError(f"Settlement '{self.aggregate_id}' has not been founded yet")

        nid = kw.get("notice_id") or f"ntc_{uuid4().hex[:12]}"
        sid = str(self._state.settlement_id or self.aggregate_id)
        self.create_event(
            BulletinNoticePinnedEvent,
            aggregate_id=_to_uuid(sid),
            notice_id=nid,
            settlement_id=sid,
            board_type=kw.get("board_type", "town_square"),
            title=title,
            author_id=str(author_id),
            category=kw.get("category", "rumor"),
            content=content,
            wax_sealed=bool(kw.get("wax_sealed", False)),
            cipher_encoded=bool(kw.get("cipher_encoded", False)),
            cipher_puzzle=str(kw.get("cipher_puzzle", "rot13")),
            cipher_solution=str(kw.get("cipher_solution", "")),
            cipher_hint=str(kw.get("cipher_hint", "")),
            hidden_content=str(kw.get("hidden_content", "")),
            metadata=dict(kw.get("metadata") or {}),
        )
        return nid

    def remove_bulletin_notice(
        self, notice_id: str, remover_id: str = "", reason: str = "removed", **kw: Any
    ) -> str:
        """Remove or fulfill a notice from the bulletin board."""
        if not self._state.is_founded:
            raise ValueError(f"Settlement '{self.aggregate_id}' has not been founded yet")
        if not (n := self._state.bulletin_notices.get(notice_id)):
            raise ValueError(f"Bulletin notice '{notice_id}' not found in settlement")
        if n.status == "removed":
            raise ValueError(f"Bulletin notice '{notice_id}' is already removed")

        sid = str(self._state.settlement_id or self.aggregate_id)
        self.create_event(
            BulletinNoticeRemovedEvent,
            aggregate_id=_to_uuid(sid),
            notice_id=notice_id,
            settlement_id=sid,
            remover_id=str(remover_id),
            reason=reason,
            metadata=kw.get("metadata") or {},
        )
        return notice_id

    def decrypt_cipher_notice(
        self, notice_id: str, player_id: str, solution: str, **kw: Any
    ) -> str:
        """Decrypt a cipher-encoded notice when a player submits the correct solution."""
        if not self._state.is_founded:
            raise ValueError(f"Settlement '{self.aggregate_id}' has not been founded yet")
        if not (notice := self._state.bulletin_notices.get(notice_id)):
            raise ValueError(f"Bulletin notice '{notice_id}' not found in settlement")
        if not notice.cipher_encoded:
            return notice.content

        expected, submitted = notice.cipher_solution.strip().lower(), solution.strip().lower()
        if expected and submitted != expected:
            raise ValueError("Incorrect cipher solution")

        sid = str(self._state.settlement_id or self.aggregate_id)
        self.create_event(
            CipherNoticeDecryptedEvent,
            aggregate_id=_to_uuid(sid),
            notice_id=notice_id,
            settlement_id=sid,
            player_id=str(player_id),
            decrypted_content=notice.hidden_content or notice.content,
            metadata=kw.get("metadata") or {},
        )
        return notice.hidden_content or notice.content
