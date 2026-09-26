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
