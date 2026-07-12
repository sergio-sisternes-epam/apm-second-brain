# apm-second-brain

A public APM demo monorepo implementing a portable knowledge format, a
Karpathy-style persistent wiki, versioned second-brain interfaces, local agent
discovery, and an APM expert -- all from scratch, using only public sources.

## Packages

| Package | Purpose |
|---------|---------|
| [`open-knowledge-format`](packages/open-knowledge-format/) | OKF v0.1 conformance tooling |
| [`karpathy-wiki`](packages/karpathy-wiki/) | Karpathy persistent-wiki engine over OKF |
| [`second-brain-interfaces`](packages/second-brain-interfaces/) | Versioned think/learn/forget contracts |
| [`second-brain-learn`](packages/second-brain-learn/) | Provider-side write implementation |
| [`second-brain-think`](packages/second-brain-think/) | Provider-side read and reasoning |
| [`second-brain`](packages/second-brain/) | Dependency-only meta-package |
| [`agent-knowledge-network`](packages/agent-knowledge-network/) | Local agent registration and discovery |
| [`apm-expert`](packages/apm-expert/) | APM documentation expert demo |

## Examples

- [`examples/local-second-brain/`](examples/local-second-brain/) -- generic provider with Knowledge Graph Canvas
- [`examples/multi-agent-discovery/`](examples/multi-agent-discovery/) -- register and discover agents (Copilot only)
- [`examples/apm-expert/`](examples/apm-expert/) -- bootstrap the corpus and query with citations

## Requirements

- APM CLI v0.25.0 (`d73e6ac3`) -- see [PROVENANCE.md](PROVENANCE.md)
- GitHub Copilot CLI or Claude Code

## Licence

Apache-2.0 -- see [LICENSE](LICENSE).

Third-party attributions: [NOTICE](NOTICE), [PROVENANCE.md](PROVENANCE.md), [CREDITS.md](CREDITS.md).
