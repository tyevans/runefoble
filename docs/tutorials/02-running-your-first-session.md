# Tutorial 02: Running Your First Collaborative Session

## Objective
Walk through an interactive storytelling encounter where a player commands the board via voice, an absent player is substituted by an AI stand-in with a "Drunk" penalty, and The Watcher adjudicates the scene.

## Step 1: Start the API Gateway and Frontend
In terminal 1:
```bash
make dev-api
```
In terminal 2:
```bash
make dev-frontend
```

## Step 2: Open the Collaborative Table
Navigate to `http://localhost:5173`. You will observe:
1. The **Tactical Realm** grid showing 4 tokens (Valeros, Kyra, Goblin Scout, Red Dragon).
2. The **Character Card** for Kyra displaying the **🤖 AI Stand-in** badge and active penalties: `🍺 Drunk (Missed Session)` and `✨ Foolishness`.
3. The **Watcher Chronicle Feed** live stream.

## Step 3: Speak and Command the Board
Click the **Push to Talk** microphone button.
Say:
> *"Valeros moves 2 squares east to protect Kyra."*

Notice what happens:
1. The Watcher parses your movement intent (`dx: 2, dy: 0`).
2. Valeros's token animates two squares to the east.
3. The Watcher posts narrative confirmation to the Chronicle feed:
   *"Valeros stepped forward 2 squares. The Watcher observes your advance into the crypt."*

## Step 4: Trigger the Missing Player Stand-In
When Kyra's turn arrives, The Watcher automatically evaluates her character sheet and penalties:
- The "Drunk" penalty prompts Kyra to sway and boast: *"Hic! No dragon can outwit Sarenrae's finest vintner!"*
- The AI stand-in executes an action with disadvantage on perception and rolls `1d20-2`.
