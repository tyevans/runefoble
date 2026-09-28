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

### 6. `NegotiationSessionStarted`
- **Topic**: `runefoble.events.tavern`, `runefoble.events.west_marches`
- **Aggregate Type**: `Negotiation`
- **Payload Fields**: `negotiation_id`, `character_id`, `item_id`, `item_name`, `original_price`, `current_offer`, `counter_price`, `patience`, `temperament`.

### 7. `GambitExecuted`
- **Topic**: `runefoble.events.tavern`, `runefoble.events.west_marches`
- **Aggregate Type**: `Negotiation`
- **Payload Fields**: `negotiation_id`, `character_id`, `gambit`, `roll_value`, `target_dc`, `is_success`, `new_offer`, `counter_price`, `patience_delta`, `new_patience`, `voice_bark`.

### 8. `DMNegotiationOverridden`
- **Topic**: `runefoble.events.tavern`, `runefoble.events.west_marches`
- **Aggregate Type**: `Negotiation`
- **Payload Fields**: `negotiation_id`, `dm_user_id`, `action`, `new_patience`, `override_price`, `narrative_bark`, `status`.

### 9. `NegotiationConcluded`
- **Topic**: `runefoble.events.tavern`, `runefoble.events.west_marches`
- **Aggregate Type**: `Negotiation`
- **Payload Fields**: `negotiation_id`, `character_id`, `item_id`, `final_price`, `status`, `currency_deducted`, `closing_bark`.

---

## Public REST Endpoints

| Endpoint | Method | Service | Zanzibar Permission | Description |
|---|---|---|---|---|
| `/api/v1/sessions/{id}/tavern/games` | `POST` | `game_session` / `gateway` | `campaign:play` | Initiates minigame with secret hands and gold pot. |
| `/api/v1/sessions/{id}/tavern/games/{gid}/turn` | `POST` | `game_session` | `session:participate` | Submits bid, calls bluff, or rolls drinking save. |
| `/api/v1/sessions/{id}/tavern/games/{gid}` | `GET` | `game_session` | `session:participate` | Retrieves live minigame state machine status. |
| `/api/v1/sessions/{id}/merchants/{mid}/haggle` | `POST` | `game_session` / `gateway` | `campaign:play` | Evaluates charisma, mood, and computes counter-quote. |
| `/api/v1/merchants/{mid}` | `GET` | `game_session` | — | Queries merchant temperament and negotiation record. |
| `/api/v1/establishments/{id}/haggle` | `POST` | `game_session` | `establishment:view` | Starts interactive bartering encounter within establishment. |
| `/api/v1/haggling/{id}/gambit` | `POST` | `game_session` | `negotiation:participate` | Executes bargaining gambit (flattery, bulk, flaw, intimidate, bluff). |
| `/api/v1/haggling/{id}/dm-override` | `PATCH` | `game_session` | `negotiation:arbitrate` | Real-time DM controls: soothe, enrage, accept deal, kick out. |
| `/api/v1/haggling/{id}` | `GET` | `game_session` | `negotiation:view` | Live negotiation state, patience meter, and dialogue history. |

---

## Microfrontend Components

### `<runefoble-tavern-parlor>`
- **Tag**: `<runefoble-tavern-parlor>`
- **Package**: `@runefoble/game-session-ui`
- **Manifest**: Advertised via `GET /ui/manifest` on `game_session`.
- **Custom Events**: `minigame-turn-taken`, `liars-dice-challenged`, `drink-taken`, `haggling-submitted`.

### `<runefoble-merchant-haggler>`
- **Tag**: `<runefoble-merchant-haggler>`
- **Package**: `@runefoble/game-session-ui`
- **Features**: Price tug-of-war meter, patience pip gauge (1-5), gambit selection cards, dialogue bark bubble.
- **Custom Events**: `gambit-executed`, `offer-accepted`.

### `<runefoble-dm-negotiation-drawer>`
- **Tag**: `<runefoble-dm-negotiation-drawer>`
- **Package**: `@runefoble/game-session-ui`
- **Features**: Live telemetry bar, one-click mood modifiers (soothe, enrage, accept, refuse), custom in-character bark injection.
- **Custom Events**: `dm-override`.

