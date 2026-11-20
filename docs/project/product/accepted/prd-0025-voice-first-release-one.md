---
id: '0025'
title: Voice-First Release One for a Private Group
status: Accepted
created: 2026-11-19
target_persona: Evelyn, Marcus, Sarah
component: platform
---

# PRD-0025 — Voice-First Release One for a Private Group

## Who this is for

- **The DM (Evelyn)**: runs a weekly game for a group of friends. She invites the players, sets up the session board, and keeps control of every AI action.
- **The players (Marcus, Sarah)**: join from a laptop in their own homes. They speak commands to move their tokens and roll dice. They talk to each other on their usual voice chat, outside Runefoble.

Release one is for a private, invite-only group on one hosted cluster with one domain. Open public sign-up is not in this release.

## What the person cannot do today

The research for this release is in `.audit/research/r1-voice-path.md`, `r1-watcher-llm.md`, `r1-hosting.md` and `r1-core-journeys.md`.

- **A friend cannot join.** The invite link opens `#/join/<token>`, and the App Shell has no route for it. Before generation, the link field shows a sample token.
- **Speech does nothing for the game.** Push to Talk only draws a level meter. No browser code sends audio. The gateway has no transcribe route. A false "WebRTC Live" badge shows.
- **A spoken move goes nowhere.** The Watcher reads only `to_x`/`to_y` or `dx`/`dy`, and the worker returns `target_x`/`target_y`, so the ghost preview has the same cell as the origin. The grammar does not parse "move my warrior to the chest".
- **No typed command exists.** The session view has no command input.
- **Dice are local.** The roller shows "Hero" and the result reaches nobody else.
- **The DM sees invented whispers**, and the Veto button does nothing.
- **Readiness and stand-ins are lost on reload.**
- **A session never ends.** No end control and no recap exist.
- **The platform runs only on local Kind.** Ingress is HTTP only, so browsers refuse microphone access for remote players. Every credential has a development default. Mailpit receives all email. No backups exist.

## What good looks like

1. Evelyn signs up, creates a campaign, and sends an invite link. Marcus and Sarah open the link, create their accounts from it (Zitadel sends the email to set a password), and join the campaign through the UI. Open self-registration is off (ADR-0023).
2. Each player creates a character. Evelyn opens a lobby. The players mark themselves ready. An absent player gets an AI stand-in. The state survives a page reload.
3. Evelyn launches the session and sets up the battlemap.
4. Marcus holds Push to Talk and says "move my warrior to the chest". A ghost preview shows the path to the chest. He confirms, and the token moves on every screen. He can also type the same command.
5. Sarah says "roll a d20". Every player sees the result in the chronicle with her character name.
6. Evelyn gets whispers that The Watcher writes with the language model. She vetoes an AI action, and the action does not happen. With no model configured, the whisper bar says that no model is configured.
7. Evelyn ends the session. Every player sees a recap of the session chronicle.
8. All of this runs on one hosted cluster over HTTPS, with real email, private credentials, daily database backups, and invite-only sign-up.

## What this does not do

- No in-app voice chat between players. Push to Talk sends game commands only, over HTTPS. No WebRTC or TURN server is needed.
- No open public sign-up, abuse controls or autoscaling.
- No duplex barge-in (TASK-0508 to TASK-0510 stay out of this release).
- No latency target is claimed until it is measured (ADR-0022 (e)).
- The broad features of earlier PRDs (West Marches, broadcast, 3D, crafting and others) stay as they are. This release does not add to them.

## What it costs at scale

- The speech-to-text engine and the language model run on a GPU host outside the cluster. One host serves one group. A second group needs a sizing review.
- A daily backup of PostgreSQL needs storage outside the cluster.

## Checkable Outcomes

1. A Playwright scenario covers account setup through Mailpit (development) or real SMTP (hosted), campaign creation, invite, join through the invite link, character creation, lobby, ready, launch, battlemap set-up, a drag move, a typed move, a spoken move (fake microphone, real speech-to-text engine), a dice roll, a whisper and veto, and session end with recap. Setup uses only the UI (Hard Invariant 7).
2. The spoken move scenario prints the time from Push to Talk release to the ghost banner.
3. The full e2e suite passes twice in a row on Kind.
4. The hosted profile renders with no development default (a render guard fails on any `DEV-ONLY` value), serves HTTPS only, and turns off Mailpit, `/mail`, `/docs` and `/analytics`.
5. A backup restore test recovers a campaign from a PostgreSQL backup.
6. The CI pipeline builds the images, installs the chart in a cluster, and runs a smoke scenario.

## Linked User Stories

- [`US-0001: Player Commands the Board via Voice`](../../user_stories/accepted/us-0001-player-commands-board-via-voice.md)
- [`US-0017: Human DM Veto and Narrative Co-Pilot Whispers`](../../user_stories/accepted/us-0017-human-dm-veto-and-narrative-copilot-whispers.md)
- [`US-0005: Absentee Session Chronicle Recap`](../../user_stories/accepted/us-0005-absentee-session-chronicle-recap.md)
- [`US-0063: Campaign Creation, Dashboard Hub, and SpiceDB Zanzibar Member Access Control`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
- [`US-0065: Game Session Pre-Game Lobby, Participant Readiness, and Live Launch Orchestration`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)

## Governing Decisions

- ADR-0022: Grammar-First Intent Routing for the Voice Loop.
- ADR-0023: A Campaign Invite Link Creates the Player Account.
- ADR-0015: Audit Remediation Decisions (no hidden fallbacks, service credentials, event store).
- ADR-0005: Kubernetes-first infrastructure with Helm and Kind.
- ADR-0013, ADR-0014: microfrontends, BDD and Playwright.

## Implementing Backlog Tasks

Voice loop: TASK-0942 to TASK-0947. The Watcher and the model: TASK-0948, TASK-0949. Core journey: TASK-0967, TASK-0950 to TASK-0954, TASK-0654, TASK-0655. Hosting: TASK-0933, TASK-0955 to TASK-0965. `docs/project/backlog/PRIORITY.md` lists them under "Release One".
