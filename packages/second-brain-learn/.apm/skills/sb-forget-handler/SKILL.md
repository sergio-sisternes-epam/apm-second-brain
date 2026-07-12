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

1. **Validate envelope**: Call `sb-forget-validate` with the request envelope.
   If `valid` is false, return a receipt with `status: not_found` and the
   validation errors joined as a human-readable `message`. Stop.

2. **Resolve target**: Interpret `target_id` using exactly one of these two
   forms (tried in order):

   a. **source_id form** (pattern `src-[0-9a-f]{8}`): Scan the wiki index for
      a concept whose frontmatter contains `source_id: <target_id>`. If found,
      extract the concept slug for use in step 3.

   b. **concept-path form** (all other strings): Treat as a forward-slash
      delimited path relative to `wiki/concepts/`. The path MUST be validated
      by `sb-forget-validate` before this step (no `..`, no absolute prefix,
      no symlink escape). Resolve the concept file at
      `wiki/concepts/<validated_path>.md`. If found, read the `slug:` or `id:`
      frontmatter field.

   If neither resolves to an existing, non-archived concept file, return:

   ```json
   {
     "correlation_id": "<matches request>",
     "target_id": "<echoes request>",
     "status": "not_found",
     "message": "No active concept matched the given target_id."
   }
   ```

   **Already-archived idempotency**: If the concept exists but its status is
   already `archived`, return `status: not_found` with message
   `"Concept already archived."`.

3. **Archive**: Call `kw-wiki-archive` with:
   - `wiki_root`: the configured wiki root path
   - `concept_id`: the resolved concept slug from step 2
   - `reason`: the `reason` field from the request

   `kw-wiki-archive` tombstones the concept (sets status to `archived`,
   updates the index to exclude it from queries, and appends a log entry).
   Do not call `kw-wiki-log` separately -- `kw-wiki-archive` handles logging.

4. **Return receipt**:

```json
{
  "correlation_id": "<matches request>",
  "target_id": "<resolved concept slug>",
  "status": "tombstoned",
  "message": "Concept archived. No data deleted."
}
```

## Receipt status values

| Status       | Meaning                                                    |
|--------------|------------------------------------------------------------|
| `tombstoned` | Concept archived; excluded from future retrieval.          |
| `not_found`  | No active concept matched the given `target_id`.           |

## Error conditions

| Condition               | Response                                              |
|-------------------------|-------------------------------------------------------|
| Validation fails        | Return `status: not_found` with validation message    |
| Target not found        | Return `status: not_found` with descriptive message   |
| Concept already archived| Return `status: not_found`, msg: "already archived"  |
| kw-wiki-archive error   | Propagate error; do not commit partial state          |

## References

- `sb-forget-validate` -- schema validation and path safety helper (called first)
- `kw-wiki-archive` -- tombstone a concept in the OKF wiki (handles index + log)
- `second-brain-interfaces` -- `second-brain.forget.v1` schema and receipt schema
