"""Recursive Zanzibar permission resolution over the parsed runefoble.zed graph.

The evaluator follows only schema-defined permissions, relations, and arrows. It holds no
role-name grants and no alias table. A name the schema does not define never matches.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from runefoble_auth.schema_graph import SchemaGraph


class PermissionEvaluator:
    """Evaluates Zanzibar graph reachability, union and arrow rules, and caveats."""

    def __init__(
        self,
        schema: SchemaGraph,
        caveats: dict[str, Callable[..., bool]] | None = None,
    ):
        self.schema = schema
        self.caveats: dict[str, Callable[..., bool]] = caveats or {}

    def evaluate_caveat(self, name: str, ctx: dict[str, Any] | None) -> bool:
        return bool(self.caveats[name](ctx or {})) if name in self.caveats else True

    def find_subjects(self, t: set[str], rt: str, rid: str, rel: str) -> list[tuple[str, str]]:
        pfx = f"{rt}:{rid}#{rel}@"
        return [
            tuple(k[len(pfx) :].split(":", 1))  # type: ignore
            for k in t
            if k.startswith(pfx) and ":" in k[len(pfx) :]
        ]

    def _has(self, t: set[str], rt: str, rid: str, rel: str, st: str, sid: str) -> bool:
        return f"{rt}:{rid}#{rel}@{st}:{sid}" in t

    async def evaluate(
        self,
        t: set[str],
        rt: str,
        rid: str,
        perm: str,
        st: str,
        sid: str,
        context: dict[str, Any] | None = None,
        visited: set[tuple[str, str, str]] | None = None,
    ) -> bool:
        """Return True when the schema grants `perm` on `rt:rid` to subject `st:sid`.

        Callers validate the names first. An undefined permission grants nothing here.
        """
        visited = visited or set()
        v_key = (rt, rid, perm)
        if v_key in visited:
            return False
        visited.add(v_key)

        obj = self.schema.definitions.get(rt)
        if obj is None or perm not in obj.permissions:
            return False

        for rule in obj.permissions[perm].rules:
            if "->" in rule:
                p_rel, p_perm = rule.split("->", 1)
                for pt, pi in self.find_subjects(t, rt, rid, p_rel):
                    if await self.evaluate(t, pt, pi, p_perm, st, sid, context, visited.copy()):
                        return True
            elif rule in obj.relations:
                if self._has(t, rt, rid, rule, st, sid):
                    return True
            elif await self.evaluate(t, rt, rid, rule, st, sid, context, visited.copy()):
                return True

        return False
