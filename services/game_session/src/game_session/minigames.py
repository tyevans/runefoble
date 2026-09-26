"""Tavern Minigames Aggregate powered by eventsource-py.

Governed by Hard Invariant 2: Domain state transitions flow strictly through
DeclarativeAggregate subclasses with @handles methods.
"""

from __future__ import annotations

import random
from typing import Any
from uuid import uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.minigame_rules import (
    PIRATE_BLUFF_BARKS,
    apply_tavern_voice_dsp,
    compute_intoxication_progression,
    resolve_liars_dice_challenge,
    roll_dice_hand,
    to_opt_uuid,
    to_uuid,
    validate_liars_dice_bid,
)
from pydantic import BaseModel, Field
from runefoble_events.tavern import (
    IntoxicationLevelChanged,
    MinigameEnded,
    MinigameStarted,
    MinigameTurnTaken,
)


class TavernGameState(BaseModel):
    """Event-sourced state machine for tavern minigames."""

    game_id: str = ""
    session_id: str | None = None
    campaign_id: str | None = None
    game_type: str = "liars_dice"  # liars_dice, card_duel, drinking_contest
    wager_gold: int = 0
    initiator_id: str = ""
    challenger_id: str = ""
    current_turn_actor: str = ""
    turn_number: int = 1
    status: str = "pending"  # active, completed
    winner_id: str | None = None
    loser_id: str | None = None
    payout: int = 0
    current_bid: dict[str, Any] | None = None
    player_hands: dict[str, list[int]] = Field(default_factory=dict)
    intoxication_levels: dict[str, str] = Field(default_factory=dict)
    consecutive_drinks: dict[str, int] = Field(default_factory=dict)
    dsp_filters: dict[str, list[str]] = Field(default_factory=dict)
    last_voice_bark: str | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)


class TavernGameAggregate(DeclarativeAggregate[TavernGameState]):
    """Event-sourced aggregate managing Liar's Dice, card tournaments, and drinking contests."""

    aggregate_type = "TavernGame"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        agg_uuid = to_uuid(aggregate_id) if aggregate_id else uuid4()
        super().__init__(aggregate_id=agg_uuid, **kwargs)
        if self._state is None:
            self._state = TavernGameState(game_id=str(aggregate_id or agg_uuid))

    @handles(MinigameStarted)
    def handle_started(self, event: MinigameStarted) -> None:
        self.state.game_id = str(event.game_id or event.aggregate_id)
        self.state.session_id = str(event.session_id) if event.session_id else None
        self.state.campaign_id = str(event.campaign_id) if event.campaign_id else None
        self.state.game_type = event.game_type
        self.state.wager_gold = event.wager_gold
        self.state.initiator_id = event.initiator_id
        self.state.challenger_id = event.challenger_id
        self.state.current_turn_actor = event.initiator_id
        self.state.status = "active"
        self.state.player_hands = event.state_summary.get("player_hands", {})
        self.state.intoxication_levels = event.state_summary.get(
            "intoxication_levels",
            {event.initiator_id: "sober", event.challenger_id: "sober"},
        )
        self.state.consecutive_drinks = event.state_summary.get(
            "consecutive_drinks",
            {event.initiator_id: 0, event.challenger_id: 0},
        )

    @handles(MinigameTurnTaken)
    def handle_turn_taken(self, event: MinigameTurnTaken) -> None:
        self.state.turn_number = event.turn_number + 1
        self.state.last_voice_bark = event.voice_bark
        if event.action_type == "bid":
            self.state.current_bid = event.action_payload
            self.state.current_turn_actor = (
                self.state.challenger_id
                if event.actor_id == self.state.initiator_id
                else self.state.initiator_id
            )
        self.state.history.append(
            {
                "turn": event.turn_number,
                "actor": event.actor_id,
                "action": event.action_type,
                "payload": event.action_payload,
            }
        )

    @handles(MinigameEnded)
    def handle_ended(self, event: MinigameEnded) -> None:
        self.state.status = "completed"
        self.state.winner_id = event.winner_id
        self.state.loser_id = event.loser_id
        self.state.payout = event.payout
        self.state.last_voice_bark = event.voice_bark

    @handles(IntoxicationLevelChanged)
    def handle_intoxication(self, event: IntoxicationLevelChanged) -> None:
        self.state.intoxication_levels[event.character_id] = event.intoxication_level
        self.state.dsp_filters[event.character_id] = event.dsp_filters
        self.state.consecutive_drinks[event.character_id] = event.consecutive_drinks

    def start_game(
        self,
        game_id: str,
        game_type: str,
        wager_gold: int,
        initiator_id: str,
        challenger_id: str,
        session_id: str | None = None,
        campaign_id: str | None = None,
    ) -> dict[str, Any]:
        """Start a new tavern minigame with secret initial hands."""
        player_hands: dict[str, list[int]] = {}
        if game_type == "liars_dice":
            player_hands = {
                initiator_id: roll_dice_hand(5),
                challenger_id: roll_dice_hand(5),
            }

        state_summary = {
            "player_hands": player_hands,
            "intoxication_levels": {initiator_id: "sober", challenger_id: "sober"},
            "consecutive_drinks": {initiator_id: 0, challenger_id: 0},
        }

        self.create_event(
            MinigameStarted,
            game_id=to_uuid(game_id),
            session_id=to_opt_uuid(session_id),
            campaign_id=to_opt_uuid(campaign_id),
            game_type=game_type,
            wager_gold=wager_gold,
            initiator_id=initiator_id,
            challenger_id=challenger_id,
            state_summary=state_summary,
        )
        return state_summary

    def submit_bid(self, actor_id: str, quantity: int, face: int) -> dict[str, Any]:
        """Submit a Liar's Dice bid advancing the game state."""
        if self.state.status != "active":
            raise ValueError("Game is not active")
        if self.state.current_turn_actor and actor_id != self.state.current_turn_actor:
            raise ValueError(f"Not {actor_id}'s turn to bid")
        if not validate_liars_dice_bid(self.state.current_bid, quantity, face):
            raise ValueError(
                f"Invalid bid ({quantity}x {face}). Must exceed previous bid: {self.state.current_bid}"
            )

        bark = random.choice(PIRATE_BLUFF_BARKS)
        payload = {"quantity": quantity, "face": face, "bidder": actor_id}
        self.create_event(
            MinigameTurnTaken,
            game_id=to_uuid(self.state.game_id),
            session_id=to_opt_uuid(self.state.session_id),
            turn_number=self.state.turn_number,
            actor_id=actor_id,
            action_type="bid",
            action_payload=payload,
            resulting_state={"current_bid": payload},
            voice_bark=bark,
        )
        return {"bid": payload, "voice_bark": bark}

    def call_challenge(self, challenger_id: str) -> dict[str, Any]:
        """Challenge the active bid in Liar's Dice ('Call Bluff' / 'Liar!')."""
        if self.state.status != "active":
            raise ValueError("Game is not active")
        if not self.state.current_bid:
            raise ValueError("No active bid to challenge")

        resolution = resolve_liars_dice_challenge(
            self.state.current_bid, self.state.player_hands, challenger_id
        )
        payout = self.state.wager_gold * 2

        self.create_event(
            MinigameTurnTaken,
            game_id=to_uuid(self.state.game_id),
            session_id=to_opt_uuid(self.state.session_id),
            turn_number=self.state.turn_number,
            actor_id=challenger_id,
            action_type="challenge",
            action_payload={"challenged_bid": self.state.current_bid},
            resulting_state=resolution,
            voice_bark=resolution["voice_bark"],
        )
        self.create_event(
            MinigameEnded,
            game_id=to_uuid(self.state.game_id),
            session_id=to_opt_uuid(self.state.session_id),
            winner_id=resolution["winner_id"],
            loser_id=resolution["loser_id"],
            wager_gold=self.state.wager_gold,
            payout=payout,
            voice_bark=resolution["voice_bark"],
            summary=f"Liar's Dice finished. {resolution['winner_id']} won {payout} gold!",
        )
        return {**resolution, "payout": payout}

    def take_drink(
        self,
        character_id: str,
        con_roll: int | None = None,
        speech_text: str | None = None,
    ) -> dict[str, Any]:
        """Process a round in a drinking contest and apply progressive intoxication."""
        if self.state.status != "active":
            raise ValueError("Contest is not active")

        current_drinks = self.state.consecutive_drinks.get(character_id, 0) + 1
        current_stage = self.state.intoxication_levels.get(character_id, "sober")
        con_dc = 10 + (current_drinks - 1) * 2

        roll = con_roll if con_roll is not None else random.randint(1, 20)
        new_stage, dsp_filters = compute_intoxication_progression(current_stage, roll, con_dc)

        self.create_event(
            IntoxicationLevelChanged,
            game_id=to_uuid(self.state.game_id),
            session_id=to_opt_uuid(self.state.session_id),
            character_id=character_id,
            intoxication_level=new_stage,
            constitution_dc=con_dc,
            consecutive_drinks=current_drinks,
            dsp_filters=dsp_filters,
        )

        dsp_result = None
        if speech_text:
            dsp_result = apply_tavern_voice_dsp(speech_text, new_stage)

        res: dict[str, Any] = {
            "character_id": character_id,
            "drinks_consumed": current_drinks,
            "con_roll": roll,
            "con_dc": con_dc,
            "intoxication_level": new_stage,
            "dsp_filters": dsp_filters,
            "voice_dsp": dsp_result,
        }

        if new_stage == "blackout":
            opponent = (
                self.state.challenger_id
                if character_id == self.state.initiator_id
                else self.state.initiator_id
            )
            self.create_event(
                MinigameEnded,
                game_id=to_uuid(self.state.game_id),
                session_id=to_opt_uuid(self.state.session_id),
                winner_id=opponent,
                loser_id=character_id,
                wager_gold=self.state.wager_gold,
                payout=self.state.wager_gold * 2,
                voice_bark="Timberrr! The contest is over, we have a standing champion!",
                summary=f"{character_id} passed out! {opponent} wins!",
            )
            res["status"] = "completed"
            res["winner_id"] = opponent

        return res


__all__ = ["TavernGameAggregate", "TavernGameState", "to_opt_uuid", "to_uuid"]
