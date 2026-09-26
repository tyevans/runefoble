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

## 5. Microfrontend Integration

The `<runefoble-soundscape-controls>` Web Component is vendored inside `services/soundscape/ui/` and discovered via `GET /ui/manifest`:

```html
<runefoble-soundscape-controls
  sessionid="session-tomb-14"
  tensionscore="65"
  stemprofile="combat"
  mastervolume="80">
</runefoble-soundscape-controls>
```

The component dispatches custom DOM events:
- `soundscape-volume`: Triggered when master volume slider moves.
- `soundscape-mood`: Triggered when DM clicks a mood override button.
- `soundscape-cue`: Triggered when tactical foley buttons are clicked.
- `soundscape-duck`: Triggered when voice ducking engages or disengages.

---

## 6. Modular Blackbox Test Organization & Architecture

The soundscape blackbox verification suite is partitioned into two focused test modules strictly adhering to Hard Invariant 6 (< 500 lines per file, strictly < 220 lines) and Hard Invariant 7 (Blackbox TDD with frontdoor setup):
- `tests/test_blackbox_soundscape_transitions.py`: Verifies multi-track stem layer mixing, ambient/combat crossfading, WebAudio -12dB voice ducking coordination triggered by `PlayerSpokeEvent`, manual mood overrides, and `<runefoble-soundscape-controls>` microfrontend component and token invariants.
- `tests/test_blackbox_soundscape_tension.py`: Verifies encounter tension scoring heuristics across exploration and combat states, tactical foley cue triggers (`POST /api/v1/soundscape/cue`), autonomous Redis Streams reactivity to `CombatEncounterStarted` and `CombatRoundAdvanced`, and SpiceDB Zanzibar DM authorization enforcement.

