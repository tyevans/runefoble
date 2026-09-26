"""In-memory mock async Redis client simulating Redis Streams operations and Consumer Groups."""

from __future__ import annotations

import time
from typing import Any


class MockAsyncRedis:
    """In-memory mock async Redis client simulating Redis Streams operations and Consumer Groups."""

    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self.groups: dict[tuple[str, str], dict[str, Any]] = {}
        self.counter: int = 0
        self.closed: bool = False

    async def xadd(self, stream: str, fields: dict[str, Any]) -> str:
        self.counter += 1
        entry_id = f"1700000000000-{self.counter}"
        self.streams.setdefault(stream, []).append((entry_id, fields))
        return entry_id

    async def xgroup_create(
        self, stream: str, group_name: str, id: str = "0", mkstream: bool = True
    ) -> bool:
        if mkstream:
            self.streams.setdefault(stream, [])
        key = (stream, group_name)
        if key in self.groups:
            raise Exception("BUSYGROUP Consumer Group name already exists")
        self.groups[key] = {"delivered_idx": 0, "pending": {}}
        return True

    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int = 10,
        block: int | None = None,
    ) -> list[tuple[str, list[tuple[str, dict[str, Any]]]]]:
        results: list[tuple[str, list[tuple[str, dict[str, Any]]]]] = []
        for stream_name in streams:
            if stream_name not in self.streams or (stream_name, groupname) not in self.groups:
                continue
            group_data = self.groups[(stream_name, groupname)]
            idx = group_data["delivered_idx"]
            available = self.streams[stream_name][idx : idx + count]
            group_data["delivered_idx"] = idx + len(available)
            now = time.time()
            for msg_id, fields in available:
                group_data["pending"][msg_id] = {
                    "consumer": consumername,
                    "fields": fields,
                    "claimed_at": now,
                    "idle_time_ms": 0.0,
                }
            if available:
                results.append((stream_name, available))
        return results

    async def xack(self, stream: str, group_name: str, *message_ids: str) -> int:
        group_data = self.groups.get((stream, group_name))
        if not group_data:
            return 0
        return sum(1 for mid in message_ids if group_data["pending"].pop(mid, None) is not None)

    async def xautoclaim(
        self,
        name: str,
        groupname: str,
        consumername: str,
        min_idle_time: int,
        start_id: str = "0-0",
        count: int = 10,
        **_kwargs: Any,
    ) -> tuple[str, list[tuple[str, dict[str, Any]]], list[str]]:
        group_data = self.groups.get((name, groupname))
        if not group_data:
            return ("0-0", [], [])
        claimed: list[tuple[str, dict[str, Any]]] = []
        now = time.time()
        for mid, data in list(group_data["pending"].items()):
            idle_ms = data.get("idle_time_ms", 0.0) + (now - data.get("claimed_at", now)) * 1000.0
            if idle_ms >= min_idle_time:
                data.update({"consumer": consumername, "claimed_at": now, "idle_time_ms": 0.0})
                claimed.append((mid, data["fields"]))
                if len(claimed) >= count:
                    break
        return ("0-0", claimed, [])

    def set_message_idle(
        self, stream: str, group_name: str, message_id: str, idle_ms: float
    ) -> None:
        """Helper for unit tests: manually simulate idle elapsed time on a pending message."""
        key = (stream, group_name)
        if key in self.groups and message_id in self.groups[key]["pending"]:
            self.groups[key]["pending"][message_id]["idle_time_ms"] = idle_ms
            self.groups[key]["pending"][message_id]["claimed_at"] = time.time()

    def get_pending(self, stream: str, group_name: str) -> dict[str, dict[str, Any]]:
        """Helper for unit tests: query currently pending messages."""
        return dict(self.groups.get((stream, group_name), {}).get("pending", {}))

    async def aclose(self) -> None:
        self.closed = True


__all__ = ["MockAsyncRedis"]
