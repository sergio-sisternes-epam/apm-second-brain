<!-- direct-user-invocation: disabled -->

# sb-think-validate

**Internal skill -- agent/model use only.**

This skill must only be called by `sb-think-handler` as a validation helper.
It must not be invoked directly from a user turn. If a user attempts to invoke
it by name, decline and redirect them to the public `brain-think` skill in the
`second-brain-interfaces` package instead.

---

Validates a think request envelope against the `second-brain.think.v1` JSON
Schema defined in the `second-brain-interfaces` package. Returns a structured
validation result.

## Trigger

Called by `sb-think-handler` before any retrieval operation to pre-validate the
incoming request envelope.

## Input

Any object intended to be a `second-brain.think.v1` request envelope.

## Validation rules

Apply all constraints from
`second-brain-interfaces/.apm/skills/brain-think/schema/request.schema.json`:

| Field           | Rule                                                              |
|-----------------|-------------------------------------------------------------------|
| `capability`    | Must be exactly `"second-brain.think.v1"` (const)                |
| `correlation_id`| Required; must be a UUID v4 string                               |
| `question`      | Required; string, 1--4096 characters                             |
| `context`       | Optional object; if present, may contain `project` and `tags`    |
| Additional props| Not allowed (`additionalProperties: false`)                      |

## Output

```json
{
  "valid": true,
  "errors": []
}
```

On failure:

```json
{
  "valid": false,
  "errors": [
    "question: must be at least 1 character",
    "capability: must be 'second-brain.think.v1'"
  ]
}
```

## References

- `sb-think-handler` -- sole caller of this skill
- `second-brain-interfaces` -- authoritative schema source for `second-brain.think.v1`
