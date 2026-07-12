# second-brain

Convenience meta-package that installs a complete second-brain provider
(both learn and think sides) in a single `apm install` command.

Part of the [apm-second-brain](../../README.md) public demo monorepo.

## Purpose

Installing this package pulls in:

- **second-brain-learn** -- provider-side write path (sb-learn-handler,
  sb-forget-handler, sb-learn-validate, sb-forget-validate)
- **second-brain-think** -- provider-side read path (sb-think-handler,
  sb-think-validate)

together with their transitive dependencies (second-brain-interfaces,
karpathy-wiki, open-knowledge-format).

## No primitives

This package contains **no skills, instructions, or other primitives of
its own**. There is no `.apm/` directory. The value it provides is
dependency resolution only.

## Usage

```bash
apm install sergio-sisternes-epam/apm-second-brain/packages/second-brain
```

This is equivalent to installing `second-brain-learn` and
`second-brain-think` individually.

## Dependencies

| Package | Role |
|---------|------|
| `second-brain-learn` | Provider write path |
| `second-brain-think` | Provider read path |

## Status

Stable. See the root [CHANGELOG.md](../../CHANGELOG.md) for progress.

## Licence

Apache-2.0 -- see [LICENSE](../../LICENSE).
