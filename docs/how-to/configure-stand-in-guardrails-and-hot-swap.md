# How-To: Configure Stand-In Guardrails & Mid-Session Hot-Swap

This guide describes how to configure tactical guardrail policies for absent players' characters, activate zero-HP permadeath safeguards, and perform seamless mid-session hot-swap takeovers (TASK-0055, PRD-0002, US-0025, US-0026).

## Authentication

Every route in this service needs a bearer token. Set `TOKEN` to a Zitadel access token for the caller. The service verifies the token itself. It ignores `X-User-Id` and similar headers.

---

## 1. Configuring Stand-In Tactical Guardrails

Players who anticipate missing a session can configure personal tactical guardrails and playstyle boundaries on their character sheet. These rules ensure that when The Watcher or an autonomous autopilot executes a turn, the AI stand-in respects the player's tactical preferences.

### Guardrail Parameters
These names are the fields of `StandInGuardrails` (character sheet) and `StandInGuardrailPolicy` (`libs/runefoble_platform`). The contract test checks that both models declare the same fields.
- `preserve_spell_slots` (object, default `{}`): Spell level to number of slots held in reserve, for example `{"3": 1}`.
- `protect_allies` (list of strings, default `[]`): Ally names the stand-in protects when they are in the scene.
- `protect_ally_hp_threshold` (float 0.0 to 1.0, default `0.3`): HP fraction below which an ally counts as wounded.
- `risk_threshold` (string, default `"cautious"`): Risk appetite profile (`"cautious"`, `"balanced"`, `"reckless"`).
- `avoid_melee` (bool, default `false` in the Watcher and worker, `true` on the character sheet): Forces ranged positioning when enemies enter close proximity.
- `permadeath_safeguard` (bool, default `true` on the character sheet): Stabilizes the character at 0 HP. See section 2.
- `custom_priorities` (list of strings, default `[]`): Free-text tactical directives. They are passed to the model as prompt text.

An unknown name fails. The Watcher and the inference worker return HTTP 422. A field that a request omits has no effect in the Watcher and worker.

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

When the stand-in acts, The Watcher returns `guardrails_applied` in the response of `POST /api/v1/watcher/stand-in/act`. The list holds the names of the guardrails that the decision enforced, for example `["protect_allies"]`. A guardrail that did not change the decision is not listed. When the model backend names a guardrail, the worker reports it only if the request activated that guardrail. See `docs/reference/inference-worker-response-contract.md`.

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

Send `"active": false` to release the stand-in. This emits `StandInReleased`. The permadeath check reads the flag from the aggregate. The `is_stand_in` field on `POST .../health` only overrides the check for one request. It does not change the stored flag.

Then damage the character:

```bash
curl -X POST http://localhost:8003/api/v1/characters/char-sarah-cleric/health \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "delta": -15,
    "source": "Orc Chieftain Greatsword"
  }'
```

---

## 2a. Leaving a Session Activates the Stand-In

A player who leaves an active session hands the character to the AI stand-in. Choose the character in the lobby first, with `POST /api/v1/sessions/{session_id}/lobby/character`.

### Leave Path

1. The player calls `POST /api/v1/sessions/{session_id}/leave` with a bearer token and `{"reason": "..."}`. The absent player is the verified caller. The caller needs `session.participate`; otherwise the route returns `403`. The body has no player id. The join, lobby readiness and lobby character routes work the same way.
2. `game_session` records the absence in memory. It reads the lobby character for that player.
3. If there is a lobby character, `game_session` calls `POST /api/v1/characters/{character_id}/stand-in` with `"active": true` on `character-sheet`. The call uses `RUNEFOBLE_CHARACTER_SHEET_URL` and forwards the player's bearer.
4. `character-sheet` sets `is_stand_in_active`. Only then does `game_session` save the leave.
5. If the URL is not set, or `character-sheet` does not confirm, the leave returns `503 Service Unavailable`. The session does not change.
6. If the player has no lobby character, the leave records the absence only. The response has `"stand_in_character_id": null`.

The leave response is the session state, plus `stand_in_character_id` (the character that holds the stand-in, or `null`).

### Rejoin Path

When an absent player calls `POST /api/v1/sessions/{session_id}/join` again, `game_session` releases the stand-in first. It calls the same stand-in route with `"active": false`. If `character-sheet` does not confirm, the join returns `503` and the player stays absent. A hot-swap takeover (section 3) releases the stand-in the same way.

---

## 3. Mid-Session Hot-Swap Takeover

When a late-arriving player connects to an active combat encounter, they can instantly take over their character from the AI stand-in without interrupting the initiative order or round progression.

### Hot-Swap Request

```bash
curl -X POST http://localhost:8004/api/v1/sessions/session-crypt-01/hot-swap \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
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
- **Stand-In Release**: Before it saves the session, `game_session` calls `POST /api/v1/characters/{character_id}/stand-in` with `"active": false` on `character-sheet`. The call uses `RUNEFOBLE_CHARACTER_SHEET_URL`. If the URL is not set, or `character-sheet` does not confirm the release, the hot-swap returns `502 Bad Gateway`. The session stays unchanged and the stand-in keeps control.

### Auto-Pilot Turns Require The Watcher

Auto-pilot turns (`POST /api/v1/sessions/{id}/turns/auto-pilot` or `/autopilot`) ask The Watcher for the stand-in action. `game_session` reads the Watcher URL from `RUNEFOBLE_WATCHER_URL` on each request.

- If the URL is unset, the route returns `503` with a detail that names `RUNEFOBLE_WATCHER_URL`.
- If The Watcher is unreachable, returns a status other than `200`, or returns an invalid body, the route returns `503`.
- In each failure case, no stand-in action is recorded and the turn does not advance. `game_session` never runs a local engine instead.

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
  riskThreshold="low"
  isStandInActive="false">
</runefoble-stand-in-guardrails>
```

### Custom Events
- `@guardrails-updated`: Dispatched when the player saves modified guardrail sliders and checkboxes.
- `@request-hot-swap`: Dispatched when clicking the "Take Control" button to initiate mid-session hot-swap.

### Modular UI Architecture (TASK-0203)
Per ADR-0004, ADR-0012, and ADR-0013, the guardrails microfrontend is decomposed into single-responsibility submodules strictly < 130 lines:
- **`runefoble-stand-in-guardrails.styles.ts`**: Encapsulates Bauhaus design tokens, card layouts, risk toggles, priority list chips, and status badges.
- **`runefoble-stand-in-guardrails.templates.ts`**: Standalone Lit HTML render helpers (`renderHeader`, `renderSpellSlotPreservation`, `renderAllyProtectionTags`, `renderSliderControls`, `renderPostureSelector`, `renderCustomPriorityChips`, `renderActionsBar`).
- **`runefoble-stand-in-guardrails.ts`**: Component controller orchestrating reactive property state, event bubbling, and custom element registration.

---

## 5. Modular Stand-In Test Organization & Architecture

The AI stand-in and absentee recap test infrastructure is partitioned into modular, focused test suites strictly adhering to Hard Invariant 6 (< 500 lines per file) and Hard Invariant 7 (Blackbox TDD with frontdoor setup):
- `tests/test_stand_in_tactics_unit.py` (TASK-0070): Pure unit tests verifying stand-in penalty mechanics (`drunk`, `foolishness`, `cowardice`, `greed`), dice roll formula adjustments (`1d20-2`), slurred dialogue, defensive positioning, looting behavior, and personality trait flavor integration (`scholarly`, `valiant`, `impulsive`).
- `tests/test_blackbox_stand_in_service.py` (TASK-0070): Blackbox integration tests verifying The Watcher stand-in action endpoint (`POST /api/v1/watcher/stand-in/act`), Redis Streams event publication (`StandInActionDecided`, `AbsencePenaltyApplied`), Game Session automated turn progression (`POST /api/v1/sessions/{id}/turns/auto-pilot`), and absentee chronicle recap generation (`POST /api/v1/watcher/stand-in/recap`).
- `tests/test_blackbox_stand_in_policies.py` (TASK-0096): Verifies tactical guardrail configuration via `PUT/GET /api/v1/characters/{id}/guardrails`, SpiceDB Zanzibar permission checks, `StandInPolicyUpdated` and `StandInStabilized` CloudEvent publications, The Watcher stand-in tactical decision graph evaluation under 'drunk' and 'foolishness' penalties, and zero-HP permadeath stabilization invariants.
- `tests/test_blackbox_stand_in_takeover.py` (TASK-0096): Verifies mid-session hot-swap handoffs via `POST /api/v1/sessions/{id}/hot-swap`, active combat round and initiative continuity, SpiceDB Zanzibar object authorization, and `CharacterControlTransferred` CloudEvent emissions.
- `tests/test_blackbox_stand_in_guardrails.py` (TASK-0112, TASK-0203): Blackbox TDD test suite validating the modular decomposition of `StandInAIEngine` across backend modules and verifying UI component line length invariants (< 130 lines) and style/template imports.
- `tests/test_blackbox_stand_in_guardrail_contract.py` (TASK-0608): Blackbox round trip of guardrails from The Watcher route to the inference worker and back. Covers `guardrails_applied`, 422 on unknown names, and the field parity check against the character sheet model.
- `frontend/test/stand-in-guardrails-decomposition.test.ts` (TASK-0203): Frontend integration tests verifying Lit template renderers, Bauhaus style token isolation, and file length constraints.

---

## 6. Stand-In Decision Engine Architecture (TASK-0112)

The stand-in decision logic within `services/the_watcher` is decoupled into focused sub-modules to preserve Hard Invariant 6 (< 500 lines limit):
- `the_watcher.stand_in_guardrails`: Implements `evaluate_tactical_guardrails` for ally protection priority matching, melee distance heuristics, spell slot preservation checks, and emergency triage.
- `the_watcher.stand_in_persona`: Implements `apply_penalty_modifiers` for humorous DM penalties (`drunk`, `foolishness`, `cowardice`, `greed`), disadvantage formulas, and personality trait weighting (`scholarly`, `valiant`, `impulsive`).
- `the_watcher.stand_in_recap`: Implements `generate_absentee_recap` for humorous chronicle paragraphs, highlight summaries, and absentee excuse generation.
- `the_watcher.stand_in_ai`: Lightweight `StandInAIEngine` facade orchestrating guardrail evaluation, penalty simulation, and chronicle recap delegation.

---

## 7. Absentee Mobile Directive & Remote Decision Voting Microfrontend (TASK-0167)

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


