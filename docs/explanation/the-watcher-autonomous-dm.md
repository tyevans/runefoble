# Explanation: The Watcher Autonomous DM Architecture

## The Problem of Tabletop DM Scarcity
In tabletop roleplaying, the Dungeon Master shoulders 90% of the cognitive and preparatory burden: memorizing hundreds of pages of rules, crafting scenes, voicing non-player characters, balancing tactical combat, and arbitrating player ingenuity.
This dynamic leads to "DM burnout" and scheduling paralysis.

## How The Watcher Operates
The Watcher is an AI-powered gameplay engine that operates in two modes:

### 1. Autonomous Game Master
When no human steps forward to DM, The Watcher assumes narrative stewardship:
- **Speech-to-Intent**: Parses natural player speech into concrete tactical moves, spellcasts, and conversational overtures.
- **Narrative Pacing**: Maintains tension arcs, adjusts monster tactics dynamically based on party health, and weaves environmental storytelling.
- **Rules Arbitration**: Applies tabletop physics and rulesets without breaking immersion.

### 2. Missing Player AI Stand-In with Penalty Infliction
When a human player cannot attend, their character remains active on the board:
- **Trait Mimicry**: The AI analyzes the character sheet (alignment, flaws, bonds, spells, personality traits like "valiant", "impulsive", "scholarly") to emulate their conversational cadence and tactical behavior.
- **DM Absence Penalties ("Session Miss Costs")**: To acknowledge absence humorously and narratively, the DM or group can inflict penalties:
  - *"Drunk"*: The character overindulged at the tavern. Disadvantage on perception, precision, and finesse checks (-2 roll penalty), slurred dialogue ("Hic!"), and staggering movements.
  - *"Foolishness"*: The character displays reckless bravado, ignoring tactical cover, taunting foes, and imposing disadvantage on enemy attacks against allies while drawing threat.
  - *"Cowardice"*: The character adopts defensive posturing and seeks tactical retreat vectors, crouching behind cover or sturdy allies.
  - *"Greed"*: The character prioritizes searching chests, grabbing loose coins, and inspecting ancient relics over optimal combat positioning.
- **Automated Turn Progression**: In `services/game_session`, when an absent character's turn arrives (`is_stand_in_active=True`), `POST /api/v1/sessions/{session_id}/turns/auto-pilot` invokes The Watcher engine, persists the stand-in action to the event-sourced session aggregate, emits `StandInActionDecided` and `AbsencePenaltyApplied` events to Redis Streams (`runefoble.events.watcher`), and advances the turn order.
- **Absentee Chronicle & Humorous Recap**: When the absent player returns for the next session, `POST /api/v1/watcher/stand-in/recap` compiles all stand-in decisions and active penalties into a comedic narrative recap with memorable quotes and battle highlights.
