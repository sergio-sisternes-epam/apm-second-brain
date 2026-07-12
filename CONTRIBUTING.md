# Contributing

Thank you for your interest in contributing to apm-second-brain.

## Prerequisites

- APM CLI v0.25.0 at commit `d73e6ac3645d2b9c5c813095e2e58f020f38f17a`
  (see [PROVENANCE.md](PROVENANCE.md))
- GitHub Copilot CLI or Claude Code for local testing

## Commit style

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]
```

Types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`, `ci`.
Scope: the package name, e.g. `karpathy-wiki`, `open-knowledge-format`.

## Branching and pull requests

1. Fork the repository (or create a branch if you are a maintainer).
2. Open a **draft** pull request early so reviewers can track progress.
3. All CI checks must pass before a PR can merge.
4. Reference the issue your PR addresses in the PR description.

## Merge gates

The following gates are enforced on every PR targeting `main` (including for
repository admins -- `enforce_admins: true` is active):

| Gate | Type | Blocks merge? |
|------|------|--------------|
| **Lint** -- private-context scan | Automated CI | Yes |
| **OKF conformance** -- pytest suite (root + per-package) | Automated CI | Yes |
| **APM package validation** -- marketplace check + dry-run pack | Automated CI | Yes |
| **Copilot Code Review** -- AI-assisted diff review | Automated, advisory | No (manual gate) |

The Copilot Code Review workflow runs automatically on every PR push.  It is
not a required status check because its output is advisory -- a failing or
incomplete review should still trigger a human decision.  Maintainers must read
and address Copilot review comments before approving a merge.

## Package manifests

Always create or update `apm.yml` files through the APM 0.25 CLI (`apm init`,
`apm install`, `apm marketplace init`). Do not hand-author manifest fields
from memory; verify against `apm --help` output.

## Privacy boundary

This is a public open-source demo. **Never** commit:
- Private repository names, internal URLs, or internal architecture details
- User-specific paths, machine names, or session artefacts
- Credentials, tokens, or secrets of any kind
- Proprietary business logic or customer data

Use synthetic examples and public upstream sources only.

## Testing

Run the full test suite before opening a PR:

```bash
# Root conformance suite + all per-package conformance suites (mirrors CI)
python -m pytest tests/conformance/ $(find packages -path '*/tests/conformance' -type d | tr '\n' ' ') -v

# Integration tests (requires APM CLI in PATH)
python -m pytest tests/integration/ -v
```

CI runs both the root `tests/conformance/` directory and every
`packages/*/tests/conformance/` directory discovered at runtime.

## Releases

Each package is independently versioned. Tags follow `<package>--v<version>`,
e.g. `open-knowledge-format--v0.1.0`. Only the release authority listed in
CODEOWNERS may publish a release.
