"""Codex lifecycle dependencies and SpiceDB Zanzibar authorization checks.

Read and edit decisions come from one schema permission each on `codex_entry`
(`libs/runefoble_auth/schema/runefoble.zed`). The entry's own relations decide access.
No campaign-level shortcut bypasses them.
"""

from typing import Annotated
from uuid import UUID

from eventsource import AggregateNotFoundError
from fastapi import Depends, HTTPException, status
from runefoble_auth.errors import AuthzError
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.permissions import check_subject
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.errors import ServiceUnavailableError
from runefoble_platform.event_sourcing import AggregateRepository

from campaign_lore.codex_aggregate import CodexAggregate, CodexEntryState
from campaign_lore.identity import CallerId
from campaign_lore.permissions import check_user_can_view_campaign

SHARED_PRIVACY = ("party_shared", "public")


async def check_user_can_view_codex_entry(
    user_id: str, entry: CodexEntryState, spicedb: SpiceDBClient
) -> bool:
    """Check the schema permission `codex_entry.view` for the caller."""
    return await check_subject(spicedb, "codex_entry", str(entry.entry_id), "view", user_id)


async def check_user_can_edit_codex_entry(
    user_id: str, entry: CodexEntryState, spicedb: SpiceDBClient
) -> bool:
    """Check the schema permission `codex_entry.edit` for the caller."""
    return await check_subject(spicedb, "codex_entry", str(entry.entry_id), "edit", user_id)


async def require_campaign_view(user_id: str, campaign_id: UUID, spicedb: SpiceDBClient) -> None:
    """Raise HTTP 403 if user cannot view the campaign."""
    if not await check_user_can_view_campaign(user_id, campaign_id, spicedb):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden: Cannot access campaign codex.")


async def load_codex_entry(
    campaign_id: UUID,
    entry_id: UUID,
    user_id: str,
    repo: AggregateRepository[CodexAggregate],
    spicedb: SpiceDBClient,
    *,
    for_edit: bool = False,
) -> CodexAggregate:
    """Load a codex entry of the path campaign and enforce its schema permission.

    An entry of another campaign returns 404, the same as a missing entry, so that
    entry existence is not revealed.
    """
    try:
        aggregate = await repo.load(entry_id)
    except AggregateNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Codex entry not found") from exc

    if aggregate.state.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Codex entry not found")

    chk = check_user_can_edit_codex_entry if for_edit else check_user_can_view_codex_entry
    if not await chk(user_id, aggregate.state, spicedb):
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
    """Write the author, editor, campaign, and privacy relations of a new entry."""
    for rel in ("author", "editor"):
        await spicedb.write_relationship("codex_entry", eid, rel, "user", author)
    await spicedb.write_relationship("codex_entry", eid, "campaign", "campaign", cid)
    if privacy in SHARED_PRIVACY:
        await spicedb.write_relationship("codex_entry", eid, privacy, "campaign", cid)


async def update_codex_permissions(
    spicedb: SpiceDBClient, eid: str, cid: str, old_p: str, new_p: str
) -> None:
    """Replace the privacy relation of an entry when its privacy changes."""
    if old_p in SHARED_PRIVACY:
        await spicedb.delete_relationship("codex_entry", eid, old_p, "campaign", cid)
    if new_p in SHARED_PRIVACY:
        await spicedb.write_relationship("codex_entry", eid, new_p, "campaign", cid)


def _repo_dep() -> AggregateRepository[CodexAggregate]:
    from campaign_lore.dependencies import get_codex_repo

    return get_codex_repo()


class CodexSessionDeps:
    """Consolidated codex session dependencies and Zanzibar helpers."""

    def __init__(
        self,
        user_id: CallerId,
        repo: Annotated[AggregateRepository[CodexAggregate], Depends(_repo_dep)],
        spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    ) -> None:
        self.user_id, self.repo, self.spicedb = user_id, repo, spicedb

    async def can_view(self, st: CodexEntryState) -> bool:
        """Check whether the authenticated caller can view the codex entry."""
        return await check_user_can_view_codex_entry(self.user_id, st, self.spicedb)

    async def persist_new_entry(
        self, agg: CodexAggregate, cid: UUID, author: str, priv: str
    ) -> None:
        """Write the authorization tuples, then save the aggregate.

        A failed tuple write raises 503 and the entry is not saved.
        """
        try:
            await write_codex_permissions(
                self.spicedb, str(agg.aggregate_id), author, str(cid), priv
            )
        except AuthzError as exc:
            raise ServiceUnavailableError(
                "Codex authorization is unavailable. The entry was not saved."
            ) from exc
        await self.repo.save(agg)

    async def persist_updated_entry(
        self, agg: CodexAggregate, cid: UUID, eid: UUID, old_p: str, new_p: str | None
    ) -> None:
        """Sync the privacy tuples, then save the aggregate. A failed write raises 503."""
        if new_p and new_p != old_p:
            try:
                await update_codex_permissions(self.spicedb, str(eid), str(cid), old_p, new_p)
            except AuthzError as exc:
                raise ServiceUnavailableError(
                    "Codex authorization is unavailable. The entry was not updated."
                ) from exc
        await self.repo.save(agg)
