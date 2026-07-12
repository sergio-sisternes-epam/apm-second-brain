# second-brain-learn

Provider-side write, learn, and forget implementation for the second-brain package ecosystem.

Part of the [apm-second-brain](../../README.md) public demo monorepo.

## Purpose

Implements the `second-brain.learn.v1` and `second-brain.forget.v1` capability contracts
defined in `second-brain-interfaces`. All primitives are internal (model/agent-invokable
only); higher-level client skills from `second-brain-interfaces` call these.

## Skills

| Skill | Surface | Purpose |
|-------|---------|---------|
| `sb-learn-handler` | Internal | Receives a validated learn request, detects duplicates, writes raw snapshot, ingests into wiki |
| `sb-forget-handler` | Internal | Receives a validated forget request, validates and resolves target, tombstones concept (v1: no destructive deletion) |
| `sb-learn-validate` | Internal | Validates a learn or forget request envelope against the interface schema |

All skills carry `<!-- direct-user-invocation: disabled -->` as their first line.

## v1 Constraints

- **Learn**: `source_id` in the receipt equals `correlation_id` -- the stable identifier for future forget requests. Duplicate detection is content-hash-based (O(N) scan over `raw/`).
- **Forget**: tombstone/archive only. No destructive deletion. Idempotent -- forgetting an already-archived concept returns `status: tombstoned`.
- **Forget path containment**: concept path inputs are validated against the wiki root before resolution.

## Dependencies

- `karpathy-wiki` -- wiki operation engine
- `second-brain-interfaces` -- think/learn/forget schemas and contracts

## Licence

Apache-2.0 -- see [LICENSE](../../LICENSE).
