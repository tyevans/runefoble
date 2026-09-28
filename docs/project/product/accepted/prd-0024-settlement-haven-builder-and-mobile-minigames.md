---
id: '0024'
title: Settlement Haven Builder, Living Urban Ecosystem & Mobile Web Minigames
status: Accepted
created: 2026-09-27
---

# PRD-0024 — Settlement Haven Builder, Living Urban Ecosystem & Mobile Web Minigames

## Who this is for

- **The Civic Architect / Frontier Mayor (Mayor Theron)**: Players and DMs who want to design, zone, and upgrade living settlements—from roadside hamlets and frontier havens to walled market towns and grand metropolises—tracking industries, trade logistics, and civic prosperity.
- **The Mobile Barfly / Social Gambler (Kip the Nimble)**: Players who want to engage directly from their smartphones (mobile web / PWA, no app download required) during rests, downtime, or social tavern scenes, shooting darts, shooting pool, betting copper in Liar's Dice, or trying their hand at casino roulette and craps.
- **The Merchant-Tycoon / Supply-Chain Opportunist (Lady Nicole)**: Players who immerse in trade, shop inventories, price fluctuations, and high-stakes haggling against personality-driven shopkeepers with DM oversight.
- **The Storyteller / Living World DM (Evelyn / The Watcher)**: Game Masters who need settlements populated with interconnected NPC workers who possess dynamic inventories, distinct temperaments, secret knowledge, and intricate interpersonal drama.
- **The Table Spectator / Bystander (Sam)**: Casual companions or stream viewers who join via a quick QR code scan on their phone to place friendly wagers, read town bulletin notices, or trigger pub cheering effects.

## What the person cannot do today

- **Static Settlements**: Towns in conventional VTTs are flat battlemap backgrounds or static folders of notes with no geographic logic, no simulated industry, and no interactive settlement building mechanics.
- **Disjointed Downtime**: Non-combat social gameplay is treated as passive theater or spreadsheet tallying, lacking tactile, multiplayer minigames that party members can play together while seated at the table.
- **Desktop Clutter & App Friction**: Players wanting mobile participation during downtime are forced to download heavy native app store packages or struggle with desktop-centric interfaces crammed onto small screens.
- **Lifeless Storefronts**: Shopping is reduced to reading equipment lists from a compendium with static prices, devoid of merchant personalities, social bartering dynamics, or DM negotiation controls.
- **Isolated NPCs**: NPCs are single-note stat blocks with no operational workplace roles, no memory of town events, and no systemic relationships with other merchants or local institutions.

## What good looks like

1. **Macro Geographic Genesis & Settlement Scaling Engine**:
   - Geographically grounded settlement formation modeling natural resources, river confluences, mountain passes, deepwater harbors, and trade route isochrones based on Central Place Theory.
   - Five distinct settlement scales with procedural and customizable spatial layouts:
     - **Hamlet / Thorp** (Pop: 20–150): Ribbon or cluster layout, communal well, wayside inn/smithy.
     - **Village / Frontier Haven** (Pop: 150–1,000): Radial green layout, timber palisade, bakery, chapel, general trading post.
     - **Market Town** (Pop: 1,000–6,000): Walled perimeter, paved marketplace, artisan quarters, guildhalls, town watch barracks, bulletin board.
     - **Fortified City / Provincial Capital** (Pop: 6,000–25,000): Multi-ring defensive walls, segregated districts (Jewelers' Row, Docks, Temple Quarter, High Citadel), civic coliseum, dedicated gambling halls.
     - **Grand Metropolis** (Pop: 25,000–100,000+): Sprawling quarters, monumental architecture, high-roller gilded casinos, imperial banks, planar curio markets.

2. **Customizable Establishments & Assignable Living NPC Workers**:
   - Building categories: Hospitality (taverns, coaching inns, casinos), Commerce (weaponsmiths, bakeries, apothecaries, leatherworkers, general outfitter), Civic (town hall, guardhouse, public square, bulletin board), Faith (shrines, cathedrals, crypts), and Underworld (fencing dens, fighting pits, thieves' dens).
   - Assignable NPC workers featuring dynamic workplace assignments (e.g. Head Baker, Master Armorer, Pit Boss, Tavern Bouncer).
   - Rich NPC social webs: Personalities (Big Five quirks, vices, temperaments), dynamic shelf vs vault inventories, knowledge/rumors observed, and interpersonal relationships (loyalty, debts, rivalries).

3. **Mobile-First Responsive Web Minigames Suite (Zero App Install)**:
   - Ultra-responsive, touch-first progressive web experience running smoothly in mobile Safari/Chrome with haptic vibration feedback (`navigator.vibrate`) and low-latency WebSocket multiplayer.
   - **Tavern & Common Spot Games**:
     - *Darts & Knife Throwing*: Touch-drag aiming with velocity flick, wind deflection, pub cricket and 501 rules.
     - *Tabletop Billiards / Pub Pool*: Overhead 2D physics, cue stick pull-back and angle control, multiplayer turn synchronization.
     - *Liar's Dice (Perudo)*: Accelerometer cup shake, private peek shield, bluffing bids, party-wide elimination.
     - *Arm Wrestling / Drinking Contest*: Dual-touch rhythm endurance, stamina gauge management, dynamic audio DSP speech slurring.
   - **Casino & Gaming Hall Games**:
     - *Imperial Roulette / Wheel of Fortune*: Multi-player digital felt betting, rotating physics wheel, customizable house edge.
     - *Dragon's Craps / Street Bones*: Two-finger physical dice toss onto felt trays, pass line and prop bets, synchronized crowd cheer foley.
     - *Three-Dragon Ante / Gilded Blackjack*: Touch card dealing, split/double down, tactile slide-to-peek card mechanic.

4. **Personality-Driven Merchant Haggling with DM Arbitration**:
   - Interactive bartering interface featuring dynamic price tug-of-war, persuasive rhetoric moves (flattery, intimidation, bundling, sob story), and merchant patience/temperament meters.
   - Live DM arbitration controls: Game Masters can view ongoing negotiations, dynamically adjust merchant mood or patience, inject narrative dialogue lines, or exercise one-click acceptance/veto.

5. **Civic Gathering & Town Bulletin Board**:
   - Interactive bulletin board with pinned parchment notices: guild bounties, missing persons, town ordinances, tavern flyers, and cryptic cipher mini-puzzles.
   - Players can pin their own requests (e.g. mercenary contracts, reagent purchase requests) and inspect local town rumors.

## What this does not do

- It does not require players to install a native iOS or Android app; everything runs in modern mobile web browsers with standard responsive Web Components.
- It does not turn Runefoble into an idle-clicker city simulator; town growth is tied directly to campaign progression, adventurer investments, and narrative milestones.
- It does not remove DM authority over shops or gambling; human DMs retain real-time veto power and setting sliders for house margins, law enforcement vigilance, and price elasticity.

## Checkable Outcomes

1. Players navigating to `#/campaigns/:id/town` on a mobile smartphone viewport experience a fluid, touch-optimized UI with sub-100ms response time and zero layout clipping.
2. An establishment created in the town builder persists in the domain aggregate and reflects assigned NPC workers, inventory goods, and district affiliation.
3. Multiplayer minigames (such as Darts, Pool, Liar's Dice, Roulette, and Craps) synchronize turns, dice rolls, and bets across multiple connected mobile clients over WebSockets within 150ms.
4. The merchant bartering interface evaluates player persuasion tactics against merchant temperaments, updating negotiation prices with live DM veto/override hooks.
5. Pinned bulletin board notices emit domain events and synchronize across party member viewports in real time.

## Linked User Stories

- [`US-0072: Mobile-Responsive Settlement Browser and Town Haven Builder`](../../user_stories/accepted/us-0072-mobile-responsive-settlement-browser-and-town-builder.md)
- [`US-0073: Customizable Establishments with Assignable NPC Workers and Social Relationship Web`](../../user_stories/accepted/us-0073-customizable-establishments-and-assignable-npc-workers.md)
- [`US-0074: Interactive Mobile Web Tavern and Casino Minigames Suite`](../../user_stories/accepted/us-0074-interactive-mobile-tavern-and-casino-minigames.md)
- [`US-0075: Dynamic Merchant Haggling Engine with Temperament State and DM Controls`](../../user_stories/accepted/us-0075-dynamic-merchant-haggling-with-dm-arbitration.md)
- [`US-0076: Civic Bulletin Board, Town Rumor Network, and Bounty Proclamations`](../../user_stories/accepted/us-0076-town-bulletin-board-civic-rumors-and-bounties.md)

## Implementing Backlog Tasks

- [`TASK-0259: Settlement Haven Builder and Establishment Aggregate Domain Model`](../../backlog/proposed/0259-settlement-haven-builder-and-establishment-aggregate.md)
- [`TASK-0260: Assignable NPC Worker Engine and Social Relationship Graph`](../../backlog/proposed/0260-assignable-npc-worker-and-social-relationship-graph.md)
- [`TASK-0261: Mobile-First Touch-Optimized Tavern and Casino Minigames Suite`](../../backlog/proposed/0261-mobile-first-touch-optimized-tavern-casino-minigames.md)
- [`TASK-0262: Interactive Merchant Haggling Engine with DM Arbitration Controls`](../../backlog/proposed/0262-interactive-merchant-haggling-engine-with-dm-controls.md)
- [`TASK-0263: Town Bulletin Board, Civic Proclamations, and Rumor Network`](../../backlog/proposed/0263-town-bulletin-board-civic-notices-and-bounty-board.md)
- [`TASK-0264: Settlement Builder and Mobile Minigames Blackbox Test Suite`](../../backlog/proposed/0264-settlement-builder-and-minigames-blackbox-test-suite.md)
