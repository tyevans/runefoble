# How-To: Run Tavern Minigames & Personality-Driven Merchant Haggling

This guide explains how to operate interactive tavern minigames (Liar's Dice wagering, card duels, and drinking contests with dynamic voice DSP effects) and negotiate with personality-driven NPC merchants using dynamic temperament state machines (TASK-0103 / PRD-0014 / US-0047).

---

## 1. Playing Liar's Dice in Town Taverns

Settlement visits feature turn-based bluffing and wagering where players roll secret dice hands under cups and challenge bids.

### Step 1: Challenge an NPC or Player with a Wager

Initiate a game of Liar's Dice via `POST /api/v1/sessions/{session_id}/tavern/games`:

```bash
curl -X POST http://localhost:8004/api/v1/sessions/session-wyvern-01/tavern/games \
  -H "Content-Type: application/json" \
  -d '{
    "game_type": "liars_dice",
    "wager_gold": 10,
    "initiator_id": "char_bram",
    "challenger_id": "npc_pirate"
  }'
```

### Response
```json
{
  "game_id": "game-7f8a9b1c",
  "game_type": "liars_dice",
  "wager_gold": 10,
  "initiator_id": "char_bram",
  "challenger_id": "npc_pirate",
  "current_turn_actor": "char_bram",
  "turn_number": 1,
  "status": "active",
  "player_hands": {
    "char_bram": [2, 3, 3, 5, 6],
    "npc_pirate": [1, 2, 4, 4, 6]
  }
}
```

### Step 2: Make Bids and Call Bluffs

Players alternate raising bids (`quantity` and `face_value`, where 1s are wildcards) or challenging the previous claim:

```bash
# Bram bids two threes:
curl -X POST http://localhost:8004/api/v1/sessions/session-wyvern-01/tavern/games/game-7f8a9b1c/turn \
  -H "Content-Type: application/json" \
  -d '{
    "actor_id": "char_bram",
    "action_type": "bid",
    "quantity": 2,
    "face": 3
  }'

# Pirate raises bid to three fours:
curl -X POST http://localhost:8004/api/v1/sessions/session-wyvern-01/tavern/games/game-7f8a9b1c/turn \
  -H "Content-Type: application/json" \
  -d '{
    "actor_id": "npc_pirate",
    "action_type": "bid",
    "quantity": 3,
    "face": 4
  }'

# Bram calls bluff ('Challenge / Liar!'):
curl -X POST http://localhost:8004/api/v1/sessions/session-wyvern-01/tavern/games/game-7f8a9b1c/turn \
  -H "Content-Type: application/json" \
  -d '{
    "actor_id": "char_bram",
    "action_type": "challenge"
  }'
```

Upon challenge, the aggregate counts matching dice across all hands (including wild 1s), determines the winner, pays out the 20 GP pot, and emits an in-character voice bark.

---

## 2. Drinking Contests & Voice DSP Conditioning

Drinking contests apply escalating Constitution checks and progressive intoxication states (`sober` -> `tipsy` -> `drunk` -> `smashed` -> `blackout`).

### Step 1: Take Drinks and Roll Constitution Saves

```bash
curl -X POST http://localhost:8004/api/v1/sessions/session-wyvern-01/tavern/games/game-drink-01/turn \
  -H "Content-Type: application/json" \
  -d '{
    "actor_id": "char_bram",
    "action_type": "drink",
    "con_roll": 6,
    "speech_text": "I can drink the whole tavern under the table!"
  }'
```

### DSP Conditioning Response
```json
{
  "intoxication_level": "drunk",
  "dsp_filters": ["drunk"],
  "voice_dsp": {
    "original_text": "I can drink the whole tavern under the table!",
    "conditioned_text": "I can dr-drink the whole tavern under the tablesh...",
    "active_filters": ["drunk"],
    "dsp_config": {
      "pitch_shift_semitones": -1.5,
      "vibrato_depth": 0.4,
      "slur_intensity": 0.8,
      "speed_factor": 0.88,
      "hiccup_frequency": 0.25
    }
  }
}
```

When a participant reaches `blackout`, the contest concludes automatically and the surviving participant is crowned champion.

---

## 3. Personality-Driven Merchant Haggling

Shopkeepers possess distinct temperament models that influence price tolerance, counter-offers, and emotional volatility:

| Temperament | Direct Discount Threshold | Counter Behavior | Description |
|---|---|---|---|
| `stubborn_greedy` | 92% (rarely folds directly) | Compromises at ~47% difference | Dwarven smiths who pride their craft |
| `shrewd` | 88% | Balances mid-point offer | Professional merchants and accountants |
| `generous` | 70% | Accepts large discounts | Cheerful innkeepers and elders |
| `hostile` | 95% | Harsh counters or insults | Black-market smugglers and fences |
| `gullible` | 65% | Easily swayed by charisma | Novice apprentices and naive vendors |

### Step 1: Submit Persuasion Dialogue & Counter-Offer

```bash
curl -X POST "http://localhost:8004/api/v1/sessions/session-wyvern-01/merchants/merchant_thorin_blacksmith/haggle?temperament=stubborn_greedy" \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "char_bram",
    "item_name": "Reinforced Shield",
    "base_price": 50,
    "offered_price": 35,
    "charisma_modifier": 3,
    "dialogue": "I am Bram the Tinkerer. Your dwarven steel is legendary, but 35 gold is a fair purse today."
  }'
```

### Response
```json
{
  "merchant_id": "merchant_thorin_blacksmith",
  "temperament": "stubborn_greedy",
  "outcome": "countered",
  "base_price": 50,
  "offered_price": 35,
  "counter_price": 42,
  "agreed_price": 42,
  "mood_score": 6.0,
  "voice_bark": "Dwarven steel doesn't bend for pennies! Meet me at 42 gold, or keep walkin'!"
}
```

---

## 4. Interactive Merchant Haggling Engine & DM Controls (TASK-0262)

The interactive merchant haggling engine provides real-time bartering with a tug-of-war price meter, persuasive bargaining gambits, and Game Master arbitration controls.

### Step 1: Bargaining Gambits
Players choose from five tactical gambits evaluated against the merchant's DC and temperament:
- **Flattery / Praise**: Appeals to artisan pride (exceptional bonus against Vain merchants).
- **Bulk Order Promise**: Promises future recurring orders (exceptional bonus against Greedy merchants).
- **Point Out Flaw**: Scrutinizes visible blemishes; offends Stubborn or Vain merchants on failure.
- **Hard Intimidation**: Aggressive threats; high reward on success, severe patience penalty on failure.
- **Walk Away Bluff**: Feigns disinterest to force a compromise before stepping out the door.

Submit a gambit via `POST /api/v1/haggling/{negotiation_id}/gambit`:
```bash
curl -X POST http://localhost:8004/api/v1/haggling/neg-101/gambit \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "char_nicole",
    "gambit": "bulk_order_promise",
    "roll_value": 18,
    "charisma_modifier": 3
  }'
```

### Step 2: DM Real-Time Arbitration Controls
Game Masters can intervene in live negotiations without halting game flow via `PATCH /api/v1/haggling/{negotiation_id}/dm-override`:
- **Soothe Merchant**: Grants +2 patience and restores morale.
- **Enrage Merchant**: Inflicts -2 patience and triggers indignation barks.
- **Accept Deal**: Forces instant agreement at current offer or override price, concluding transactions with zero race conditions.
- **Refuse & Kick Out**: Immediately ejects the customer and terminates the exchange.

```bash
curl -X PATCH http://localhost:8004/api/v1/haggling/neg-101/dm-override \
  -H "Content-Type: application/json" \
  -H "x-user-id: dm_wyvern_01" \
  -d '{
    "action": "force_accept",
    "override_price_gp": 280,
    "narrative_bark": "Torvin scowls, then nods in begrudging respect. Done."
  }'
```

---

## 5. Web Component & Storybook Verification

Interactive components render with high-contrast Bauhaus tokens and shadow DOM isolation:
- `<runefoble-tavern-parlor>`: Shaker cups, drinking contest meters, and legacy merchant panels.
- `<runefoble-merchant-haggler>`: Responsive tug-of-war price meter, patience pips (1-5), and dialogue cards.
- `<runefoble-dm-negotiation-drawer>`: Live DM arbitration drawer with one-click mood buttons and custom bark injection.

Viewable in Storybook:
- `Minigames/RunefobleMerchantHaggler`: `ActiveNegotiationLight`, `ActiveNegotiationDark`, `LowPatienceWarning`, `CompletedTransaction`.
- `DMControls/RunefobleDMNegotiationDrawer`: `LiveArbitrationLight`, `LiveArbitrationDark`, `DealCompletedDrawer`.

