"""Soundscape gateway APIRouter proxying to soundscape microservice with Zanzibar authorization."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from gateway_api.auth import get_current_user, get_spicedb_client
from gateway_api.campaign_store import campaign_store
from runefoble_auth.zitadel import AuthenticatedUser
from soundscape.models import MoodOverrideRequest, SoundscapeCueRequest, TensionCalculationRequest
from soundscape.routers.cue import trigger_sound_cue
from soundscape.routers.leitmotif import get_character_leitmotif_profile
from soundscape.routers.stems import override_mood
from soundscape.routers.tension import calculate_tension, get_tension_status

router = APIRouter(prefix="/api/v1/soundscape", tags=["Soundscape"])
SOUNDSCAPE_SERVICE_URL = os.environ.get("SOUNDSCAPE_SERVICE_URL", "http://soundscape:8010")


async def _proxy_or_fallback(
    method: str, path: str, fn: Callable[[], Any], json: Any = None, params: Any = None
) -> Any:
    if SOUNDSCAPE_SERVICE_URL:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.request(
                    method, f"{SOUNDSCAPE_SERVICE_URL}{path}", json=json, params=params
                )
                if 200 <= res.status_code < 300:
                    return res.json()
        except Exception:
            pass
    r = await fn()
    return r.model_dump() if hasattr(r, "model_dump") else r


async def _check_soundscape_perm(
    user_id: str, perm: str, sid: str | None = None, cid: Any = None
) -> None:
    c = get_spicedb_client()
    targets = [t for t in (cid, sid if sid != "default" else None) if t]
    sess = campaign_store.get_session(sid) if sid and sid != "default" else None
    if sess and sess.campaign_id:
        targets.append(sess.campaign_id)
    for t in targets:
        if await c.check_permission("campaign", str(t), perm, "user", user_id) or (
            perm == "run_session"
            and await c.check_permission("campaign", str(t), "manage", "user", user_id)
        ):
            return
    if sid and sid != "default":
        sp = "participate" if perm == "play" else "control"
        for rt in ("session", "game_session"):
            if await c.check_permission(rt, sid, sp, "user", user_id):
                return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "permission_denied",
            "message": f"Subject lacks '{perm}'.",
            "required_permission": perm,
        },
    )


@router.post("/cue")
async def trigger_cue(
    req: SoundscapeCueRequest, user: Annotated[AuthenticatedUser, Depends(get_current_user)]
) -> dict[str, Any]:
    await _check_soundscape_perm(user.user_id, "play", req.session_id, req.campaign_id)
    return await _proxy_or_fallback(
        "POST",
        "/api/v1/soundscape/cue",
        lambda: trigger_sound_cue(req, user_id=None, spicedb=get_spicedb_client()),
        json=req.model_dump(mode="json"),
    )


@router.get("/tension")
async def get_tension(session_id: str = Query(default="default")) -> dict[str, Any]:
    return await _proxy_or_fallback(
        "GET",
        "/api/v1/soundscape/tension",
        lambda: get_tension_status(session_id=session_id),
        params={"session_id": session_id},
    )


@router.post("/tension/calculate")
async def calculate_encounter_tension(req: TensionCalculationRequest) -> dict[str, Any]:
    return await _proxy_or_fallback(
        "POST",
        "/api/v1/soundscape/tension/calculate",
        lambda: calculate_tension(req),
        json=req.model_dump(mode="json"),
    )


@router.post("/stems/override")
@router.post("/override")
async def override_soundscape_mood(
    req: MoodOverrideRequest, user: Annotated[AuthenticatedUser, Depends(get_current_user)]
) -> dict[str, Any]:
    await _check_soundscape_perm(user.user_id, "run_session", req.session_id, req.campaign_id)
    return await _proxy_or_fallback(
        "POST",
        "/api/v1/soundscape/override",
        lambda: override_mood(req, user_id=None, spicedb=get_spicedb_client()),
        json=req.model_dump(mode="json"),
    )


@router.get("/leitmotif/{character_id}")
@router.get("/leitmotif/profile/{character_id}")
async def get_leitmotif_profile(
    character_id: str, session_id: str = Query(default="default")
) -> dict[str, Any]:
    return await _proxy_or_fallback(
        "GET",
        f"/api/v1/soundscape/leitmotif/profile/{character_id}",
        lambda: get_character_leitmotif_profile(character_id=character_id, session_id=session_id),
        params={"session_id": session_id},
    )
