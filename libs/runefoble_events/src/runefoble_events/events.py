"""Event models for Runefoble reactive gameplay and real-time storytelling."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
import uuid
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseRunefobleEvent(BaseModel):
    """Base event payload adhering to CloudEvent principles."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=utc_now_iso)
    campaign_id: str
    session_id: str
    event_type: str


class PlayerSpokeEvent(BaseRunefobleEvent):
    """Event emitted when a player or voice stream is transcribed."""

    event_type: Literal["player.spoke"] = "player.spoke"
    speaker_id: str
    speaker_name: str
    transcript: str
    is_whisper: bool = False
    target_character_id: Optional[str] = None


class WatcherNarrationEvent(BaseRunefobleEvent):
    """Event emitted when The Watcher AI acts as Game Master or responds."""

    event_type: Literal["watcher.narration"] = "watcher.narration"
    narrative_text: str
    tone: str = "mysterious"
    audio_stream_url: Optional[str] = None
    applied_board_mutations: List[Dict[str, Any]] = Field(default_factory=list)


class BoardMoveEvent(BaseRunefobleEvent):
    """Event emitted when a token is repositioned on the tactical board."""

    event_type: Literal["board.move"] = "board.move"
    token_id: str
    character_name: str
    from_x: int
    from_y: int
    to_x: int
    to_y: int
    initiated_by: Literal["player", "the_watcher", "stand_in"]


class DiceRollEvent(BaseRunefobleEvent):
    """Event emitted when dice are cast."""

    event_type: Literal["game.dice_roll"] = "game.dice_roll"
    roller_name: str
    dice_notation: str
    individual_rolls: List[int]
    modifier: int = 0
    total: int
    reason: str


class SessionPenaltyEvent(BaseRunefobleEvent):
    """Event emitted when a missing player's PC is assigned an absent penalty."""

    event_type: Literal["session.penalty_applied"] = "session.penalty_applied"
    character_id: str
    character_name: str
    penalty_type: Literal["drunk", "foolishness", "cowardice", "greed", "curse"]
    description: str
    imposed_by: Literal["human_dm", "the_watcher"]
