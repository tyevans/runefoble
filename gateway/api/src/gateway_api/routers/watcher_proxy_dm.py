"""Dungeon Master, stand-in, whisper, and action routes proxied to The Watcher (TASK-0596).

The gateway verifies the bearer token and forwards each request with that token. The owner
checks every object permission: DM veto and approval, stand-in guardrails, and whisper
visibility (ADR-0002: players and DMs keep veto authority). Routes that call the inference
worker use the LLM timeout from `PlatformSettings`, which is longer than the owner's worker
budget, so the owner answers first. Each route is a row in `ROUTES` (TASK-0822).
"""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.dependencies import platform_settings
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes

SERVICE = "the_watcher"
LLM_TIMEOUT_S = platform_settings.watcher_llm_proxy_timeout_s

router = APIRouter(tags=["The Watcher"])

ROUTES = (
    ProxyRoute(
        "POST",
        "/api/v1/watcher/scenes/generate",
        ("api", "v1", "watcher", "scenes", "generate"),
        SERVICE,
        name="watcher_generate_scene",
        doc="Generate scene atmosphere, lighting, and an ambient audio prompt (The Watcher).",
        body="json",
        principal=True,
        timeout=LLM_TIMEOUT_S,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/encounters/spawn",
        ("api", "v1", "watcher", "encounters", "spawn"),
        SERVICE,
        name="watcher_spawn_encounter",
        doc="Spawn a balanced encounter for the party (The Watcher; DM only).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/encounters/npc-turn",
        ("api", "v1", "watcher", "encounters", "npc-turn"),
        SERVICE,
        name="watcher_npc_turn",
        doc="Resolve one tactical NPC or monster turn (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/narrate",
        ("api", "v1", "watcher", "narrate"),
        SERVICE,
        name="watcher_narrate",
        doc="Generate atmospheric narration and DM rulings (The Watcher; DM only).",
        body="json",
        principal=True,
        timeout=LLM_TIMEOUT_S,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/stand-in/act",
        ("api", "v1", "watcher", "stand-in", "act"),
        SERVICE,
        name="watcher_stand_in_act",
        doc="Generate the action of an absent player's stand-in (The Watcher).",
        body="json",
        principal=True,
        timeout=LLM_TIMEOUT_S,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/stand-in/recap",
        ("api", "v1", "watcher", "stand-in", "recap"),
        SERVICE,
        name="watcher_stand_in_recap",
        doc="Write the absentee recap for a returning player (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/chronicle/recap",
        ("api", "v1", "watcher", "chronicle", "recap"),
        SERVICE,
        name="watcher_chronicle_recap",
        doc="Write the absentee chronicle and recap event (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/watcher/whispers",
        ("api", "v1", "watcher", "whispers"),
        SERVICE,
        name="watcher_list_whispers",
        doc="List the DM's private narrative whispers (The Watcher).",
        query_all=True,
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/whispers",
        ("api", "v1", "watcher", "whispers"),
        SERVICE,
        name="watcher_create_whisper",
        doc="Create a private narrative suggestion for the DM (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/whispers/generate",
        ("api", "v1", "watcher", "whispers", "generate"),
        SERVICE,
        name="watcher_generate_whispers",
        doc="Generate DM whispers: hints, monster tactics, and perception checks (The Watcher).",
        body="json",
        principal=True,
        timeout=LLM_TIMEOUT_S,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/whispers/{whisper_id}/dispatch",
        ("api", "v1", "watcher", "whispers", "{whisper_id}", "dispatch"),
        SERVICE,
        name="watcher_dispatch_whisper",
        doc="Send an audience narration to the table (The Watcher; DM only).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/actions/propose",
        ("api", "v1", "watcher", "actions", "propose"),
        SERVICE,
        name="watcher_propose_action",
        doc="Propose an AI game action with a pre-execution pause window (The Watcher).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/watcher/actions/pending",
        ("api", "v1", "watcher", "actions", "pending"),
        SERVICE,
        name="watcher_list_pending_actions",
        doc="List every action a session holds with its status (The Watcher; DM only).",
        query_all=True,
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/veto",
        ("api", "v1", "watcher", "veto"),
        SERVICE,
        name="watcher_veto_action",
        doc="Cancel a pending AI action before it changes the board (The Watcher; DM only).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/approve",
        ("api", "v1", "watcher", "approve"),
        SERVICE,
        name="watcher_approve_action",
        doc="Commit a pending AI action at once (The Watcher; DM only).",
        body="json",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/watcher/modify",
        ("api", "v1", "watcher", "modify"),
        SERVICE,
        name="watcher_modify_action",
        doc="Change the parameters or target of a pending AI action (The Watcher; DM only).",
        body="json",
        principal=True,
    ),
)

register_proxy_routes(router, ROUTES)
