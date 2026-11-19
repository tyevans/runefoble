# Tutorial 02: Running Your First Collaborative Session

## Objective

This tutorial shows how far a session runs on the platform today. It covers the App Shell steps in order. Each step has a status line.

- `Available`: the step works as written.
- `Not yet available: <blocker>`: the step does not work. Do not expect the result that the step would show. The blocker names the task or gap that stops it.

The target design is in [The Watcher as an Autonomous DM](../explanation/the-watcher-autonomous-dm.md). This tutorial does not describe that design as working.

## Status Summary

| Step | Action | Status |
|---|---|---|
| 1 | Start the gateway and the frontend | Available |
| 2 | Sign in, create a session, and launch it | Available. The table route then shows a load error. |
| 2b | Open the live table with a board and tokens | Not yet available: no App Shell route creates a board |
| 2c | Read the session feed | Endpoint available. The App Shell shows it only after step 2b. |
| 2d | Apply a penalty to a character | Available |
| 3 | Speak a command to the board | Not yet available: no App Shell caller, and `board_state` does not apply a spoken move |
| 4 | Run a stand-in turn for an absent player | Not yet available: no App Shell control or automatic trigger |

## Step 1: Start the Gateway and the Frontend

Status: `Available`.

Complete [Tutorial 01](01-local-development-setup.md) first. It starts the platform services that the gateway needs.

In terminal 1, run:

```bash
make dev-api
```

The gateway listens on port 8000. Set `GATEWAY_PORT` to change the port.

In terminal 2, run:

```bash
make dev-frontend
```

Vite serves the App Shell on port 5173. Vite sends every `/api/v1` request to the gateway.

Open `http://localhost:5173` in a browser.

## Step 2: Sign In, Create a Session, and Launch It

Status: `Available` for sign-in, campaign, session, and lobby. The table route shows a load error after launch, until step 2b is available.

1. Sign in on the login route (`#/login`).
2. Open the campaign list (`#/campaigns`). Create a campaign.
3. Open the campaign. Create a session.
4. Open the session lobby (`#/campaigns/<campaign id>/lobby/<session id>`). Check the participant list.
5. Choose a character for your seat.
6. As the DM, select launch. The App Shell sends a `session_started` message and opens the session route (`#/campaigns/<campaign id>/sessions/<session id>`).

On the session route, the App Shell calls `GET /api/v1/boards/<session id>`. No board exists for a new session, so the gateway returns `404`. The App Shell then shows a data error with a retry control. It does not show the table.

## Step 2b: Open the Live Table

Status: `Not yet available`. Blocker: no backlog task exists yet for an App Shell route that creates a board or places tokens.

The board service creates a board only through `POST /api/v1/boards`. The MCP tool `create_encounter` calls that route. No App Shell view calls it. No App Shell view places a token either.

When a board exists, the table shows the tokens that `GET /api/v1/boards/<session id>` returns. The App Shell does not add or change token data. Do not expect a fixed set of tokens.

## Step 2c: Read the Session Feed

Status: The endpoint `GET /api/v1/sessions/<session id>/events` is `Available`. The App Shell shows the feed only on the table route, so the feed is `Not yet available` until step 2b is.

The feed lists these line kinds, in commit order:

- `session_started`
- `dice_roll`
- `stand_in_action`
- `session_ended`

Speech lines are not in the feed. A session with no events returns an empty list.

## Step 2d: Apply a Penalty to a Character

Status: `Available`. This step does not need the table.

1. Open the character roster (`#/characters`). Select a character.
2. In the panel named Conditions and Penalties, open the list. Choose the option under Runefoble Absence Penalties:
   - `Drunk (Session Miss)`
   - `Foolishness (Session Miss)`
   - `Greed (Session Miss)`
   - `Cowardice (Session Miss)`
3. Select Apply.

The App Shell sends `POST /api/v1/characters/<character id>/conditions` with the penalty key. The panel then lists the penalty. The badge shows the lowercase key, for example `drunk`. Select the close control on the badge to remove the penalty.

The table character card (`runefoble-character-card`) does not show conditions. It shows the `AI Stand-in` badge only when the character record has the stand-in flag set. See step 4.

## Step 3: Speak a Command to the Board

Status: `Not yet available`. Blockers: an App Shell task that is not yet filed, and no board path that applies a spoken move.

What works today:

- Push to Talk on the voice controls toggles the listening state. The control draws a waveform from the microphone.
- The control does not send audio or text to a server.

What does not work today:

- `POST /api/v1/watcher/speak-and-act` proxies to The Watcher intent route. The Watcher parses the transcript. Nothing moves the token on the board yet.
- No App Shell code calls `POST /api/v1/voice/transcribe`, `POST /api/v1/watcher/transcribe-and-act`, or `POST /api/v1/watcher/speak-and-act`.
- Nothing moves a token from a spoken command.

## Step 4: Run a Stand-In Turn for an Absent Player

Status: `Not yet available`. Blockers: no App Shell control calls the stand-in routes, and no automatic trigger runs at the start of a turn.

The public API has these routes. The App Shell does not call them:

- `POST /api/v1/sessions/<session id>/leave`: saves the leave. It also activates the character stand-in in the character service.
- `POST /api/v1/sessions/<session id>/turns/auto-pilot`: runs one stand-in turn through The Watcher. It needs the `RUNEFOBLE_WATCHER_URL` setting. It does not run on its own.

The lobby control `Mark Absent (AI Stand-In)` does not save anything. It sends a `player_stand_in` WebSocket message. The gateway broadcasts that message to the session, and no service stores it.

Do not expect the AI stand-in to act, or the penalty to change a roll, during a session.

## Current Limits

Each limit below has no App Shell path yet. Fix the blocker, then update the status line of the step.

| Limit | Affects | Blocker |
|---|---|---|
| No App Shell route creates a board or places tokens | Steps 2b, 2c | No backlog task yet |
| A spoken move waits for the player's `confirm_move` on the board socket. The App Shell does not send `confirm_move` for a spoken proposal yet | Step 3 | No backlog task yet |
| The App Shell does not call any speech route | Step 3 | No backlog task yet |
| The App Shell does not call the leave or auto-pilot routes | Step 4 | No backlog task yet |
| No automatic stand-in trigger runs at a turn start | Step 4 | No backlog task yet |
| The lobby stand-in control does not save state | Step 4 | No backlog task yet |

Tutorial 02 is verified against the code. A live run on a local stack is not yet recorded. Re-check each status line after the blockers land.
