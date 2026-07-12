# second-brain-think

Provider-side read and citation-backed reasoning for the second-brain package ecosystem.

Part of the [apm-second-brain](../../README.md) public demo monorepo.

## Purpose

Implements the `second-brain.think.v1` capability contract defined in
`second-brain-interfaces`. All primitives are internal (model/agent-invokable only)
and strictly read-only -- thinking never modifies the wiki.

## Skills

| Skill | Surface | Purpose |
|-------|---------|---------|
| `sb-think-handler` | Internal | Receives a validated think request, retrieves concepts via kw-wiki-query, synthesises a citation-backed answer, classifies quality |
| `sb-think-validate` | Internal | Validates a think request envelope against the interface schema |

All skills carry `<!-- direct-user-invocation: disabled -->` as their first line.

## v1 Constraints

- **Read-only**: no wiki writes, no archives, no ingestion calls.
- **Citation format**: each citation includes `source_id` (required), `label` (required), and `excerpt` (optional), matching the `second-brain.think.v1.response` schema.
- **Error codes**: validation errors return `code: VALIDATION_ERROR`; provider errors return `code: PROVIDER_ERROR`. All error envelopes match the `second-brain.error` schema.
- **Quality classification**: `answered` | `partial` | `unanswered`.

## Dependencies

- `karpathy-wiki` -- wiki query engine
- `second-brain-interfaces` -- think/learn/forget schemas and contracts

## Licence

Apache-2.0 -- see [LICENSE](../../LICENSE).
