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

### 5. `MerchantCreated`
- **Topic**: `runefoble.events.tavern`
- **Aggregate Type**: `Merchant`
- **Emitted**: Once, when a merchant id is first recorded. It precedes the first `HagglingNegotiated` for that merchant.
- **Payload Fields**:
  - `merchant_id`: str — NPC merchant identifier, as given in the haggle route.
  - `name`: str — Display name. A known temperament sets its default name.
  - `temperament`: str — `stubborn_greedy`, `shrewd`, `generous`, `hostile`, or `gullible`.

### 6. `HagglingNegotiated`
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

### 7. `NegotiationSessionStarted`
- **Topic**: `runefoble.events.tavern`, `runefoble.events.west_marches`
- **Aggregate Type**: `Negotiation`
- **Payload Fields**: `negotiation_id`, `character_id`, `item_id`, `item_name`, `original_price`, `current_offer`, `counter_price`, `patience`, `temperament`.

### 8. `GambitExecuted`
- **Topic**: `runefoble.events.tavern`, `runefoble.events.west_marches`
- **Aggregate Type**: `Negotiation`
- **Payload Fields**: `negotiation_id`, `character_id`, `gambit`, `roll_value`, `target_dc`, `is_success`, `new_offer`, `counter_price`, `patience_delta`, `new_patience`, `voice_bark`.

### 9. `DMNegotiationOverridden`
- **Topic**: `runefoble.events.tavern`, `runefoble.events.west_marches`
- **Aggregate Type**: `Negotiation`
- **Payload Fields**: `negotiation_id`, `dm_user_id`, `action`, `new_patience`, `override_price`, `narrative_bark`, `status`.

### 10. `NegotiationConcluded`
- **Topic**: `runefoble.events.tavern`, `runefoble.events.west_marches`
- **Aggregate Type**: `Negotiation`
- **Payload Fields**: `negotiation_id`, `character_id`, `item_id`, `final_price`, `status`, `currency_deducted`, `closing_bark`.


### Multiplayer Table Events (`runefoble_events.tavern_tables`)

Table state is event-sourced on the `TavernGame` aggregate, where `game_id` is the table id. Each event carries the outcome that the command decided. Replaying the events gives the table state. All table events publish to `runefoble.events.tavern`.

| Event | Payload Fields |
|---|---|
| `TableOpened` | `game_id`, `establishment_id`, `game_type` |
| `TablePlayerSeated` | `game_id`, `player_id`, `name`, `chips`, `score`, `dice` |
| `TableBetPlaced` | `game_id`, `player_id`, `amount`, `bet_type`, `target` |
| `DartThrown` | `game_id`, `player_id`, `hit`, `score_remaining`, `is_bust`, `is_won`, `next_turn_index`, `payout` |
| `TableBidPlaced` | `game_id`, `player_id`, `quantity`, `face`, `next_turn_index` |
| `TableChallengeResolved` | `game_id`, `challenger_id`, `bidder_id`, `loser_id`, `winner_id`, `loser_dice_after`, `next_hands`, `champion_id`, `payout` |
| `RouletteSpun` | `game_id`, `winning_number`, `color`, `payouts` |
| `CrapsRolled` | `game_id`, `dice`, `point`, `payouts`, `remaining_bets`, `narrative` |

A table ends with `MinigameEnded` when a darts winner or a Liar's Dice champion is set.

---

## Public REST Endpoints

| Endpoint | Method | Service | Zanzibar Permission | Description |
|---|---|---|---|---|
| `/api/v1/sessions/{id}/tavern/games` | `POST` | `game_session` (gateway proxy) | `campaign:play` | Initiates minigame with secret hands and gold pot. |
| `/api/v1/sessions/{id}/tavern/games/{gid}/turn` | `POST` | `game_session` | `session:participate` | Submits bid, calls bluff, or rolls drinking save. |
| `/api/v1/sessions/{id}/tavern/games/{gid}` | `GET` | `game_session` | `session:participate` | Retrieves live minigame state machine status. |
| `/api/v1/tavern/tables` | `POST` | `game_session` | `establishment:play` (or `view`, `manage`) | Opens a minigame table (`table_id`, `establishment_id`, `game_type`). Returns `409` when the id is already open. Sockets never open a table. |
| `/api/v1/tavern/tables/{table_id}` | `GET` | `game_session` | `establishment:play` (or `view`, `manage`) | Returns the seats, chips, pot, bets, and current game state of an open table. Returns `404` when the table is not open. |
| `/api/v1/sessions/{id}/merchants/{mid}/haggle` | `POST` | `game_session` (gateway proxy) | `establishment:play` | Gateway route. It forwards to the owner `POST /api/v1/haggling/start` with the session and merchant ids in the body. Requires `campaign_id`, `establishment_id`, and `item_id` in the request. Returns the owner negotiation state and the owner status codes. |
| `/api/v1/merchants/{mid}` | `GET` | `game_session` | — | Queries merchant temperament and negotiation record. Returns `404` when no merchant exists for the id. Returns `503` when the event store is unavailable. |
| `/api/v1/establishments/{id}/haggle` | `POST` | `game_session` | `establishment:view` | Starts interactive bartering encounter within establishment. |
| `/api/v1/haggling/{id}/gambit` | `POST` | `game_session` | `negotiation:participate` | Executes bargaining gambit (flattery, bulk, flaw, intimidate, bluff). |
| `/api/v1/haggling/{id}/dm-override` | `PATCH` | `game_session` | `negotiation:arbitrate` | Real-time DM controls: soothe, enrage, accept deal, kick out. |
| `/api/v1/haggling/{id}` | `GET` | `game_session` | `negotiation:view` | Live negotiation state, patience meter, and dialogue history. |

---

## Minigame Table Sockets

| Path | Owner | Auth | Description |
|---|---|---|---|
| `/ws/minigames/{table_id}` | `game_session` | Bearer subprotocol (`runefoble.bearer.<jwt>`) | Standalone table channel. Reached through the gateway, which relays frames unchanged (TASK-0592) |
| `/ws/establishments/{establishment_id}/tables/{table_id}` | `game_session` | Bearer subprotocol | Establishment-scoped table channel. The path must name the establishment that the table names |

The owner verifies the bearer and checks `establishment` play access (SpiceDB). Close codes the owner sends:
- `1008`: no valid bearer subprotocol, closed before accept.
- `4403`: the caller lacks play access (authorization refusal). The owner sends a `PERMISSION_DENIED` error frame first.
- `4404`: the table is not open, or the path names another establishment. The owner sends a `TABLE_NOT_FOUND` error frame first.

Through the gateway, a refusal before accept reaches the client as `4403`, and an unreachable owner closes the client with `1013`.

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

