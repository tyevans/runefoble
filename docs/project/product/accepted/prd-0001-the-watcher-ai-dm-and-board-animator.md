---
id: 0001
title: The Watcher AI Dungeon Master and Real-Time Board Animator
status: Accepted
created: 2026-09-25
---

# PRD-0001 — The Watcher AI Dungeon Master and Real-Time Board Animator

## Who this is for

Tabletop roleplaying groups who lack a human Dungeon Master, or human DMs who desire an autonomous assistant to handle real-time board manipulation and rule rulings.

## What the person cannot do today

Currently, virtual tabletop platforms require human players to manually click, drag, calculate distances, track line-of-sight, and fiddle with token menus. If no human steps up to spend 10+ hours preparing a campaign as DM, the group cannot play.

## What good looks like

- **Spoken Command Execution**: A player says "I advance 3 squares north and draw my blade," and within 500ms the tactical board animates the token and updates the narrative log.
- **Autonomous DM Narration**: When no human DM is present, The Watcher narrates atmospheric scene changes, arbitrates player decisions, and triggers monster actions.
- **Co-Pilot Assistance**: When a human DM is running the table, The Watcher functions as an assistant: resolving distances, managing initiative, and proposing descriptions.

## What this does not do

- It does not replace player free will; players can override any AI action.
- It does not require a rigid grammar; natural colloquial speech is supported.
- It does not force combat if players choose diplomacy or stealth.

## What it costs at scale

Low latency audio transcription and LLM inference require optimized streaming connections and token caching.

## Checkable Outcomes

1. Spoken voice commands parse to structured board actions within 500ms and animate tokens on the tactical grid.
2. The Watcher generates atmospheric narration, ambient sound prompts, and monster actions during combat encounters.
3. FastMCP gateway exposes dynamic session state resource (`session://{session_id}/state`) aggregating active tokens, scene atmosphere, and encounter threat level.
4. FastMCP tool `execute_agent_action_plan` sequentially validates and executes multi-turn action plans with per-step timing and error handling for out-of-bounds coordinates and invalid tools.

