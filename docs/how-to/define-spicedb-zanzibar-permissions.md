# How-To: Define and Check SpiceDB Zanzibar Permissions

## Overview
Runefoble uses SpiceDB to evaluate Zanzibar-style graph relationships and permissions. All schema rules live in `libs/runefoble_auth/schema/runefoble.zed`.

## Adding a Relation or Permission

### 1. Update the Zanzibar Schema
Edit `libs/runefoble_auth/schema/runefoble.zed`:
```zed
definition secret_note {
    relation campaign: campaign
    relation author: user

    // The note can be read only by the author or the campaign DM
    permission read = author + campaign->run_session
}
```

### 2. Write Relationship Tuples
When an entity is created in your service, record the relationship tuple:
```python
from runefoble_auth.spicedb import SpiceDBClient

client = SpiceDBClient()

# Record author
await client.write_relationship(
    resource_type="secret_note",
    resource_id="note_42",
    relation="author",
    subject_type="user",
    subject_id="alice_user_id",
)
```

### 3. Check Permissions
Before fulfilling an action, evaluate authorization:
```python
can_read = await client.check_permission(
    resource_type="secret_note",
    resource_id="note_42",
    permission="read",
    subject_type="user",
    subject_id="bob_user_id",
)

if not can_read:
    raise AuthorizationError("bob_user_id", "read", "secret_note:note_42")
```
