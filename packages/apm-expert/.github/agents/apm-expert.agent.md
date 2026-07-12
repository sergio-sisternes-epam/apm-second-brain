---
name: apm-expert
type: agent
version: 0.1.0
public: true
description: >
  APM documentation specialist. Answers questions about the Agent Package
  Manager (commands, manifests, primitives, marketplace). SCAFFOLD: corpus
  not yet built -- returns unanswered until knowledge-build pipeline runs.
capabilities:
  - apm-expert.answer.v1
status: scaffold
---

# apm-expert

**Name:** apm-expert
**Type:** agent
**Status:** SCAFFOLD -- not yet operational (corpus not populated)

## Description

APM documentation specialist. When the OKF corpus is populated (see
`docs/knowledge-build.md`), this agent answers questions about the Agent
Package Manager by retrieving passages from the vendored corpus and returning
citation-backed responses.

**This package is currently a scaffold.** The corpus has not been built or
ingested. Until the knowledge-build pipeline runs, all queries return
`quality: unanswered` with a `knowledge_gaps` notice and no synthesised
answer or citations.

Public: user-invokable and agent-invokable.

## Fail-closed behaviour (corpus not populated)

When `apm-knowledge` reports `corpus_populated: false` or returns an empty
`passages` list, this agent MUST:

1. Return `quality: unanswered`.
2. Return an empty `sources` list -- no citations.
3. Return NO synthesised answer.
4. Include a `knowledge_gaps` entry:
   `"APM documentation corpus not yet populated -- run knowledge build pipeline."`
5. Direct the user to `docs/knowledge-build.md` for next steps.

This is a hard fail-closed rule. The agent must never fabricate citations or
synthesise answers from model weights when corpus evidence is absent.

## Capabilities

- `apm-expert.answer.v1` -- answers APM questions backed by the corpus

## Invocation (once corpus is built)

Users may ask questions about the Agent Package Manager:

> "How do I publish a package to the APM marketplace?"
> "What is the difference between a skill and an instruction?"
> "Explain the lockfile format."

## Corpus scope

The vendored corpus targets microsoft/apm tag v0.25.0 at commit d73e6ac3.

## Transparency

Every response (including fail-closed responses) includes:
- **Sources** -- OKF corpus entries cited, or `[]` when corpus is empty
- **Quality** -- `answered` | `partial` | `unanswered`
- **knowledge_gaps** -- populated whenever quality is not `answered`
