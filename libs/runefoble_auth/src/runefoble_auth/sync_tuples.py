"""SpiceDB relationship tuple formatting, normalization tables, and low-level helpers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from runefoble_auth.spicedb import Relationship
from runefoble_auth.zitadel import AuthenticatedUser, ZitadelAuthService

logger = logging.getLogger(__name__)


class SyncResult(BaseModel):
    """Result summary of a synchronization operation."""

    status: str = "success"
    synced_tuples: list[str] = Field(default_factory=list)
    revoked_tuples: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# Mapping from incoming role names to canonical Zanzibar campaign relations
CAMPAIGN_ROLE_RELATIONS: dict[str, list[str]] = {
    "gm": ["gm", "dungeon_master"],
    "dm": ["gm", "dungeon_master"],
    "dungeon_master": ["gm", "dungeon_master"],
    "player": ["player"],
    "spectator": ["spectator"],
    "owner": ["owner"],
}


def normalize_campaign_role(role: str) -> list[str]:
    """Normalize role string into corresponding Zanzibar campaign relations."""
    return CAMPAIGN_ROLE_RELATIONS.get(role.strip().lower(), [role.strip().lower()])


def format_tuple(res_t: str, res_id: str, rel: str, sub_t: str, sub_id: str) -> str:
    """Format Zanzibar tuple string representation (resource#relation@subject)."""
    return f"{res_t}:{res_id}#{rel}@{sub_t}:{sub_id}"


def resolve_user_claims(
    zitadel_auth: ZitadelAuthService | Any,
    user_or_claims: AuthenticatedUser | dict[str, Any] | str,
) -> AuthenticatedUser:
    """Resolve raw token, dict claims, or AuthenticatedUser instance."""
    if isinstance(user_or_claims, str):
        return zitadel_auth.decode_token(user_or_claims)
    if isinstance(user_or_claims, AuthenticatedUser):
        return user_or_claims
    if isinstance(user_or_claims, dict):
        token = user_or_claims.get("token")
        if token:
            return zitadel_auth.decode_token(token)
        return AuthenticatedUser(
            user_id=str(user_or_claims.get("user_id") or user_or_claims.get("sub", "anon")),
            username=str(user_or_claims.get("username") or "User"),
            email=user_or_claims.get("email"),
            roles=user_or_claims.get("roles", []),
            is_admin=bool(user_or_claims.get("is_admin", False)),
        )
    raise ValueError(f"Unsupported user_or_claims type: {type(user_or_claims)}")


async def execute_with_retry(
    coro_func: Any,
    max_retries: int = 3,
    retry_delay_seconds: float = 0.05,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute SpiceDB operation with exponential backoff on transient errors."""
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return await coro_func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            logger.warning("SpiceDB sync failed (attempt %d/%d): %s", attempt, max_retries, exc)
            if attempt < max_retries:
                await asyncio.sleep(retry_delay_seconds * (2 ** (attempt - 1)))
    if last_exc:
        raise last_exc


async def _mutate(
    method: Any,
    res_t: str,
    res_id: str,
    rel: str,
    sub_t: str,
    sub_id: str,
    executor: Callable[..., Any] | None,
) -> str:
    runner = executor or (lambda f, **kw: f(**kw))
    await runner(
        method,
        resource_type=res_t,
        resource_id=res_id,
        relation=rel,
        subject_type=sub_t,
        subject_id=sub_id,
    )
    return format_tuple(res_t, res_id, rel, sub_t, sub_id)


async def write_relationship_tuple(
    spicedb_client: Any,
    res_t: str,
    res_id: str,
    rel: str,
    sub_t: str,
    sub_id: str,
    executor: Callable[..., Any] | None = None,
) -> str:
    """Write relationship tuple via SpiceDB client, optionally with an execution wrapper."""
    return await _mutate(
        spicedb_client.write_relationship, res_t, res_id, rel, sub_t, sub_id, executor
    )


async def delete_relationship_tuple(
    spicedb_client: Any,
    res_t: str,
    res_id: str,
    rel: str,
    sub_t: str,
    sub_id: str,
    executor: Callable[..., Any] | None = None,
) -> str:
    """Delete relationship tuple via SpiceDB client, optionally with an execution wrapper."""
    return await _mutate(
        spicedb_client.delete_relationship, res_t, res_id, rel, sub_t, sub_id, executor
    )


async def batch_write_tuples(
    write_tuple_func: Callable[..., Any],
    relationships: list[tuple[str, str, str, str, str] | Relationship],
) -> list[str]:
    """Batch write relationships idempotently."""
    synced: list[str] = []
    for item in relationships:
        rel = item if isinstance(item, Relationship) else Relationship(*item)
        synced.append(
            await write_tuple_func(
                rel.resource_type, rel.resource_id, rel.relation, rel.subject_type, rel.subject_id
            )
        )
    return synced


async def reconcile_tuples(
    spicedb_client: Any,
    write_tuple_func: Callable[..., Any],
    expected_tuples: list[tuple[str, str, str, str, str] | Relationship],
) -> dict[str, Any]:
    """Reconcile expected Zanzibar relationships against current state."""
    existing_keys = {r.to_tuple_key() for r in await spicedb_client.read_relationships()}
    added: list[str] = []
    for item in expected_tuples:
        rel = item if isinstance(item, Relationship) else Relationship(*item)
        if rel.to_tuple_key() not in existing_keys:
            key = await write_tuple_func(
                rel.resource_type, rel.resource_id, rel.relation, rel.subject_type, rel.subject_id
            )
            added.append(key)
    return {
        "reconciled": True,
        "total_expected": len(expected_tuples),
        "added_count": len(added),
        "added_tuples": added,
    }
