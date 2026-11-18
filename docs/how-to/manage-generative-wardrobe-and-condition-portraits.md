# How-To: Manage Generative Character Wardrobe & Condition Portraits

This guide explains how to generate thematic character wardrobe variations (such as ballroom masquerade, arctic tundra, or tavern casual attire) through the configured wardrobe generator, configure real-time condition overlays (bloodied injury vignettes, poisoned auras, and stunned dizzy halos), and synchronize character portraits with board tokens.

## Authentication

Every route in this service needs a bearer token. Set `TOKEN` to a Zitadel access token for the caller. The service verifies the token itself. It ignores `X-User-Id` and similar headers.

Every forge request names a campaign. Send `campaign_id` in the body. Without it the service returns `400`. The caller needs the `campaign.play` permission on that campaign (players and DMs). Spectators get `403`. The service writes the `creator` and `campaign` relations of each new asset before it stores the asset. If SpiceDB cannot write them, the service returns `503` and stores nothing. Reads of a forged asset need `forged_asset.view`: the creator, or a campaign member with view rights.

---

## 1. Automatic Dynamic Condition & Injury Overlays

The character sheet condition engine resolves and applies visual overlays in real time based on active combat health and status conditions:

| Condition / State | Trigger Condition | Visual Overlay & Badge | Mechanical / Narrative Meaning |
|---|---|---|---|
| **Healthy / Normal** | $\text{HP} \ge 50\%$ | Unmodified base portrait avatar | Full stamina, no combat penalties |
| **Bloodied** | $\text{HP} < 50\%$ | Crimson vignette gradient (`#e63946`), blood scratch decals, and `🩸 Bloodied` badge | Physical wounds, low endurance |
| **Poisoned** | `poisoned` status condition | Sickly green aura ring (`#00f5d4`), toxic bubbles, and `🧪 Poisoned` badge | Disadvantage on attack rolls and ability checks |
| **Stunned** | `stunned` status condition | Swirling dizzy stars halo (`#ffd166`) and `💫 Stunned` badge | Incapacitated, cannot move, fails Str/Dex saves |
| **Downed** | $\text{HP} \le 0$ | Full dark vignette, red border, and `downed` badge | Unconscious, begins death saves |

### Checking Active Portrait URL & Condition Badges
Query the public REST API endpoint:
```http
GET /api/v1/characters/{character_id}/portrait
```
Returns:
```json
{
  "character_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "active_portrait_url": "data:image/svg+xml;utf8,...",
  "base_portrait_url": "/assets/portraits/nadia.png",
  "active_variant_id": "var-ballroom-01",
  "condition_badges": ["bloodied", "poisoned"],
  "svg_overlay": "<svg ... class=\"bloodied-vignette\" ...></svg>",
  "current_hp": 18,
  "max_hp": 40
}
```

A character with no portrait answers `null` for `active_portrait_url` and `base_portrait_url`. The character sheet never returns a path to a file that does not exist. A bloodied, poisoned or stunned character with no base portrait still gets an overlay data URI, drawn on the dark backdrop without a base image.

---

## 2. Generative Wardrobe Synthesis via Asset Forge

Players and DMs can synthesize stylistic narrative attire variants tailored for specific campaign scenes.

**Face preservation.** The default generator is the `placeholder`. It draws a flat colour portrait. It does not read the character face, and it does not use the attire prompt to draw the image. The placeholder preserves no face. Each response says so with `"generator": "placeholder"` and `"preserves_face": false`. Do not present a placeholder variant as a likeness of the character.

To use another image generator, implement the `WardrobeGenerator` port in `services/asset_forge/src/asset_forge/wardrobe_generator.py` and add it to `build_wardrobe_generator`. Select it with `RUNEFOBLE_WARDROBE_GENERATOR`. A generator that preserves the face must set `preserves_face = True`.

### Synthesizing an Outfit Variant
Send a POST request to the Asset Forge service:
```http
POST /api/v1/forge/wardrobe
Content-Type: application/json
Authorization: Bearer {TOKEN}

{
  "character_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "character_name": "Nadia the Bard",
  "attire_type": "ballroom_masquerade",
  "prompt": "Ornate gold filigree mask and violet velvet gown",
  "face_embedding_seed": "nadia_face_v1",
  "size_px": 256
}
```

Response (default placeholder):

```json
{
  "variant_id": "var-3f9a1c2b7d",
  "character_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "variant_name": "Nadia the Bard - Ballroom Masquerade",
  "attire_type": "ballroom_masquerade",
  "image_url": "http://silo:9000/runefoble-assets/wardrobe/var-3f9a1c2b7d.png",
  "download_url": "http://silo:9000/runefoble-assets/wardrobe/var-3f9a1c2b7d.png",
  "prompt": "Ornate royal masquerade ball attire, ... Ornate gold filigree mask and violet velvet gown",
  "generator": "placeholder",
  "preserves_face": false,
  "status": "forged"
}
```

### Supported Thematic Attire Styles
- **`ballroom_masquerade`**: Royal masquerade gown/doublet, gilded filigree Venetian mask, velvet mantle, crystal chandelier lighting.
- **`arctic_tundra`**: Heavy wolf pelt mantle, rime-encrusted frost armor, icy mist atmosphere.
- **`tavern_casual`**: Relaxed traveler linen tunic, unbuttoned leather vest, warm amber candlelight.
- **`battle_damaged`**: Scorched plate harness, scarred shield crest, drifting smoke and embers.
- **`ceremonial`**: Sacred temple silk vestments, glowing golden rune borders, celestial circlet.

---

## 3. Unlocking and Equipping Wardrobe Variants

### Adding an Unlocked Variant to a Character
Register the forged variant on the character's wardrobe gallery:
```http
POST /api/v1/characters/{character_id}/wardrobe
Content-Type: application/json
Authorization: Bearer {TOKEN}

{
  "variant_id": "var-masquerade-01",
  "variant_name": "Royal Masquerade Gown",
  "attire_type": "ballroom_masquerade",
  "image_url": "http://silo:9000/runefoble-assets/wardrobe/var-masquerade-01.png",
  "prompt": "Ornate gold filigree mask and violet velvet gown",
  "set_active": true
}
```

### Assigning an Active Portrait Avatar
```http
POST /api/v1/characters/{character_id}/portrait/active
Content-Type: application/json
Authorization: Bearer {TOKEN}

{
  "variant_id": "var-masquerade-01"
}
```

---

## 4. Microfrontend Embedding (`<runefoble-wardrobe-gallery>`)

Embed the wardrobe gallery component into the character sheet or tabletop sidebar:

```html
<runefoble-wardrobe-gallery
  characterId="9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  characterName="Nadia the Expressive Bard"
  currentHp="18"
  maxHp="40"
  activePortraitUrl="http://silo:9000/runefoble-assets/wardrobe/var-masquerade-01.png"
  activeVariantId="var-masquerade-01"
></runefoble-wardrobe-gallery>

<script type="module">
  import '@runefoble/character-sheet-ui';

  const gallery = document.querySelector('runefoble-wardrobe-gallery');

  // Handle outfit selection
  gallery.addEventListener('portrait-selected', (e) => {
    const { variantId, imageUrl } = e.detail;
    console.log(`Equipped outfit: ${variantId} -> ${imageUrl}`);
  });

  // Handle outfit synthesis request
  gallery.addEventListener('generate-wardrobe', async (e) => {
    const { characterId, attireType } = e.detail;
    console.log(`Synthesizing ${attireType} for character ${characterId}`);
  });
</script>
```

### Modular Styles & Sub-Component Architecture

Per **ADR-0004** and **ADR-0013**, the wardrobe gallery is decomposed into modular files under `services/character_sheet/ui/src/` to strictly uphold Hard Invariant 6 (< 500 lines per file, with each module < 250 lines):

- **`runefoble-wardrobe-gallery.styles.ts`**: Dedicated stylesheet module exporting `wardrobeGalleryStyles` with Bauhaus geometric tokens, condition badge pill highlights, avatar border state glows, and outfit selection cards.
- **`runefoble-wardrobe-gallery.ts`**: Lightweight Lit component orchestrating reactive properties, event dispatching, and isolated sub-renderers (`renderConditionBadge`, `renderConditionBadges`, `renderVariantCard`, `renderActiveSection`, `renderForgePanel`).
- **Export Packaging**: Re-exported via `services/character_sheet/ui/src/index.ts`, advertised in `package.json` under `./runefoble-wardrobe-gallery.styles`, and declared in `/ui/manifest`.

---


## 5. Domain Event Catalog

When characters take damage, synthesize wardrobe outfits, or swap active portraits, standard domain events are emitted:

- **`runefoble.events.character.damaged`**: Emitted when hit points are reduced by damage.
- **`runefoble.events.character.portrait_variant_generated`**: Emitted when an attire variant is forged or registered.
- **`runefoble.events.character.portrait_updated`**: Emitted when active avatar/portrait is assigned.
- **`runefoble.events.character.condition_applied`**: Emitted when a status condition (poisoned, stunned) is inflicted.

---

## 6. Modular Blackbox Test Organization & Architecture

Per **ADR-0013** and **Hard Invariant 6** (< 500 lines per file), the blackbox test suite for generative character wardrobe, condition overlays, and portrait galleries is partitioned into focused, single-responsibility frontdoor modules under `tests/test_blackbox_wardrobe_gallery/` (with all test files < 200 lines):

- **`tests/test_blackbox_wardrobe_gallery/test_wardrobe_api.py`**: Verifies REST endpoints (`/api/v1/characters/{id}/portrait/active`, `/wardrobe`), object-level SpiceDB Zanzibar authorization (`viewer`/`owner`), and `<runefoble-wardrobe-gallery>` microfrontend manifest advertisement and Storybook coverage.
- **`tests/test_blackbox_wardrobe_gallery/test_wardrobe_conditions.py`**: Verifies dynamic 50% HP threshold bloodied overlays/vignettes, status affliction auras (poisoned, stunned), and condition badge removals.
- **`tests/test_blackbox_wardrobe_gallery/test_wardrobe_events.py`**: Verifies generative wardrobe variant synthesis, Silo S3 binary asset persistence, and CloudEvents dispatching (`CharacterDamaged`, `PortraitVariantGenerated`, `CharacterPortraitUpdated`).

Run the test suite:
```bash
uv run pytest tests/test_blackbox_wardrobe_gallery/
```

