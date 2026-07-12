# second-brain-learn

Provider-side write, learn, and forget implementation for the second-brain package ecosystem.
Implements the learn and forget capabilities defined in `second-brain-interfaces`.

Part of the [apm-second-brain](../../README.md) public demo monorepo.

## Purpose

This package exposes internal agent skills invoked by the higher-level client
skills in `second-brain-interfaces`. All skills are **internal**
(direct-user-invocation disabled). End users interact through the `brain-learn`
and `brain-forget` public client skills only.

## Internal skills

| Skill                | Responsibility                                                   |
|----------------------|------------------------------------------------------------------|
| `sb-learn-handler`   | Validates a learn envelope, derives source_id, ingests content.  |
| `sb-forget-handler`  | Validates a forget envelope, resolves target, archives concept.  |
| `sb-forget-validate` | Schema + path-safety validation helper for forget requests.      |
| `sb-learn-validate`  | Schema validation helper for learn requests.                     |

## source_id lifecycle

source_id is a stable content-addressed identifier: `src-<SHA256(content)[0:8]>`.
It is derived deterministically from the raw content string, written to the
raw file and concept document YAML frontmatter during ingestion, and returned
in the learn receipt.

Clients can use source_id as `target_id` in a future `brain-forget` request
to tombstone the associated concept.

- `accepted` and `duplicate` receipts always carry a `source_id`.
- `invalid` receipts never include a `source_id`.

## Forget: tombstone-only (v1)

Version 1 forget is archive-only. `kw-wiki-archive` sets concept status to
`archived` and excludes it from future retrieval. No file is deleted.
Archived content remains recoverable by a wiki administrator.

target_id is resolved in order: source_id form (`src-[0-9a-f]{8}`) then
concept-path form (forward-slash delimited path relative to `wiki/concepts/`).
Absolute paths, parent traversal (`..`), and other unsafe patterns are
rejected by `sb-forget-validate` before any archive operation.

Already-archived concepts are treated as idempotent: forget returns
`not_found` with the message "Concept already archived." without error.

## Dependencies

- `karpathy-wiki` -- wiki engine skills (ingest, archive, query, etc.)
- `second-brain-interfaces` -- versioned request/response schemas

## Targets

Declared targets: `claude`, `copilot`.
Run `apm install` from this directory to regenerate target deployment dirs.

## Running tests

```bash
pytest packages/second-brain-learn/tests/ -v
```

Requires: `jsonschema>=4.0`, `pyyaml`

## Licence

Apache-2.0 -- see [LICENSE](../../LICENSE).

