# How-To: Build Settlements & Play Mobile-First Web Minigames

This guide demonstrates how to design, zone, and upgrade persistent settlements across geographic biomes, customize establishments with assignable living NPC workers, engage in personality-driven merchant haggling with DM controls, and play real-time tavern and casino minigames from mobile phone browsers without requiring native app installation (PRD-0024 / US-0072–US-0076).

---

## 1. Settlement Genesis, Biomes, and Scaling

Settlements in Runefoble model geographic realism and Central Place Theory. They scale across five tiers:

| Tier | Scale | Population | Typical Districts | Key Establishments |
|---|---|---|---|---|
| **Tier 1** | **Hamlet / Thorp** | 20–150 | Rural Commons | Wayside Inn, Communal Well, Blacksmith |
| **Tier 2** | **Village / Haven** | 150–1,000 | Commons, Green, Palisade | Bakery, Parish Chapel, General Trading Post |
| **Tier 3** | **Market Town** | 1,000–6,000 | Market Core, Artisan, Watch | Weaponsmith, Multiple Taverns, Bulletin Board |
| **Tier 4** | **Fortified City** | 6,000–25,000 | Citadel, High Street, Docks, Warrens | Dedicated Casinos, Arcane Apothecary, Bank |
| **Tier 5** | **Grand Metropolis** | 25,000–100,000+ | Imperial Rings, Monumental Wards | High-Roller Casino Palaces, Planar Bazaars |

### Founding a Settlement Haven

Initialize a new settlement via `POST /api/v1/campaigns/{campaign_id}/settlements`:

```bash
curl -X POST http://localhost:8000/api/v1/campaigns/cmp-west-01/settlements \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Oakhaven Haven",
    "scale": "village",
    "biome": "river_confluence",
    "coordinates": {"x": 1420, "y": 860},
    "defenses": "timber_palisade"
  }'
```

---

## 2. Constructing Establishments & Assigning Living NPC Workers

Establishments are living entities within designated district slots. Each establishment supports assigned NPC workers with distinct personalities, dynamic inventories, and interpersonal relationships.

### Step 1: Construct a Weapon Smithy

```bash
curl -X POST http://localhost:8000/api/v1/settlements/stl-oak-01/establishments \
  -H "Content-Type: application/json" \
  -d '{
    "district_id": "dst-artisan-01",
    "category": "weapon_smithy",
    "name": "The Ember Anvil",
    "tier": 1,
    "operating_costs_per_month": 45
  }'
```

### Step 2: Assign an NPC Worker with Temperament & Social Ties

```bash
curl -X POST http://localhost:8000/api/v1/establishments/est-ember-01/workers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Torvin Ironbreaker",
    "role": "head_blacksmith",
    "wage_gold": 12,
    "temperament": "gruff_stubborn",
    "patience": 4,
    "vices": ["ale", "pride"],
    "shelf_inventory": [
      {"item_id": "longsword_standard", "price_gp": 15, "stock": 4},
      {"item_id": "shield_steel", "price_gp": 10, "stock": 2}
    ],
    "vault_inventory": [
      {"item_id": "blade_folded_adamantine", "price_gp": 350, "stock": 1}
    ],
    "relationships": [
      {"target_npc": "npc_baker_marta", "relation": "debtor", "intensity": 0.6}
    ]
  }'
```

### Step 3: Query Staff Roster & Operational Projections

```bash
curl -X GET http://localhost:8000/api/v1/establishments/est-ember-01/roster \
  -H "x-user-id: user-dm-01"
```

Response includes computed service quality score, operational costs, and redstring knowledge graph edges:

```json
{
  "establishment_id": "est-ember-01",
  "workers": [...],
  "operations": {
    "total_staff": 1,
    "total_wages": 12,
    "net_operating_cost": 57,
    "projected_service_quality": 2.2,
    "service_quality_tier": "standard",
    "interpersonal_tension_index": 0.15
  },
  "social_graph_edges": [
    {
      "source_id": "npc-torvin-01",
      "target_id": "npc_baker_marta",
      "relationship_type": "debtor",
      "intensity": 0.6,
      "confidence": 0.95
    }
  ]
}
```

### Step 4: Shift Worker Mood & Temperament

When external world events occur (e.g. flour supply hijacked by river bandits), update worker temperament:

```bash
curl -X PATCH http://localhost:8000/api/v1/npcs/npc-torvin-01/mood \
  -H "Content-Type: application/json" \
  -H "x-user-id: user-dm-01" \
  -d '{
    "mood": "desperate",
    "temperament": "Anxious and Desperate",
    "patience_delta": -3,
    "metadata": {"crisis": "ore_shortage"}
  }'
```

This emits `NPCMoodUpdated`, updates individual morale, and dynamically recalculates projected service quality across the establishment storefront.

---


## 3. Playing Mobile-First Web Minigames (No App Install)

Players on iOS and Android can open `#/campaigns/:id/town/minigames` in mobile Safari or Chrome. The interface provides single-handed portrait mode interaction, touch velocity gestures, and native haptic feedback (`navigator.vibrate`).

### Tavern Games: Darts & Pub Billiards

1. **Darts**:
   - Touch and drag down to pull back the dart flight.
   - Release with forward flick velocity; the 2D physics engine calculates wind deviation and board trajectory.
   - Haptic vibration confirms board hit. Scores sync over WebSockets to opponents.
2. **Pub Billiards / Pool**:
   - Rotate cue stick around the white cue ball via touch dial.
   - Pull back cue stick slider to adjust impact force.
   - 2D ball-to-ball and cushion collisions render at 60 FPS on mobile canvas.

### Casino Games: Roulette, Liar's Dice & Dragon Craps

1. **Imperial Roulette (`runefoble-minigame-roulette`)**:
   - Tap chips (1, 5, 25 gold) and place them onto the digital felt betting grid (Straight Up 0-36, Red/Black, Odd/Even).
   - Tap "SPIN WHEEL" or trigger croupier countdown.
   - Smooth deceleration physics resolve winning pocket, 35:1 or 1:1 payouts, and haptic pulses.
2. **Liar's Dice (`runefoble-minigame-liars-dice`)**:
   - Accelerometer and swipe cup shaker with dice clatter audio and `navigator.vibrate([20, 40, 20])`.
   - Touch-and-hold privacy peek shade protects hidden dice from spectator view.
   - Bluff bids escalation interface and instant "Liar!" challenge showdown with elimination tracking.
3. **Dragon Craps (Street Bones)**:
   - Perform a two-finger upward swipe to fling physical 3D dice across the wooden tray.
   - Evaluates Pass Line / Don't Pass naturals (7, 11) and craps (2, 3, 12), point establishment, and field payouts.

### Real-Time WebSocket Table Protocol

Connect to table channels at `/ws/establishments/{establishment_id}/tables/{table_id}` or standalone `/ws/minigames/{table_id}`:

```json
// 1. Join Table
{ "action": "join", "player_id": "kip", "name": "Kip", "chips": 100, "game_type": "darts" }

// 2. Place Bet
{ "action": "bet", "player_id": "kip", "amount": 10, "bet_type": "straight", "target": 17 }

// 3. Game Actions (dispatched to all connected mobile clients < 150ms)
{ "action": "throw_dart", "player_id": "kip", "vx": 0.5, "vy": -2.1 }
{ "action": "spin_roulette", "winning_number": 17 }
{ "action": "bid", "player_id": "kip", "quantity": 3, "face": 4 }
{ "action": "challenge", "challenger_id": "sam" }
{ "action": "roll_craps", "dice": [3, 4] }
```

---

## 4. Personality-Driven Merchant Haggling with DM Controls

Shopping is an active social confrontation between player charisma and merchant temperament.

### Starting a Bargaining Session

```bash
curl -X POST http://localhost:8000/api/v1/establishments/est-ember-01/haggle \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "char_nicole",
    "item_id": "blade_folded_adamantine",
    "initial_offer_gp": 260,
    "gambit": "bulk_order_promise"
  }'
```

### Game Master Real-Time Overrides

Game Masters can adjust the merchant's mood meter or override prices via the DM control panel:

```bash
curl -X PATCH http://localhost:8000/api/v1/haggling/hgl-8f12a3/dm-override \
  -H "X-RuneFoble-Role: dungeon_master" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "force_accept",
    "override_price_gp": 280,
    "narrative_bark": "Torvin scowls, then nods in begrudging respect. Done."
  }'
```

---

## 5. Town Bulletin Board & Secret Cipher Notices

Town squares and tavern common rooms feature an interactive bulletin board for local proclamations:

1. **Reading Notices**: Tap any pinned parchment card to view bounties, lost artifact flyers, or guild notices. Touch interactions trigger acoustic paper rustle audio feedback.
2. **Posting Adventurer Requests**: Click "+ Pin Notice" to offer mercenary contracts, job postings, or civic ordinances.
3. **Deciphering Ciphers**: Rotate hidden glyph rings on coded notices to reveal secret meeting places and illicit faction quests.

### Pinning a Notice or Bounty

```bash
curl -X POST http://localhost:8000/api/v1/settlements/stl-oak-01/bulletin \
  -H "X-User-Id: usr_kip" \
  -H "Content-Type: application/json" \
  -d '{
    "board_type": "town_square",
    "title": "WANTED: Manticore of Wyvern Crag",
    "category": "bounty",
    "content": "A wounded manticore preys on cattle north of the mill. 250gp reward.",
    "wax_sealed": false,
    "cipher_encoded": false
  }'
```

### Pinning a Coded Thieves' Cant Cipher Notice

```bash
curl -X POST http://localhost:8000/api/v1/settlements/stl-oak-01/bulletin \
  -H "X-User-Id: usr_rogue" \
  -H "Content-Type: application/json" \
  -d '{
    "board_type": "tavern",
    "title": "Whispers Behind the Barrels",
    "category": "rumor",
    "content": "Seek the shadow where the three-toed crow perches.",
    "wax_sealed": false,
    "cipher_encoded": true,
    "cipher_puzzle": "rot13",
    "cipher_solution": "gilded serpent",
    "cipher_hint": "Where gold scales rattle...",
    "hidden_content": "Midnight rendezvous at the Gilded Serpent back alley."
  }'
```

### Retrieving Active Notices

```bash
# Filter by board location: town_square, tavern, guildhall
curl -X GET "http://localhost:8000/api/v1/settlements/stl-oak-01/bulletin?board_type=town_square" \
  -H "X-User-Id: usr_adventurer"
```

### Submitting Cipher Solution

```bash
curl -X POST http://localhost:8000/api/v1/settlements/stl-oak-01/bulletin/ntc-004/decrypt \
  -H "X-User-Id: usr_kip" \
  -H "Content-Type: application/json" \
  -d '{
    "solution": "gilded serpent"
  }'
```

### Embedding the Lit Web Component

```html
<runefoble-bulletin-board
  settlement-id="stl-oak-01"
  settlement-name="Oakhaven Crossroads"
  board-type="town_square"
  current-user-id="usr_kip"
></runefoble-bulletin-board>
```

### Modular Style Architecture

Per Hard Invariant 6 and ADR-0004 / ADR-0012, bulletin board styling is decoupled into focused sub-sheets under `frontend/src/styles/`:
- `bulletin-board-layout.styles.ts`: Corkboard container, textured radial gradient, header action controls, and responsive grid layout.
- `bulletin-board-card.styles.ts`: Parchment notice cards, push-pin badges, wax seals, cipher rune indicators, and category ribbons.
- `bulletin-board-dialog.styles.ts`: Notice authoring dialog, cipher puzzle inspection overlays, and modal action buttons.

The aggregator `frontend/src/components/runefoble-bulletin-board.styles.ts` composes these sheets into a cohesive `CSSResultGroup` array.

---

## 6. Modular Settlement Auth & Zanzibar Permissions Architecture

Per ADR-0001, ADR-0003, ADR-0005, ADR-0007, and ADR-0013, settlement authentication and object authorization in `services/game_session/src/game_session/settlement/auth/` are decoupled into single-responsibility submodules strictly under 130 lines:

- **`tokens.py`**: Zitadel OIDC bearer token extraction, verification via `ZitadelAuthService`, and development mode mock user context (`dev-user-001`).
- **`permissions.py`**: SpiceDB Zanzibar object permission evaluators for settlement viewing/upgrading, establishment management/patronage, and worker editing.
- **`relationships.py`**: SpiceDB Zanzibar tuple writers (`write_settlement_relationships`, `write_establishment_relationships`, `write_npc_relationships`, `write_negotiation_relationships`).
- **`dependencies.py`**: FastAPI route dependency factories (`get_current_settlement_user`, `require_haven_builder`, `require_establishment_manager`, `require_haven_viewer`).
- **`auth.py` / `__init__.py`**: Aggregator facades (< 40 lines) preserving 100% backwards-compatible re-exports for existing routers and services.

---

## 7. Modular Settlement Workers APIRouter Architecture

Per ADR-0003, ADR-0007, ADR-0013, and PRD-0024, the settlement NPC workers router is decomposed into dedicated submodules under `services/game_session/src/game_session/settlement/workers/` with all route modules remaining strictly under 130 lines:

- **`routes_roster.py`**: Worker assignment (`POST /api/v1/establishments/{id}/workers`), staff listing (`GET /api/v1/establishments/{id}/workers`), roster operations projection (`GET /api/v1/establishments/{id}/roster`), duty relieving (`POST /api/v1/establishments/{id}/workers/{npc_id}/relieve`), and worker profile retrieval (`GET /api/v1/npcs/{npc_id}`).
- **`routes_relationships.py`**: Interpersonal social ties (`POST /api/v1/npcs/{npc_id}/relationships`), relationship queries (`GET /api/v1/npcs/{npc_id}/relationships`), mood and loyalty updates (`PATCH /api/v1/npcs/{npc_id}/mood`), and workplace rumor discovery (`GET /api/v1/npcs/{npc_id}/rumors`).
- **`routes_inventory.py`**: Shelf stock listings (`GET /api/v1/npcs/{npc_id}/inventory`), manager backroom vault access (`GET /api/v1/npcs/{npc_id}/inventory/vault`), item pricing lookups (`GET /api/v1/npcs/{npc_id}/inventory/{item_id}`), and merchandise restocking (`POST /api/v1/npcs/{npc_id}/inventory/restock`).
- **`loaders.py` & `operations.py`**: Aggregate loaders, SpiceDB Zanzibar object-level permission enforcement, and establishment operational metrics synchronization.
- **`workers_router.py`**: Aggregator router facade (< 35 lines) combining `roster_router`, `relationships_router`, and `inventory_router` with 100% backward route compatibility.

---

## 8. Blackbox Test Suites & Verification

In accordance with Hard Invariant 7 (Blackbox TDD with frontdoor setup) and ADR-0008, all settlement haven and mobile minigame mechanics are covered by comprehensive end-to-end blackbox suites driving public HTTP endpoints and WebSocket streams:

1. **Settlement Integration Suite (`tests/test_blackbox_settlements_integration/`)**:
   - Decomposed into modular test submodules strictly under 130 lines per Invariant 6 (`test_invariants_and_compat.py`, `test_auth_and_permissions.py`, `test_settlement_and_establishments.py`, `test_haggling_and_bulletin.py`).
   - `test_found_settlement_and_upgrade_tier_flow`: Verifies civic scaling caps (hamlet 2 districts, village 4 districts), prosperity gates, and event publishing (`SettlementFounded`, `SettlementTierUpgraded`).
   - `test_establishment_creation_and_worker_assignment`: Validates storefront construction, assignable NPC workers with role synergy bonuses, and dynamic inventory inspection via `GET /api/v1/establishments/{id}/workers`.
   - `test_merchant_haggling_gambits_and_dm_override`: Simulates persuasion rolls against merchant temperament, flattery gambits, and real-time DM mood/force-accept arbitration controls.
   - `test_bulletin_board_pin_and_cipher_decrypt`: Tests wax-sealed bounty proclamations, cipher decryption workflows, and live party broadcast over `/ws/campaigns/{id}`.

2. **Multiplayer WebSocket Synchronization Suite (`tests/test_blackbox_minigames_websocket.py`)**:
   - `test_darts_and_billiards_multiplayer_turn_sync`: Tests concurrent player connections exchanging touch trajectory vectors (`throw_dart`, `billiards_stroke`), double bullseye scoring, and turn order passing.
   - `test_casino_craps_and_roulette_betting_and_payouts`: Validates multi-patron wagering, dice tumble evaluation (natural 7 and point phase hits), roulette wheel spins, and automatic character coin purse crediting.

Execute the suites locally via UV:

```bash
uv run pytest tests/test_blackbox_settlements_integration/ tests/test_blackbox_minigames_websocket.py
```




