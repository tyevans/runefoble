"""Recursive Zanzibar permission resolution, arrow expressions, and caveat evaluation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from runefoble_auth.mock.schema_parser import SchemaGraph

DM_PERMS = set(  # noqa: SIM905
    "dungeon_master game_master gm run_session play view read edit move "  # noqa: SIM905
    "move_token modify_hp apply_condition spawn_monster set_scene "
    "control participate observe inspect moderate approve veto".split()  # noqa: SIM905
)
PLAYER_PERMS = set(
    "player play view read participate observe inspect".split()  # noqa: SIM905
)
SPECTATOR_PERMS = set("spectator view read observe inspect".split())  # noqa: SIM905
FALLBACK_RES = set(
    "session game_session lore_document audience_poll atlas codex_entry".split()  # noqa: SIM905
)
ALIAS_MAP = {
    "read": "view",
    "inspect": "view",
    "observe": "view",
    "control": "run_session",
    "participate": "play",
    "move_token": "move",
}


class PermissionEvaluator:
    """Evaluates Zanzibar graph reachability, arrow expressions, and caveats."""

    def __init__(
        self,
        schema: SchemaGraph | None = None,
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

    def _has_any(
        self, t: set[str], rt: str, rid: str, rels: tuple[str, ...], st: str, sid: str
    ) -> bool:
        return any(f"{rt}:{rid}#{r}@{st}:{sid}" in t for r in rels)

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
        """Recursively check if subject has permission on resource."""
        v_key = (rt, rid, perm)
        visited = visited or set()
        if v_key in visited:
            return False
        visited.add(v_key)

        norm = ALIAS_MAP.get(perm, perm)
        if self._has(t, rt, rid, perm, st, sid) or self._has(t, rt, rid, norm, st, sid):
            return True

        if rt == "campaign":
            if self._has(t, "campaign", rid, "owner", st, sid):
                return True
            if perm in DM_PERMS and self._has_any(
                t, "campaign", rid, ("dungeon_master", "game_master", "gm"), st, sid
            ):
                return True
            if perm in PLAYER_PERMS and self._has(t, "campaign", rid, "player", st, sid):
                return True
            if perm in SPECTATOR_PERMS and self._has(t, "campaign", rid, "spectator", st, sid):
                return True

        if self.schema:
            rules = self.schema.get_permission_rules(rt, perm) or self.schema.get_permission_rules(
                rt, norm
            )
            for rule in rules:
                if "->" in rule:
                    p_rel, p_perm = rule.split("->", 1)
                    parents = self.find_subjects(t, rt, rid, p_rel)
                    if not parents and p_rel == "campaign" and rt in FALLBACK_RES:
                        parents = [("campaign", rid)]
                    for pt, pi in parents:
                        if await self.evaluate(t, pt, pi, p_perm, st, sid, context, visited.copy()):
                            return True
                elif self._has(t, rt, rid, rule, st, sid) or await self.evaluate(
                    t, rt, rid, rule, st, sid, context, visited.copy()
                ):
                    return True

        if rt == "codex_entry":
            if self._has_any(t, "codex_entry", rid, ("author", "editor"), st, sid):
                return True
            for _, pi in self.find_subjects(t, "codex_entry", rid, "campaign") or [
                ("campaign", rid)
            ]:
                sh = self._has_any(
                    t, "codex_entry", rid, ("party_shared", "shared"), "campaign", pi
                )
                if sh and await self.evaluate(
                    t, "campaign", pi, "play", st, sid, context, visited.copy()
                ):
                    return True
                if self._has(
                    t, "codex_entry", rid, "public", "campaign", pi
                ) and await self.evaluate(
                    t, "campaign", pi, "view", st, sid, context, visited.copy()
                ):
                    return True

        if rt == "caravan_contract":
            if self._has_any(
                t, "caravan_contract", rid, ("guild_officer", "poster", "contractor"), st, sid
            ):
                return True
            for pt, pi in self.find_subjects(t, "caravan_contract", rid, "shared_world"):
                target = (
                    "trade"
                    if perm in ("claim", "trade")
                    else ("manage" if perm == "manage" else "view")
                )
                if await self.evaluate(t, pt, pi, target, st, sid, context, visited.copy()):
                    return True

        return False
