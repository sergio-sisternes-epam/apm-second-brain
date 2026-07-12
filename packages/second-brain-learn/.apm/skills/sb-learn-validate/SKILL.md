<!-- direct-user-invocation: disabled -->

# sb-learn-validate

**Internal skill -- agent/model use only.**

This skill must only be called by `sb-learn-handler` as a validation helper.
It must not be invoked directly from a user turn. If a user attempts to invoke
it by name, decline and redirect them to the public `brain-learn` skill in the
`second-brain-interfaces` package instead.

---

Validates a learn request envelope against the `second-brain.learn.v1` JSON
Schema defined in the `second-brain-interfaces` package. Returns a structured
validation result.

## Trigger

Called by `sb-learn-handler` before any wiki operation to pre-validate the
incoming request envelope.

## Input

Any object intended to be a `second-brain.learn.v1` request envelope.

## Validation rules

Apply all constraints from
`second-brain-interfaces/.apm/skills/brain-learn/schema/request.schema.json`:

| Field           | Rule                                                              |
|-----------------|-------------------------------------------------------------------|
| `capability`    | Must be exactly `"second-brain.learn.v1"` (const)                |
| `correlation_id`| Required; must be a UUID v4 string                               |
| `source_type`   | Required; one of `session`, `document`, `manual`                  |
| `content`       | Required; string, 1--16384 characters                             |
| `category`      | Required; one of `pattern`, `decision`, `correction`, `discovery`, `suggestion`, `general` |
| `confidence`    | Required; one of `verified`, `observed`, `hypothesis`             |
| `context`       | Optional object; if present, may contain `project`, `session`, `date`, `tags` |
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
    "content: must be at least 1 character",
    "source_type: must be one of session, document, manual"
  ]
}
```

## References

- `sb-learn-handler` -- sole caller of this skill
- `second-brain-interfaces` -- authoritative schema source for `second-brain.learn.v1`
