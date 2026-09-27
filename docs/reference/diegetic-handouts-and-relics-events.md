# Reference: Diegetic Handout & 3D Relic Events Schema

All handout and relic events inherit from `BaseRunefobleEvent` and are powered by `eventsource-py`.

## Diegetic Handout Events (`aggregate_type: DiegeticHandout`)

### `HandoutGenerated`
Emitted when an in-world diegetic document is forged (`runefoble.events.lore.handout_generated`).
- `handout_id`: UUID (Aggregate identifier)
- `campaign_id`: UUID
- `title`: String
- `handout_type`: String ("letter", "decree", "bounty", "crypt_map", "scroll")
- `paper_texture`: String ("weathered_parchment", "royal_vellum", "ancient_papyrus")
- `calligraphy_font`: String ("royal_chancery", "elvish_script", "dwarven_runic", "cursed_blackletter")
- `content`: String (Visible text body)
- `has_wax_seal`: Boolean (default True)
- `wax_seal`: Dict[str, Any] (Color, stamp symbol, physics stiffness/brittleness)
- `has_invisible_ink`: Boolean (default False)
- `invisible_ink`: Optional[Dict[str, Any]] (Secret text, 365nm UV wavelength, luminescence)
- `created_by`: Optional[String]
- `metadata`: Dict[str, Any]

### `WaxSealBroken`
Emitted when a player or DM breaks the wax seal (`runefoble.events.lore.wax_seal_broken`).
- `handout_id`: UUID
- `campaign_id`: UUID
- `broken_by`: String (User or character ID)
- `break_force`: Float (e.g. 14.0 N)
- `haptic_audio_effect`: String ("wax_crack_crisp_01.wav", "wax_fracture_heavy.wav")
- `revealed_content_preview`: String

### `InvisibleInkRevealed`
Emitted when secret runes are revealed under UV torchlight (`runefoble.events.lore.invisible_ink_revealed`).
- `handout_id`: UUID
- `campaign_id`: UUID
- `revealed_by`: String
- `secret_text`: String
- `uv_intensity`: Float

---

## 3D Relic Events (`aggregate_type: Relic`)

### `RelicForged`
Emitted when a 3D relic model is forged (`runefoble.events.lore.relic_forged`).
- `relic_id`: UUID (Aggregate identifier)
- `campaign_id`: UUID
- `name`: String
- `relic_type`: String ("amulet", "dagger", "puzzle_box", "ring", "chalice")
- `model_geometry`: String ("amulet_sunken_spire", "dagger_shadow_weave", "puzzle_box_celestial")
- `shader_properties`: Dict[str, Any] (PBR metallic, roughness, emissive parameters)
- `runes`: List[Dict[str, Any]] (Positions, inscriptions, translations)
- `is_secret`: Boolean (Restricted to DM/GMs)
- `created_by`: Optional[String]
- `metadata`: Dict[str, Any]

### `RelicInspected`
Emitted when a player rotates and inspects a 3D relic (`runefoble.events.lore.relic_inspected`).
- `relic_id`: UUID
- `campaign_id`: UUID
- `inspected_by`: String
- `name`: String
- `model_geometry`: String
- `shader_properties`: Dict[str, Any]
- `discovered_runes`: List[Dict[str, Any]]
- `inspection_notes`: Optional[String]

### `RelicRuneTranslated`
Emitted when an inscription is deciphered (`runefoble.events.lore.relic_rune_translated`).
- `relic_id`: UUID
- `campaign_id`: UUID
- `rune_id`: String
- `translated_by`: String
- `original_inscription`: String
- `translation`: String
