# How-To: Manage Dynamic Soundscapes & Adaptive Audio Ducking

This guide explains how to use the `soundscape` bounded context (TASK-0050, PRD-0010, US-0039) to score encounter tension dynamically, crossfade adaptive audio stem layers, trigger synchronized tactical foley sound effects, and enforce -12dB WebAudio ducking during voice communication.

---

## 1. Calculating Encounter Tension & Stem Transitions

The Encounter Tension Scoring Engine computes real-time tension (0–100) based on combat round progression, enemy Challenge Rating (CR) threat, and party health ratios:

```bash
curl -X POST http://localhost:8009/api/v1/soundscape/tension/calculate \
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
  -H "X-User-Id: dm-evelyn" \
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

Whenever a player speaks (via `PlayerSpokeEvent` or WebRTC audio frames), the ducking coordinator immediately attenuates music layers by -12 dB (~0.2512 linear multiplier):

```bash
curl -X POST http://localhost:8009/api/v1/soundscape/duck \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-tomb-14",
    "is_ducked": true,
    "reason": "speech"
  }'
```

---

## 4. Manual DM Mood Override (Zanzibar Guarded)

DMs retain final authority over table atmosphere. To lock the soundscape to a specific theme regardless of tension:

```bash
curl -X POST http://localhost:8009/api/v1/soundscape/override \
  -H "Content-Type: application/json" \
  -H "X-User-Id: dm-evelyn" \
  -d '{
    "session_id": "session-tomb-14",
    "mood": "combat",
    "master_volume": 0.85
  }'
```

This operation checks Zanzibar permissions (`run_session` or `control` on `session:session-tomb-14`).

---

## 5. Personal Character Leitmotifs & Adaptive Musical Signatures

Players can configure distinct instrument signatures and melodic leitmotifs (TASK-0102, PRD-0016, US-0046). The soundscape engine blends character motifs dynamically into active combat scores during clutch moments:

### Configuring a Character Profile
```bash
curl -X POST http://localhost:8009/api/v1/soundscape/leitmotif/profile \
  -H "Content-Type: application/json" \
  -H "X-User-Id: player-nadia" \
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
- **Clutch Criticals**: When a player rolls a natural 20 (`CriticalHitScored` or `DiceRolled(is_crit=True)`), the audio mixer triggers their triumphant stinger within 250ms, blending seamlessly into active combat stems.
- **Death Saves**: When a character drops to 0 HP (`DeathSaveStarted`), the audio soundtrack smoothly transitions to introduce their somber theme variant (e.g. solitary cello), amplifying dramatic tension.
- **Voice Sidechain Ducking**: Whenever voice activity is detected (`PlayerSpokeEvent`), leitmotif stems are attenuated by -12dB alongside background music.

---

## 6. Microfrontend Integration

The soundscape microfrontends are vendored inside `services/soundscape/ui/` and advertised via `GET /ui/manifest`:
- `<runefoble-soundscape-controls>`: Real-time tension bar, mood override buttons, stem sliders, and tactical foley trigger grid.
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

| Gateway Endpoint | Method | Required Zanzibar Permission | Downstream Proxy / Action |
|---|---|---|---|
| `/api/v1/soundscape/cue` | POST | `play` on campaign or session | Triggers tactical foley cue (`SoundscapeCueRequest`) |
| `/api/v1/soundscape/tension` | GET | Public / Authenticated | Retrieves session encounter tension & stem profile |
| `/api/v1/soundscape/tension/calculate` | POST | Public / Authenticated | Computes tension score from combat round and CR |
| `/api/v1/soundscape/stems/override` | POST | `run_session` or `manage` on campaign | Forces DM mood override (exploration, combat, etc.) |
| `/api/v1/soundscape/leitmotif/{character_id}` | GET | Public / Authenticated | Queries character leitmotif signature configuration |

The gateway router (`gateway/api/src/gateway_api/routers/soundscape.py`) checks SpiceDB Zanzibar object permissions before forwarding to `SOUNDSCAPE_SERVICE_URL` (`http://soundscape:8010`) with an automatic in-process fallback for local execution.

---

## 8. Modular Blackbox Test Organization & Architecture

The soundscape blackbox verification suite is partitioned into focused test modules strictly adhering to Hard Invariant 6 (< 500 lines per file) and Hard Invariant 7 (Blackbox TDD with frontdoor setup):
- `tests/test_blackbox_soundscape_ui/`: Modular blackbox test suite (`test_manifest.py`, `test_stem_mixing.py`, `test_foley_ducking.py`, `conftest.py`) verifying microfrontend manifest advertising, package metadata integrity, TypeScript element exports, Storybook coverage, multi-channel stem mixing, tension scoring, WebAudio -12dB audio ducking, and Zanzibar authorization.
- `tests/test_blackbox_soundscape_transitions.py`: Verifies multi-track stem layer mixing, ambient/combat crossfading, WebAudio -12dB voice ducking coordination triggered by `PlayerSpokeEvent`, manual mood overrides, and `<runefoble-soundscape-controls>` microfrontend component and token invariants.
- `tests/test_blackbox_soundscape_tension.py`: Verifies encounter tension scoring heuristics across exploration and combat states, tactical foley cue triggers (`POST /api/v1/soundscape/cue`), autonomous Redis Streams reactivity to `CombatEncounterStarted` and `CombatRoundAdvanced`, and SpiceDB Zanzibar DM authorization enforcement.
- `tests/test_blackbox_leitmotif_events.py`: Verifies CloudEvents domain event class mapping (`LeitmotifProfileConfigured`, `LeitmotifTriggered`, `CriticalHitScored`, `DeathSaveStarted`) and payload serialization roundtrips.
- `tests/test_blackbox_leitmotif_api.py`: Verifies REST API routes (`/api/v1/soundscape/leitmotif/timbres`, `profile`, `trigger`, `active`), SpiceDB Zanzibar character owner authorization enforcement, and `<runefoble-leitmotif-config>` microfrontend manifest and component invariants.
- `tests/test_blackbox_leitmotif_triggers.py`: Verifies multi-modal combat and reactive triggers (critical hits, near-death cello themes, WebAudio sidechain -12dB voice ducking) and volume envelope stage calculations.
- `tests/test_blackbox_soundscape_gateway.py`: Verifies API Gateway `/api/v1/soundscape/*` proxy routing, OpenAPI schema exposure, SpiceDB Zanzibar object authorization (`play`, `run_session`, `manage`), and downstream service forwarding (< 500 lines).
- `tests/test_blackbox_soundscape_event_handlers.py`: Verifies domain event subscription handlers (`CombatEncounterStarted`, `InitiativeTurnAdvanced`, `PlayerSpokeEvent`, `CriticalHitScored`, `DeathSaveStarted`), platform bus subscription wiring, backward-compatibility re-exports, and file length limit invariants (< 180 lines).

---

## 9. Modular Event Subscription & Service Architecture

Per ADR-0003, ADR-0006, ADR-0007, and Hard Invariant 6, domain event handlers and dependency injection are cleanly separated into focused modules strictly maintained under 180 lines:
- `services/soundscape/src/soundscape/dependencies.py`: Retains repository singleton factories, SpiceDB Zanzibar permission guards, mixer session registries, and re-exports domain event dispatchers (< 150 lines).
- `services/soundscape/src/soundscape/event_handlers.py`: Contains domain event subscription callbacks (`CombatEncounterStarted`, `CombatRoundAdvanced`, `InitiativeTurnAdvanced`, `PlayerSpokeEvent`, `CriticalHitScored`, `DiceRolled`, `DeathSaveStarted`), dynamic tension recalculation triggers, and bus listener registration (`register_soundscape_event_handlers()`) (< 180 lines).
- `services/soundscape/src/soundscape/main.py`: Coordinates service startup and registers event handlers during FastAPI application lifespan.
