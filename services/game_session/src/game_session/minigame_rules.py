"""Tavern minigames rules engine for Liar's Dice, cards, and drinking contests.

Part of TASK-0103 / PRD-0014 / US-0047.
"""

from __future__ import annotations

import random
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid5

from voice_agent.dsp import VoiceDSPPipeline


def to_uuid(val: Any) -> UUID:
    """Coerce string/UUID to valid UUID."""
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except Exception:
        return uuid5(NAMESPACE_DNS, str(val))


def to_opt_uuid(val: Any) -> UUID | None:
    """Coerce optional string/UUID to valid UUID."""
    if not val:
        return None
    return to_uuid(val)


INTOXICATION_STAGES: list[str] = ["sober", "tipsy", "drunk", "smashed", "blackout"]

PIRATE_VICTORY_BARKS: list[str] = [
    "By the kraken's beard, fair play! Take yer gold, landlubber!",
    "Ah, ye got sharp eyes and the devil's luck! Well won!",
    "Sink me! You read my dice like an open ledger. Gold is yers!",
]

PIRATE_BLUFF_BARKS: list[str] = [
    "Three fours, and not a pip less! Dare ye call me a liar?",
    "More dice on this deck than stars in the sky! Match that bid!",
    "Ye hesitate, matey! The sea smells fear!",
]


def roll_dice_hand(num_dice: int = 5) -> list[int]:
    """Roll a secret hand of 6-sided dice."""
    return sorted([random.randint(1, 6) for _ in range(num_dice)])


def validate_liars_dice_bid(
    prev_bid: dict[str, int] | None,
    new_quantity: int,
    new_face: int,
) -> bool:
    """Ensure new bid escalates either quantity or face value."""
    if not (1 <= new_face <= 6 and new_quantity >= 1):
        return False
    if not prev_bid:
        return True
    prev_qty = prev_bid["quantity"]
    prev_face = prev_bid["face"]
    return new_quantity > prev_qty or (new_quantity == prev_qty and new_face > prev_face)


def count_matching_dice(all_dice: list[int], target_face: int, ones_wild: bool = True) -> int:
    """Count matching dice across hands with 1s treated as wildcards."""
    if target_face == 1 or not ones_wild:
        return all_dice.count(target_face)
    return all_dice.count(target_face) + all_dice.count(1)


def resolve_liars_dice_challenge(
    current_bid: dict[str, Any],
    all_hands: dict[str, list[int]],
    challenger_id: str,
) -> dict[str, Any]:
    """Resolve a Liar's Dice challenge: counts matching dice and determines winner."""
    all_dice = [die for hand in all_hands.values() for die in hand]
    target_face = current_bid["face"]
    bid_qty = current_bid["quantity"]
    bidder_id = current_bid["bidder"]

    matching_count = count_matching_dice(all_dice, target_face)
    bid_was_truth = matching_count >= bid_qty

    if bid_was_truth:
        winner_id = bidder_id
        loser_id = challenger_id
        bark = (
            f"Truth revealed! Found {matching_count} dice showing {target_face}. {bidder_id} wins!"
        )
    else:
        winner_id = challenger_id
        loser_id = bidder_id
        bark = f"Bluff caught! Only found {matching_count} dice showing {target_face}. {challenger_id} wins!"

    return {
        "matching_count": matching_count,
        "target_face": target_face,
        "bid_quantity": bid_qty,
        "bid_was_truth": bid_was_truth,
        "winner_id": winner_id,
        "loser_id": loser_id,
        "voice_bark": random.choice(PIRATE_VICTORY_BARKS) if winner_id != "npc_pirate" else bark,
        "revealed_hands": all_hands,
    }


def compute_intoxication_progression(
    current_stage: str,
    con_check_roll: int,
    con_dc: int,
) -> tuple[str, list[str]]:
    """Progress character intoxication on failed Constitution check and assign DSP filters."""
    curr_idx = (
        INTOXICATION_STAGES.index(current_stage) if current_stage in INTOXICATION_STAGES else 0
    )
    if con_check_roll >= con_dc:
        new_stage = current_stage
    else:
        new_stage = INTOXICATION_STAGES[min(curr_idx + 1, len(INTOXICATION_STAGES) - 1)]

    dsp_filters: list[str] = []
    if new_stage in ("drunk", "smashed", "blackout"):
        dsp_filters.append("drunk")
    if new_stage in ("smashed", "blackout"):
        dsp_filters.append("slur")

    return new_stage, dsp_filters


def apply_tavern_voice_dsp(text: str, intoxication_stage: str) -> dict[str, Any]:
    """Condition speech through voice DSP pipeline based on intoxication level."""
    pipeline = VoiceDSPPipeline()
    filters = []
    if intoxication_stage in ("drunk", "smashed", "blackout"):
        filters.append("drunk")
    res = pipeline.process(text, filters)
    return {
        "original_text": text,
        "conditioned_text": res.conditioned_text,
        "active_filters": res.active_filters,
        "dsp_config": res.dsp_config.model_dump(),
    }


__all__ = [
    "INTOXICATION_STAGES",
    "PIRATE_BLUFF_BARKS",
    "PIRATE_VICTORY_BARKS",
    "apply_tavern_voice_dsp",
    "compute_intoxication_progression",
    "count_matching_dice",
    "resolve_liars_dice_challenge",
    "roll_dice_hand",
    "to_opt_uuid",
    "to_uuid",
    "validate_liars_dice_bid",
]
