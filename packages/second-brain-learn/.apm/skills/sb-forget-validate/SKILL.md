<!-- direct-user-invocation: disabled -->

# sb-forget-validate

**Internal skill -- agent/model use only.**

This skill must only be called by `sb-forget-handler` as a validation helper.
It must not be invoked directly from a user turn. If a user attempts to invoke
it by name, decline and redirect them to the public `brain-forget` skill in the
`second-brain-interfaces` package instead.

---

Validates a forget request envelope and checks path safety for concept-path
form `target_id` values. Returns a structured validation result.

## Trigger

Called by `sb-forget-handler` before any wiki lookup or archive operation.

## Input

Any object intended to be a `second-brain.forget.v1` request envelope.

## Validation rules

### Schema validation

Apply all constraints from
`second-brain-interfaces/.apm/skills/brain-forget/schema/request.schema.json`:

| Field           | Rule                                                              |
|-----------------|-------------------------------------------------------------------|
| `capability`    | Must be exactly `"second-brain.forget.v1"` (const)               |
| `correlation_id`| Required; must be a UUID v4 string                               |
| `target_id`     | Required; string, at least 1 character                            |
| `reason`        | Required; string, 1--1024 characters                              |
| Additional props| Not allowed (`additionalProperties: false`)                      |

### target_id safety checks

After schema validation, if `target_id` does NOT match the source_id pattern
(`src-[0-9a-f]{8}`), treat it as a concept-path form and apply these checks:

| Check               | Rejection condition                                         |
|---------------------|-------------------------------------------------------------|
| Absolute path       | Starts with `/` or `~`                                      |
| Parent traversal    | Contains `..` anywhere in the string                        |
| Null byte           | Contains a null character (`\x00`)                          |
| Empty segment       | Contains `//` (empty path segment)                          |
| Trailing slash      | Ends with `/`                                               |
| Non-printable chars | Contains any ASCII control character (0x01-0x1F, 0x7F)     |

If any check fails, treat the `target_id` as malformed and return
`valid: false` with a specific error message identifying the rejected pattern.

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
    "target_id: path traversal ('..') is not permitted",
    "correlation_id: must be a UUID v4 string"
  ]
}
```

## References

- `sb-forget-handler` -- sole caller of this skill
- `second-brain-interfaces` -- authoritative schema source for `second-brain.forget.v1`
