# akn-discover

Discover and list agents registered in the local Agent Knowledge Network registry.

Returns active agents only. Stale agents are excluded from results.

## When to invoke

Invoke this skill when a user or calling agent says any of:
- "list registered agents"
- "discover agents in the knowledge network"
- "what agents are registered?"
- "find agents that can <capability>"
- "akn-discover"
- "show me the agent registry"

## Inputs

All inputs are optional.

| Field | Description |
|-------|-------------|
| `capabilityId` | Filter results to agents that expose this capability ID (exact match). Omit to return all active agents. |

## Procedure

1. Resolve the registry path: `${APM_HOME:-~/.apm}/agent-knowledge-network/registry.json`.
2. Call **akn-registry-io** with op `list` to retrieve the current registry.
3. If the registry does not exist or `agents[]` is empty, emit an empty result
   set with an informational note.
4. Filter: keep only agents where `status == 'active'`.
5. If `capabilityId` was supplied, further filter to agents whose
   `capabilities[].id` contains the requested value (exact string match).
6. For each matching agent, project the summary fields listed below.
7. Emit the results table to the user.

## Output

Emit a summary table. If no agents match, say so clearly.

```
Active agents in the Agent Knowledge Network
=============================================
Total active: <n>   Filter: <capabilityId or 'none'>

agentId       : <uuid>
displayName   : <name>
owner/project : <owner> / <project>
transport     : copilot-app / <projectId>
capabilities  : <id@version> [, ...]
knowledge root: <default root label> (<format>)
---
(repeat for each agent)
```

If the registry file does not exist, emit:

```
No registry found at <path>.
Run akn-register to add the first agent.
```

## Error handling

- If **akn-registry-io** returns `ok: false`, surface the error message verbatim.
- Do not attempt to repair or re-initialise the registry from this skill.

## Notes

- This skill is read-only; it never mutates the registry.
- All file I/O is delegated to **akn-registry-io**.
- Stale agents (those with `status == 'stale'`) are intentionally hidden from
  the output to keep the result set actionable.
