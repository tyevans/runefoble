"""DM Live Vocal Modulator and Real-Time NPC Formant DSP Router."""

from __future__ import annotations

import base64

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field
from voice_agent.coordinator import get_voice_room_coordinator
from voice_agent.dsp.pipeline import StreamPipelineFilter
from voice_agent.dsp.presets import NPCVoicePreset, get_preset, list_presets

router = APIRouter(tags=["Vocal Modulator"])
AUTH_SPECS = (
    ("game_session", "control"),
    ("session", "control"),
    ("game_session", "participate"),
    ("session", "participate"),
)


class ModulateVoiceRequest(BaseModel):
    session_id: str
    peer_id: str = "dm_speaker"
    preset_name: str | None = None
    pitch_shift_semitones: float | None = None
    formant_shift: float | None = None
    resonance_hz: float | None = None
    octave_offset: float | None = None
    audio_base64: str | None = None
    sample_rate: int = 16000
    enabled: bool = True


class ModulateVoiceResponse(BaseModel):
    session_id: str
    peer_id: str
    preset_name: str | None = None
    pitch_shift_semitones: float = 0.0
    formant_shift: float = 1.0
    resonance_hz: float = 0.0
    octave_offset: float = 0.0
    active_filters: list[str] = Field(default_factory=list)
    audio_base64: str | None = None
    audio_bytes_length: int = 0
    latency_ms: float = 0.0
    status: str = "success"


def _extract_user_id(request: Request, x_user_id: str | None, authorization: str | None) -> str:
    if x_user_id:
        return x_user_id
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:].strip()
    return request.query_params.get("user_id") or "dm_user"


async def _check_session_auth(coord, session_id: str, user_id: str) -> None:
    for rtype, perm in AUTH_SPECS:
        if await coord.spicedb.check_permission(rtype, session_id, perm, "user", user_id):
            return
    raise HTTPException(
        status_code=403, detail=f"Forbidden: '{user_id}' lacks permission for '{session_id}'"
    )


@router.get("/voice/presets", response_model=list[NPCVoicePreset])
@router.get("/api/v1/voice/presets", response_model=list[NPCVoicePreset])
async def get_presets():
    """List all available NPC voice presets."""
    return list_presets()


@router.post("/voice/modulate", response_model=ModulateVoiceResponse)
@router.post("/api/v1/voice/modulate", response_model=ModulateVoiceResponse)
async def modulate_voice(
    req: ModulateVoiceRequest,
    request: Request,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """Set active preset or fine-tune pitch/formant parameters on an active stream session."""
    user_id = _extract_user_id(request, x_user_id, authorization)
    coord = get_voice_room_coordinator()
    await _check_session_auth(coord, req.session_id, user_id)

    preset = get_preset(req.preset_name) if req.preset_name else None
    if req.preset_name and preset is None:
        raise HTTPException(status_code=404, detail=f"Preset '{req.preset_name}' not found")

    p = preset
    pitch = (
        req.pitch_shift_semitones
        if req.pitch_shift_semitones is not None
        else (p.pitch_shift_semitones if p else 0.0)
    )
    formant = (
        req.formant_shift if req.formant_shift is not None else (p.formant_shift if p else 1.0)
    )
    resonance = req.resonance_hz if req.resonance_hz is not None else (p.resonance_hz if p else 0.0)
    octave = req.octave_offset if req.octave_offset is not None else (p.octave_offset if p else 0.0)
    filters = list(p.active_filters) if p else []

    out_b64, bytes_len, latency_ms = None, 0, 0.5
    if req.audio_base64:
        try:
            in_bytes = base64.b64decode(req.audio_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid audio_base64 encoding") from None

        pipeline_filter = StreamPipelineFilter(preset=preset)
        pipeline_filter.configure(pitch, formant, resonance, octave, req.enabled)
        out_pcm, _, latency_ms = pipeline_filter.process_frame(
            in_bytes, sample_rate=req.sample_rate
        )
        out_b64, bytes_len = base64.b64encode(out_pcm).decode("ascii"), len(out_pcm)

    preset_title = preset.name if preset else (req.preset_name or "Custom")
    await coord.apply_vocal_preset(
        req.session_id,
        req.peer_id,
        preset_title,
        pitch_shift_semitones=pitch,
        formant_shift=formant,
        resonance_hz=resonance,
        octave_offset=octave,
        reverb_wet=preset.reverb_wet if preset else 0.0,
        active_filters=filters,
        user_id=user_id,
    )
    if not req.enabled:
        await coord.toggle_voice_filter(
            req.session_id,
            req.peer_id,
            preset_title,
            enabled=False,
            parameters={"pitch": pitch, "formant": formant},
            user_id=user_id,
        )

    return ModulateVoiceResponse(
        session_id=req.session_id,
        peer_id=req.peer_id,
        preset_name=preset_title if (preset or req.preset_name) else None,
        pitch_shift_semitones=pitch,
        formant_shift=formant,
        resonance_hz=resonance,
        octave_offset=octave,
        active_filters=filters,
        audio_base64=out_b64,
        audio_bytes_length=bytes_len,
        latency_ms=round(latency_ms, 2),
    )


__all__ = ["ModulateVoiceRequest", "ModulateVoiceResponse", "router"]
