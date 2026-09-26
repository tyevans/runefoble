# How-To: Inspect Diegetic Handouts, Break Wax Seals & Explore 3D Relics

This guide covers how to generate diegetic in-world artifacts—such as weathered parchment letters with breakable wax seals, invisible UV-reactive ink ciphers, and interactive 3D WebGL magical relics—within the `services/campaign_lore` bounded context under SpiceDB Zanzibar authorization.

---

## 1. Generating Diegetic Handouts

To synthesize a new in-world document with custom calligraphy, weathered parchment, wax seal, and optional invisible ink runes:

```bash
curl -X POST http://localhost:8006/api/v1/lore/handouts/generate \
  -H "Content-Type: application/json" \
  -H "x-user-id: user-dm-1" \
  -d '{
    "campaign_id": "8a329ef2-5c91-4cf1-83d8-21d4bb67f101",
    "title": "Intercepted Courier Scroll",
    "content": "To the Black Gate Vanguard: The Citadel guards rotate at midnight.",
    "handout_type": "letter",
    "paper_texture": "weathered_parchment",
    "calligraphy_font": "royal_chancery",
    "seal_color": "crimson",
    "seal_stamp": "raven_crest",
    "has_wax_seal": true,
    "secret_ink_text": "THE HIGH PRIEST IS AN ILLUSION"
  }'
```

### Response
```json
{
  "handout_id": "9e47d139-b1b5-4377-bdc1-b1d950229dca",
  "campaign_id": "8a329ef2-5c91-4cf1-83d8-21d4bb67f101",
  "title": "Intercepted Courier Scroll",
  "status": "forged",
  "wax_seal": {
    "state": "intact",
    "color": "crimson",
    "stamp_symbol": "raven_crest"
  },
  "has_invisible_ink": true,
  "invisible_ink": {
    "secret_text": "THE HIGH PRIEST IS AN ILLUSION",
    "revealed": false
  }
}
```

This persists an event-sourced `DiegeticHandoutAggregate` emitting the `HandoutGenerated` CloudEvent.

---

## 2. Breaking Wax Seals with Acoustic Feedback

Players or DMs can break the seal to unroll and read the document. Breaking triggers acoustic soundscape cues:

```bash
curl -X POST http://localhost:8006/api/v1/lore/handouts/9e47d139-b1b5-4377-bdc1-b1d950229dca/break-seal \
  -H "Content-Type: application/json" \
  -H "x-user-id: player-rowan" \
  -d '{
    "broken_by": "player-rowan",
    "break_force": 14.0
  }'
```

### Response
```json
{
  "handout_id": "9e47d139-b1b5-4377-bdc1-b1d950229dca",
  "seal_state": "broken",
  "broken_by": "player-rowan",
  "break_force": 14.0,
  "haptic_audio_effect": "wax_crack_crisp_01.wav",
  "revealed_content": "To the Black Gate Vanguard: The Citadel guards rotate at midnight."
}
```

This emits `WaxSealBroken`. Once broken, subsequent break attempts return HTTP 409 Conflict.

---

## 3. Revealing Invisible Ink with Simulated UV Torchlight

Hidden messages written in invisible ink can be inspected under UV torchlight:

```bash
curl -X POST http://localhost:8006/api/v1/lore/handouts/9e47d139-b1b5-4377-bdc1-b1d950229dca/reveal-invisible-ink \
  -H "Content-Type: application/json" \
  -H "x-user-id: player-rowan" \
  -d '{
    "revealed_by": "player-rowan",
    "uv_intensity": 1.0
  }'
```

### Response
```json
{
  "handout_id": "9e47d139-b1b5-4377-bdc1-b1d950229dca",
  "secret_text": "THE HIGH PRIEST IS AN ILLUSION",
  "revealed": true,
  "luminescence_color": "#00ffcc",
  "uv_intensity": 1.0
}
```

---

## 4. Forging and Inspecting 3D WebGL Relics

To forge an interactive 3D artifact with PBR shaders and engraved runic coordinates:

```bash
curl -X POST http://localhost:8006/api/v1/lore/relics/forge \
  -H "Content-Type: application/json" \
  -H "x-user-id: user-dm-1" \
  -d '{
    "campaign_id": "8a329ef2-5c91-4cf1-83d8-21d4bb67f101",
    "name": "Amulet of the Sunken Spire",
    "relic_type": "amulet",
    "model_geometry": "amulet_sunken_spire",
    "shader_properties": {
      "metallic": 0.90,
      "roughness": 0.20,
      "emissive_color": "#00ffcc",
      "emissive_intensity": 1.5
    },
    "runes": [
      {
        "id": "rune-spire-1",
        "inscription": "Khar-Drak-Mor",
        "position": [0.0, 0.35, -0.15],
        "translated": "By Blood Sealed"
      }
    ]
  }'
```

### Logging an Inspection:
```bash
curl -X POST http://localhost:8006/api/v1/lore/relics/<relic_id>/inspect \
  -H "Content-Type: application/json" \
  -H "x-user-id: player-rowan" \
  -d '{
    "inspected_by": "player-rowan",
    "notes": "Rotated relic 180 degrees to discover backplate runes."
  }'
```

This records an inspection event and publishes `RelicInspected`.

---

## 5. Deciphering Ancient Inscriptions

Deciphering a rune updates its translated status on the aggregate:

```bash
curl -X POST http://localhost:8006/api/v1/lore/relics/<relic_id>/translate-rune \
  -H "Content-Type: application/json" \
  -H "x-user-id: player-rowan" \
  -d '{
    "rune_id": "rune-spire-1",
    "translated_by": "player-rowan",
    "translation": "By Blood Sealed"
  }'
```

---

## 6. Microfrontend Web Components

The components are vendored in `@runefoble/campaign-lore-ui`:

```html
<!-- Interactive Handout Viewer with Breakable Wax Seal and UV Torchlight -->
<runefoble-handout-viewer
  title="Intercepted Courier Dispatch"
  handoutType="letter"
  paperTexture="weathered_parchment"
  calligraphyFont="royal_chancery"
  content="The Spire must be sealed before the equinox."
  hasWaxSeal
  sealState="intact"
  sealColor="crimson"
  hasInvisibleInk
  secretInkText="ᚱᚢᚾᛖ: THE GATES REQUIRE DRAGON BLOOD"
></runefoble-handout-viewer>

<!-- Interactive 3D Relic Inspector with Orbit Controls and Clickable Runes -->
<runefoble-relic-inspector
  relicName="Amulet of the Sunken Spire"
  relicType="amulet"
  modelGeometry="amulet_sunken_spire"
  metallic="0.88"
  roughness="0.22"
  emissiveColor="#00ffcc"
></runefoble-relic-inspector>
```

---

## 7. SpiceDB Zanzibar Permissions

SpiceDB evaluates object-level permissions against `libs/runefoble_auth/schema/runefoble.zed`:
- `diegetic_handout->view`: Requires `campaign->view` (players, spectators, DMs) or creator.
- `diegetic_handout->interact`: Requires `campaign->play` (active players, DMs).
- `relic->inspect`: Requires `campaign->view`.
- Secret DM relics (`is_secret: true`): Restricted strictly to `campaign->run_session` (DMs/GMs/Owner).
