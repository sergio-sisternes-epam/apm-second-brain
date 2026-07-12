# brain-think

Send a versioned think request to the configured second-brain provider and
surface the answer to the user.

## Capability

`second-brain.think.v1`

## When to invoke

Invoke this skill before implementing any multi-step task, debugging session,
infrastructure change, or tool-integration when relevant prior knowledge may
exist. The skill queries the provider and returns distilled guidance.

## Request envelope

```json
{
  "capability": "second-brain.think.v1",
  "correlation_id": "<uuid-v4>",
  "question": "<natural-language question>",
  "context": {
    "project": "<project name or empty string>",
    "tags": ["<tag>"]
  }
}
```

Read `schema/request.schema.json` for the full JSON Schema.

## Response envelope

```json
{
  "correlation_id": "<matches request>",
  "quality": "answered | partial | unanswered",
  "answer": "<text or empty string>",
  "citations": [
    { "source_id": "<id>", "label": "<human-readable label>", "excerpt": "<short quote>" }
  ],
  "knowledge_gaps": ["<gap description>"]
}
```

Read `schema/response.schema.json` for the full JSON Schema.

## Handling response quality

| `quality`     | Agent action                                                            |
|---------------|-------------------------------------------------------------------------|
| `answered`    | Surface `answer` and `citations` to the user; proceed with confidence. |
| `partial`     | Surface what is known; note `knowledge_gaps`; flag uncertainty.        |
| `unanswered`  | Inform the user that no relevant knowledge was found; proceed carefully.|

## Error handling

On transport error or provider-side failure the adapter returns the standard
error envelope (see `schema/error.schema.json`). Log `code` and
`correlation_id`; do not retry automatically unless `code` is `TRANSIENT`.

## Schemas

| File                        | Purpose                    |
|-----------------------------|----------------------------|
| `schema/request.schema.json`  | Think request envelope     |
| `schema/response.schema.json` | Think response envelope    |
| `schema/error.schema.json`    | Standard error envelope    |

## Adapter contract

See `.apm/instructions/adapter-contract.md` for how adapters map this
capability to a concrete transport.
