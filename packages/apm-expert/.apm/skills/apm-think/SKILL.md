# apm-think

Public capability: `apm-expert.answer.v1`

Answers questions about the Agent Package Manager by querying the internal
`apm-knowledge` corpus and synthesising a citation-backed response.

## When to invoke

Invoke this skill whenever a user or agent asks a question about:

- APM CLI commands, flags, or workflows
- APM manifest (`apm.yml`) or lockfile (`apm.lock.yaml`) format
- APM primitives (skills, instructions, agents, personas)
- Publishing, installing, or removing APM packages
- APM marketplace governance and policy
- Any other topic covered by the APM v0.25.0 documentation

## How it works

1. Receives the user's question as a natural-language string.
2. Invokes `apm-knowledge` internally to retrieve relevant corpus passages.
3. Synthesises a response grounded in those passages.
4. Attaches source citations and a quality marker to every answer.

## Response format

Every response includes:

```
## Answer

<synthesised answer grounded in corpus passages>

## Sources

- <okf-entry-id> -- <short description of the source entry>

## Quality

answered | partial | unanswered
```

Quality levels:

| Level | Meaning |
|-------|---------|
| `answered` | The corpus contains sufficient information to answer confidently. |
| `partial` | The corpus contains related information but not a complete answer. |
| `unanswered` | The question falls outside the corpus scope; say so explicitly. |

## Acknowledging gaps

When quality is `unanswered` or `partial`, include a note directing the
user to the upstream repository (microsoft/apm) or the official APM
documentation for the most current information.

## Corpus scope

The vendored corpus covers microsoft/apm at tag v0.25.0 (d73e6ac3).
Questions about features or behaviour introduced after that tag receive a
`partial` or `unanswered` quality marker.
