# Runefoble User Personas

Derived from our speculative feature inventory, these five archetypes represent the spectrum of storytellers, players, spectators, and builders who interact with Runefoble.

---

## 1. Evelyn — The Overworked Dungeon Master
- **Role**: Human Game Master running weekly campaigns for 4–6 players.
- **Pain Points**:
  - Spends 8+ hours preparing maps, monsters, and stat blocks each week.
  - Gets bogged down in spatial math, line-of-sight arguments, and turn bookkeeping during combat.
  - Frustrated when an absent player forces her to cancel game night or awkwardly control their character.
- **Goals with Runefoble**:
  - Let The Watcher handle tactical math, token moves, and initiative rotation so she can focus purely on dramatic storytelling.
  - Have The Watcher stand in for absent players with humorous penalties like "drunk" to keep momentum.
  - Use The Watcher as an atmospheric co-pilot that suggests sensory descriptions and monster banter on the fly.
- **Key Features Used**: `FEAT-WAT-02`, `FEAT-WAT-03`, `FEAT-WAT-04`, `FEAT-BRD-01`, `FEAT-BRD-03`, `FEAT-SEC-01`.

---

## 2. Marcus — The Voice-First Casual Adventurer
- **Role**: Player controlling a Fighter/Paladin character.
- **Pain Points**:
  - Hates looking down at complicated digital menus, dragging tokens with a mouse, or calculating grid distances.
  - Wants tabletop gaming to feel like conversational theater with friends, not spreadsheet management.
- **Goals with Runefoble**:
  - Speak naturally ("I charge three squares north and prepare my shield") and see the board respond immediately.
  - Hear atmospheric audio and see dynamic visual confirmation of his heroism without touching keyboard shortcuts.
- **Key Features Used**: `FEAT-BRD-01`, `FEAT-VOX-01`, `FEAT-VOX-02`, `FEAT-RUL-01`, `FEAT-RUL-03`.

---

## 3. Sarah — The Absent Player
- **Role**: Party member (Cleric) whose demanding work/family schedule causes her to miss 1 out of every 4 sessions.
- **Pain Points**:
  - Guilt over causing session cancellations or throwing off party combat balance.
  - Returning to a game with no idea what happened to her character or missing out on inside jokes.
- **Goals with Runefoble**:
  - Never want game night canceled on her account.
  - Love that her character remains active via an AI stand-in that mimics her persona.
  - Enjoy the playful penalties inflicted by her friends ("Kyra drank too much dwarven stout and spent the dungeon stumbling into traps").
  - Listen to a 2-minute Watcher recap when she returns next week.
- **Key Features Used**: `FEAT-WAT-03`, `FEAT-WAT-04`, `FEAT-WAT-05`, `FEAT-VOX-03`, `FEAT-VOX-04`.

---

## 4. Devon — The Live Streamer / Spectator
- **Role**: Content creator broadcasting tabletop actual-play sessions on Twitch/YouTube, and spectator fans watching the stream.
- **Pain Points**:
  - Dead air on stream while DMs shuffle papers or calculate spell areas.
  - Ugly virtual tabletop interfaces cluttered with stat sheets that distract viewers from the narrative.
- **Goals with Runefoble**:
  - Clean, dramatic, animated board views that update instantaneously via WebSockets.
  - Live Watcher Chronicle feed providing a real-time transcript of dialogue, dice rolls, and atmospheric narration.
  - Fine-grained spectator permissions preventing stream viewers from manipulating tokens.
- **Key Features Used**: `FEAT-BRD-01`, `FEAT-BRD-02`, `FEAT-VOX-01`, `FEAT-SEC-01`, `FEAT-WAT-01`.

---

## 5. Alex — The Developer / Plugin Modder
- **Role**: Software engineer and homebrew system creator building custom tools, Discord bots, and AI DM integrations.
- **Pain Points**:
  - Proprietary VTTs with closed APIs or brittle DOM scraping.
  - Difficulties hooking LLM agents directly into real-time tabletop state.
- **Goals with Runefoble**:
  - Standard Model Context Protocol (MCP) server exposing tools like `roll_dice`, `inspect_tactical_board`, and `move_board_token`.
  - Clean OpenAPI specifications aggregated in a single Swagger UI.
  - High-throughput Redis Streams event broker allowing external microservices to consume domain events in real time.
- **Key Features Used**: `FEAT-DEV-01`, `FEAT-DEV-02`, `FEAT-DEV-03`, `FEAT-SEC-01`.

---

## 6. Rowan — The Chronicler & Worldbuilding Artisan
- **Role**: Lorecrafter, cartographer, and narrative co-creator (Bard/Wizard player, or co-DM).
- **Pain Points**:
  - Virtual handouts feel like plain text windows instead of tactile, diegetic fantasy artifacts.
  - Worldbuilding lore is fragmented in personal notes; the group lacks a shared living atlas or collaborative memory codex.
  - Zero connection between digital session lore and real-world physical props (papercraft, printable handouts, 3D tokens).
- **Goals with Runefoble**:
  - Generate and inspect diegetic in-world artifacts: ancient letters with broken wax seals, illuminated manuscripts, weathered parchment with hidden runes, and interactive 3D rotating relics.
  - Annotate a shared living campaign atlas with timeline pins, faction rumor webs, and collaborative codex entries.
  - Export calibrated 1-inch printable battlemaps, papercraft character standees, and 3D printable STL token rings for hybrid game nights.
- **Key Features Used**: `FEAT-LRE-02`, `FEAT-LRE-03`, `FEAT-LRE-04`, `FEAT-MAK-01`, `FEAT-MAK-02`.

---

## 7. Bram — The Tinkerer & Downtime Crafter
- **Role**: Tactician, artisan, and social roleplayer (Artificer/Rogue/Druid player).
- **Pain Points**:
  - VTT sessions frequently reduce non-combat downtime to quick hand-waving or tedious accounting.
  - Crafting, potion brewing, and enchanting feel like static spreadsheet lookups rather than creative, experimental game loops.
  - Gold and loot accumulate with little expressive outlet—no base-building, camp customization, or social tavern minigames.
- **Goals with Runefoble**:
  - Engage in rich campfire downtime activities during rests: experimenting with alchemical catalysts, forging custom item infusions, and training animal companions.
  - Challenge NPCs and party members to interactive tavern minigames (Liar's Dice, card wagering, drinking contests with dynamic voice DSP slurring).
  - Build and customize a persistent party campsite, wagon caravan, or stronghold that grants unique rest boons.
  - Haggle with shopkeepers possessing dynamic personality temperaments and reactive regional inventories.
- **Key Features Used**: `FEAT-DWN-01`, `FEAT-DWN-02`, `FEAT-DWN-03`, `FEAT-DWN-04`.

---

## 8. Nadia — The Expressive Thespian & Performer
- **Role**: Dramatic roleplayer and sensory creative (Bard/Sorcerer/Warlock player).
- **Pain Points**:
  - Combat boards feel purely mechanical; spells lack visual and emotional weight beyond numbers in a chat box.
  - Lack of distinct auditory identity—no personalized musical theme or dramatic sound triggers for signature character moments.
  - Character appearance is frozen in a single static token portrait, ignoring story progression, wounds, or disguise spells.
- **Goals with Runefoble**:
  - Define character musical leitmotifs that weave dynamically into the encounter soundtrack during clutch criticals, inspiration turns, or death saves.
  - Trigger kinetic WebGL spell visual effects and particle animations across the board canvas when speaking spell incantations.
  - Maintain an evolving generative wardrobe and emotional portrait gallery (battle-worn, masked, festive, shadow-infused) reflecting current game state.
- **Key Features Used**: `FEAT-EXP-01`, `FEAT-EXP-02`, `FEAT-EXP-03`, `FEAT-VOX-05`.

