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

## Linked User Stories
- [`US-0001: Spoken Tactical Board Manipulation`](../../user_stories/accepted/us-0001-player-commands-board-via-voice.md)
- [`US-0003: AI-Assisted Narrative Adjudication for Game Masters`](../../user_stories/accepted/us-0003-dm-adjudicates-scene-with-ai-assistance.md)
- [`US-0007: Autonomous DM Session Execution`](../../user_stories/accepted/us-0007-autonomous-dm-session-execution.md)
- [`US-0008: MCP Tool Invocation for Autonomous AI Agents`](../../user_stories/accepted/us-0008-mcp-tool-invocation-for-agents.md)
- [`US-0009: Fine-Grained Zanzibar Access Control for Campaign Roles`](../../user_stories/accepted/us-0009-zanzibar-campaign-access-control.md)
- [`US-0017: Human DM Veto and Private Narrative Co-Pilot Whispers`](../../user_stories/accepted/us-0017-human-dm-veto-and-narrative-copilot-whispers.md)
- [`US-0021: Conversational Intent Disambiguation and Multi-Action Combos`](../../user_stories/accepted/us-0021-conversational-intent-disambiguation-and-combos.md)
- [`US-0023: Spoken Reaction Interrupts and Ready-Action Triggers`](../../user_stories/accepted/us-0023-spoken-reaction-interrupts-and-ready-actions.md)
- [`US-0032: Custom LLM Provider Injection and Intent Middleware Interceptors`](../../user_stories/accepted/us-0032-custom-llm-provider-injection-and-intent-middleware.md)
- [`US-0035: Runtime MCP Tool Hot-Reloading and Web Component Extension Slots`](../../user_stories/accepted/us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md)

## Implementing Backlog Tasks
- [`TASK-0000: Bootstrap Repository and Platform Foundations`](../../backlog/complete/0000-bootstrap-repository-and-foundations.md)
- [`TASK-0001: Redis Streams Event Bus Infrastructure and Helm Integration`](../../backlog/complete/0001-redis-streams-event-bus-infrastructure.md)
- [`TASK-0002: Speech-to-Intent Sub-500ms Pipeline`](../../backlog/complete/0002-speech-to-intent-sub-500ms-pipeline.md)
- [`TASK-0013: Autonomous DM Session & Scene Orchestration Engine`](../../backlog/complete/0013-autonomous-dm-scene-orchestration.md)
- [`TASK-0017: Bauhaus Geometric Dice Physics & Roll Arithmetic Web Component`](../../backlog/complete/0017-bauhaus-dice-roller-component.md)
- [`TASK-0020: FastMCP Agent Tool Loop & Session State Context Server`](../../backlog/complete/0020-mcp-agent-tool-loop-context.md)
- [`TASK-0039: Sub-500ms Streaming Audio Whisper Transcription & VAD Pipeline`](../../backlog/complete/0039-streaming-whisper-speech-to-intent.md)
- [`TASK-0040: Modular APIRouter Decomposition for The Watcher & Game Session Microservices`](../../backlog/complete/0040-service-modular-router-decomposition.md)
- [`TASK-0053: DM Co-Pilot Whisper Prompts and Veto Override Engine`](../../backlog/complete/0053-dm-copilot-whisper-and-veto-override-engine.md)
- [`TASK-0054: Conversational Disambiguation and Compound Action Intents`](../../backlog/complete/0054-conversational-disambiguation-and-compound-intents.md)
- [`TASK-0062: Autonomous DM Presets, Monster Templates, and Combat Tactics Modular Decomposition`](../../backlog/complete/0062-autonomous-dm-presets-and-tactics-modular-decomposition.md)
- [`TASK-0069: Speech Intent Parser and Action Grammar Extractors Modular Decomposition`](../../backlog/refined/0069-speech-intent-parser-and-action-grammar-decomposition.md)
- [`TASK-0090: Modular Routers Blackbox Test Suite Modular Decomposition`](../../backlog/complete/0090-modular-routers-test-suite-decomposition.md)
- [`TASK-0093: DM Co-Pilot Router and Blackbox Test Suite Modular Decomposition`](../../backlog/complete/0093-dm-copilot-router-and-blackbox-test-suite-decomposition.md)
- [`TASK-0094: Intent Disambiguation Router and Blackbox Test Suite Modular Decomposition`](../../backlog/complete/0094-intent-disambiguation-router-and-blackbox-test-suite-decomposition.md)
