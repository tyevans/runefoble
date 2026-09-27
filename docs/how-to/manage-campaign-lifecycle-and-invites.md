# How to Manage Campaign Lifecycle and Membership Invites

This recipe demonstrates how to create campaigns, generate shareable invite tokens, join existing campaigns, and inspect active party membership using Runefoble's Gateway API backed by SpiceDB Zanzibar object authorization.

## Prerequisites

- Local Kind cluster or developer environment running (`make cluster-up` or `uv run pytest`).
- Authenticated user session with Zitadel JWT bearer token or local developer mode header (`X-User-Id`).
- SpiceDB running locally on port `50051`.

---

## 1. Creating a New Campaign

When creating a new campaign via `POST /api/v1/campaigns`, the API automatically:
1. Generates a unique campaign identifier (`camp-<uuid>`).
2. Persists campaign metadata (title, description, setting, system, and settings).
3. Writes the `campaign:<id>#owner@user:<user_id>` relationship tuple to SpiceDB Zanzibar.

```bash
curl -X POST "http://localhost:8000/api/v1/campaigns" \
  -H "Authorization: Bearer <ZITADEL_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Shadows of Drakkenheim",
    "description": "Gothic horror urban survival campaign.",
    "setting": "Gothic Fantasy",
    "system": "5e",
    "settings": {
      "ruleset": "2024",
      "gritty_realism": true
    }
  }'
```

**Response (`201 Created`):**
```json
{
  "id": "camp-a1b2c3d4",
  "title": "Shadows of Drakkenheim",
  "description": "Gothic horror urban survival campaign.",
  "setting": "Gothic Fantasy",
  "system": "5e",
  "status": "active",
  "owner_id": "usr-dm-evelyn",
  "role": "owner",
  "member_count": 1,
  "settings": {
    "ruleset": "2024",
    "gritty_realism": true
  },
  "created_at": "2026-09-27T10:15:00Z",
  "updated_at": "2026-09-27T10:15:00Z"
}
```

---

## 2. Listing Viewable Campaigns

`GET /api/v1/campaigns` lists only campaigns where the requesting user has the Zanzibar `view` permission (granted to owners, DMs, players, and spectators).

```bash
curl -X GET "http://localhost:8000/api/v1/campaigns" \
  -H "Authorization: Bearer <ZITADEL_JWT>"
```

**Response (`200 OK`):**
```json
[
  {
    "id": "camp-a1b2c3d4",
    "title": "Shadows of Drakkenheim",
    "setting": "Gothic Fantasy",
    "system": "5e",
    "status": "active",
    "role": "owner",
    "member_count": 1
  }
]
```

---

## 3. Generating Shareable Invite Links

Dungeon Masters and owners (holding `run_session` permission) can generate cryptographically secure shareable invite tokens:

```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/camp-a1b2c3d4/invites" \
  -H "Authorization: Bearer <ZITADEL_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "player",
    "expires_in_hours": 72,
    "max_uses": 5
  }'
```

**Response (`201 Created`):**
```json
{
  "token": "dGVzdF9pbnZpdGVfdG9rZW4",
  "campaign_id": "camp-a1b2c3d4",
  "role": "player",
  "invite_url": "/#/join/dGVzdF9pbnZpdGVfdG9rZW4",
  "expires_at": "2026-09-30T10:15:00Z",
  "created_at": "2026-09-27T10:15:00Z",
  "max_uses": 5,
  "uses": 0
}
```

---

## 4. Joining a Campaign via Invite

A player or spectator redeems an invite code via `POST /api/v1/campaigns/join`. The gateway writes the corresponding Zanzibar relation (`player` or `spectator`) for the user:

```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/join" \
  -H "Authorization: Bearer <PLAYER_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "invite_token": "dGVzdF9pbnZpdGVfdG9rZW4"
  }'
```

**Response (`200 OK`):**
```json
{
  "status": "joined",
  "campaign_id": "camp-a1b2c3d4",
  "user_id": "usr-player-marcus",
  "role": "player",
  "zanzibar_relation": "campaign:camp-a1b2c3d4#player@user:usr-player-marcus"
}
```

---

## 5. Querying Campaign Members and Active Roles

Inspect all members and their Zanzibar roles via `GET /api/v1/campaigns/{id}/members`:

```bash
curl -X GET "http://localhost:8000/api/v1/campaigns/camp-a1b2c3d4/members" \
  -H "Authorization: Bearer <PLAYER_JWT>"
```

**Response (`200 OK`):**
```json
[
  {
    "user_id": "usr-dm-evelyn",
    "role": "owner",
    "subject_type": "user",
    "zanzibar_relation": "campaign:camp-a1b2c3d4#owner@user:usr-dm-evelyn"
  },
  {
    "user_id": "usr-player-marcus",
    "role": "player",
    "subject_type": "user",
    "zanzibar_relation": "campaign:camp-a1b2c3d4#player@user:usr-player-marcus"
  }
]
```
