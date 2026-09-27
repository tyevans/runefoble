---
id: '0017'
title: Autonomous NPC Faction Agendas, Geopolitical Radar & Living World Simulation
status: Accepted
created: 2026-09-26
---

# PRD-0017 — Autonomous NPC Faction Agendas, Geopolitical Radar & Living World Simulation

## Who this is for

Game Masters (like Evelyn the Overworked Dungeon Master) and worldbuilders (like Rowan the Chronicler) who want living, breathing campaign worlds that evolve dynamically between sessions without requiring hours of manual faction tracking and spreadsheet bookkeeping.

## What the person cannot do today

- Evelyn spends 8+ hours preparing weekly game nights; tracking background political shifts, faction moves, thieves' guild heists, and cult plots between sessions is mentally exhausting.
- Virtual campaign worlds freeze the moment players leave a town; NPCs remain static until players return, shattering the illusion of an evolving fantasy universe.
- DMs have no intuitive visual interface to monitor cross-faction rivalries, regional unrest, or background faction resources at a glance.
- Inaction by player parties has no automated consequences—if players ignore a growing goblin army or a corrupt merchant syndicate, the DM must manually remember and write consequences rather than having the world state advance naturally.

## What good looks like

1. **Autonomous Background Faction Simulation Engine**:
   - The Watcher executes inter-session simulation ticks where non-player factions, guilds, and villains advance active agendas based on resource dice rolls, defensive barriers, and regional stability.
   - Factions pursue goal hierarchies (e.g., "Infiltrate City Watch", "Smuggle Arcane Weapons", "Establish Frontier Outpost") with branching outcome trees (success, setback, rival interception, collateral discovery).
2. **Geopolitical Faction Radar & Interactive Node Graph**:
   - Dedicated DM microfrontend rendering an interactive radar and force-directed graph displaying faction influence, alliance vectors, hostility ratings, and territorial control zones.
   - Real-time heatmaps overlaying regional maps to show rising tension levels and contested borders.
3. **DM Intelligence Bulletin & Rumor Mill Generator**:
   - At the conclusion of a world tick, The Watcher compiles a concise, confidential DM intelligence brief detailing faction movements, clandestine operations, and power shifts.
   - Automatically populates local tavern rumor tables with public breadcrumbs and hearsay that players can organically discover during roleplay.
4. **Dynamic World State Ripple Effects on Tactical Play**:
   - Faction territory captures directly alter board states, merchant inventories, guard alertness, and environmental hazards when the party visits affected regions.
   - The Watcher seamlessly weaves faction updates into spoken NPC dialogue and spontaneous encounter tables.

## What this does not do

- It does not strip the DM of narrative control; all simulation tick results are presented as recommendations with a one-click DM veto, reroll, or manual override.
- It does not create chaotic or lore-breaking world destruction without respecting established campaign boundaries and RAG-indexed world rules.

## Checkable Outcomes

1. Faction agenda simulation ticks process up to 50 concurrent faction goals across multiple regions in under 500ms.
2. Geopolitical radar microfrontend renders reactive SVG/Canvas node graphs at 60fps with clear visual distinction between allied, neutral, and hostile factions.
3. Intelligence bulletins and tavern rumors generate structured markdown summaries within 2 seconds of simulation tick completion.
4. Regional board state mutations (outpost banners, merchant inventory modifiers, NPC dispositions) synchronize across Redis Streams and update tactical sessions automatically.

## Linked User Stories
- [`US-0057: Autonomous NPC Faction Agendas & Background Simulation Engine`](../../user_stories/accepted/us-0057-autonomous-npc-faction-agendas-and-world-simulation.md)
- [`US-0019: Ad-Hoc Ephemeral NPC Spawning and Scene Conditions`](../../user_stories/accepted/us-0019-ad-hoc-ephemeral-npc-spawning-and-scene-conditions.md)

## Implementing Backlog Tasks
- [`TASK-0126: Autonomous NPC Faction Agendas & World Simulation`](../../backlog/complete/0126-autonomous-npc-faction-agendas-and-world-simulation.md)
- [`TASK-0137: Autonomous NPC Faction Agendas Radar & Bulletin Microfrontend`](../../backlog/complete/0137-npc-faction-agendas-radar-and-bulletin-microfrontend.md)
- [`TASK-0161: NPC Faction Resource Operations and Bribery Mechanics Aggregate`](../../backlog/complete/0161-npc-faction-resource-and-bribery-aggregate.md)
- [`TASK-0162: Faction Turf War and Regional Unrest Event Pipeline`](../../backlog/proposed/0162-faction-turf-war-and-unrest-event-pipeline.md)
- [`TASK-0163: Faction Espionage and Alert Feeds Microfrontend`](../../backlog/proposed/0163-faction-espionage-radar-alerts-microfrontend.md)
