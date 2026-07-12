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

## source_id derivation and lifecycle

`source_id` is derived deterministically as `src-<SHA256(content)-full-hex-64-chars>` (the
hex string of the full 256-bit SHA-256 digest of the raw `content`
field). This derivation is content-addressed: the same content always produces
the same `source_id`. Consequences:

- **accepted**: source_id is derived and returned. The raw file is written and
  kw-wiki-ingest is called.
- **duplicate**: source_id is derived from the same content and returned. No
  write occurs. The caller receives the same source_id as would have been
  returned on the original accepted receipt, enabling round-trip forget.
- **invalid**: source_id is absent from the receipt. Do not invent or return a
  placeholder.

The source_id is written into the `source_id:` frontmatter field of the raw
file at `raw/<correlation_id>.md` for duplicate identity checking. The raw file
is the immutable source record.

**kw-wiki-ingest does NOT write source_id into concept frontmatter.** The
concept documents it creates carry only `id`, `title`, `type`, `created`,
`modified`, and a body link to the raw file. The post-ingest provenance
annotation (step 6 below) is what writes the plural `source_ids:` array into
concept frontmatter. Forget scans individual concept files to find this array;
it does not rely on the wiki index, which does not carry provenance metadata.

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
   If `valid` is false, return a receipt with `status: invalid`, omit
   `source_id`, and join the `errors` as a human-readable string in `message`.
   Stop.

2. **Derive source_id**: Compute SHA-256 of the raw `content` string. Take the
   full 64-character hex digest. Prepend `src-`. Result: `src-<64 hex chars>` (256 bits; full SHA-256).

3. **Duplicate detection**: Check whether a file matching the derived
   `source_id` already exists under `raw/` (by scanning frontmatter or a
   hash-index if present). If found, return:

   ```json
   {
     "correlation_id": "<matches request>",
     "source_id": "<same derived source_id>",
     "status": "duplicate",
     "message": "Content already ingested."
   }
   ```

   Do not re-ingest.

   Note: this is an O(N) scan over the `raw/` corpus for demo-scale wikis.
   A production implementation would maintain `raw/.hash-index.json` for O(1)
   lookup. The interface contract is identical either way.

4. **Write raw snapshot**: Write a file to `raw/<correlation_id>.md` with
   YAML frontmatter including `source_id: <derived>` and `content_hash:
   <SHA-256 hex>`, followed by the `content` body. This persists the source_id
   for later forget resolution.

5. **Ingest**: Call `kw-wiki-ingest` with:
   - `wiki_root`: the configured wiki root path
   - `source_file`: the raw file written in step 4

   `kw-wiki-ingest` handles concept extraction, index rebuild, and log append
   internally. Do not call `kw-wiki-index` or `kw-wiki-log` again after this.

6. **Annotate concept provenance**: After `kw-wiki-ingest` completes, enumerate
   all concept files under `wiki/concepts/`. For each concept file, determine
   whether it links to the raw snapshot written in step 4 using the following
   exact-match procedure:

   a. **Parse Markdown links**: Extract all Markdown link destinations from the
      concept body (pattern `[text](destination)`). Ignore image links, external
      URLs, and anchors.
   b. **Resolve relative paths**: For each link destination that is a relative
      file path (does not start with `http://`, `https://`, `/`, or `#`),
      resolve it relative to the concept file's own directory. For example, a
      concept at `wiki/concepts/concept.md` with link `../../raw/abc123.md`
      resolves to `raw/abc123.md` relative to `wiki_root`.
   c. **Canonicalise**: Apply `realpathSync` / `os.path.realpath` to the
      resolved path to eliminate `..` traversals and symlinks. Do the same for
      the expected raw snapshot path (`raw/<correlation_id>.md` under
      `wiki_root`).
   d. **Exact comparison**: The concept links to this raw snapshot if and only if
      its canonicalised resolved path equals the canonicalised expected path.
      Substring matching against concept body text is NOT sufficient and MUST NOT
      be used.
   e. **Non-file links**: Absolute URLs, anchors, and any destination that fails
      canonicalisation are silently ignored.

   For each concept that passes the exact-match check, append or update a
   `source_ids` YAML frontmatter array:

   ```yaml
   source_ids:
     - src-<64 hex chars>   # derived source_id from step 2
   ```

   Deduplication rules:
   - If `source_ids` is absent, add it containing the new source_id.
   - If `source_ids` is present, append the new source_id only if not already
     present. Preserve all existing source_ids.
   - If a concept is updated from a second ingest, add the new source_id to the
     existing array (multi-source concept accumulates provenance).
   - Update the `modified` frontmatter field to today's date.
   - The `source_ids` field is a provider implementation detail; it is not part
     of the OKF v0.1 specification.

7. **Return accepted receipt**:

```json
{
  "correlation_id": "<matches request>",
  "source_id": "src-<64 hex chars>",
  "status": "accepted",
  "message": "Learning ingested."
}
```

## Receipt status values

| Status      | Meaning                                                        |
|-------------|----------------------------------------------------------------|
| `accepted`  | Learning ingested; `source_id` present.                        |
| `duplicate` | Content hash matched an existing entry; `source_id` present.  |
| `invalid`   | Envelope failed validation; `source_id` absent.               |

## Error conditions

| Condition              | Response                                               |
|------------------------|--------------------------------------------------------|
| Validation fails       | Return `status: invalid`, omit `source_id`             |
| Duplicate detected     | Return `status: duplicate` with existing `source_id`   |
| kw-wiki-ingest error   | Propagate error; do not commit partial state           |

## References

- `sb-learn-validate` -- envelope validation helper
- `kw-wiki-ingest` -- raw source ingestion into OKF wiki (handles index + log internally)
- `second-brain-interfaces` -- `second-brain.learn.v1` schema and receipt schema
