# akn-register

Register or update an agent in the local Agent Knowledge Network registry.

This skill performs idempotent provider bootstrap. If an agent with the same
`transport.projectId` already exists, the record is updated in place without
creating a duplicate. On first registration a stable UUID `agentId` is generated.

## When to invoke

Invoke this skill when a user or automated agent bootstrap flow says any of:
- "register this agent in the knowledge network"
- "add this agent to the registry"
- "bootstrap agent capabilities"
- "update my agent registration"
- "akn-register"

## Inputs

Collect the following from the user or calling context. Items marked optional
may be omitted; use the stated default.

| Field | Required | Description |
|-------|----------|-------------|
| `displayName` | yes | Human-readable agent name |
| `owner` | yes | Owner identifier (e.g. team name) |
| `project` | yes | Project short name |
| `transport.projectId` | yes | Copilot App project ID for this agent |
| `capabilities` | yes | List of capability objects (see schema below) |
| `knowledgeRoots` | no | List of knowledge root objects (see schema below) |
| `constraints` | no | List of constraint strings; defaults to `[]` |

### Capability object schema

```json
{
  "id": "<string>",
  "version": "<string>",
  "interactionMode": "<string>"
}
```

### Knowledge root object schema

```json
{
  "id": "<string>",
  "label": "<string>",
  "format": "<string>",
  "pathBase": "project",
  "path": "<relative path from project root>",
  "default": true
}
```

## Procedure

1. Resolve the registry path: `${APM_HOME:-~/.apm}/agent-knowledge-network/registry.json`.
2. Call **akn-registry-io** with op `read` to load the current registry (or start
   from an empty one if the file does not yet exist).
3. Search `agents[]` for an entry whose `transports[].projectId` matches the
   supplied `transport.projectId`.
4. **If no match** (new registration):
   - Generate a new UUID v4 as `agentId`.
   - Build the full agent record using the supplied fields.
   - Set `status: 'active'`, `registeredAt: <now ISO 8601>`,
     `lastValidatedAt: null`, `lastValidationError: null`.
   - Append the record to `agents[]`.
   - Set `outcome: 'registered'`.
5. **If match found** (update):
   - Preserve the existing `agentId` and `registeredAt`.
   - Overwrite `displayName`, `owner`, `project`, `transports`, `capabilities`,
     `knowledgeRoots`, `constraints`.
   - Set `status: 'active'`, `lastValidatedAt: null`, `lastValidationError: null`.
   - Set `outcome: 'updated'`.
6. Call **akn-registry-io** with op `upsert` to persist the mutated registry,
   supplying the full updated `agents[]` array and the current `revision + 1`.
7. Emit a registration receipt to the user.

## Output

Emit a concise receipt in this format:

```
Registration receipt
--------------------
agentId  : <uuid>
status   : registered | updated
project  : <project>
transport: copilot-app / <projectId>
capabilities: <comma-separated capability IDs>
```

## Error handling

- If **akn-registry-io** returns `ok: false`, surface the error message and
  stop; do not retry automatically.
- If required fields are missing, list them and ask the caller to supply them.
- Do not silently swallow registry I/O errors.

## Notes

- This skill delegates all file I/O to **akn-registry-io**; it does not touch
  the filesystem directly.
- `agentId` is stable once assigned; it must not change on subsequent updates.
- The registry path is live state and is never committed to version control.
