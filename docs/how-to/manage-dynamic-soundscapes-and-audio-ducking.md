# How-To: Manage Dynamic Soundscapes & Adaptive Audio Ducking

This guide explains how to use the `soundscape` bounded context (TASK-0050, PRD-0010, US-0039) to score encounter tension dynamically, crossfade adaptive audio stem layers, trigger synchronized tactical foley sound effects, and enforce -12dB WebAudio ducking during voice communication.

## Authentication

Every route in this service needs a bearer token. Set `TOKEN` to a Zitadel access token for the caller. The service verifies the token itself. It ignores `X-User-Id` and similar headers.

Authorization fails closed:
- No verified token returns `401`.
- A verified caller without the schema permission returns `403`.
- SpiceDB cannot answer. The service returns `503` with `{"error": "authorization_unavailable"}`. A failed check is never a denial or an allow.

Each control route checks one schema permission. The table in section 7 lists them.

---

## 1. Calculating Encounter Tension & Stem Transitions

The Encounter Tension Scoring Engine computes real-time tension (0–100) based on combat round progression, enemy Challenge Rating (CR) threat, and party health ratios. The caller needs `session.control` on `session_id` (DM authority). A player receives `403`.

The event path derives these inputs from game state. No value is fixed:

- **Enemy CR**: On `runefoble.events.session.combat_encounter_started`, the engine sums the `cr` field of each roster combatant. A CR can be a number or an SRD fraction such as `"1/4"`. A combatant without `cr` adds nothing. Later rounds reuse this sum.
- **Encounter end**: On `runefoble.events.session.combat_encounter_ended`, the engine clears the enemy CR and round inputs, and re-scores tension once with combat inactive. Later health changes do not raise combat tension until the next `runefoble.events.session.combat_encounter_started`.
- **Round**: `runefoble.events.session.combat_round_advanced` and `runefoble.events.session.initiative_turn_advanced` set the round.
- **Party health**: Each `runefoble.events.character.health_changed` event with a `session_id` stores that character's HP ratio (current HP / max HP). The engine uses the lowest stored ratio. A character that has not reported counts as full health. During combat, each health change re-scores tension at once.

```bash
curl -X POST http://localhost:8009/api/v1/soundscape/tension/calculate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-tomb-14",
    "combat_active": true,
    "combat_round": 3,
    "enemy_cr_balance": 3.0,
    "lowest_party_health_ratio": 0.20
  }'
```

### Response
```json
{
  "session_id": "session-tomb-14",
  "tension_score": 90,
  "stem_profile": "boss",
  "active_stems": ["boss"],
  "stem_volumes": {
    "ambient": 0.0,
    "tension": 0.2,
    "combat": 0.6,
    "boss": 1.0
  },
  "master_volume": 1.0,
  "is_ducked": false,
  "ducking_attenuation_db": 0.0,
  "effective_gain": 1.0,
  "manual_override": false
}
```

Tension scores automatically map to four adaptive profiles:
- **0–29 (`exploration`)**: Ambient soundscapes, dripping water, cavern winds.
- **30–59 (`tension`)**: Suspenseful low strings, cello ostinatos, anticipation.
- **60–84 (`combat`)**: Driving battle drums, horns, fast-paced rhythm.
- **85–100 (`boss`)**: Climactic choir, heavy brass, lethal peril.

---

## 2. Triggering Tactical Sound Foley & Stingers

To fire a tactical sound effect (e.g. upon spell casting or critical rolls):

```bash
curl -X POST http://localhost:8009/api/v1/soundscape/cue \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "session_id": "session-tomb-14",
    "cue_name": "fireball",
    "cue_type": "spell",
    "volume_gain": 1.0,
    "duck_music": true
  }'
```

### Predefined Presets
Available presets include:
- `sword_slash` (melee slash, gain 1.0)
- `shield_block` (deflection, gain 0.9)
- `fireball` (explosive spell detonation, ducks music, gain 1.0)
- `critical_hit` (stinger fanfare, ducks music, gain 1.2)
- `dungeon_drip` (ambient environmental drop, gain 0.7)
- `thunder_clap` (lightning burst, ducks music, gain 1.1)

---

## 3. WebAudio Background Ducking (-12dB)

The soundscape aggregate owns the duck. A speech duck and a cue duck each record a `DuckingEngaged` event with a stored `duration_ms`:
- Speech (`runefoble.events.watcher.player_spoke`) ducks for 2500 ms.
- A cue with `duck_music: true` ducks for 2000 ms.

After the stored duration passes, `GET /tension` and the other read routes report `is_ducked: false`. No client call is needed. No speech-end domain event exists in the platform, so the stored duration ends a speech duck.

To duck by hand, call the duck route with `is_ducked: true` and a `duration_ms`. A `duration_ms` of `0` holds the duck until a release:

```bash
curl -X POST http://localhost:8009/api/v1/soundscape/duck \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-tomb-14",
    "is_ducked": true,
    "reason": "speech",
    "duration_ms": 2500
  }'
```

To end a duck before its duration, call the same route with `is_ducked: false`. The aggregate records `DuckingReleased` and the duck ends at once.

The browser component `<runefoble-soundscape-controls>` sends each duck and release to the gateway route `POST /api/v1/soundscape/duck` (TASK-0589). It sets the `apiBase` and `authorization` properties for this call. If the owner rejects the duck or cannot be reached, the panel shows the reason in an alert. The local badge and timer still change, so the alert is the only signal of the failure.

---

## 4. Manual DM Mood Override (Zanzibar Guarded)

DMs retain final authority over table atmosphere. To lock the soundscape to a specific theme regardless of tension:

```bash
curl -X POST http://localhost:8009/api/v1/soundscape/stems/override \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "session_id": "session-tomb-14",
    "mood": "combat",
    "master_volume": 0.85
  }'
```

The override records `StemProfileOverridden` and, when `master_volume` is set, `MasterVolumeChanged`. A restart keeps both values because they live in the event store.

This operation checks `session.control` on `session:session-tomb-14`. When the request names a `campaign_id`, `campaign.run_session` on that campaign also grants it. A player receives `403`.

---

## 5. Personal Character Leitmotifs & Adaptive Musical Signatures

Players can configure distinct instrument signatures and melodic leitmotifs (TASK-0102, PRD-0016, US-0046). The soundscape engine blends character motifs dynamically into active combat scores during clutch moments:

### Configuring a Character Profile
```bash
curl -X POST http://localhost:8009/api/v1/soundscape/leitmotif/profile \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "session_id": "session-tomb-14",
    "character_id": "char-nadia",
    "character_name": "Nadia",
    "instrument_timbre": "lute",
    "tempo_multiplier": 1.05,
    "volume_gain": 1.0,
    "attack_ms": 120,
    "release_ms": 300,
    "duration_ms": 4000
  }'
```

Available instrument timbre presets:
- `lute`: Lute & Celtic Flute (acoustic strings, folk woodwinds)
- `brass`: Heroic Brass & Fanfare (horns, noble trumpets)
- `woodwind`: Haunting Woodwind & Flute (panpipes, ethereal clarinets)
- `strings`: Somber Cello & Virtuoso Violins (melancholic cello, driving strings)
- `synth`: Arcane Synthesizer & Astral Chime (crystal chords, ethereal synth)

### Reactive Tabletop Triggering
- **Clutch Criticals**: When a player rolls a natural 20 (`DiceRolled` with `is_crit=True`), the audio mixer triggers their triumphant stinger within 250ms, blending seamlessly into active combat stems.
- **Death Saves**: When a health change leaves a character at 0 HP (`CharacterHealthChanged` with `current_hp` 0), the audio soundtrack smoothly transitions to introduce their somber theme variant (e.g. solitary cello), amplifying dramatic tension.
- **Voice Sidechain Ducking**: Whenever voice activity is detected (`runefoble.events.watcher.player_spoke`), leitmotif stems are attenuated by -12dB alongside background music.

---

## 6. Microfrontend Integration

The soundscape microfrontends are vendored inside `services/soundscape/ui/` and advertised via `GET /ui/manifest`:
- `<runefoble-soundscape-controls>`: Real-time tension bar, mood override buttons, stem sliders, and tactical foley trigger grid.
  Set `apiBase` to the gateway origin (empty for the same origin) and `authorization` to `Bearer <token>`. Ducks post to `/api/v1/soundscape/duck` through the gateway.
- `<runefoble-leitmotif-config>`: Character instrument signature selector, tempo/volume sliders, and triumphant/somber auditioning buttons with immediate WebAudio earcon feedback.

```html
<runefoble-leitmotif-config
  sessionId="session-tomb-14"
  characterId="char-nadia"
  characterName="Nadia"
  instrumentTimbre="lute"
  tempoMultiplier="1.05"
  volumeGain="100">
</runefoble-leitmotif-config>
```

The component dispatches custom DOM events:
- `leitmotif-configured`: Emitted when character profile is saved.
- `leitmotif-audition`: Emitted when triumphant or somber audition buttons are clicked.
- `leitmotif-timbre-selected`: Emitted when an instrument timbre is selected.

---

## 7. Gateway API Soundscape Routing & Edge Zanzibar Authorization

When frontend microfrontends such as `<runefoble-soundscape-controls>` or external client SDKs interact with soundscape capabilities, requests are routed through the API Gateway at `http://localhost:8000/api/v1/soundscape/*` (governed by TASK-0436, ADR-0001, ADR-0010, ADR-0013):

The soundscape service checks these schema permissions on each control route. The gateway verifies the bearer token only, then forwards the request. It does not check a permission itself.

| Route | Method | Service Permission (`runefoble.zed`) | Action |
|---|---|---|---|
| `/api/v1/soundscape/cue` | POST | `session.participate` or `session.control`. With a `campaign_id`, also `campaign.play` or `campaign.run_session`. | Triggers tactical foley cue (`SoundscapeCueRequest`) |
| `/api/v1/soundscape/stems/volume` | POST | `session.control` (or `campaign.run_session` with a `campaign_id`) | Sets stem channel volumes |
| `/api/v1/soundscape/duck` | POST | `session.control` | Engages -12dB ducking for `duration_ms` (0 holds), or releases it with `is_ducked: false` |
| `/api/v1/soundscape/tension/calculate` | POST | `session.control` (or `campaign.run_session` with a `campaign_id`) | Computes tension score from combat round and CR |
| `/api/v1/soundscape/stems/override` | POST | `session.control` (or `campaign.run_session` with a `campaign_id`) | Forces DM mood override (exploration, combat, etc.) |
| `/api/v1/soundscape/leitmotif/profile` and `/trigger` | POST | `character.edit` on the character, or `session.control` (or `campaign.run_session` with a `campaign_id`) | Configures or triggers a character leitmotif |
| `/api/v1/soundscape/tension` and `/stems` | GET | Verified token only | Reads session encounter tension and stem profile |

Known gap: the GET read routes do not check `session.observe` yet. The request models type `campaign_id` as a UUID, but gateway campaign ids are strings. A campaign grant cannot reach these routes until that contract changes.

The gateway router (`gateway/api/src/gateway_api/routers/soundscape.py`) verifies the bearer token and forwards the request to `RUNEFOBLE_SOUNDSCAPE_URL` (no code default; the chart renders `http://soundscape:8009`). The soundscape service checks the SpiceDB Zanzibar permissions in the table. The gateway forwards the caller's bearer token. Each control route has a gateway 403 test: `tests/test_blackbox_soundscape_gateway.py` (cue, override, tension calculate), `tests/test_blackbox_soundscape_gateway_duck.py` (duck), and `tests/test_blackbox_soundscape_gateway_stems.py` (stems volume). If the soundscape service returns `5xx`, the gateway returns `502`. If the service is unreachable, the gateway returns `503`. It does not run soundscape code in process. See [Gateway Proxy Identity and Errors](../reference/ports-and-endpoints.md#gateway-proxy-identity-and-errors).

---

## 8. Event Subscription & Service Architecture

Per ADR-0003, ADR-0006, ADR-0007, and Hard Invariant 6, the service keeps no session state in process memory (TASK-0576):
- `services/soundscape/src/soundscape/dependencies.py`: Holds the event repository factory, the SpiceDB permission guards, the Zitadel verifier seam, and the event bus seam. It holds no mixer, tension, or leitmotif state.
- `services/soundscape/src/soundscape/session_state.py`: Reads and writes one session's state through the aggregate. It projects the public tension and mixer view from the stored state.
- `services/soundscape/src/soundscape/ids.py`: Derives the aggregate id from the session id with UUID v5. Every process resolves the same event stream for one session.
- `services/soundscape/src/soundscape/event_handlers.py`: Contains the domain event handler `handle_incoming_domain_event`. It handles `runefoble.events.session.combat_encounter_started`, `runefoble.events.session.combat_encounter_ended`, `runefoble.events.session.combat_round_advanced`, `runefoble.events.session.initiative_turn_advanced`, `runefoble.events.watcher.player_spoke`, `DiceRolled`, `CharacterHealthChanged`, `TokenHazardTriggered`, `PhysicsCollisionOccurred`, `SpellCast`, and `AreaEffectExploded`. The last four record a foley cue on the session aggregate. A hazard plays `hazard_<hazard_type>` at gain 1.0. A collision plays `impact_<collision_type>`, and its gain scales with `impact_energy` (full gain at 50, clamped to 0.2 through 1.5). A spell cast plays `cast_<spell_archetype>`. An area burst plays `burst_<decal_type>`, or `burst_generic` when the decal is empty. The board routes publish `SpellCast` and `AreaEffectExploded` on `runefoble.events.board` for both REST and WebSocket casts.
- `services/soundscape/src/soundscape/consumer.py`: Runs the only caller of the handler. One Redis Streams consumer reads the `runefoble.events.session`, `runefoble.events.watcher`, `runefoble.events.character`, and `runefoble.events.board` streams (TASK-0710, TASK-0438). No in-process bus delivers events to the handler.
- `services/soundscape/src/soundscape/main.py`: Coordinates service startup. The FastAPI lifespan connects the Redis Streams bus and starts the consumer.

Event handlers and routes never catch a broad `Exception`. A failed store read answers `503`.

---

## 9. Aggregate & Domain Handler Architecture

Per ADR-0003, ADR-0007, ADR-0011, and ADR-0013, the event-sourced `SoundscapeAggregate` delegates domain mutations and `@handles` appliers to mixin submodules under `services/soundscape/src/soundscape/handlers/`:

- `services/soundscape/src/soundscape/aggregate.py`: Defines `SoundscapeState` and `SoundscapeAggregate`. The state holds the master volume, channel volumes, stem profile, ducking flag, ducking expiry (`ducking_until`), and the leitmotif profiles. `is_ducked_at(now)` and `mixer_at(now)` derive the read view.
- `services/soundscape/src/soundscape/handlers/stems.py`: `StemHandlersMixin` records `TrackChanged`, `ChannelVolumeChanged`, and `MasterVolumeChanged`.
- `services/soundscape/src/soundscape/handlers/foley.py`: `FoleyHandlersMixin` records cue triggers, `DuckingEngaged`, and `DuckingReleased`.
- `services/soundscape/src/soundscape/handlers/tension.py`: `TensionHandlersMixin` records tension updates and `StemProfileOverridden`.
- `services/soundscape/src/soundscape/handlers/leitmotif.py`: `LeitmotifHandlersMixin` records leitmotif profiles and triggers.
- `services/soundscape/src/soundscape/mixer.py`: `AudioStemMixer` is a pure view of gains and ducking. It holds no session state.
- `services/soundscape/src/soundscape/leitmotif.py`: `LeitmotifEngine.from_state()` rebuilds the leitmotif view from the stored state for each request.
