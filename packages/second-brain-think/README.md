# second-brain-think

Provider-side read and citation-backed reasoning for the second-brain package ecosystem.
Implements the think capability defined in `second-brain-interfaces`.

Part of the [apm-second-brain](../../README.md) public demo monorepo.

## Purpose

This package exposes internal agent skills invoked by the `brain-think` client
skill in `second-brain-interfaces`. All skills are **internal**
(direct-user-invocation disabled). Thinking is **strictly read-only** -- no wiki
write, ingest, or archive operations occur in this package.

End users interact through the `brain-think` public client skill only.

## Internal skills

| Skill               | Responsibility                                                    |
|---------------------|-------------------------------------------------------------------|
| `sb-think-handler`  | Validates request, queries wiki, synthesises cited answer.        |
| `sb-think-validate` | Schema validation helper for think requests.                      |

## Request/response contract

**Request** (`second-brain.think.v1`):
- `question` (required): natural-language question (1--4096 chars)
- `context.project` (optional): scope hint for retrieval
- `context.tags` (optional): tags to narrow retrieval

**Response**:
- `quality`: `answered` | `partial` | `unanswered`
- `answer`: distilled text (empty when unanswered)
- `citations`: list of `{ source_id, label, excerpt }` -- source_id is the
  content-addressed identifier from the concept's YAML frontmatter (not a slug)
- `knowledge_gaps`: aspects the wiki could not address

`quality: answered` requires at least one citation with a valid `source_id`.

**Error handling**: validation failures return `quality: unanswered` with
`knowledge_gaps[0]` prefixed `VALIDATION_ERROR: <details>`.

## Citation semantics

Each citation's `source_id` is the `src-<SHA256(content)[0:8]>` identifier
written to the concept's frontmatter by `sb-learn-handler` during ingestion.
This enables round-trip semantics: a caller can pass the same `source_id` to
`brain-forget` to tombstone the cited source.

## Architectural note: bundled skills

APM 0.25 bundles all skills from declared dependencies. Because this package
depends on `karpathy-wiki`, the deployed bundle includes wiki write skills
(`kw-wiki-ingest`, `kw-wiki-archive`, `kw-wiki-log`, `kw-wiki-index`,
`kw-wiki-init`). These skills are present in the bundle but are **not called**
by any second-brain-think skill. A read-only karpathy-wiki sub-package would
remove them; that refactor is out of scope for v0.1.0.

## Dependencies

- `karpathy-wiki` -- wiki engine skills (kw-wiki-query used for retrieval)
- `second-brain-interfaces` -- versioned request/response schemas

## Targets

Declared targets: `claude`, `copilot`.
Run `apm install` from this directory to regenerate target deployment dirs.

## Running tests

```bash
pytest packages/second-brain-think/tests/ -v
```

Requires: `jsonschema>=4.0`, `pyyaml`

## Licence

Apache-2.0 -- see [LICENSE](../../LICENSE).

