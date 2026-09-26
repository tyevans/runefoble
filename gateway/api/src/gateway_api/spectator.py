"""Spectator Stream Overlay models and state sanitization for Runefoble Gateway API.

Filters out private DM tools, hidden tokens, monster stat blocks, and secret notes
to deliver a clean, audience-safe spectator view for live streams and OBS sources.
"""

from typing import Any

from pydantic import BaseModel, Field


class SpectatorToken(BaseModel):
    """Sanitized token representation for spectator screens."""

    id: str
    name: str
    x: int
    y: int
    conditions: list[str] = Field(default_factory=list)
    color: str | None = None
    is_ai_controlled: bool = False


class SpectatorSceneAtmosphere(BaseModel):
    """Active scene sensory atmosphere and ambient audio prompts."""

    location_name: str
    lighting: str
    mood: str
    description: str
    ambient_audio_prompt: str | None = None


class SpectatorChronicleMessage(BaseModel):
    """Public narrative chronicle entry for spectators."""

    id: str
    speaker: str
    text: str
    timestamp: str
    action_type: str = "speech"


class SpectatorViewerInfo(BaseModel):
    """Connected spectator viewer identity."""

    viewer_id: str
    viewer_name: str


class SpectatorStateResponse(BaseModel):
    """Sanitized campaign session state tailored for spectator stream overlays."""

    session_id: str
    status: str = "active"
    round: int = 1
    cols: int = 8
    rows: int = 8
    tokens: list[SpectatorToken] = Field(default_factory=list)
    atmosphere: SpectatorSceneAtmosphere | None = None
    chronicle: list[SpectatorChronicleMessage] = Field(default_factory=list)
    viewer: SpectatorViewerInfo | None = None


# Session registry for dynamic test fixtures and live state overrides
_RAW_SESSION_STORE: dict[str, dict[str, Any]] = {}


def set_raw_session_state(session_id: str, state: dict[str, Any]) -> None:
    """Register or override raw session state for testing or live caching."""
    _RAW_SESSION_STORE[session_id] = state


def clear_raw_session_state(session_id: str | None = None) -> None:
    """Clear session registry."""
    if session_id:
        _RAW_SESSION_STORE.pop(session_id, None)
    else:
        _RAW_SESSION_STORE.clear()


def get_default_raw_state(session_id: str) -> dict[str, Any]:
    """Default raw session state containing both public elements and secret GM data."""
    return {
        "session_id": session_id,
        "status": "active",
        "round": 3,
        "cols": 8,
        "rows": 8,
        "tokens": [
            {
                "id": "t1",
                "name": "Valeros",
                "x": 2,
                "y": 3,
                "color": "#2563eb",
                "conditions": ["blessed"],
                "hp": 45,
                "max_hp": 45,
                "ac": 18,
                "dm_notes": "Carrying secret potion of speed.",
            },
            {
                "id": "t2",
                "name": "Kyra",
                "x": 3,
                "y": 3,
                "color": "#db2777",
                "conditions": ["drunk (missed session)"],
                "is_ai_controlled": True,
                "hp": 28,
                "max_hp": 32,
                "ac": 16,
            },
            {
                "id": "t_hidden_1",
                "name": "Goblin Stalker",
                "x": 6,
                "y": 2,
                "hidden": True,
                "hp": 12,
                "max_hp": 12,
                "stat_block": {"cr": "1/2", "ac": 13, "stealth": "+6"},
                "dm_notes": "Lurking in shadows ready to ambush frontline.",
            },
            {
                "id": "t_secret_1",
                "name": "Mimic Chest",
                "x": 5,
                "y": 5,
                "is_secret": True,
                "hp": 58,
                "max_hp": 58,
                "dm_notes": "Adhesive pseudopod ready.",
            },
        ],
        "dm_notes": "Secret GM encounter notes: Trap at (4,4), DC 15 Dex save or 3d6 poison.",
        "monster_stat_blocks": {
            "goblin_stalker": {"cr": "1/2", "hp": 12, "ac": 13},
            "mimic": {"cr": "2", "hp": 58, "ac": 12},
        },
        "atmosphere": {
            "location_name": "Tomb of the Star-Eater - Crypt Antechamber",
            "lighting": "Dim cold luminescence from weeping wall runes",
            "mood": "Suspenseful",
            "description": "Ancient stone sarcophagi line the chamber walls. A bone-chilling draft stirs dry shrouds.",
            "ambient_audio_prompt": "hollow stone reverberations, distant faint whispers, cold draft",
            "private_dm_lore": "The crypt actually belonged to Queen Sorshen's vizier.",
        },
        "chronicle": [
            {
                "id": "c1",
                "speaker": "Valeros",
                "text": "I shield my eyes and peer into the shadowed corridor.",
                "timestamp": "2026-09-25T20:15:00Z",
                "action_type": "speech",
            },
            {
                "id": "c2",
                "speaker": "The Watcher",
                "text": "The shadows stretch unnaturally as you step toward the rune-carved archway.",
                "timestamp": "2026-09-25T20:15:10Z",
                "action_type": "dm_ruling",
            },
            {
                "id": "c_secret",
                "speaker": "The Watcher (Private Note)",
                "text": "DC 15 trap triggered check failed secretly.",
                "timestamp": "2026-09-25T20:15:12Z",
                "is_private": True,
            },
        ],
    }


def get_raw_session_state(session_id: str) -> dict[str, Any]:
    """Retrieve raw session state from registry or generate default."""
    if session_id in _RAW_SESSION_STORE:
        return _RAW_SESSION_STORE[session_id]
    return get_default_raw_state(session_id)


def sanitize_spectator_state(
    raw_state: dict[str, Any],
    viewer_info: SpectatorViewerInfo | None = None,
) -> dict[str, Any]:
    """Strictly sanitize raw game state for spectator stream overlay.

    Rules:
    1. Filter out hidden tokens (hidden=True, is_secret=True, is_hidden=True, secret=True).
    2. Redact monster stat blocks, hp, ac, dm_notes from tokens (only keep id, name, x, y, conditions, color, is_ai_controlled).
    3. Redact private DM notes, secret encounters, monster stat blocks from root state.
    4. Strip secret/private chronicle messages.
    5. Cleanse atmosphere of private DM lore.
    """
    session_id = raw_state.get("session_id") or raw_state.get("id") or "session_default"
    status = raw_state.get("status", "active")
    round_num = raw_state.get("round", 1)

    # Resolve grid dimensions
    board_data = raw_state.get("board", {})
    cols = raw_state.get("cols") or board_data.get("cols") or 8
    rows = raw_state.get("rows") or board_data.get("rows") or 8

    # Extract tokens from raw_state or raw_state['board']['tokens']
    raw_tokens = raw_state.get("tokens") or board_data.get("tokens") or []
    if isinstance(raw_tokens, dict):
        raw_tokens = list(raw_tokens.values())

    sanitized_tokens: list[dict[str, Any]] = []
    for tok in raw_tokens:
        tok_dict = tok if isinstance(tok, dict) else tok.model_dump()
        # 1. Filter out hidden/secret tokens
        is_hidden = (
            bool(tok_dict.get("hidden"))
            or bool(tok_dict.get("is_secret"))
            or bool(tok_dict.get("is_hidden"))
            or bool(tok_dict.get("secret"))
        )
        if is_hidden:
            continue

        # 2. Extract visible spectator fields only (strip hp, stat_block, dm_notes, ac, cr)
        conditions = tok_dict.get("conditions", [])
        if isinstance(conditions, list):
            clean_conditions = [str(c) if not isinstance(c, dict) else str(c.get("name", "")) for c in conditions]
        else:
            clean_conditions = []

        sanitized_tok = {
            "id": str(tok_dict.get("id", "")),
            "name": str(tok_dict.get("name", "Unknown")),
            "x": int(tok_dict.get("x", 0)),
            "y": int(tok_dict.get("y", 0)),
            "conditions": clean_conditions,
            "color": tok_dict.get("color"),
            "is_ai_controlled": bool(tok_dict.get("is_ai_controlled", False)),
        }
        sanitized_tokens.append(sanitized_tok)

    # 3. Clean atmosphere
    raw_atmosphere = raw_state.get("atmosphere") or raw_state.get("scene") or {}
    sanitized_atmosphere: dict[str, Any] | None = None
    if raw_atmosphere and isinstance(raw_atmosphere, dict):
        sanitized_atmosphere = {
            "location_name": raw_atmosphere.get("location_name", "Unknown Location"),
            "lighting": raw_atmosphere.get("lighting", "Normal"),
            "mood": raw_atmosphere.get("mood", "Neutral"),
            "description": raw_atmosphere.get("description", ""),
            "ambient_audio_prompt": raw_atmosphere.get("ambient_audio_prompt"),
        }

    # 4. Clean chronicle (public messages only)
    raw_chronicle = raw_state.get("chronicle", [])
    if isinstance(raw_chronicle, dict):
        raw_chronicle = raw_chronicle.get("messages", [])

    sanitized_chronicle: list[dict[str, Any]] = []
    for item in raw_chronicle:
        item_dict = item if isinstance(item, dict) else item.model_dump()
        if item_dict.get("is_private") or item_dict.get("private"):
            continue
        sanitized_chronicle.append(
            {
                "id": str(item_dict.get("id", "")),
                "speaker": str(item_dict.get("speaker", "The Watcher")),
                "text": str(item_dict.get("text", "")),
                "timestamp": str(item_dict.get("timestamp", "")),
                "action_type": str(item_dict.get("action_type", "speech")),
            }
        )

    response = {
        "session_id": str(session_id),
        "status": status,
        "round": int(round_num),
        "cols": int(cols),
        "rows": int(rows),
        "tokens": sanitized_tokens,
        "atmosphere": sanitized_atmosphere,
        "chronicle": sanitized_chronicle,
    }
    if viewer_info:
        response["viewer"] = viewer_info.model_dump()

    return response
