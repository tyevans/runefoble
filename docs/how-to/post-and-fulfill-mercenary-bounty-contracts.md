# How-To: Post & Fulfill Frontier Mercenary Bounty Contracts

This guide explains how to post, claim, and complete mercenary bounties and resource retrieval contracts with locked escrow between adventuring parties sharing a West Marches frontier (TASK-0165 / PRD-0018 / US-0058 / ADR-0001 / ADR-0006 / ADR-0007).

---

## 1. Overview

In shared frontier campaigns, adventuring parties often require specialized monster trophies, rare alchemical reagents, or reconnaissance from dangerous sectors. The Bounty Board router in `services/game_session/` provides an asynchronous in-world commissioning mechanism backed by:
- **Event-Sourced Contract Engine**: States flow strictly through `MercenaryBountyAggregate` (`POSTED` -> `ACCEPTED` -> `FULFILLED` -> `DISPUTED` -> `COMPLETED`).
- **Escrow Locks**: Gold and item rewards are locked upon posting and atomically disbursed upon verified completion.
- **SpiceDB Zanzibar Authorization**: Object-level permissions on `bounty_contract` prevent unauthorized claiming, spoofed completions, or premature payouts.

---

## 2. Posting a Bounty with Escrow

An adventuring party leader posts a contract to the session bounty board:

```bash
curl -X POST http://localhost:8004/sessions/{session_id}/contracts/bounties \
  -H "Content-Type: application/json" \
  -H "x-user-id: questgiver_alec" \
  -d '{
    "title": "Cull the Glacial Wyrm",
    "description": "Hunt the frost wyrm in the Northern Pass and recover its horn.",
    "target_type": "monster_hunt",
    "target_name": "Glacial Wyrm",
    "target_quantity": 1,
    "escrow_gold": 500,
    "escrow_items": [{"item_id": "frost_shard", "quantity": 2}],
    "campaign_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
  }'
```

Response:
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "bounty": {
    "bounty_id": "4c3d2e1a-0b9a-8f7e-6d5c-4b3a2f1e0d9c",
    "status": "POSTED",
    "escrow_locked": true,
    "escrow_gold": 500,
    "poster_user_id": "questgiver_alec"
  }
}
```

This locks the escrow and writes SpiceDB relationships:
```zed
bounty_contract:4c3d2e1a#creator@user:questgiver_alec
bounty_contract:4c3d2e1a#session@session:9b1deb4d
```

---

## 3. Querying the Notice Board

Adventuring parties query open bounties with optional query filters:

```bash
curl -X GET "http://localhost:8004/sessions/{session_id}/contracts/bounties?status=POSTED&min_gold=300" \
  -H "x-user-id: mercenary_drake"
```

---

## 4. Claiming an Active Bounty

A mercenary company claims an open bounty:

```bash
curl -X POST http://localhost:8004/sessions/{session_id}/contracts/bounties/{bounty_id}/claim \
  -H "Content-Type: application/json" \
  -H "x-user-id: mercenary_drake" \
  -d '{
    "claimant_campaign_id": "f1e2d3c4-b5a6-9788-1234-56789abcdef0",
    "claimant_party_name": "Drake'\''s Rangers"
  }'
```

Transitions status to `ACCEPTED` and assigns `claimant` relationship in SpiceDB. Note that creators cannot claim their own bounties.

---

## 5. Submitting Proof & Releasing Escrow

Upon completing the hunt, the claimant or authorized DM submits proof and resolves the contract:

```bash
curl -X POST http://localhost:8004/sessions/{session_id}/contracts/bounties/{bounty_id}/complete \
  -H "Content-Type: application/json" \
  -H "x-user-id: questgiver_alec" \
  -d '{
    "proof": "Glacial Wyrm horn delivered and verified by Outpost Warden.",
    "notes": "Trophy mounted in Haven Great Hall."
  }'
```

Response:
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "bounty_id": "4c3d2e1a-0b9a-8f7e-6d5c-4b3a2f1e0d9c",
  "status": "COMPLETED",
  "payout": {
    "gold": 500,
    "items": [{"item_id": "frost_shard", "quantity": 2}]
  },
  "escrow_locked": false
}
```

Escrow is unlocked, payout is disbursed to the claimant, and `MercenaryBountyFulfilledEvent` is published to `runefoble.events.session`.
