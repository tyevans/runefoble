"""Valuation rules, DC evaluation, and dialogue barks for merchant haggling.

Part of TASK-0262 / PRD-0024 / US-0075.
Governed by ADR-0002, ADR-0006, and ADR-0012.
"""

from __future__ import annotations

import random

from game_session.settlement.haggling_models import (
    GambitEvaluationResult,
    GambitType,
    MerchantTemperament,
)


def evaluate_gambit(
    gambit_raw: str,
    original_price: int,
    current_offer: int,
    counter_price: int,
    temperament_raw: str,
    patience: int,
    mood_score: float,
    charisma_mod: int = 0,
    explicit_roll: int | None = None,
) -> GambitEvaluationResult:
    """Evaluate a player's bargaining gambit against merchant DC and temperament."""
    gambit = GambitType.normalize(gambit_raw)
    temperament = MerchantTemperament.normalize(temperament_raw)

    # Base DC by temperament
    base_dcs = {
        MerchantTemperament.GENEROUS: 10,
        MerchantTemperament.VAIN: 13,
        MerchantTemperament.GREEDY: 14,
        MerchantTemperament.STUBBORN: 15,
    }
    target_dc = base_dcs.get(temperament, 14)

    # Gambit-specific temperament affinity modifiers
    if gambit == GambitType.FLATTERY:
        if temperament == MerchantTemperament.VAIN:
            target_dc -= 4
        elif temperament == MerchantTemperament.STUBBORN:
            target_dc += 1
    elif gambit == GambitType.BULK_ORDER_PROMISE:
        if temperament == MerchantTemperament.GREEDY:
            target_dc -= 4
    elif gambit == GambitType.POINT_OUT_FLAW:
        if temperament in (MerchantTemperament.VAIN, MerchantTemperament.STUBBORN):
            target_dc += 3
    elif gambit == GambitType.HARD_INTIMIDATION:
        if temperament == MerchantTemperament.STUBBORN:
            target_dc += 2
        elif temperament == MerchantTemperament.GENEROUS:
            target_dc -= 2
    elif gambit == GambitType.WALK_AWAY_BLUFF and temperament == MerchantTemperament.GREEDY:
        target_dc -= 1

    # Mood modifies DC: -1 DC per 10 positive mood, +1 DC per 10 negative mood
    mood_dc_adjustment = int(-mood_score / 10.0)
    target_dc = max(6, min(25, target_dc + mood_dc_adjustment))

    # Evaluate roll
    d20 = random.randint(1, 20) if explicit_roll is None else explicit_roll
    roll_total = d20 + charisma_mod
    is_success = roll_total >= target_dc

    gap = max(0, counter_price - current_offer)
    new_patience = patience
    new_mood = mood_score
    status = "active"

    if is_success:
        if gambit == GambitType.HARD_INTIMIDATION:
            price_delta = max(1, int(gap * 0.50))
            patience_delta = 0
            mood_delta = -5.0
            bark = "Fine, fine! Lower your weapon. Take it at that price and be on your way!"
        elif gambit == GambitType.BULK_ORDER_PROMISE:
            price_delta = max(1, int(gap * 0.45))
            patience_delta = 1 if temperament == MerchantTemperament.GREEDY else 0
            mood_delta = 8.0
            bark = "A recurring contract? Now that's music to my ears. I can shave the margin down."
        elif gambit == GambitType.FLATTERY:
            price_delta = max(1, int(gap * 0.35))
            patience_delta = 1 if temperament == MerchantTemperament.VAIN else 0
            mood_delta = 10.0
            bark = "You have an eye for true artisan craft, traveler. I can part with it for less."
        elif gambit == GambitType.POINT_OUT_FLAW:
            price_delta = max(1, int(gap * 0.40))
            patience_delta = 0
            mood_delta = 2.0
            bark = "An astute eye... You caught that seam. Fair enough, I'll reduce the tag."
        else:  # WALK_AWAY_BLUFF
            price_delta = max(1, int(gap * 0.60))
            patience_delta = 0
            mood_delta = 3.0
            bark = "Wait, don't leave just yet! Let's reach an accord before you walk out the door."

        new_counter = max(current_offer, counter_price - price_delta)
    else:
        price_delta = 0
        if gambit == GambitType.HARD_INTIMIDATION:
            patience_delta = -2
            mood_delta = -20.0
            bark = "You dare threaten me under my own roof?! Guards are one whistle away!"
        elif gambit == GambitType.POINT_OUT_FLAW:
            patience_delta = (
                -2
                if temperament in (MerchantTemperament.VAIN, MerchantTemperament.STUBBORN)
                else -1
            )
            mood_delta = -15.0
            bark = "Flaw?! That is masterwork craftsmanship! How dare you insult my wares!"
        elif gambit == GambitType.FLATTERY:
            patience_delta = -1
            mood_delta = -3.0
            bark = "Flattery won't fill my coinpurse, friend. The price is firm."
        elif gambit == GambitType.BULK_ORDER_PROMISE:
            patience_delta = -1
            mood_delta = -5.0
            bark = "Empty promises of future coin don't pay the ironworks guild today."
        else:  # WALK_AWAY_BLUFF
            patience_delta = -1
            mood_delta = -8.0
            bark = "Go on then, walk! You won't find honest steel like this anywhere else."

        new_counter = counter_price

    new_patience = max(0, min(5, patience + patience_delta))
    new_mood = max(-50.0, min(50.0, mood_score + mood_delta))

    if new_counter <= current_offer:
        status = "completed"
        bark = f"Sold! Take the item for {current_offer} gold. A hard bargain well struck."
    elif new_patience <= 0:
        status = "refused"
        bark = "My patience is at its end. Take the original price or get out of my shop!"

    return GambitEvaluationResult(
        gambit=gambit,
        roll_value=roll_total,
        target_dc=target_dc,
        is_success=is_success,
        price_delta=price_delta,
        new_offer=current_offer,
        counter_price=new_counter,
        patience_delta=patience_delta,
        new_patience=new_patience,
        mood_delta=mood_delta,
        new_mood_score=new_mood,
        voice_bark=bark,
        status=status,
    )
