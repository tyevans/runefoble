# How-To: Manage Generative Character Wardrobe & Condition Portraits

This guide explains how to generate thematic character wardrobe variations (such as ballroom masquerade, arctic tundra, or tavern casual attire) preserving character facial embeddings, configure real-time condition overlays (bloodied injury vignettes, poisoned auras, and stunned dizzy halos), and synchronize character portraits with board tokens.

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

---

## 2. Generative Wardrobe Synthesis via Asset Forge

Players and DMs can synthesize stylistic narrative attire variants tailored for specific campaign scenes without altering the character's facial features.

### Synthesizing an Outfit Variant
Send a POST request to the Asset Forge service:
```http
POST /api/v1/forge/wardrobe
Content-Type: application/json
X-User-Id: player-nadia

{
  "character_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "character_name": "Nadia the Bard",
  "attire_type": "ballroom_masquerade",
  "prompt": "Ornate gold filigree mask and violet velvet gown",
  "face_embedding_seed": "nadia_face_v1",
  "size_px": 256
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
X-User-Id: player-nadia

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
X-User-Id: player-nadia

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

---

## 5. Domain Event Catalog

When characters take damage, synthesize wardrobe outfits, or swap active portraits, standard domain events are emitted:

- **`runefoble.events.character.damaged`**: Emitted when hit points are reduced by damage.
- **`runefoble.events.character.portrait_variant_generated`**: Emitted when an attire variant is forged or registered.
- **`runefoble.events.character.portrait_updated`**: Emitted when active avatar/portrait is assigned.
- **`runefoble.events.character.condition_applied`**: Emitted when a status condition (poisoned, stunned) is inflicted.
