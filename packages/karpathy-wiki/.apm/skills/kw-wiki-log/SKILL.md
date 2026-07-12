<!-- direct-user-invocation: disabled -->

# kw-wiki-log

**Internal skill -- agent/model use only.**

This skill must only be called by other internal karpathy-wiki skills
(`kw-wiki-ingest`, `kw-wiki-archive`). It must not be invoked directly from a
user turn. If a user attempts to invoke it by name, decline and redirect them
to the public second-brain skills instead.

---

Append a new entry to `wiki/log.md` using newest-first ISO date groups.
Records ingest, update, and archive events with concept paths and summaries.

## Trigger

Called automatically after any state-changing operation on the wiki.

## Parameters

| Name | Required | Description |
|------|----------|-------------|
| `wiki_root` | yes | Path to the provider-project directory |
| `event` | yes | Event type: `ingest`, `update`, `archive` |
| `concept_paths` | yes | List of concept paths affected (relative to `wiki_root`) |
| `summary` | yes | Human-readable description of what changed |

## Procedure

1. **Read log.md**: Load `<wiki_root>/wiki/log.md`. If missing, create it
   with a `# Knowledge Log` heading before proceeding.

2. **Determine today's date group**: Format as `YYYY-MM-DD`.

3. **Locate or insert date heading**: Search for `## YYYY-MM-DD` in the log.
   - If found: append the new entry below the existing entries under that
     date heading.
   - If not found: insert a new `## YYYY-MM-DD` section immediately after the
     `# Knowledge Log` heading (newest-first order). Never reorder existing
     date groups.

4. **Write entry**: Append under the date heading:
   ```
   - [<event>] <summary> (<concept_path>, ...)
   ```
   Example:
   ```
   - [ingest] Absorbed "Sparse Autoencoders" from raw/karpathy-llm-notes.md
     (wiki/concepts/sparse-autoencoder.md)
   ```

5. **Write back**: Save the modified log.md. Validate that date headings
   remain in newest-first order before writing.

## OKF log.md format

- Heading: `# Knowledge Log`
- Date groups: `## YYYY-MM-DD` (ISO 8601)
- Newest date group first
- Entries: `- [event] summary (paths)`
- No frontmatter in log.md

## Error conditions

| Condition | Response |
|-----------|----------|
| `log.md` missing | Create it, then proceed |
| Date group order broken after insert | Abort and report; do not write corrupted log |
| Empty summary | Use a default: `(no summary provided)` |

## References

- OKF v0.1 specification -- L1-log-date-headings, L2-log-newest-first rules
- `kw-wiki-ingest` and `kw-wiki-archive` call this skill
