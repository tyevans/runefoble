# How-To: Resolve Conversational Disambiguation & Compound Action Combos

This guide explains how to use The Watcher's conversational disambiguation and compound action engine (TASK-0054, PRD-0001, US-0021) to parse multi-part tactical combos and clarify ambiguous voice targets in real time.

---

## 1. Detecting Ambiguous Entity References

When a voice-first player issues a command targeting an ambiguous entity (e.g., *"I shoot the goblin"* when multiple goblins occupy the grid), The Watcher detects ambiguity against active board entities within sub-400ms:

```bash
curl -X POST http://localhost:8001/api/v1/watcher/intent/parse \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-crypt-01",
    "campaign_id": "campaign-valeros",
    "speaker_id": "marcus-1",
    "speaker_name": "Marcus",
    "transcript": "I shoot the goblin",
    "from_x": 2,
    "from_y": 2,
    "entities": [
      {
        "id": "goblin_archer",
        "name": "Goblin",
        "tag": "archer",
        "descriptor": "archer by the pillar",
        "x": 5,
        "y": 3
      },
      {
        "id": "goblin_shaman",
        "name": "Goblin",
        "tag": "shaman",
        "descriptor": "shaman on the altar",
        "x": 8,
        "y": 9
      }
    ]
  }'
```

### Clarification Response

```json
{
  "session_id": "session-crypt-01",
  "speaker_name": "Marcus",
  "transcript": "I shoot the goblin",
  "requires_disambiguation": true,
  "disambiguation_id": "disambig-9a7f32bc1042",
  "clarification_prompt": "Which goblin? The archer by the pillar or the shaman on the altar?",
  "candidates": [
    {
      "id": "goblin_archer",
      "name": "Goblin",
      "tag": "archer",
      "descriptor": "archer by the pillar",
      "x": 5,
      "y": 3,
      "distance_ft": 15,
      "preview_coordinates": [5, 3]
    },
    {
      "id": "goblin_shaman",
      "name": "Goblin",
      "tag": "shaman",
      "descriptor": "shaman on the altar",
      "x": 8,
      "y": 9,
      "distance_ft": 35,
      "preview_coordinates": [8, 9]
    }
  ],
  "is_compound": false,
  "actions": [
    {
      "node_id": "node-7f12a84c",
      "order": 1,
      "action_type": "attack",
      "target": "goblin",
      "requires_disambiguation": true,
      "status": "pending"
    }
  ],
  "execution_latency_ms": 1.45
}
```

During this call:
1. `IntentDisambiguationRequested` is published to Redis Stream `runefoble.events.watcher`.
2. Candidate preview locations are emitted as `CandidateGhostPreviewEmitted` to `runefoble.events.board` to render preview highlights on `<runefoble-board>`.

---

## 2. Resolving Disambiguation Choices

Once the player speaks or selects their choice (e.g. *"The archer"* or taps the candidate ghost token), submit the selection to resolve the target:

```bash
curl -X POST http://localhost:8001/api/v1/watcher/intent/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-crypt-01",
    "disambiguation_id": "disambig-9a7f32bc1042",
    "selected_candidate_id": "goblin_archer"
  }'
```

### Resolved Response

```json
{
  "session_id": "session-crypt-01",
  "disambiguation_id": "disambig-9a7f32bc1042",
  "resolved_target": "archer by the pillar",
  "status": "ready",
  "actions": [
    {
      "node_id": "node-7f12a84c",
      "order": 1,
      "action_type": "attack",
      "parameters": {
        "action": "attack",
        "target": "archer by the pillar",
        "target_id": "goblin_archer",
        "target_x": 5,
        "target_y": 3
      },
      "target": "archer by the pillar",
      "status": "pending",
      "requires_disambiguation": false
    }
  ],
  "narrative_summary": "Resolved target to 'archer by the pillar'. Combo actions ready for execution.",
  "execution_latency_ms": 0.82
}
```

This publishes `CompoundActionResolved` over `runefoble.events.watcher`.

---

## 3. Chaining Multi-Part Compound Action Combos

Players can speak complex tactical combinations such as *"I vault the table and strike the brute with my greatsword"*:

```bash
curl -X POST http://localhost:8001/api/v1/watcher/intent/parse \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-crypt-01",
    "speaker_id": "marcus-1",
    "speaker_name": "Marcus",
    "transcript": "I vault the table and strike the brute with my greatsword",
    "entities": [
      {
        "id": "brute_1",
        "name": "Brute",
        "descriptor": "orc brute with spiked maul",
        "x": 6,
        "y": 4
      }
    ]
  }'
```

### Decomposed Action Graph

The utterance automatically parses into sequential capability checks:
- **Node 1 (`order: 1`)**: `skill_check` (`athletics`, DC 12) targeting the `table`.
- **Node 2 (`order: 2`)**: `attack` targeting `orc brute with spiked maul` with weapon `greatsword`.

---

## 4. Partial Failure & Rollback Handling

When executing a compound combo via `/api/v1/watcher/intent/execute`, if an intermediate action fails (e.g. an athletics check fails mid-jump):

```bash
curl -X POST http://localhost:8001/api/v1/watcher/intent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-crypt-01",
    "speaker_name": "Marcus",
    "actions": [...],
    "step_results": {
      "node-jump-id": false
    },
    "rollback_on_failure": true
  }'
```

- When `rollback_on_failure` is `true`:
  - Completed preceding movements are marked `rolled_back`.
  - The failing node is marked `failed`.
  - Dependent subsequent attacks are marked `aborted`.
  - The overall combo status is `rolled_back`.
- When `rollback_on_failure` is `false`:
  - Completed steps remain `completed`.
  - The failing node is marked `failed`.
  - Subsequent steps are marked `aborted`.
  - The overall combo status is `partial_failure`.
