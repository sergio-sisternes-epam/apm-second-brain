<!-- direct-user-invocation: disabled -->

# sb-learn-handler

**Internal skill -- agent/model use only.**

This skill must only be called by higher-level second-brain orchestration
skills (e.g. `brain-learn`). It must not be invoked directly from a user turn.
If a user attempts to invoke it by name, decline and redirect them to the
public `brain-learn` skill in the `second-brain-interfaces` package instead.

---

Receives a validated `second-brain.learn.v1` request envelope and ingests the
learning into the Karpathy wiki.

## Trigger

Called by `brain-learn` after the client has assembled a valid learn request
envelope that matches the `second-brain.learn.v1` schema.

## Input

A `second-brain.learn.v1` request envelope:

```json
{
  "capability": "second-brain.learn.v1",
  "correlation_id": "<uuid-v4>",
  "source_type": "session | document | manual",
  "content": "<structured learning text>",
  "category": "pattern | decision | correction | discovery | suggestion | general",
  "confidence": "verified | observed | hypothesis",
  "context": {
    "project": "<optional>",
    "session": "<optional>",
    "date": "<ISO-8601 date>",
    "tags": ["<optional>"]
  }
}
```

## Procedure

1. **Validate envelope**: Call `sb-learn-validate` with the request envelope.
   If `valid` is false, return a receipt with `status: invalid` and the
   `errors` joined as a human-readable string in the `message` field. Stop.

2. **Validate source_type**: Confirm `source_type` is one of `session`,
   `document`, or `manual`. If not, return `status: invalid`.

3. **Duplicate detection**: Compute a content hash (SHA-256) of `content`.
   Scan all existing files under `raw/` in the wiki root and compare their
   content hashes against the computed hash. If any match is found, return a
   receipt with `status: duplicate` and a human-readable message. Do not
   re-ingest. (Files in `raw/` are named by `correlation_id`; the hash
   comparison reads file contents, not filenames.)

4. **Write raw snapshot**: Write `content` to a file in `raw/` using the
   `correlation_id` as the filename stem (e.g. `raw/<correlation_id>.md`).

5. **Ingest**: Call `kw-wiki-ingest` with:
   - `wiki_root`: the configured wiki root path
   - `source_file`: the raw file written in step 4

   `kw-wiki-ingest` handles concept extraction, index rebuild, and log append
   internally -- do not call `kw-wiki-index` or `kw-wiki-log` again after this step.

6. **Return receipt**:

```json
{
  "correlation_id": "<matches request>",
  "source_id": "<assigned identifier>",
  "status": "accepted",
  "message": "<human-readable confirmation>"
}
```

## Receipt status values

| Status      | Meaning                                                        |
|-------------|----------------------------------------------------------------|
| `accepted`  | Learning ingested successfully.                                |
| `duplicate` | Content hash matched an existing raw entry; not re-ingested.  |
| `invalid`   | Envelope failed validation; see `message` for details.        |

## Error conditions

| Condition              | Response                                               |
|------------------------|--------------------------------------------------------|
| Validation fails       | Return `status: invalid` with error details            |
| Duplicate detected     | Return `status: duplicate`; do not modify wiki         |
| kw-wiki-ingest error   | Propagate error; do not commit partial state           |

## References

- `sb-learn-validate` -- envelope validation helper
- `kw-wiki-ingest` -- raw source ingestion into OKF wiki (handles index + log internally)
- `second-brain-interfaces` -- `second-brain.learn.v1` schema and receipt schema
