"""Soundscape gateway APIRouter proxying to soundscape microservice with Zanzibar authorization."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from gateway_api.auth import CurrentPrincipal, get_spicedb_client
from gateway_api.campaign_store import campaign_store
from gateway_api.proxy import forward_json, upstream_url
from soundscape.models import MoodOverrideRequest, SoundscapeCueRequest, TensionCalculationRequest

router = APIRouter(prefix="/api/v1/soundscape", tags=["Soundscape"])
SOUNDSCAPE_DEFAULT_URL = "http://soundscape:8009"


def _soundscape_url() -> str:
    return upstream_url("SOUNDSCAPE_SERVICE_URL", SOUNDSCAPE_DEFAULT_URL)


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
async def trigger_cue(req: SoundscapeCueRequest, user: CurrentPrincipal, request: Request) -> Any:
    await _check_soundscape_perm(user.user_id, "play", req.session_id, req.campaign_id)
    return await forward_json(
        request,
        method="POST",
        base_url=_soundscape_url(),
        path="/api/v1/soundscape/cue",
        json_body=req.model_dump(mode="json"),
    )


@router.get("/tension")
async def get_tension(
    user: CurrentPrincipal, request: Request, session_id: str = Query(default="default")
) -> Any:
    return await forward_json(
        request,
        method="GET",
        base_url=_soundscape_url(),
        path="/api/v1/soundscape/tension",
        params={"session_id": session_id},
    )


@router.post("/tension/calculate")
async def calculate_encounter_tension(
    req: TensionCalculationRequest, user: CurrentPrincipal, request: Request
) -> Any:
    return await forward_json(
        request,
        method="POST",
        base_url=_soundscape_url(),
        path="/api/v1/soundscape/tension/calculate",
        json_body=req.model_dump(mode="json"),
    )


@router.post("/stems/override")
@router.post("/override")
async def override_soundscape_mood(
    req: MoodOverrideRequest, user: CurrentPrincipal, request: Request
) -> Any:
    await _check_soundscape_perm(user.user_id, "run_session", req.session_id, req.campaign_id)
    return await forward_json(
        request,
        method="POST",
        base_url=_soundscape_url(),
        path="/api/v1/soundscape/override",
        json_body=req.model_dump(mode="json"),
    )


@router.get("/leitmotif/{character_id}")
@router.get("/leitmotif/profile/{character_id}")
async def get_leitmotif_profile(
    character_id: str,
    user: CurrentPrincipal,
    request: Request,
    session_id: str = Query(default="default"),
) -> Any:
    return await forward_json(
        request,
        method="GET",
        base_url=_soundscape_url(),
        path=f"/api/v1/soundscape/leitmotif/profile/{character_id}",
        params={"session_id": session_id},
    )
