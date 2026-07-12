# apm-think

Public capability: `apm-expert.answer.v1`

**Status: SCAFFOLD** -- the OKF corpus has not been built. Until the
knowledge-build pipeline runs (see `docs/knowledge-build.md`), this skill
MUST follow the fail-closed path defined below.

Answers questions about the Agent Package Manager by querying the internal
`apm-knowledge` corpus and synthesising a citation-backed response.

## Fail-closed branch (MANDATORY)

Before synthesising any answer, check `corpus_populated` from `apm-knowledge`.

**If `corpus_populated` is `false` OR `passages` is empty:**

```
## Answer

No answer available. The APM documentation corpus has not yet been populated.

## Sources

[]

## Quality

unanswered

## knowledge_gaps

- APM documentation corpus not yet populated -- run knowledge build pipeline.
  See docs/knowledge-build.md for the refresh procedure.
```

Stop here. Do NOT synthesise an answer from model weights. Do NOT fabricate
citations. Return the fail-closed response verbatim.

## When to invoke (once corpus is built)

Invoke this skill whenever a user or agent asks a question about:

- APM CLI commands, flags, or workflows
- APM manifest (`apm.yml`) or lockfile (`apm.lock.yaml`) format
- APM primitives (skills, instructions, agents, personas)
- Publishing, installing, or removing APM packages
- APM marketplace governance and policy
- Any other topic covered by the APM v0.25.0 documentation

## How it works (corpus populated)

1. Receives the user's question as a natural-language string.
2. Invokes `apm-knowledge` internally to retrieve relevant corpus passages.
3. Checks `corpus_populated` -- if false or passages empty, returns fail-closed response.
4. Synthesises a response grounded in the retrieved passages only.
5. Attaches source citations and a quality marker to every answer.

## Response format (corpus populated)

```
## Answer

<synthesised answer grounded in corpus passages only>

## Sources

- <okf-entry-id> -- <short description of the source entry>

## Quality

answered | partial | unanswered

## knowledge_gaps

<populated when quality is partial or unanswered; empty list when answered>
```

Quality levels:

| Level | Meaning |
|-------|---------|
| `answered` | The corpus contains sufficient information to answer confidently. |
| `partial` | The corpus contains related information but not a complete answer. |
| `unanswered` | The question falls outside the corpus scope; say so explicitly. |

## Acknowledging gaps

When quality is `unanswered` or `partial`, add a `knowledge_gaps` entry
directing the user to the upstream repository (microsoft/apm) or the official
APM documentation for the most current information.

## Corpus scope

The vendored corpus covers microsoft/apm at tag v0.25.0 (d73e6ac3).
Questions about features or behaviour introduced after that tag receive a
`partial` or `unanswered` quality marker.
