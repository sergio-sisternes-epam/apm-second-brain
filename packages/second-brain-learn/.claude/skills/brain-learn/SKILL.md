# brain-learn

Send a versioned learn request to the configured second-brain provider,
submitting a structured learning for ingestion.

## Capability

`second-brain.learn.v1`

## When to invoke

Invoke after completing a task when the session produced knowledge worth
preserving: debugging breakthroughs, tool behaviour discoveries, architecture
decisions, negative results, or step-by-step procedures. Do not submit
routine code changes or well-documented standard procedures.

## Request envelope

```json
{
  "capability": "second-brain.learn.v1",
  "correlation_id": "<uuid-v4>",
  "source_type": "session | document | manual",
  "content": "<structured learning text>",
  "category": "pattern | decision | correction | discovery | suggestion | general",
  "confidence": "verified | observed | hypothesis",
  "context": {
    "project": "<project name or empty string>",
    "session": "<session identifier or empty string>",
    "date": "<ISO-8601 date>",
    "tags": ["<tag>"]
  }
}
```

Read `schema/request.schema.json` for the full JSON Schema.

### Confidence levels

| Level        | Meaning                                              |
|--------------|------------------------------------------------------|
| `verified`   | Tested and confirmed with reproducible evidence.     |
| `observed`   | Seen in practice but not exhaustively tested.        |
| `hypothesis` | Reasonable inference; needs further validation.      |

## Receipt envelope

```json
{
  "correlation_id": "<matches request>",
  "source_id": "<assigned identifier>",
  "status": "accepted | duplicate | invalid",
  "message": "<human-readable status detail>"
}
```

Read `schema/response.schema.json` for the full JSON Schema.

## Handling receipt status

| `status`    | Agent action                                                         |
|-------------|----------------------------------------------------------------------|
| `accepted`  | Record `source_id`; learning is queued for ingestion.               |
| `duplicate` | Provider detected near-duplicate; no action needed.                 |
| `invalid`   | Fix the envelope (check `message`) and resubmit if appropriate.     |

## Error handling

On transport error the adapter returns the standard error envelope
(see `schema/error.schema.json`). Log `code` and `correlation_id`.

## Schemas

| File                        | Purpose                    |
|-----------------------------|----------------------------|
| `schema/request.schema.json`  | Learn request envelope     |
| `schema/response.schema.json` | Learn receipt envelope     |
| `schema/error.schema.json`    | Standard error envelope    |

## Adapter contract

See `.apm/instructions/adapter-contract.md` for how adapters map this
capability to a concrete transport.
