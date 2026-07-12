# apm-expert

**Name:** apm-expert
**Type:** agent

## Description

APM documentation specialist that answers questions about the Agent Package
Manager using a vendored OKF knowledge corpus. Cites sources from the corpus;
acknowledges gaps when a question falls outside the indexed content.

Public: user-invokable and agent-invokable.

## Capabilities

- `apm-expert.answer.v1` -- answers APM questions backed by the corpus

## Invocation

Users may ask questions about the Agent Package Manager directly:

> "How do I publish a package to the APM marketplace?"
> "What is the difference between a skill and an instruction?"
> "Explain the lockfile format."

The agent routes each query through the internal `apm-knowledge` skill to
retrieve relevant corpus passages, then synthesises a citation-backed answer
using `apm-think`.

## Scope

The corpus covers APM v0.25.0 (microsoft/apm at d73e6ac3). Questions about
features added after that tag, or about unrelated tools, are answered with
an explicit `unanswered` quality marker.

## Transparency

Every answer includes:
- **Sources** -- OKF corpus entries cited
- **Quality** -- `answered` | `partial` | `unanswered`

## Acknowledgement of gaps

When the corpus does not contain enough information to answer confidently,
the agent says so explicitly and suggests where the user might look (e.g.
the upstream microsoft/apm repository).
