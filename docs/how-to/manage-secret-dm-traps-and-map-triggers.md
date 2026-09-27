# How-To: Manage Secret DM Traps, Map Switching, and Stage Triggers

This guide explains how Dungeon Masters configure secret spatial traps, handle movement-pause breach detection, and execute seamless battlemap switching with party token teleportation in `services/board_state/`.

---

## 1. Overview & Architecture

Governed by **US-0018**, **ADR-0001 (SpiceDB Zanzibar)**, and **ADR-0011 (eventsource-py)**:
- **DM Secret Layer**: Secret pit falls, pressure plates, and ambush triggers are hidden from player views and fog-of-war queries.
- **Trigger Types**:
  - `step`: Triggered when a token steps onto the exact coordinate `(x, y)`.
  - `touch`: Triggered when a token makes contact with the specific cell.
  - `proximity`: Triggered when a token moves within `proximity_radius` grid units.
- **Movement Pause**: When a player token breaches an armed trap cell, movement immediately halts at the breach coordinate, flagging `movement_paused: true` and emitting `runefoble.events.board.trap_sprung`.
- **Atomic Map Switch**: Transitions the board dimensions, background imagery, and teleports all party tokens to new spawn coordinates in a single atomic transaction.

---

## 2. Placing a Secret DM Trap

To place a secret trap on the board (requires DM permissions in SpiceDB):

```http
POST /api/v1/boards/{board_id}/traps?campaign_id={campaign_id}
X-User-Id: dm_evelyn
Content-Type: application/json

{
  "name": "Secret Spiked Pit",
  "x": 4,
  "y": 4,
  "trigger_type": "step",
  "dc_detection": 16,
  "damage_dice": "2d10",
  "is_secret": true
}
```

### Response
```json
{
  "trap_id": "trap-c93f01ab",
  "board_id": "board-42",
  "name": "Secret Spiked Pit",
  "x": 4,
  "y": 4,
  "trigger_type": "step",
  "proximity_radius": 1,
  "dc_detection": 16,
  "trap_type": "pit_trap",
  "is_secret": true,
  "is_armed": true,
  "is_sprung": false,
  "is_disarmed": false,
  "damage_dice": "2d10"
}
```

---

## 3. Querying Traps & Zanzibar Player Masking

Players and spectators cannot view secret traps. When querying `/api/v1/boards/{board_id}/traps`:

- **DM View (`X-User-Id: dm_evelyn`)**: Returns all traps, including secret traps.
- **Player View (`X-User-Id: player_alice`)**: Secret traps (`is_secret: true`) are filtered out; only revealed/public traps are returned.

---

## 4. Triggering Traps & Movement Pause

When a player moves a token along a path that enters a trap trigger cell:

```http
POST /api/v1/boards/{board_id}/tokens/valeros/move
Content-Type: application/json

{
  "to_x": 6,
  "to_y": 4
}
```

If a step trap is armed at `(4, 4)`:
1. Token traversal pauses at `(4, 4)`.
2. `MoveTokenResponse` returns `x: 4`, `y: 4`, `trap_triggered: "trap-c93f01ab"`, and `movement_paused: true`.
3. `TrapSprungEvent` is emitted to the event store and published over Redis Streams (`runefoble.events.board`).

---

## 5. Mid-Session Map Switching & Party Teleportation

To transition the stage to a new battlemap and teleport the party:

```http
POST /api/v1/boards/{board_id}/switch-map?campaign_id={campaign_id}
X-User-Id: dm_evelyn
Content-Type: application/json

{
  "new_map_id": "dungeon_level_2",
  "cols": 20,
  "rows": 20,
  "background_image_url": "https://assets.runefoble.com/maps/dungeon_lvl2.png",
  "token_teleports": {
    "valeros": [10, 15],
    "kyra": [10, 16]
  }
}
```

All tokens are relocated atomically, and `BattlemapSwitchedEvent` is emitted.
