from fastapi import APIRouter
from gateway_api.auth import CurrentPrincipal
from gateway_api.dependencies import ws_manager
from gateway_api.session_access import require_session_permission

router = APIRouter(tags=["Tabletop & Game Sessions"])


@router.post("/api/v1/watcher/speak-and-act")
async def speak_and_act(
    transcript: str,
    speaker_name: str,
    session_id: str,
    user: CurrentPrincipal,
) -> dict:
    await require_session_permission(session_id, user.user_id, "participate")
    event = {
        "type": "speech_action",
        "speaker": speaker_name,
        "transcript": transcript,
        "action_taken": "Valeros stepped forward 2 squares.",
        "watcher_commentary": "The Watcher observes your advance into the crypt.",
    }
    await ws_manager.broadcast(session_id, event)
    return event
