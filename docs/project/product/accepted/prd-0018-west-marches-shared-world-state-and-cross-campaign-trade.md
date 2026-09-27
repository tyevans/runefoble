---
id: '0018'
title: West Marches Multi-Party Persistent Universe, Shared World Atlas & Cross-Campaign Trade
status: Accepted
created: 2026-09-26
---

# PRD-0018 — West Marches Multi-Party Persistent Universe, Shared World Atlas & Cross-Campaign Trade

## Who this is for

Worldbuilding artisans (like Rowan the Chronicler), downtime crafters (like Bram the Tinkerer), and community coordinators running West Marches open tables or multi-party shared campaigns where multiple adventuring groups explore the same living frontier.

## What the person cannot do today

- Tabletop campaigns operate in strict isolation; two parties adventuring in the same setting on different nights cannot discover each other's traces or interact with shared regional infrastructure.
- Collaborative map annotation is fragmented across third-party tools; when Party Blue clears a dungeon or builds a bridge, Party Gold has no way of seeing the updated frontier map next session.
- Crafting materials, trade surplus, and crafted magical goods are trapped in single-party inventories with no macro-economic outlet or cross-party trade routes.
- Guild strongholds, outposts, and settlement upgrades cannot be co-funded or shared across multiple adventuring groups.

## What good looks like

1. **Shared Persistent World State & Communal Atlas**:
   - A single canonical regional map shared across multiple campaigns within a West Marches guild or multi-party universe.
   - When any party discovers ancient ruins, clears an encampment, or charts a mountain pass, a persistent discovery pin with time-stamp and party credit is published to the shared world atlas.
2. **Cross-Campaign Caravan Trading & Economic Ledgers**:
   - Overland caravan scheduling engine simulating trade routes between player-settled frontier outposts and major trade hubs.
   - Players can dispatch goods, alchemical reagents, and crafted artifacts via caravans, arriving on scheduled game calendar dates to stock regional merchant inventories across campaigns.
3. **Communal Stronghold & Guild Haven Hub**:
   - A shared base-camp dashboard where multiple adventuring parties contribute gold and resources to construct workshop upgrades, arcane libraries, defensive walls, and resting sanctums.
   - Unlocked stronghold perks (e.g. bonus starting inspiration, masterwork crafting forge) benefit any guild party embarking on expeditions from the base.
4. **Frontier Bounty Board & Cross-Party Contracts**:
   - In-world mercenary contract board where parties post requests (e.g., "Gather 5 Wyvern scales in the Whispering Fen for 200 gold") or leave clues and warnings for fellow adventurers.

## What this does not do

- It does not expose hidden DM secrets, unmapped traps, or unvisited dungeon interiors to other parties before legitimate in-game discovery.
- It does not cause race conditions or conflicting overwrites when multiple parties adventure simultaneously; updates are coordinated via event-sourced optimistic concurrency.

## Checkable Outcomes

1. Discovery pins and map annotations published by one campaign appear on the shared world atlas across all linked campaigns in under 500ms.
2. Caravan trading ledgers execute atomic, idempotent transfers of inventory and gold without item duplication or ledger drift.
3. Communal stronghold upgrade contributions calculate collective milestone thresholds and dispatch rest boon events reliably over Redis Streams.
4. Interactive frontier bounty board supports real-time contract claiming, status updates, and payout verification across multi-party campaigns.

## Linked User Stories
- [`US-0058: West Marches Shared Persistent World State & Cross-Campaign Trade`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)
- [`US-0050: Collaborative Campaign Atlas and Multi-Layered Living Codex`](../../user_stories/accepted/us-0050-collaborative-campaign-atlas-and-living-codex.md)

## Implementing Backlog Tasks
- [`TASK-0127: West Marches Shared World State & Cross-Campaign Registry`](../../backlog/complete/0127-west-marches-shared-world-state-and-cross-campaign-registry.md)
- [`TASK-0129: Cross-Campaign Caravan Trading & Frontier Contracts`](../../backlog/complete/0129-cross-campaign-caravan-trading-and-frontier-contracts.md)
- [`TASK-0135: West Marches Shared World Atlas Pins & Stronghold Microfrontend`](../../backlog/complete/0135-west-marches-shared-atlas-and-stronghold-microfrontend.md)
- [`TASK-0136: Cross-Campaign Caravan Trading & Bounty Board Microfrontend`](../../backlog/complete/0136-cross-campaign-caravan-board-and-contracts-microfrontend.md)
- [`TASK-0164: Cross-Campaign Settlement and Haven Registry`](../../backlog/refined/0164-cross-campaign-settlement-haven-registry.md)
- [`TASK-0165: Frontier Mercenary Contract and Bounty Board Router`](../../backlog/refined/0165-frontier-mercenary-contract-bounty-board-router.md)
