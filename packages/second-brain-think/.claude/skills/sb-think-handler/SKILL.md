<!-- direct-user-invocation: disabled -->

# sb-think-handler

**Internal skill -- agent/model use only.**

This skill must only be called by higher-level second-brain orchestration
skills (e.g. `brain-think`). It must not be invoked directly from a user turn.
If a user attempts to invoke it by name, decline and redirect them to the
public `brain-think` skill in the `second-brain-interfaces` package instead.

---

Receives a validated `second-brain.think.v1` request envelope, retrieves
relevant concepts from the Karpathy wiki, and returns a citation-backed answer.

## Read-only guarantee

This skill is strictly read-only. It never modifies the wiki, never archives
any concept, and never passes content to any ingestion skill. It calls only
`kw-wiki-query` for retrieval and `sb-think-validate` for validation.

## Trigger

Called by `brain-think` after the client has assembled a valid think request
envelope that matches the `second-brain.think.v1` schema.

## Input

A `second-brain.think.v1` request envelope:

```json
{
  "capability": "second-brain.think.v1",
  "correlation_id": "<uuid-v4>",
  "question": "<natural-language question>",
  "context": {
    "project": "<optional>",
    "tags": ["<optional>"]
  }
}
```

## Procedure

1. **Validate envelope**: Call `sb-think-validate` with the request envelope.
   If `valid` is false, return an error envelope with the validation messages.
   Stop.

2. **Retrieve concepts**: Call `kw-wiki-query` with:
   - `wiki_root`: the configured wiki root path
   - `query`: the `question` field from the request

   Collect the ranked list of matching concept documents returned by
   `kw-wiki-query` (index-first retrieval).

3. **Synthesise answer**: Read each retrieved concept document and compose a
   concise, grounded answer to the question. Base the answer only on content
   present in the retrieved concepts. Do not hallucinate facts.

4. **Build citations**: For each concept used in the answer, include a citation:

   ```json
   {
     "source_id": "<concept slug or source_id>",
     "label": "<concept title>",
     "excerpt": "<relevant 1-3 sentence excerpt from the concept>"
   }
   ```

5. **Classify quality**:
   - `answered`: at least one relevant concept was found and the question is
     fully addressed.
   - `partial`: relevant concepts exist but do not fully address the question.
   - `unanswered`: no relevant concepts were found.

6. **Identify knowledge gaps**: List topics or sub-questions that could not be
   answered from the wiki content.

7. **Return response envelope**:

```json
{
  "correlation_id": "<matches request>",
  "quality": "answered | partial | unanswered",
  "answer": "<synthesised answer with inline citation references>",
  "citations": [
    {
      "source_id": "<slug>",
      "label": "<concept title>",
      "excerpt": "<excerpt>"
    }
  ],
  "knowledge_gaps": ["<gap description>"]
}
```

## Quality classification guide

| Quality       | When to use                                                      |
|---------------|------------------------------------------------------------------|
| `answered`    | Retrieved concepts fully address the question.                   |
| `partial`     | Partial coverage; some aspects of the question remain open.      |
| `unanswered`  | No concepts retrieved or none relevant to the question.          |

## Error conditions

| Condition            | Response                                               |
|----------------------|--------------------------------------------------------|
| Validation fails     | Return error envelope with validation messages         |
| kw-wiki-query error  | Return `unanswered` with knowledge gap note            |
| Empty question       | Caught by validation; return error envelope            |

## References

- `sb-think-validate` -- envelope validation helper
- `kw-wiki-query` -- index-first concept retrieval from the OKF wiki
- `second-brain-interfaces` -- `second-brain.think.v1` schema and response schema
