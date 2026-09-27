# Reference: Tavern Minigames & Merchant Haggling Events

This reference details the domain events, aggregates, and REST interfaces introduced for Tavern Minigames (Liar's Dice, Drinking Contests, Card Duels) and Personality-Driven Merchant Haggling (TASK-0103 / PRD-0014 / US-0047).

## Domain Events (`runefoble_events.tavern`)

All events subclass `BaseRunefobleEvent` and are CloudEvents 1.0-compliant.

### 1. `MinigameStarted`
- **Topic**: `runefoble.events.tavern`
- **Aggregate Type**: `TavernGame`
- **Payload Fields**:
  - `game_id`: UUID | str — Minigame match identifier.
  - `session_id`: Optional[UUID] — Active game session.
  - `campaign_id`: Optional[UUID] — Campaign context.
  - `game_type`: str — `liars_dice`, `card_duel`, or `drinking_contest`.
  - `wager_gold`: int — Gold pieces wagered per participant.
  - `initiator_id`: str — Challenging player or character.
  - `challenger_id`: str — Opposing participant or NPC.
  - `state_summary`: Dict[str, Any] — Initial rolls, hands, and intoxication meters.

### 2. `MinigameTurnTaken`
- **Topic**: `runefoble.events.tavern`
- **Aggregate Type**: `TavernGame`
- **Payload Fields**:
  - `game_id`: UUID | str — Minigame match identifier.
  - `session_id`: Optional[UUID] — Active game session.
  - `turn_number`: int — Turn count.
  - `actor_id`: str — Participant taking the action.
  - `action_type`: str — `bid`, `challenge`, `play_card`, or `drink`.
  - `action_payload`: Dict[str, Any] — Action parameters (bid quantity, face value, con roll).
  - `resulting_state`: Dict[str, Any] — Match state snapshot.
  - `voice_bark`: Optional[str] — In-character reactive voice bark.

### 3. `MinigameEnded`
- **Topic**: `runefoble.events.tavern`
- **Aggregate Type**: `TavernGame`
- **Payload Fields**:
  - `game_id`: UUID | str — Minigame match identifier.
  - `winner_id`: Optional[str] — Victorious participant.
  - `loser_id`: Optional[str] — Defeated participant.
  - `wager_gold`: int — Initial wager amount.
  - `payout`: int — Total gold credited to winner.
  - `voice_bark`: Optional[str] — Victory voice bark.
  - `summary`: str — Summary narration.

### 4. `IntoxicationLevelChanged`
- **Topic**: `runefoble.events.tavern`
- **Aggregate Type**: `TavernGame`
- **Payload Fields**:
  - `game_id`: UUID | str — Minigame match identifier.
  - `character_id`: str — Participant consuming beverage.
  - `intoxication_level`: str — `sober`, `tipsy`, `drunk`, `smashed`, or `blackout`.
  - `constitution_dc`: int — Escalating DC check.
  - `consecutive_drinks`: int — Total drinks consumed.
  - `dsp_filters`: List[str] — Active DSP affliction filters (e.g. `["drunk"]`).

### 5. `HagglingNegotiated`
- **Topic**: `runefoble.events.tavern`
- **Aggregate Type**: `Merchant`
- **Payload Fields**:
  - `merchant_id`: str — NPC merchant identifier.
  - `session_id`: Optional[UUID] — Active game session.
  - `campaign_id`: Optional[UUID] — Campaign context.
  - `character_id`: str — Player bargaining with merchant.
  - `item_name`: str — Target trade good.
  - `base_price`: int — Initial quoted price in gold.
  - `offered_price`: int — Player's counter-offer.
  - `counter_price`: Optional[int] — Merchant counter quote.
  - `agreed_price`: Optional[int] — Final negotiated price.
  - `merchant_mood`: str — `stubborn_greedy`, `shrewd`, `generous`, `hostile`, `gullible`.
  - `mood_score`: float — Dynamic mood meter (-50.0 to +50.0).
  - `outcome`: str — `accepted`, `countered`, `rejected`, or `insulted`.
  - `dialogue`: str — Persuasion dialogue submitted by player.
  - `voice_bark`: Optional[str] — Merchant in-character voice line.

---

## Public REST Endpoints

| Endpoint | Method | Service | Zanzibar Permission | Description |
|---|---|---|---|---|
| `/api/v1/sessions/{id}/tavern/games` | `POST` | `game_session` / `gateway` | `campaign:play` | Initiates minigame with secret hands and gold pot. |
| `/api/v1/sessions/{id}/tavern/games/{gid}/turn` | `POST` | `game_session` | `session:participate` | Submits bid, calls bluff, or rolls drinking save. |
| `/api/v1/sessions/{id}/tavern/games/{gid}` | `GET` | `game_session` | `session:participate` | Retrieves live minigame state machine status. |
| `/api/v1/sessions/{id}/merchants/{mid}/haggle` | `POST` | `game_session` / `gateway` | `campaign:play` | Evaluates charisma, mood, and computes counter-quote. |
| `/api/v1/merchants/{mid}` | `GET` | `game_session` | — | Queries merchant temperament and negotiation record. |

---

## Microfrontend Component

- **Tag**: `<runefoble-tavern-parlor>`
- **Package**: `@runefoble/game-session-ui`
- **Manifest**: Advertised via `GET /ui/manifest` on `game_session`.
- **Custom Events**:
  - `minigame-turn-taken`: Emitted on bid placement (`action`, `quantity`, `face`).
  - `liars-dice-challenged`: Emitted on bluff call (`challengerId`, `currentBid`).
  - `drink-taken`: Emitted on drinking round (`drinksConsumed`, `intoxicationLevel`, `dspActive`).
  - `haggling-submitted`: Emitted on bargain submit (`basePrice`, `offeredPrice`, `counterOffer`).
