<!-- direct-user-invocation: disabled -->

# kw-wiki-query

**Internal skill -- agent/model use only.**

This skill must only be called by higher-level second-brain orchestration
skills (e.g. `brain-think`). It must not be invoked directly from a user turn.
If a user attempts to invoke it by name, decline and redirect them to the
public second-brain skills instead.

---

Query the Karpathy wiki using index-first retrieval. Searches `index.md` first,
then individual concept files. Returns citation-backed results.

## Trigger

Called when a higher-level skill needs to retrieve knowledge from the wiki to
answer a question or populate a response.

## Parameters

| Name | Required | Description |
|------|----------|-------------|
| `wiki_root` | yes | Path to the provider-project directory |
| `query` | yes | Natural language question or search terms |

## Procedure

1. **Index scan**: Read `<wiki_root>/wiki/index.md`. Find all listed concept
   entries whose titles or slugs match the query terms. Prefer exact matches,
   then partial.

2. **Concept retrieval**: For each matched entry, read the corresponding
   concept file from `<wiki_root>/wiki/concepts/`. Extract the summary and
   any relevant passages.

3. **Full-text fallback**: If the index yields no matches, scan all `.md`
   files under `<wiki_root>/wiki/concepts/` directly for keyword matches.

4. **Compose result**:
   ```
   Quality: answered | partial | unanswered
   Concepts:
     - <concept-title> -- <wiki/concepts/<slug>.md>
       Excerpt: <...>
   Gaps: <list any knowledge gaps detected>
   ```

5. **Classify quality**:
   - `answered` -- one or more concepts directly address the query
   - `partial` -- related concepts found but incomplete coverage
   - `unanswered` -- no relevant concepts found; note gaps for future ingest

6. **Note gaps**: If quality is `partial` or `unanswered`, list specific
   missing concepts or topics. This feeds back to `brain-learn` for future
   ingestion.

## Return contract

Always return a structured block with: `quality`, `concepts` (list of
`{title, path, excerpt}`), and `gaps` (list of missing topic strings).
Never return raw file contents -- always excerpt and cite.

## OKF constraints

- Only read files from `<wiki_root>/wiki/`. Never read from `raw/`.
- Cite concept paths relative to `wiki_root`.

## Error conditions

| Condition | Response |
|-----------|----------|
| `wiki/` not found | Return quality=unanswered; suggest running `kw-wiki-init` |
| `index.md` missing | Fall back to full-text scan; warn about missing index |
| Query empty | Return error; require non-empty query |

## References

- OKF v0.1 specification (see `open-knowledge-format` package)
- `kw-wiki-index` for index structure
