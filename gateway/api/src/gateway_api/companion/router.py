"""Mobile companion HTTP REST API routes."""

from __future__ import annotations

from fastapi import APIRouter
from gateway_api.auth import CurrentPrincipal
from gateway_api.companion.manager import mobile_companion_manager
from gateway_api.session_access import require_session_permission
from pydantic import BaseModel
from voice_agent.mobile import PROFILES

router = APIRouter(prefix="/api/v1/mobile/companion", tags=["Mobile Companion"])


class WhisperDispatchRequest(BaseModel):
    recipient_id: str
    content: str
    sender: str = "The Watcher"
    character_name: str | None = None


class TurnAlertDispatchRequest(BaseModel):
    recipient_id: str
    character_name: str
    round_num: int | None = None


class HapticDispatchRequest(BaseModel):
    recipient_id: str
    alert_type: str = "secret_whisper"
    vibration_pattern: list[int] | None = None


@router.get("/profiles")
async def get_mobile_profiles():
    """List available mobile audio streaming profiles."""
    return {k: v.model_dump() for k, v in PROFILES.items()}


@router.post("/{session_id}/whisper")
async def dispatch_whisper_endpoint(
    session_id: str,
    req: WhisperDispatchRequest,
    principal: CurrentPrincipal,
):
    """Dispatch a secret DM whisper and trigger mobile haptic ping."""
    await require_session_permission(session_id, principal.user_id, "control")

    frame = await mobile_companion_manager.dispatch_whisper(
        session_id=session_id,
        recipient_id=req.recipient_id,
        content=req.content,
        sender=req.sender,
        character_name=req.character_name,
    )
    return {"status": "dispatched", "session_id": session_id, "haptic_frame": frame}


@router.post("/{session_id}/turn-alert")
async def dispatch_turn_alert_endpoint(
    session_id: str,
    req: TurnAlertDispatchRequest,
    principal: CurrentPrincipal,
):
    """Trigger combat turn initiative haptic alert for mobile companion."""
    await require_session_permission(session_id, principal.user_id, "control")

    frame = await mobile_companion_manager.dispatch_turn_alert(
        session_id=session_id,
        recipient_id=req.recipient_id,
        character_name=req.character_name,
        round_num=req.round_num,
    )
    return {"status": "dispatched", "session_id": session_id, "haptic_frame": frame}


__all__ = ["router"]
