<!-- direct-user-invocation: disabled -->

# apm-knowledge

**Internal skill -- must only be called by apm-think or another internal agent
skill. Decline any direct user invocation and redirect to apm-think.**

## Purpose

Retrieves relevant passages from the vendored APM OKF corpus stored under
`references/knowledge/` and returns them for synthesis by the caller.

## Corpus metadata

| Field | Value |
|-------|-------|
| Source | microsoft/apm |
| Tag | v0.25.0 |
| Commit | d73e6ac3645d2b9c5c813095e2e58f020f38f17a |
| Format | OKF (Open Knowledge Format) |
| Location | `.apm/skills/apm-knowledge/references/knowledge/` |

## Corpus population

> **NOT YET POPULATED.** The `references/knowledge/` directory currently
> contains only a placeholder `CORPUS.md`. The corpus is built by a
> separate pipeline step and committed as a build artefact. See
> `docs/knowledge-build.md` for the refresh procedure.

## Query interface (internal)

Callers pass a natural-language query string. This skill:

1. Searches the OKF corpus entries under `references/knowledge/` for
   passages relevant to the query.
2. Returns a list of matching passages with their source OKF entry
   identifiers for citation.
3. Returns an empty list if no relevant passages are found.

## Return format

```json
{
  "passages": [
    {
      "id": "<okf-entry-id>",
      "text": "<passage text>",
      "source": "microsoft/apm@d73e6ac3"
    }
  ],
  "corpus_populated": false
}
```

`corpus_populated` is `false` until the knowledge-build pipeline runs.

## Error handling

If the corpus directory is empty or contains only `CORPUS.md`, return
`corpus_populated: false` and an empty `passages` list. Do not throw.
