# How-To: Configure Stand-In Guardrails & Mid-Session Hot-Swap

This guide describes how to configure tactical guardrail policies for absent players' characters, activate zero-HP permadeath safeguards, and perform seamless mid-session hot-swap takeovers (TASK-0055, PRD-0002, US-0025, US-0026).

---

## 1. Configuring Stand-In Tactical Guardrails

Players who anticipate missing a session can configure personal tactical guardrails and playstyle boundaries on their character sheet. These rules ensure that when The Watcher or an autonomous autopilot executes a turn, the AI stand-in respects the player's tactical preferences.

### Guardrail Parameters
- `spell_slot_reserve_level` (int, default `3`): Maximum spell slot level the AI is permitted to cast autonomously, reserving high-level slots (e.g. 3rd-level and above for Revivify or Fireball) for human control.
- `ally_protection_target` (string, default `"Marcus"`): Ally name whom the stand-in prioritizes for healing or protective intervention when under threat.
- `avoid_melee` (bool, default `true`): Forces ranged positioning and disengage actions when enemies enter close proximity.
- `risk_threshold` (string, default `"low"`): Risk appetite profile (`"low"`, `"moderate"`, `"high"`).
- `custom_priorities` (list of strings): Explicit tactical directives (e.g. `["Save Level 3 slots for Revivify", "Prioritize healing Marcus if under 30% HP", "Avoid frontline melee"]`).

### Updating Guardrails via REST API

```bash
curl -X PUT http://localhost:8003/api/v1/characters/char-sarah-cleric/guardrails \
  -H "Content-Type: application/json" \
  -H "X-User-Id: sarah-user" \
  -d '{
    "spell_slot_reserve_level": 3,
    "ally_protection_target": "Marcus",
    "avoid_melee": true,
    "risk_threshold": "low",
    "custom_priorities": [
      "Save Level 3 slots for Revivify",
      "Prioritize healing Marcus if under 30% HP",
      "Avoid frontline melee"
    ]
  }'
```

### Retrieving Active Guardrails

```bash
curl -X GET http://localhost:8003/api/v1/characters/char-sarah-cleric/guardrails \
  -H "X-User-Id: sarah-user"
```

---

## 2. Permadeath Safeguard & Zero-HP Stabilization

When an absent player's character is controlled by the AI stand-in (`is_stand_in: true`), an aggregate-level invariant protects the character from permanent death:

1. **Automatic Stabilization**: If damage reduces character HP to 0 or below, the character is automatically stabilized (`current_hp: 0`, `is_unconscious: true`, `is_stable: true`).
2. **Death Save Immunity**: The character does not accrue failed death saving throws while under stand-in control.
3. **Domain Event**: Emits a `StandInStabilized` event over Redis Streams (`runefoble.events.character.stand_in_stabilized`) notifying the DM and table chronicle.

To activate stand-in status during combat:

```bash
curl -X POST http://localhost:8003/api/v1/characters/char-sarah-cleric/health \
  -H "Content-Type: application/json" \
  -H "X-User-Id: dm-evelyn" \
  -d '{
    "delta": -15,
    "source": "Orc Chieftain Greatsword",
    "is_stand_in": true
  }'
```

---

## 3. Mid-Session Hot-Swap Takeover

When a late-arriving player connects to an active combat encounter, they can instantly take over their character from the AI stand-in without interrupting the initiative order or round progression.

### Hot-Swap Request

```bash
curl -X POST http://localhost:8004/api/v1/sessions/session-crypt-01/hot-swap \
  -H "Content-Type: application/json" \
  -H "X-User-Id: sarah-user" \
  -d '{
    "character_id": "char-sarah-cleric",
    "player_id": "sarah-user",
    "target_controller": "player"
  }'
```

### Response
```json
{
  "session_id": "session-crypt-01",
  "character_id": "char-sarah-cleric",
  "previous_controller_id": "the_watcher_stand_in",
  "new_controller_id": "sarah-user",
  "success": true,
  "round_number": 2,
  "active_turn": 3,
  "message": "Character control successfully transferred to player sarah-user"
}
```

### Key Guarantees
- **Latency < 100ms**: Control is shifted synchronously in memory and persisted event-sourced.
- **SpiceDB Zanzibar Authorization**: Validates that the requesting player has `participate` rights on the session or ownership of the character.
- **Round & Turn Continuity**: The combat round and active initiative order are preserved intact without reload.
- **Domain Event Publication**: Emits `CharacterControlTransferred` (`runefoble.events.session.character_control_transferred`) over Redis Streams.

---

## 4. Web Component UI Integration

The `<runefoble-stand-in-guardrails>` custom element is vendored in `services/character_sheet/ui/`:

```html
<runefoble-stand-in-guardrails
  characterId="char-sarah-cleric"
  characterName="Sarah the Cleric"
  spellSlotReserveLevel="3"
  allyProtectionTarget="Marcus"
  avoidMelee="true"
  riskThreshold="low"
  isStandInActive="false">
</runefoble-stand-in-guardrails>
```

### Custom Events
- `@guardrails-updated`: Dispatched when the player saves modified guardrail sliders and checkboxes.
- `@request-hot-swap`: Dispatched when clicking the "Take Control" button to initiate mid-session hot-swap.

---

## 5. Modular Stand-In Test Organization & Architecture

The AI stand-in and absentee recap test infrastructure is partitioned into modular, focused test suites strictly adhering to Hard Invariant 6 (< 500 lines per file) and Hard Invariant 7 (Blackbox TDD with frontdoor setup):
- `tests/test_stand_in_tactics_unit.py` (TASK-0070): Pure unit tests verifying stand-in penalty mechanics (`drunk`, `foolishness`, `cowardice`, `greed`), dice roll formula adjustments (`1d20-2`), slurred dialogue, defensive positioning, looting behavior, and personality trait flavor integration (`scholarly`, `valiant`, `impulsive`).
- `tests/test_blackbox_stand_in_service.py` (TASK-0070): Blackbox integration tests verifying The Watcher stand-in action endpoint (`POST /api/v1/watcher/stand-in/act`), Redis Streams event publication (`StandInActionDecided`, `AbsencePenaltyApplied`), Game Session automated turn progression (`POST /api/v1/sessions/{id}/turns/auto-pilot`), and absentee chronicle recap generation (`POST /api/v1/watcher/stand-in/recap`).
- `tests/test_blackbox_stand_in_policies.py` (TASK-0096): Verifies tactical guardrail configuration via `PUT/GET /api/v1/characters/{id}/guardrails`, SpiceDB Zanzibar permission checks, `StandInPolicyUpdated` and `StandInStabilized` CloudEvent publications, The Watcher stand-in tactical decision graph evaluation under 'drunk' and 'foolishness' penalties, and zero-HP permadeath stabilization invariants.
- `tests/test_blackbox_stand_in_takeover.py` (TASK-0096): Verifies mid-session hot-swap handoffs via `POST /api/v1/sessions/{id}/hot-swap`, active combat round and initiative continuity, SpiceDB Zanzibar object authorization, and `CharacterControlTransferred` CloudEvent emissions.

