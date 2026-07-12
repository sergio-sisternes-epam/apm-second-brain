<!-- direct-user-invocation: disabled -->

# sb-forget-handler

**Internal skill -- agent/model use only.**

This skill must only be called by higher-level second-brain orchestration
skills (e.g. `brain-forget`). It must not be invoked directly from a user turn.
If a user attempts to invoke it by name, decline and redirect them to the
public `brain-forget` skill in the `second-brain-interfaces` package instead.

---

Receives a validated `second-brain.forget.v1` request envelope and tombstones
the target concept in the Karpathy wiki.

## v1 Constraint: tombstone-only, no destructive deletion

Version 1 of the forget capability is tombstone and archive only. Tombstoning
marks a concept as archived and excludes it from future retrieval results. It
does NOT delete the underlying raw file or the concept document from disk.
No destructive removal of any file occurs. This constraint is intentional:
archived content remains recoverable by an administrator with direct wiki
access.

## Trigger

Called by `brain-forget` after the client has assembled a valid forget request
envelope that matches the `second-brain.forget.v1` schema.

## Input

A `second-brain.forget.v1` request envelope:

```json
{
  "capability": "second-brain.forget.v1",
  "correlation_id": "<uuid-v4>",
  "target_id": "<source_id from a learn receipt, or concept path>",
  "reason": "<human-readable rationale>"
}
```

## Procedure

1. **Resolve target**: Interpret `target_id` as either:
   - A `source_id` previously returned in a learn receipt (e.g. `src-a1b2c3d4`).
     Locate the corresponding raw file and concept documents via the wiki index.
   - A concept path (e.g. `infra/kubernetes/pull-policy`). Locate the concept
     document directly at `wiki/concepts/<target_id>.md`.

   If neither resolves, return a receipt with `status: not_found`.

2. **Archive**: Call `kw-wiki-archive` with:
   - `wiki_root`: the configured wiki root path
   - `concept_id`: the resolved concept slug (e.g. `kubernetes-pull-policy`)
   - `reason`: the `reason` field from the request

   `kw-wiki-archive` tombstones the concept (sets status to `archived`,
   updates the index to exclude it from queries, and appends a log entry)
   without deleting the file. Do not call `kw-wiki-log` separately after
   this step -- `kw-wiki-archive` handles logging internally.

3. **Return receipt**:

```json
{
  "correlation_id": "<matches request>",
  "target_id": "<resolved target identifier>",
  "status": "tombstoned",
  "message": "<human-readable confirmation>"
}
```

## Receipt status values

| Status       | Meaning                                                    |
|--------------|------------------------------------------------------------|
| `tombstoned` | Concept archived; excluded from future retrieval.          |
| `not_found`  | No concept matched the given `target_id`.                  |

## Error conditions

| Condition               | Response                                              |
|-------------------------|-------------------------------------------------------|
| Target not found        | Return `status: not_found` with a descriptive message |
| kw-wiki-archive error   | Propagate error; do not commit partial state          |

## References

- `kw-wiki-archive` -- tombstone a concept in the OKF wiki (handles index + log internally)
- `second-brain-interfaces` -- `second-brain.forget.v1` schema and receipt schema
