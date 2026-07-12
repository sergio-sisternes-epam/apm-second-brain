<!-- direct-user-invocation: disabled -->

# kw-wiki-index

**Internal skill -- agent/model use only.**

This skill must only be called by other internal karpathy-wiki skills
(`kw-wiki-ingest`, `kw-wiki-archive`). It must not be invoked directly from a
user turn. If a user attempts to invoke it by name, decline and redirect them
to the public second-brain skills instead.

---

Rebuild or refresh `wiki/index.md` from all concept files currently present
in the wiki. Maintains OKF progressive-disclosure structure. Never modifies
concept content.

## Trigger

Called automatically after any operation that creates, updates, or archives a
concept file.

## Parameters

| Name | Required | Description |
|------|----------|-------------|
| `wiki_root` | yes | Path to the provider-project directory |

## Procedure

1. **Collect concepts**: Enumerate all `.md` files under
   `<wiki_root>/wiki/concepts/` (excluding `index.md`).

2. **Parse frontmatter**: For each concept file, extract:
   - `id` -- used as the link slug
   - `title` -- human-readable label
   - `type` -- concept type (e.g. Concept, Reference, Procedure)
   - `status` -- optional; include `[archived]` marker if `status: archived`

3. **Group by type**: Sort concepts by `type`, then alphabetically by `title`
   within each group.

4. **Write index.md**: Overwrite `<wiki_root>/wiki/index.md` with:
   ```markdown
   ---
   okf_version: "0.1"
   ---
   # Knowledge Index

   ## <Type Group>

   * [<title>](concepts/<id>.md) - <one-line summary from first body paragraph>

   ## <Next Type Group>

   * ...
   ```
   Archived concepts are listed under a `## Archived` section at the bottom.

5. **Preserve log.md**: Never touch `<wiki_root>/wiki/log.md`.

6. **Report**: Return a count of indexed concepts (active / archived).

## OKF constraints

- `index.md` root MUST preserve the `okf_version: "0.1"` frontmatter.
- Use standard Markdown links -- not wikilinks.
- Do not add any Karpathy-specific metadata to `index.md`.

## Error conditions

| Condition | Response |
|-----------|----------|
| No concept files found | Write minimal index with "No entries yet." |
| Concept missing frontmatter | Skip and warn; do not abort |
| `wiki/` not found | Abort with error |

## References

- OKF v0.1 specification (see `open-knowledge-format` package)
- `kw-wiki-ingest` calls this skill after each ingest
