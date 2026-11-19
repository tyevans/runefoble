"""SpiceDB Zanzibar authorization helpers for town bulletin boards and notices.

Governed by ADR-0001 (Zanzibar Fine-Grained Authorization) and Hard Invariant 1.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from runefoble_auth.permissions import check_subject, require_subject


async def check_bulletin_board_view_permission(
    spicedb: Any,
    settlement_id: str,
    user_id: str,
) -> None:
    """Ensure user has permission to view notices on the settlement bulletin board."""
    await require_subject(
        spicedb,
        "settlement",
        str(settlement_id),
        "view",
        str(user_id),
        detail=f"Permission denied: subject '{user_id}' cannot view settlement:{settlement_id}",
    )


async def check_bulletin_board_edit_permission(
    spicedb: Any,
    settlement_id: str,
    user_id: str,
) -> None:
    """Ensure user has permission to pin new notices to the bulletin board."""
    allowed = (
        await check_subject(spicedb, "settlement", str(settlement_id), "edit", str(user_id))
        or await check_subject(spicedb, "settlement", str(settlement_id), "upgrade", str(user_id))
        or await check_subject(spicedb, "settlement", str(settlement_id), "manage", str(user_id))
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' lacks edit permission on settlement:{settlement_id}",
        )


async def check_bulletin_notice_view_permission(
    spicedb: Any,
    notice_id: str,
    settlement_id: str,
    user_id: str,
) -> None:
    """Ensure user has permission to view / decrypt a specific notice."""
    allowed = await check_subject(
        spicedb, "bulletin_notice", str(notice_id), "view", str(user_id)
    ) or await check_subject(spicedb, "settlement", str(settlement_id), "view", str(user_id))
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' cannot view notice:{notice_id}",
        )


async def check_bulletin_notice_edit_permission(
    spicedb: Any,
    notice_id: str,
    settlement_id: str,
    user_id: str,
) -> None:
    """Ensure user is author or DM/manager to remove or moderate a notice."""
    allowed = (
        await check_subject(spicedb, "bulletin_notice", str(notice_id), "edit", str(user_id))
        or await check_subject(spicedb, "bulletin_notice", str(notice_id), "manage", str(user_id))
        or await check_subject(spicedb, "settlement", str(settlement_id), "manage", str(user_id))
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' cannot edit/remove notice:{notice_id}",
        )


async def write_bulletin_notice_relationships(
    spicedb: Any,
    notice_id: str,
    settlement_id: str,
    author_id: str | None = None,
    campaign_id: str | None = None,
) -> None:
    """Write SpiceDB Zanzibar tuples for a pinned bulletin board notice."""
    nid = str(notice_id)
    await spicedb.write_relationship(
        resource_type="bulletin_notice",
        resource_id=nid,
        relation="settlement",
        subject_type="settlement",
        subject_id=str(settlement_id),
    )
    if campaign_id:
        await spicedb.write_relationship(
            resource_type="bulletin_notice",
            resource_id=nid,
            relation="campaign",
            subject_type="campaign",
            subject_id=str(campaign_id),
        )
    if author_id:
        await spicedb.write_relationship(
            resource_type="bulletin_notice",
            resource_id=nid,
            relation="author",
            subject_type="user",
            subject_id=str(author_id),
        )


async def delete_bulletin_notice_relationships(
    spicedb: Any,
    notice_id: str,
    settlement_id: str,
    author_id: str | None = None,
    campaign_id: str | None = None,
) -> None:
    """Delete SpiceDB Zanzibar tuples when a bulletin notice is removed. Failures propagate."""
    nid = str(notice_id)
    await spicedb.delete_relationship(
        resource_type="bulletin_notice",
        resource_id=nid,
        relation="settlement",
        subject_type="settlement",
        subject_id=str(settlement_id),
    )
    if campaign_id:
        await spicedb.delete_relationship(
            resource_type="bulletin_notice",
            resource_id=nid,
            relation="campaign",
            subject_type="campaign",
            subject_id=str(campaign_id),
        )
    if author_id:
        await spicedb.delete_relationship(
            resource_type="bulletin_notice",
            resource_id=nid,
            relation="author",
            subject_type="user",
            subject_id=str(author_id),
        )
