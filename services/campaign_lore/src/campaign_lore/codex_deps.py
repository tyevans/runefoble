"""Codex lifecycle dependencies and SpiceDB Zanzibar authorization checks."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.event_sourcing import AggregateRepository

from campaign_lore.codex_aggregate import CodexAggregate, CodexEntryState
from campaign_lore.permissions import check_user_can_view_campaign, get_current_user_id


async def check_user_can_view_codex_entry(
    user_id: str | None, entry: CodexEntryState, campaign_id: UUID, spicedb: SpiceDBClient
) -> bool:
    """Check whether user can read a codex entry under SpiceDB Zanzibar."""
    if not user_id:
        return entry.privacy == "public"
    if entry.author_id == user_id:
        return True
    if await spicedb.check_permission("codex_entry", str(entry.entry_id), "view", "user", user_id):
        return True
    cid = str(campaign_id)
    if entry.privacy == "party_shared":
        for perm in ("play", "run_session"):
            if await spicedb.check_permission("campaign", cid, perm, "user", user_id):
                return True
    return entry.privacy == "public" and await spicedb.check_permission(
        "campaign", cid, "view", "user", user_id
    )


async def check_user_can_edit_codex_entry(
    user_id: str | None, entry: CodexEntryState, campaign_id: UUID, spicedb: SpiceDBClient
) -> bool:
    """Check whether user can edit a codex entry under SpiceDB Zanzibar."""
    if not user_id:
        return False
    if entry.author_id == user_id:
        return True
    if await spicedb.check_permission("codex_entry", str(entry.entry_id), "edit", "user", user_id):
        return True
    return await spicedb.check_permission(
        "campaign", str(campaign_id), "run_session", "user", user_id
    )


async def require_campaign_view(
    user_id: str | None, campaign_id: UUID, spicedb: SpiceDBClient
) -> None:
    """Raise HTTP 403 if user cannot view the campaign."""
    if not await check_user_can_view_campaign(user_id, campaign_id, spicedb):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden: Cannot access campaign codex.")


async def load_codex_entry(
    campaign_id: UUID,
    entry_id: UUID,
    user_id: str | None,
    repo: AggregateRepository[CodexAggregate],
    spicedb: SpiceDBClient,
    *,
    for_edit: bool = False,
) -> CodexAggregate:
    """Load codex entry aggregate and enforce Zanzibar permissions."""
    try:
        aggregate = await repo.load(entry_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Codex entry not found") from exc

    chk = check_user_can_edit_codex_entry if for_edit else check_user_can_view_codex_entry
    if not await chk(user_id, aggregate.state, campaign_id, spicedb):
        err = (
            "Not authorized to edit this codex entry."
            if for_edit
            else "SpiceDB Zanzibar policy denies access to this private codex entry."
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Forbidden: {err}")
    return aggregate


async def write_codex_permissions(
    spicedb: SpiceDBClient, eid: str, author: str, cid: str, privacy: str
) -> None:
    """Write initial SpiceDB Zanzibar ownership and privacy relations."""
    for rel in ("author", "editor"):
        await spicedb.write_relationship("codex_entry", eid, rel, "user", author)
    await spicedb.write_relationship("codex_entry", eid, "campaign", "campaign", cid)
    if privacy in ("party_shared", "public"):
        await spicedb.write_relationship("codex_entry", eid, privacy, "campaign", cid)


async def update_codex_permissions(
    spicedb: SpiceDBClient, eid: str, cid: str, old_p: str, new_p: str
) -> None:
    """Synchronize SpiceDB Zanzibar privacy relations on privacy change."""
    for p, fn in [(old_p, spicedb.delete_relationship), (new_p, spicedb.write_relationship)]:
        if p in ("party_shared", "public"):
            await fn("codex_entry", eid, p, "campaign", cid)


def _repo_dep() -> AggregateRepository[CodexAggregate]:
    from campaign_lore.dependencies import get_codex_repo

    return get_codex_repo()


def _spicedb_dep() -> SpiceDBClient:
    from campaign_lore.dependencies import get_spicedb_client

    return get_spicedb_client()


class CodexSessionDeps:
    """Consolidated codex session dependencies and Zanzibar helpers."""

    def __init__(
        self,
        user_id: Annotated[str | None, Depends(get_current_user_id)],
        repo: Annotated[AggregateRepository[CodexAggregate], Depends(_repo_dep)],
        spicedb: Annotated[SpiceDBClient, Depends(_spicedb_dep)],
    ) -> None:
        self.user_id, self.repo, self.spicedb = user_id, repo, spicedb

    async def can_view(self, st: CodexEntryState, campaign_id: UUID) -> bool:
        """Check whether authenticated user can view codex entry under Zanzibar."""
        return await check_user_can_view_codex_entry(self.user_id, st, campaign_id, self.spicedb)

    async def persist_new_entry(
        self, agg: CodexAggregate, cid: UUID, author: str, priv: str, idx: dict[UUID, list[UUID]]
    ) -> None:
        """Save aggregate and write SpiceDB authorization tuples."""
        await self.repo.save(agg)
        idx.setdefault(cid, []).append(agg.aggregate_id)
        await write_codex_permissions(self.spicedb, str(agg.aggregate_id), author, str(cid), priv)

    async def persist_updated_entry(
        self, agg: CodexAggregate, cid: UUID, eid: UUID, old_p: str, new_p: str | None
    ) -> None:
        """Save updated aggregate and sync revised SpiceDB authorization tuples."""
        await self.repo.save(agg)
        if new_p and new_p != old_p:
            await update_codex_permissions(self.spicedb, str(eid), str(cid), old_p, new_p)
