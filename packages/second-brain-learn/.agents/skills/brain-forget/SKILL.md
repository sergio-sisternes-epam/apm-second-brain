# brain-forget

Send a versioned forget request to the configured second-brain provider,
marking a previously ingested source as tombstoned.

## Capability

`second-brain.forget.v1`

## When to invoke

Invoke when a previously ingested learning is known to be incorrect,
superseded, or no longer applicable. This operation archives the entry --
it does NOT perform a destructive purge in v1. The tombstone prevents the
entry from surfacing in future `brain-think` answers while preserving an
audit trail.

## Request envelope

```json
{
  "capability": "second-brain.forget.v1",
  "correlation_id": "<uuid-v4>",
  "target_id": "<source_id from brain-learn receipt OR concept path>",
  "reason": "<human-readable rationale>"
}
```

Read `schema/request.schema.json` for the full JSON Schema.

### `target_id` formats

| Format         | Example                        | Resolution                          |
|----------------|--------------------------------|-------------------------------------|
| `source_id`    | `src-a1b2c3d4`                 | Direct lookup by ingestion receipt. |
| `concept path` | `infra/kubernetes/pull-policy` | Provider resolves to matching entry.|

## Tombstone receipt envelope

```json
{
  "correlation_id": "<matches request>",
  "target_id": "<echoes request target_id>",
  "status": "tombstoned | not_found",
  "message": "<human-readable status detail>"
}
```

Read `schema/response.schema.json` for the full JSON Schema.

## v1 tombstone semantics

- `tombstoned` -- the entry is archived and excluded from future think results.
- `not_found` -- no entry matched `target_id`; no change applied.
- v1 does NOT expose a destructive delete. Purge support is reserved for v2.

## Handling receipt status

| `status`      | Agent action                                                      |
|---------------|-------------------------------------------------------------------|
| `tombstoned`  | Confirm to user; record `target_id` as archived.                 |
| `not_found`   | Inform user; verify `target_id` is correct before re-submitting. |

## Error handling

On transport error the adapter returns the standard error envelope
(see `schema/error.schema.json`). Log `code` and `correlation_id`.

## Schemas

| File                        | Purpose                       |
|-----------------------------|-------------------------------|
| `schema/request.schema.json`  | Forget request envelope       |
| `schema/response.schema.json` | Tombstone receipt envelope    |
| `schema/error.schema.json`    | Standard error envelope       |

## Adapter contract

See `.apm/instructions/adapter-contract.md` for how adapters map this
capability to a concrete transport.
