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
   If `valid` is false, return a schema-valid error envelope:

   ```json
   {
     "correlation_id": "<matches request or empty-uuid if unparseable>",
     "quality": "unanswered",
     "answer": "",
     "citations": [],
     "knowledge_gaps": ["VALIDATION_ERROR: <joined error messages>"]
   }
   ```

   Use the prefix `VALIDATION_ERROR:` in `knowledge_gaps[0]` so callers can
   programmatically detect the failure mode. Stop.

2. **Retrieve concepts**: Call `kw-wiki-query` with:
   - `wiki_root`: the configured wiki root path
   - `query`: the `question` field from the request

   Collect the ranked list of matching, non-archived concept documents.

3. **No-match handling**: If `kw-wiki-query` returns zero results, return
   immediately with `quality: unanswered`, empty `answer`, empty `citations`,
   and a knowledge gap naming the unresolved question. Do not synthesise a
   response from general knowledge.

4. **Synthesise answer**: Read each retrieved concept document and compose a
   concise, grounded answer to the question. Base the answer only on content
   present in the retrieved concepts. Do not hallucinate facts.

5. **Build citations**: For each concept document used in the answer, read its
   YAML frontmatter and extract the `source_id:` field (written there by the
   learn handler during ingestion). Build a citation object:

   ```json
   {
     "source_id": "<value of source_id frontmatter field, e.g. src-a1b2c3d4>",
     "label": "<value of title: frontmatter field>",
     "excerpt": "<relevant 1-3 sentence excerpt from the concept body>"
   }
   ```

   Do NOT substitute concept slugs or file paths for `source_id`. If a concept
   document lacks a `source_id:` frontmatter field, omit that document from
   citations and note the gap.

6. **Classify quality**:
   - `answered`: at least one relevant concept was found, the question is fully
     addressed, and `citations` is non-empty.
   - `partial`: relevant concepts exist but do not fully address the question;
     `citations` may be non-empty.
   - `unanswered`: no relevant non-archived concepts were found, or no
     synthesised answer is possible.

   **Invariant**: `quality: answered` requires at least one citation.
   If no concept yields a valid `source_id`, downgrade quality to `partial`.

7. **Identify knowledge gaps**: List topics or sub-questions that could not be
   answered from the wiki content.

8. **Return response envelope**:

```json
{
  "correlation_id": "<matches request>",
  "quality": "answered | partial | unanswered",
  "answer": "<synthesised answer>",
  "citations": [
    {
      "source_id": "src-a1b2c3d4",
      "label": "<concept title from frontmatter>",
      "excerpt": "<excerpt>"
    }
  ],
  "knowledge_gaps": ["<gap description>"]
}
```

## Quality classification guide

| Quality       | When to use                                                      |
|---------------|------------------------------------------------------------------|
| `answered`    | Full coverage; at least one citation with real source_id.        |
| `partial`     | Partial coverage; some aspects remain open.                      |
| `unanswered`  | No concepts retrieved, zero results, or validation error.        |

## Error conditions

| Condition            | Response                                               |
|----------------------|--------------------------------------------------------|
| Validation fails     | Return unanswered with VALIDATION_ERROR in gaps        |
| kw-wiki-query error  | Return `unanswered` with knowledge gap note            |
| No results           | Return `unanswered`; empty citations                   |
| No source_id in docs | Downgrade to `partial`; note missing provenance        |

## References

- `sb-think-validate` -- envelope validation helper
- `kw-wiki-query` -- index-first concept retrieval from the OKF wiki
- `second-brain-interfaces` -- `second-brain.think.v1` schema and response schema
