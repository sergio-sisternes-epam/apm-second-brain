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

Run the test suite before opening a PR:

```bash
# conformance
python -m pytest tests/conformance/

# integration (requires APM CLI in PATH)
python -m pytest tests/integration/
```

## Releases

Each package is independently versioned. Tags follow `<package>--v<version>`,
e.g. `open-knowledge-format--v0.1.0`. Only the release authority listed in
CODEOWNERS may publish a release.
