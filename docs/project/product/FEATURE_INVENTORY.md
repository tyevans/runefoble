# Speculative Feature Inventory & MVP Capability Matrix

This catalog inventories all speculative and visionary capabilities for Runefoble, categorizing them across functional domains and establishing their release tier:
- **P0 (MVP Launch)**: Critical path capabilities required for the first playable, collaborative AI-native storytelling experience.
- **P1 (Post-MVP Beta)**: High-value enhancements extending immersion, audio fidelity, and campaign persistence.
- **P2 (Future Horizon)**: Long-term moonshots including 3D spatial engines, generative video, and hardware accessories.

---

## 1. Tactical Board & Spatial Simulation Domain

| Feature ID | Feature Name | Description | Release Tier | Governing Systems |
|---|---|---|---|---|
| `FEAT-BRD-01` | **Spoken Movement Execution** | Spoken natural language commands (e.g. "Valeros moves 3 squares east") are parsed and immediately animate tokens on the board. | **P0 (MVP)** | `the_watcher`, `board_state` |
| `FEAT-BRD-02` | **Grid & Token Positioning** | Discrete grid cells (square/hex) supporting token placement, coordinates, collision detection, and drag-and-drop fallback. | **P0 (MVP)** | `board_state`, `frontend` |
| `FEAT-BRD-03` | **Dynamic Fog-of-War** | Tokens clear fog-of-war based on individual vision radii and lighting conditions; shared party visibility. | **P0 (MVP)** | `board_state`, `frontend` |
| `FEAT-BRD-04` | **Line-of-Sight & Cover Calculation** | Automatic raycasting to calculate half/three-quarters cover from terrain and wall obstructions. | **P1 (Beta)** | `board_state` |
| `FEAT-BRD-05` | **Procedural Battlemap Generation** | Generative image models synthesize tactical maps on demand from DM narrative descriptions, saved to Silo S3. | **P1 (Beta)** | `the_watcher`, `silo` |
| `FEAT-BRD-06` | **3D Animated Miniature Physics** | Full 3D WebGL miniature tokens with collision ragdolls and physical dice bouncing on terrain. | **P2 (Horizon)** | `frontend` |

---

## 2. Voice, Audio & Speech Processing Domain

| Feature ID | Feature Name | Description | Release Tier | Governing Systems |
|---|---|---|---|---|
| `FEAT-VOX-01` | **Collaborative Voice Channel** | Bidirectional push-to-talk audio streaming connecting party members and AI agents. | **P0 (MVP)** | `voice_agent`, `gateway_api` |
| `FEAT-VOX-02` | **Realtime Speech-to-Intent Pipeline** | Low-latency audio transcription (<200ms) with intent extraction for moves, attacks, spells, and narrative statements. | **P0 (MVP)** | `voice_agent`, `the_watcher` |
| `FEAT-VOX-03` | **AI Voice Persona Synthesis** | Distinct TTS voice profiles for The Watcher DM (deep mystical baritone) and character archetypes. | **P0 (MVP)** | `voice_agent` |
| `FEAT-VOX-04` | **Dynamic Vocal Audio Filters** | DSP audio filters applied to player and AI voices based on status conditions (e.g., drunkenness slurs, underwater muffling, ghostly echo). | **P0 (MVP)** | `voice_agent` |
| `FEAT-VOX-05` | **Ambient Dynamic Soundscape** | Adaptive background music and foley sound effects triggered by combat tension, dungeon atmosphere, and spell casts. | **P1 (Beta)** | `voice_agent`, `the_watcher` |
| `FEAT-VOX-06` | **Zero-Latency Neural Speech Duplex** | Real-time speech interruptions allowing human players to naturally cut off or interject while the AI DM speaks. | **P2 (Horizon)** | `voice_agent` |

---

## 3. The Watcher AI Gameplay & DM Engine Domain

| Feature ID | Feature Name | Description | Release Tier | Governing Systems |
|---|---|---|---|---|
| `FEAT-WAT-01` | **Autonomous Game Master** | The Watcher runs complete sessions when no human DM is present: setting scenes, managing monsters, arbitrating rules, and pacing encounters. | **P0 (MVP)** | `the_watcher`, `game_session` |
| `FEAT-WAT-02` | **Human DM Co-Pilot Assistant** | When a human DM runs the game, The Watcher suggests atmospheric descriptions, manages initiative, and resolves rule lookups. | **P0 (MVP)** | `the_watcher` |
| `FEAT-WAT-03` | **Missing Player AI Stand-In** | When a player is absent, The Watcher pilots their PC, mimicking their character traits, spells, and tactics without canceling session night. | **P0 (MVP)** | `the_watcher`, `character_sheet` |
| `FEAT-WAT-04` | **Session Miss Penalty Infliction** | The DM or group inflicts flavorful penalties on stand-ins (e.g., "Drunk" = slurred speech, courage boost, perception drop; "Foolishness" = reckless bravery). | **P0 (MVP)** | `the_watcher`, `character_sheet` |
| `FEAT-WAT-05` | **Chronicler Narrative Memory & Recap** | When an absent player returns, The Watcher delivers an audio/text recap of what their character did while under penalty influence. | **P0 (MVP)** | `the_watcher`, `game_session` |
| `FEAT-WAT-06` | **Campaign Lore Vector RAG** | Vector retrieval over custom campaign lorebooks, factions, NPCs, and historical world events. | **P1 (Beta)** | `the_watcher`, `silo` |
| `FEAT-WAT-07` | **Autonomous NPC Society Simulation** | Background factions pursue agenda ticks between sessions, altering the world state independently. | **P2 (Horizon)** | `the_watcher`, `game_session` |

---

## 4. Game Rules, Character Sheet & Session Management Domain

| Feature ID | Feature Name | Description | Release Tier | Governing Systems |
|---|---|---|---|---|
| `FEAT-RUL-01` | **Digital Character Sheets** | Tracking HP, armor class, initiative, spell slots, inventory items, and dynamic conditions. | **P0 (MVP)** | `character_sheet` |
| `FEAT-RUL-02` | **Encounter Turn & Initiative Tracking** | Turn ordering, round advancing, active turn highlighting, and delayed actions. | **P0 (MVP)** | `game_session` |
| `FEAT-RUL-03` | **Automated Dice Roller & Mechanics** | Standard RPG dice notation parsing (`1d20+5`, `2d6+3`), critical hit/fumble detection, advantage/disadvantage. | **P0 (MVP)** | `game_session`, `gateway_mcp` |
| `FEAT-RUL-04` | **SRD 5e / OGL Rule Compendium** | Built-in reference data for core classes, spells, monsters, and magical items. | **P1 (Beta)** | `character_sheet` |
| `FEAT-RUL-05` | **Level Up & Character Builder Wizard** | Interactive step-by-step leveling flow with subclass selection and spell selection. | **P1 (Beta)** | `character_sheet`, `frontend` |

---

## 5. Security, Authorization & Developer Platform Domain

| Feature ID | Feature Name | Description | Release Tier | Governing Systems |
|---|---|---|---|---|
| `FEAT-SEC-01` | **Zanzibar Object-Level Authorization** | SpiceDB fine-grained permissions for campaign ownership, DM delegation, player character editing, and spectator viewing. | **P0 (MVP)** | `runefoble_auth` |
| `FEAT-SEC-02` | **Self-Hosted Zitadel OIDC Authentication** | Secure user registration, login, and JWT issuance across all web and voice endpoints. | **P0 (MVP)** | `runefoble_auth` |
| `FEAT-DEV-01` | **Model Context Protocol (MCP) Server** | Tool and resource endpoints exposing dice rolls, board states, token movements, and DM prompts to external LLMs. | **P0 (MVP)** | `gateway_mcp` |
| `FEAT-DEV-02` | **Aggregated Swagger UI Hub** | Unified Swagger interface aggregating OpenAPI documentation across all microservices. | **P0 (MVP)** | `gateway_api`, `helm` |
| `FEAT-DEV-03` | **Redis Streams Event Fanout** | High-throughput, distributed event streaming across microservice bounded contexts. | **P0 (MVP)** | `runefoble_platform` |

---

## 6. Frontend, Design System & Player Immersion Domain

| Feature ID | Feature Name | Description | Release Tier | Governing Systems |
|---|---|---|---|---|
| `FEAT-UI-01` | **Bauhaus Modernist Theming System** | CSS custom property token system with Bauhaus modernist default aesthetic and multi-theme runtime switching. | **P0 (MVP)** | `frontend` |
| `FEAT-UI-02` | **Global Settings Modal & Mode Switcher** | Centralized settings modal with Dark / Light / System appearance mode toggle, moving theme controls out of the header. | **P1 (Beta)** | `frontend` |
| `FEAT-UI-03` | **Cross-Component Semantic Dark/Light Invariants** | Unified semantic tokens ensuring high-contrast, WCAG 2.1 AA compliant rendering in all components across dark and light modes. | **P1 (Beta)** | `frontend` |
| `FEAT-UI-04` | **Tactile Token Kinematics & Momentum** | Drag-and-drop token physics with momentum, spring dampening, step counters, and live waypoint route measurement. | **P1 (Beta)** | `frontend`, `board_state` |
| `FEAT-UI-05` | **Spoken Command Ghost Previews** | Real-time semi-transparent token trajectory and targeting ghost preview before voice mutations commit to the board. | **P1 (Beta)** | `frontend`, `the_watcher` |
| `FEAT-UI-06` | **Radial Token Action Menu & AoE Templates** | Contextual circular dial for one-tap token actions and rotatable geometric AoE spell templates with live target intersection highlighting. | **P1 (Beta)** | `frontend`, `board_state` |

---

## 7. Worldbuilding, In-World Artifacts & Living Codex Domain

| Feature ID | Feature Name | Description | Release Tier | Governing Systems |
|---|---|---|---|---|
| `FEAT-LRE-02` | **Generative In-World Handouts & Forged Letters** | AI synthesis of diegetic in-world artifacts: aged parchment, calligraphy, wax seals with stamp physics, and hidden runes. | **P1 (Beta)** | `campaign_lore`, `frontend` |
| `FEAT-LRE-03` | **3D Relic & Artifact Inspector** | Interactive WebGL canvas inspector allowing 3D rotation, inspection of engravings, attunement glow, and hidden compartment mechanics. | **P1 (Beta)** | `frontend`, `campaign_lore` |
| `FEAT-LRE-04` | **Living Campaign Atlas & Multi-Layered Codex** | Interactive world map with chronological timeline breadcrumbs, player secret notes, and collaborative party journal codex. | **P1 (Beta)** | `campaign_lore`, `frontend` |

---

## 8. Downtime Activities, Social Minigames & Base Building Domain

| Feature ID | Feature Name | Description | Release Tier | Governing Systems |
|---|---|---|---|---|
| `FEAT-DWN-01` | **Interactive Campfire & Long Rest Downtime Engine** | Campfire rest rituals, companion bonding, campfire storytelling prompts, and collaborative party banter generators. | **P1 (Beta)** | `game_session`, `the_watcher` |
| `FEAT-DWN-02` | **Alchemical Brewing, Enchanting & Recipe Synthesis** | Drag-and-drop reagent laboratory, volatile concoction risk tables, and custom homebrew crafting progression. | **P1 (Beta)** | `character_sheet`, `rules_compendium` |
| `FEAT-DWN-03` | **Interactive Tavern Minigames & Merchant Haggling** | Playable Liar's Dice, card tournaments, drinking challenges with DSP speech slurring, and personality-driven bartering. | **P1 (Beta)** | `game_session`, `voice_agent` |
| `FEAT-DWN-04` | **Party Stronghold, Camp & Base Customization** | Upgradable campsite and guildhall stronghold customization granting persistent party rest boons and defensive buffers. | **P1 (Beta)** | `game_session`, `board_state` |

---

## 9. Expressive Performance, Audio Leitmotifs & Particle VFX Domain

| Feature ID | Feature Name | Description | Release Tier | Governing Systems |
|---|---|---|---|---|
| `FEAT-EXP-01` | **Personal Character Leitmotifs & Theme Scoring** | Dynamic musical signatures woven into the adaptive audio soundtrack during heroic criticals, dramatic speeches, and death saves. | **P1 (Beta)** | `voice_agent`, `frontend` |
| `FEAT-EXP-02` | **Multi-Modal Kinetic Spell VFX & Particle Magic** | Spoken incantations trigger real-time WebGL particle bursts, chromatic fire, spell rings, and elemental trails on the board canvas. | **P1 (Beta)** | `frontend`, `board_state` |
| `FEAT-EXP-03` | **Generative Wardrobe, Emotion & State Portrait Gallery** | Dynamic character portrait variants adapting to current HP, conditions, disguised personas, and narrative milestones. | **P1 (Beta)** | `character_sheet`, `asset_forge` |

---

## 10. Hybrid Tabletop & Tangible Maker Domain

| Feature ID | Feature Name | Description | Release Tier | Governing Systems |
|---|---|---|---|---|
| `FEAT-MAK-01` | **Printable Tabletop Handout & Battlemap Forge** | 1-inch grid calibrated multi-page PDF map exports, printable folding papercraft standees, and diegetic letter printouts. | **P1 (Beta)** | `asset_forge`, `frontend` |
| `FEAT-MAK-02` | **3D Printable Miniature & Token STL Exporter** | Procedural 3D printable token bases, condition ring clips, and miniature STL generation for tabletop 3D printers. | **P2 (Horizon)** | `asset_forge` |


