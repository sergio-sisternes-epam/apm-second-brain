<!-- direct-user-invocation: disabled -->

# kw-wiki-archive

**Internal skill -- agent/model use only.**

This skill must only be called by higher-level second-brain orchestration
skills (e.g. `brain-forget`). It must not be invoked directly from a user turn.
If a user attempts to invoke it by name, decline and redirect them to the
public second-brain skills instead.

---

Mark a concept as archived. This is the tombstone / v1-forget operation.
Preserves provenance -- files are never deleted. Adds `status: archived` to
frontmatter, updates the index, and appends a log entry.

## Trigger

Called when a higher-level skill has determined that a concept is obsolete,
superseded, or no longer relevant.

## Parameters

| Name | Required | Description |
|------|----------|-------------|
| `wiki_root` | yes | Path to the provider-project directory |
| `concept_id` | yes | Slug of the concept to archive (e.g. `sparse-autoencoder`) |
| `reason` | no | Human-readable reason for archiving |

## Procedure

1. **Locate concept**: Resolve `<wiki_root>/wiki/concepts/<concept_id>.md`.
   Abort if not found.

2. **Guard against double-archive**: If frontmatter already contains
   `status: archived`, report and exit cleanly (idempotent).

3. **Update frontmatter**:
   - Add or update: `status: archived`
   - Update: `modified: YYYY-MM-DD` to today's date
   - Preserve all other frontmatter fields unchanged.

4. **Preserve provenance**: Do NOT delete the concept file. Do NOT remove
   its body content. The archive is a tombstone, not a deletion.
   Optionally append an `> **Archived**: <reason>` blockquote at the top
   of the body to make the status visible to human readers.

5. **Update indexes**: Call `kw-wiki-index` to rebuild `wiki/index.md` and
   `wiki/concepts/index.md`. Archived concepts appear in a separate
   `## Archived` section and remain excluded from normal fallback queries.

6. **Append log entry**: Call `kw-wiki-log` with:
   - event: `archive`
   - concept_paths: `[wiki/concepts/<concept_id>.md]`
   - summary: `Archived "<concept title>"` + reason if provided

7. **Report**: Confirm the concept path and new status.

## OKF constraints

- Concept files must retain all required frontmatter fields after archiving.
- Never delete files -- provenance must be preserved.
- Standard Markdown links only inside concept body.
- Archived concepts remain queryable only through archive-focused lookups; the
  default query fallback must not resurface tombstones.

## Error conditions

| Condition | Response |
|-----------|----------|
| Concept file not found | Abort with error; list available concept IDs |
| Frontmatter parse failure | Abort with error; do not write partial state |
| Already archived | Log a warning, exit cleanly (idempotent) |

## References

- OKF v0.1 specification (see `open-knowledge-format` package)
- `kw-wiki-index` for index rebuild
- `kw-wiki-log` for log append
- `second-brain-interfaces` forget contract
