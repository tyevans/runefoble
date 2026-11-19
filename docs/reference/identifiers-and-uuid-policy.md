# Identifiers and UUID policy

Module: `runefoble_platform.identifiers` (TASK-0816, ADR-0015).

Use this module for every id that a client sends. Do not write a local UUID helper.

## Rule

A bad or missing id never becomes a different id. The platform never draws a random id to
replace a bad or missing input. A bad id is an error. A missing aggregate is a 404.

## Two kinds of id

Choose the kind that the domain defines for the id.

| Kind | Function | Use for | Bad input |
|---|---|---|---|
| Strict UUID | `parse_uuid(value, field=...)` | Ids the domain creates as UUIDs: campaigns, settlements, bounties, shared worlds, establishments, workers, caravan contracts | HTTP 400, detail names the field |
| Strict UUID, optional | `parse_optional_uuid(value, field=...)` | An optional UUID field. `None` and `""` return `None` | HTTP 400 for a malformed value |
| Opaque key | `opaque_aggregate_id(value, field=...)` | String keys the domain stores as text: board, soundscape, and chronicle session keys, game ids, faction ids, The Watcher and voice session keys. Game session ids are strict UUIDs (TASK-0706) | `""` or `None`: HTTP 400. Any other string maps to a stable id |
| Opaque key, optional | `opaque_optional_aggregate_id(value, field=...)` | Optional string keys. `None` and `""` return `None` | Same as above |

### Opaque key mapping

A value that parses as a UUID keeps that UUID. Any other non-empty string maps to
`uuid5(NAMESPACE_DNS, value)`. The mapping is the same in every process and on every call.
Two calls with the same session id reach the same stream.

## Error shape

`InvalidIdentifierError` is an `HTTPException` with status 400. Its detail is:

```text
Invalid id for field '<field>'
```

Raise the error only before a read or write. Do not wrap a parse call in `try ... except`.
A parse error inside a broad `except` becomes a silent fallback, which hides the bad input.

## Server-assigned ids on create

A create route that receives no id may assign a fresh UUID. This applies only when the
caller omits the id field. A supplied bad id is still a 400.

Current creation points: `CaravanContractAggregate()` with no id, `minigames` and
`merchants` tavern creation with no `aggregate_id`.

## Examples

```python
from runefoble_platform.identifiers import opaque_aggregate_id, parse_uuid

settlement_uuid = parse_uuid(settlement_id, field="settlement_id")  # 400 on "abc"
stream_id = opaque_aggregate_id(session_id, field="session_id")  # stable for "sess-1"
```

## Tests

- `tests/test_blackbox_uuid_policy_routes.py`: bad ids answer 400 and publish nothing.
- `tests/test_blackbox_settlements/test_uuid_policy_settlement_ids.py`: a bad settlement id
  answers 400 before the load.
- `tests/test_blackbox_chronicle_opaque_session_ids.py`: an opaque session id reuses one
  aggregate id.
