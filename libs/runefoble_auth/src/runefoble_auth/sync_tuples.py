"""SpiceDB relationship tuple formatting, normalization tables, and low-level helpers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from runefoble_auth.errors import AuthzUnavailableError
from runefoble_auth.relationship import Relationship

logger = logging.getLogger(__name__)


class SyncResult(BaseModel):
    """Result summary of a synchronization operation."""

    status: str = "success"
    synced_tuples: list[str] = Field(default_factory=list)
    revoked_tuples: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def format_tuple(res_t: str, res_id: str, rel: str, sub_t: str, sub_id: str) -> str:
    """Format Zanzibar tuple string representation (resource#relation@subject)."""
    return f"{res_t}:{res_id}#{rel}@{sub_t}:{sub_id}"


async def execute_with_retry(
    coro_func: Any,
    max_retries: int = 3,
    retry_delay_seconds: float = 0.05,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute a SpiceDB operation. Retry only `AuthzUnavailableError`, with exponential backoff.

    Every other exception is permanent (a schema rejection, a refused write, or a defect).
    It propagates on the first attempt and is not logged as a transient failure.
    """
    if max_retries < 1:
        raise ValueError(f"max_retries must be at least 1, got {max_retries}")
    for attempt in range(1, max_retries + 1):
        try:
            return await coro_func(*args, **kwargs)
        except AuthzUnavailableError as exc:
            if attempt == max_retries:
                raise
            logger.warning("SpiceDB unavailable (attempt %d/%d): %s", attempt, max_retries, exc)
            await asyncio.sleep(retry_delay_seconds * (2 ** (attempt - 1)))
    raise AssertionError("unreachable: the final attempt either returns or raises")


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
