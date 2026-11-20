# How-To: Configure Stand-In Guardrails & Mid-Session Hot-Swap

This guide describes how to configure tactical guardrail policies for absent players' characters, activate zero-HP permadeath safeguards, and perform seamless mid-session hot-swap takeovers (TASK-0055, PRD-0002, US-0025, US-0026).

## Authentication

Every route in this service needs a bearer token. Set `TOKEN` to a Zitadel access token for the caller. The service verifies the token itself. It ignores `X-User-Id` and similar headers.

---

## 1. Configuring Stand-In Tactical Guardrails

Players who anticipate missing a session can configure personal tactical guardrails and playstyle boundaries on their character sheet. These rules ensure that when The Watcher or an autonomous autopilot executes a turn, the AI stand-in respects the player's tactical preferences.

### Guardrail Parameters
These names are the fields of `StandInGuardrailPolicy` (`libs/runefoble_platform`). It is the only policy model. The character sheet stores it, and the Watcher and worker validate it. Each omitted field takes the default shown below.
- `preserve_spell_slots` (object, default `{}`): Spell level to number of slots held in reserve, for example `{"3": 1}`.
- `protect_allies` (list of strings, default `[]`): Ally names the stand-in protects when they are in the scene.
- `protect_ally_hp_threshold` (float 0.0 to 1.0, default `0.3`): HP fraction below which an ally counts as wounded.
- `risk_threshold` (string, default `"cautious"`): Risk appetite profile (`"cautious"`, `"balanced"`, `"reckless"`).
- `avoid_melee` (bool, default `true`): Forces ranged positioning when enemies enter close proximity.
- `permadeath_safeguard` (bool, default `true`): Stabilizes the character at 0 HP. See section 2.
- `custom_priorities` (list of strings, default `[]`): Ordered target names. The stand-in engines pick the first priority that names a visible or scene target. They also pass the list to the model as prompt text.

An unknown name fails. The Watcher, the inference worker, and the character sheet write route return HTTP 422 with the field name. A field that a request omits takes its default.

### Enforced Guardrails
The stand-in engines enforce four guardrails. They report each one by name in `guardrails_applied`:
- `protect_allies`: Heals a named ally when the scene names that ally or mentions healing.
- `preserve_spell_slots`: Casts a cantrip instead of a spell. The reserved slots stay unspent.
- `custom_priorities`: Targets the first priority that names a foe.
- `avoid_melee`: Chooses a ranged action.

The other fields are stored but not enforced by the stand-in engines yet. The engines do not report them.

### Auto-Pilot Requests
The auto-pilot route (`POST /api/v1/sessions/{session_id}/turns/auto-pilot`) does not accept a policy. The stand-in obeys only the policy stored on the absent character. For each turn, `game_session` reads `GET /api/v1/characters/{character_id}/guardrails` from `character_sheet` with the service credential, then sends that policy to The Watcher. A body that carries any other field, such as `guardrails`, returns HTTP 422, and no action is recorded.

If `character_sheet` is unreachable, returns a status other than `200`, or returns an invalid policy, the route returns `503`. No action is recorded, and the turn does not advance. A default policy never takes the place of the stored one.

### Updating Guardrails via REST API

Requests can be issued directly to `character-sheet:8003` or through `gateway-api:8000`:

```bash
curl -X PUT http://localhost:8000/api/v1/characters/char-sarah-cleric/guardrails \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "preserve_spell_slots": {"3": 1},
    "protect_allies": ["Marcus"],
    "protect_ally_hp_threshold": 0.3,
    "avoid_melee": true,
    "risk_threshold": "cautious",
    "custom_priorities": [
      "Save Level 3 slots for Revivify"
    ]
  }'
```

### Reading the Applied Guardrails

When the stand-in acts, The Watcher returns `guardrails_applied` in the response of `POST /api/v1/watcher/stand-in/act`. The list holds the names of the guardrails that the decision enforced, for example `["protect_allies"]`. Every name comes from the `GuardrailName` enumeration, and the local engine and the worker use the same names. A guardrail that did not change the decision is not listed. When the model backend names a guardrail, the worker reports it only if the request activated that guardrail. See `docs/reference/inference-worker-response-contract.md`.

```bash
curl -X POST http://localhost:8001/api/v1/watcher/stand-in/act \
  -H "Content-Type: application/json" \
  -d '{
    "character_name": "Seoni",
    "character_class": "Cleric",
    "scene_context": "Marcus is wounded and the orcs close in",
    "guardrails": {"protect_allies": ["Marcus"]},
    "session_id": "sess-1",
    "campaign_id": "camp-1"
  }'
```

### Retrieving Active Guardrails

```bash
curl -X GET http://localhost:8003/api/v1/characters/char-sarah-cleric/guardrails \
  -H "Authorization: Bearer $TOKEN"
```

---

## 2. Permadeath Safeguard & Zero-HP Stabilization

When an absent player's character is controlled by the AI stand-in (`is_stand_in: true`), an aggregate-level invariant protects the character from permanent death:

1. **Automatic Stabilization**: If damage reduces character HP to 0 or below, the character is automatically stabilized (`current_hp: 0`, `is_unconscious: true`, `is_stable: true`).
2. **Death Save Immunity**: The character does not accrue failed death saving throws while under stand-in control.
3. **Domain Event**: Emits a `StandInStabilized` event over Redis Streams (`runefoble.events.character.stand_in_stabilized`) notifying the DM and table chronicle.

To activate the stand-in for an absent player, call the character sheet route. This route emits `StandInActivated` and stores the flag in the character aggregate:

```bash
curl -X POST http://localhost:8003/api/v1/characters/char-sarah-cleric/stand-in \
  -H "Content-Type: application/json" \
  -d '{
    "active": true,
    "session_id": "session-crypt-01"
  }'
```

Send `"active": false` to release the stand-in. This emits `StandInReleased`. The permadeath check reads the flag from the aggregate. The `is_stand_in` field on `POST .../healthz` only overrides the check for one request. It does not change the stored flag.

Then damage the character:

```bash
curl -X POST http://localhost:8003/api/v1/characters/char-sarah-cleric/healthz \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "delta": -15,
    "source": "Orc Chieftain Greatsword"
  }'
```

---

## 2a. Leaving a Session Activates the Stand-In

A player who leaves an active session hands the character to the AI stand-in. Choose the character in the lobby first, with `POST /api/v1/sessions/{session_id}/lobby/character`. The lobby control `Mark Absent (AI Stand-In)` calls `POST /api/v1/sessions/{session_id}/seats/{player_id}/stand-in` through the gateway (TASK-0952). A player sets their own seat. The DM (`session.control`) sets any seat. The gateway stores nothing. It sends `player_stand_in` to the session sockets after the owner saves the change.

### Leave Path

1. The player calls `POST /api/v1/sessions/{session_id}/leave` with a bearer token and `{"reason": "..."}`. The lobby uses the seat route instead (`POST /api/v1/sessions/{session_id}/seats/{player_id}/stand-in`, body `{"is_absent": true}`), which the DM may also call for another seat. The absent player is the verified caller. The caller needs `session.participate`; otherwise the route returns `403`. The body has no player id. The join, lobby readiness and lobby character routes work the same way.
2. `game_session` records the absence in memory. It reads the lobby character for that player.
3. If there is a lobby character, `game_session` calls `POST /api/v1/characters/{character_id}/stand-in` with `"active": true` on `character-sheet`. The call uses `RUNEFOBLE_CHARACTER_SHEET_URL` and forwards the player's bearer.
4. `character-sheet` sets `is_stand_in_active`. Only then does `game_session` save the leave.
5. If the URL is not set, or `character-sheet` does not confirm, the leave returns `503 Service Unavailable`. The session does not change.
6. If the player has no lobby character, the leave records the absence only. The response has `"stand_in_character_id": null`.

The leave response is the session state, plus `stand_in_character_id` (the character that holds the stand-in, or `null`).

### Rejoin Path

When an absent player calls `POST /api/v1/sessions/{session_id}/join` again (the lobby uses `POST .../seats/{player_id}/stand-in` with `{"is_absent": false}`, which the DM may also call), `game_session` releases the stand-in first. It calls the same stand-in route with `"active": false`. If `character-sheet` does not confirm, the join returns `503` and the player stays absent. A hot-swap takeover (section 3) releases the stand-in the same way.

---

## 3. Mid-Session Hot-Swap Takeover

When a late-arriving player connects to an active combat encounter, they can instantly take over their character from the AI stand-in without interrupting the initiative order or round progression.

### Hot-Swap Request

```bash
curl -X POST http://localhost:8004/api/v1/sessions/session-crypt-01/hot-swap \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "character_id": "char-sarah-cleric"
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
- **SpiceDB Zanzibar Authorization**: Takes the player from the verified bearer token. The body has no player id. The caller needs `session.participate` and `character.edit` on the character. Another player gets `403`.
- **Round & Turn Continuity**: The combat round and active initiative order are preserved intact without reload.
- **Domain Event Publication**: Emits `CharacterControlTransferred` (`runefoble.events.session.character_control_transferred`) over Redis Streams.
- **Stand-In Release**: Before it saves the session, `game_session` calls `POST /api/v1/characters/{character_id}/stand-in` with `"active": false` on `character-sheet`. The call uses `RUNEFOBLE_CHARACTER_SHEET_URL`. If the URL is not set, or `character-sheet` does not confirm the release, the hot-swap returns `502 Bad Gateway`. The session stays unchanged and the stand-in keeps control.

### Auto-Pilot Turns Require The Watcher

Auto-pilot turns (`POST /api/v1/sessions/{id}/turns/auto-pilot`) ask The Watcher for the stand-in action. `game_session` reads the Watcher URL from `RUNEFOBLE_WATCHER_URL` on each request.

- If the URL is unset, the route returns `503` with a detail that names `RUNEFOBLE_WATCHER_URL`.
- If The Watcher is unreachable, returns a status other than `200`, or returns an invalid body, the route returns `503`.
- In each failure case, no stand-in action is recorded and the turn does not advance. `game_session` never runs a local engine instead.

The stored policy is read before The Watcher is called, so a turn with an unreachable `character_sheet` returns `503` before The Watcher is reached. `game_session` uses `RUNEFOBLE_CHARACTER_SHEET_URL` for this read.

In `staging` and `production`, `game_session` does not start without `RUNEFOBLE_WATCHER_URL`. See [Platform Services](../reference/platform-services.md#deployed-mode-and-start-up-failures-adr-0015-4).

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
  riskThreshold="cautious"
  isStandInActive="false">
</runefoble-stand-in-guardrails>
```

### Custom Events
- `@guardrails-updated`: Dispatched when the player saves modified guardrail sliders and checkboxes.
- `@request-hot-swap`: Dispatched when clicking the "Take Control" button to initiate mid-session hot-swap.

## 5. Stand-In Decision Engine Architecture (TASK-0112)

The stand-in decision logic within `services/the_watcher` is decoupled into focused sub-modules to preserve Hard Invariant 6 (< 500 lines limit):
- `the_watcher.stand_in_guardrails`: Implements `evaluate_tactical_guardrails` for ally protection priority matching, melee distance heuristics, spell slot preservation checks, and emergency triage.
- `the_watcher.stand_in_persona`: Implements `apply_penalty_modifiers` for humorous DM penalties (`drunk`, `foolishness`, `cowardice`, `greed`), disadvantage formulas, and personality trait weighting (`scholarly`, `valiant`, `impulsive`).
- `the_watcher.stand_in_recap`: Implements `generate_absentee_recap` for humorous chronicle paragraphs, highlight summaries, and absentee excuse generation.
- `the_watcher.stand_in_ai`: Lightweight `StandInAIEngine` facade orchestrating guardrail evaluation, penalty simulation, and chronicle recap delegation.

---

## 6. Absentee Mobile Directive & Remote Decision Voting Microfrontend (TASK-0167)

When players are away from their primary desktop setup, the `<runefoble-absentee-directive>` mobile Web Component (`services/the_watcher/ui/`) allows them to monitor stand-in status, switch tactical posture directives with one tap, and cast remote votes with tactile haptic feedback:

```html
<runefoble-absentee-directive
  characterName="Sarah"
  characterClass="Life Domain Cleric (Lvl 5)"
  standInActive="true"
  currentStance="defensive"
  currentHp="28"
  maxHp="38">
</runefoble-absentee-directive>
```

### Tactical Posture Presets
- **Defensive (`defensive`)**: Prioritizes ally protection, healing wounded companions, preserving high-level spell slots, and avoiding frontline melee.
- **Cautious (`cautious`)**: Ranged spell and projectile support while conserving slots for emergencies.
- **Heroic (`heroic`)**: Frontline engagement, burst spellcasting, and high-impact interventions.

### Remote Party Decision Voting (`<runefoble-absentee-vote-card>`)
Active party decisions (e.g. resting in dangerous dungeons, pressing forward, or dividing loot) render an interactive vote card that triggers physical haptic vibration pulses (`navigator.vibrate([100, 50, 100])`):
- `@directive-changed`: Dispatched when the player shifts tactical stance.
- `@vote-cast`: Dispatched when the player records a vote on an active party decision poll.
- `@haptic-pulse`: Emitted when tactile vibration events fire.

