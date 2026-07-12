# akn-deregister

Explicitly remove an agent from the local Agent Knowledge Network registry.

This is a destructive, irreversible operation. A confirmation step is required
before the record is deleted.

## When to invoke

Invoke this skill when a user or calling agent says any of:
- "deregister agent <agentId>"
- "remove agent from the knowledge network"
- "unregister agent"
- "akn-deregister"
- "delete agent registration"

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `agentId` | yes | The stable UUID of the agent to remove |

## Procedure

1. Resolve the registry path: `${APM_HOME:-~/.apm}/agent-knowledge-network/registry.json`.
2. Call **akn-registry-io** with op `read` to load the current registry.
3. Search `agents[]` for an entry whose `agentId` matches the supplied value.
4. If no match is found, emit a clear "not found" message and stop.
5. **Confirmation gate**: Present the agent details to the user and ask for
   explicit confirmation before proceeding. Do not proceed without it.

   ```
   You are about to permanently remove:
     agentId    : <uuid>
     displayName: <name>
     project    : <project>
   This cannot be undone. Confirm? [yes / no]
   ```

6. If the user confirms, call **akn-registry-io** with op `delete`, supplying
   the `agentId` to remove and the current `revision + 1`.
7. Emit a deregistration receipt.

## Output

On success:

```
Deregistration receipt
----------------------
agentId    : <uuid>
displayName: <name>
status     : removed
```

On cancellation:

```
Deregistration cancelled. Registry unchanged.
```

On not found:

```
No agent with agentId '<uuid>' found in the registry.
Use akn-discover to list registered agents.
```

## Error handling

- If **akn-registry-io** returns `ok: false`, surface the error message verbatim
  and do not proceed.
- If a stale-revision conflict is reported, reload and retry once. If it fails
  again, surface the error.

## Notes

- All file I/O is delegated to **akn-registry-io**.
- The confirmation gate must not be bypassed, even when called from an
  automated context, unless the caller explicitly passes a pre-confirmed flag
  (`confirmed: true`) in its invocation payload.
- If the agent is already marked `stale`, deregistration still proceeds
  (stale agents remain in the registry until explicitly removed).
