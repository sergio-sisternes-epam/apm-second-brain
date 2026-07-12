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
   If `valid` is false, return a schema-valid error envelope (NOT a forget
   receipt -- the forget receipt has no invalid status):

   ```json
   {
     "correlation_id": "<from request, or generated UUID if request malformed>",
     "code": "VALIDATION_ERROR",
     "message": "<validation errors joined as human-readable string>"
   }
   ```

   Stop. Do not proceed to target resolution.

2. **Resolve target**: Interpret `target_id` using exactly one of these two
   forms (tried in order):

   a. **source_id form** (pattern `src-[0-9a-f]{64}`): Enumerate ALL concept
      files under `wiki/concepts/` (NOT wiki/index.md -- it does not carry
      provenance). For each concept, read its frontmatter `source_ids:` array.
      Collect every concept whose `source_ids` array contains `target_id`.
      This may match zero, one, or multiple concepts (multi-source concepts
      accumulate provenance).

      If no concept matches, return:

      ```json
      {
        "correlation_id": "<matches request>",
        "target_id": "<echoes request>",
        "status": "not_found",
        "message": "No active concept matched the given source_id."
      }
      ```

      If one or more concepts match, proceed to step 3 for EACH matched concept.
      Document the v1 conservative behaviour: a multi-source concept is
      tombstoned as a whole because contribution-level subtraction is
      unsupported in v1. Raw files remain immutable.

   b. **concept-path form** (all other strings): Treat as a forward-slash
      delimited path relative to `wiki/concepts/`. The path MUST be validated
      by `sb-forget-validate` before this step (no `..`, no absolute prefix,
      no symlink escape). Resolve the concept file at
      `wiki/concepts/<validated_path>.md`. If found, read the `id:`
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

   **Already-archived idempotency**: If ALL matched concepts already have
   `status: archived`, return `status: not_found` with message
   `"Concept(s) already archived."` (idempotent).

3. **Archive ALL matched concepts**: For EACH concept slug resolved in step 2,
   call `kw-wiki-archive` with:
   - `wiki_root`: the configured wiki root path
   - `concept_id`: the concept slug
   - `reason`: the `reason` field from the request

   `kw-wiki-archive` tombstones the concept (sets status to `archived`,
   updates the index, and appends a log entry). Do not call `kw-wiki-log`
   separately. For source_id-form forget, all matched concepts are tombstoned
   in sequence; the receipt reports all tombstoned slugs.

4. **Return receipt**:

   Single-concept form:
   ```json
   {
     "correlation_id": "<matches request>",
     "target_id": "<resolved concept slug or source_id>",
     "status": "tombstoned",
     "message": "Concept archived. No data deleted."
   }
   ```

   Multi-concept form (source_id matched N > 1 concepts):
   ```json
   {
     "correlation_id": "<matches request>",
     "target_id": "<source_id from request>",
     "status": "tombstoned",
     "message": "N concept(s) archived. No data deleted. Multi-source concept: all contributions tombstoned as a whole (v1 conservative behaviour; contribution-level subtraction is unsupported)."
   }
   ```

## Receipt status values

| Status       | Meaning                                                    |
|--------------|------------------------------------------------------------|
| `tombstoned` | Concept archived; excluded from future retrieval.          |
| `not_found`  | No active concept matched the given `target_id`.           |

## Error conditions

| Condition               | Response type          | code / status              |
|-------------------------|------------------------|----------------------------|
| Validation fails        | Error envelope         | `VALIDATION_ERROR`         |
| Target not found        | Forget receipt         | `status: not_found`        |
| Concept already archived| Forget receipt         | `status: not_found`, idempotent |
| kw-wiki-archive error   | Error envelope         | `PROVIDER_ERROR`           |

Error envelopes match `second-brain.error` schema (correlation_id, code, message).
Forget receipts match `second-brain.forget.v1.response` schema (correlation_id, target_id, status).

## References

- `sb-forget-validate` -- schema validation and path safety helper (called first)
- `kw-wiki-archive` -- tombstone a concept in the OKF wiki (handles index + log)
- `second-brain-interfaces` -- `second-brain.forget.v1` schema and receipt schema
