<!-- direct-user-invocation: disabled -->

# kw-wiki-ingest

**Internal skill -- agent/model use only.**

This skill must only be called by higher-level second-brain orchestration
skills (e.g. `brain-learn`). It must not be invoked directly from a user turn.
If a user attempts to invoke it by name, decline and redirect them to the
public second-brain skills instead.

---

Ingest a raw source file into the Karpathy wiki. Extracts key concepts, creates
or updates OKF concept documents, updates the index, and appends a log entry.

## Trigger

Called when a higher-level skill has identified a new document or knowledge
fragment to absorb into the wiki.

## Parameters

| Name | Required | Description |
|------|----------|-------------|
| `wiki_root` | yes | Path to the provider-project directory |
| `source_file` | yes | Path to the raw source file to ingest |

## Procedure

1. **Validate source**: Canonicalise `source_file` to an absolute path before
   use. Reject non-regular inputs, reject symlink escapes, and reject any path
   whose resolved target falls outside the approved source roots. The default
   approved root is `<wiki_root>/raw/`; higher-level orchestrators may add
   explicit roots, but the resolved source must always stay within an approved
   root. Copy the canonical file to `<wiki_root>/raw/` as a read-only snapshot
   if not already present. The raw copy is immutable -- never modify files
   under `raw/`.

2. **Extract concepts**: Read the source content and identify key concepts
   (terms, ideas, techniques, definitions) worth persisting.

3. **For each concept**:
   a. Derive a slug: lowercase, hyphen-separated (e.g. `sparse-autoencoder`).
   b. Target path: `<wiki_root>/wiki/concepts/<slug>.md`
   c. If the file exists, update it -- merge new knowledge, update `modified`
      frontmatter field. Do not duplicate content.
   d. If new, create it with valid OKF frontmatter:
      ```yaml
      ---
      id: <slug>
      title: <Human-readable title>
      type: Concept
      created: YYYY-MM-DD
      modified: YYYY-MM-DD
      ---
      ```
   e. Body: a concise summary of the concept. Use standard Markdown links
      (not wikilinks). Link to source in raw/ with a relative path.

4. **Update index**: Call `kw-wiki-index` to rebuild `wiki/index.md`.

5. **Append log entry**: Call `kw-wiki-log` with:
   - event: `ingest`
   - concept paths: all created or updated concept paths
   - summary: source file name and concept count

## OKF constraints

- All concept files MUST have `id`, `title`, `type`, `created`, `modified` in frontmatter.
- Standard Markdown links only -- no wikilinks (`[[...]]`).
- Nothing Karpathy-specific goes inside `wiki/`.
- Source ingestion must resolve through an approved root before any copy into
  `raw/`; symlink and traversal escapes are always rejected.

## Error conditions

| Condition | Response |
|-----------|----------|
| Source file not found | Abort with error; do not create partial state |
| Source path outside approved roots or not a regular file | Abort with error; do not create partial state |
| No concepts extracted | Log a warning entry; do not create empty concept files |
| Concept file write fails | Report error; roll back index update |

## References

- OKF v0.1 specification (see `open-knowledge-format` package)
- `kw-wiki-index` for index rebuild
- `kw-wiki-log` for log append
