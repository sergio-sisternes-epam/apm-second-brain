<!-- direct-user-invocation: disabled -->

# akn-registry-io

**Internal skill -- agent/model use only.**

This skill must only be called by `akn-register`, `akn-discover`, or
`akn-deregister`. It must never be invoked directly from a user turn. If a user
attempts to invoke it by name, politely decline and explain that it is an
internal implementation detail of the Agent Knowledge Network; direct the user
to one of the three public skills instead.

---

Low-level registry read-modify-write for the Agent Knowledge Network.

Implements advisory locking, revision-based conflict detection, atomic
file replacement, and restricted file permissions on the registry JSON.

## Registry path

```
${APM_HOME:-~/.apm}/agent-knowledge-network/registry.json
```

The directory is created if it does not exist. The registry file is
initialised on first write.

## Supported operations

The skill (via `registry_io.py`) accepts a JSON operation on stdin:

```json
{ "op": "<read|upsert|delete|list>", "payload": { ... } }
```

### `read`

Returns the full registry as-is. No payload fields required.

```json
{ "op": "read", "payload": {} }
```

Returns `{ "ok": true, "result": { <full registry> } }` or an empty
registry object if the file does not exist.

### `list`

Alias for `read` -- returns the full registry. Callers filter client-side.

### `upsert`

Write (create or replace) the full `agents[]` array. The caller supplies
the complete updated array; the script does not merge individual fields.

```json
{
  "op": "upsert",
  "payload": {
    "expectedRevision": <integer>,
    "agents": [ <full agent objects> ]
  }
}
```

The script checks that the stored `revision` equals `expectedRevision`.
If it does not, the operation is rejected with a stale-revision error.
On success, `revision` is incremented by one.

### `delete`

Remove a single agent by `agentId`.

```json
{
  "op": "delete",
  "payload": {
    "expectedRevision": <integer>,
    "agentId": "<uuid>"
  }
}
```

Same revision check applies.

## I/O procedure

1. **Acquire advisory lock**: write `<registry_path>.lock`. If the lock
   file already exists, wait up to 5 seconds then fail with a timeout
   error. Do not forcibly remove an existing lock.
2. **Read registry**: parse `registry.json` if present; otherwise treat as
   `{ schemaVersion: '1', revision: 0, agents: [] }`.
3. **Check `schemaVersion`**: if present and not `'1'`, reject with an
   incompatible-schema error.
4. **Revision check** (for mutating ops): compare stored `revision` with
   `payload.expectedRevision`. If they differ, return
   `{ ok: false, error: 'stale-revision: expected <n>, found <m>' }`.
5. **Perform mutation**: apply the requested change to the in-memory object.
6. **Write to `.tmp`**: serialise the updated object to
   `<registry_path>.tmp`, then flush/fsync.
7. **Atomic rename**: rename `.tmp` to `registry.json`.
8. **Set permissions**: `chmod 0600` on `registry.json`.
9. **Release lock**: delete `<registry_path>.lock`.

## Error responses

All errors are returned as:

```json
{ "ok": false, "error": "<human-readable message>" }
```

Never mutate the registry when returning an error.

## Script invocation

The skill calls `registry_io.py` located alongside this SKILL.md:

```bash
python3 .apm/skills/akn-registry-io/registry_io.py <<'EOF'
{ "op": "read", "payload": {} }
EOF
```

Always pass the operation as a single JSON object on stdin. The script
returns a single JSON object on stdout.

## Security notes

- `chmod 0600` on the registry ensures only the owning user can read/write it.
- The lock file is advisory only; the mechanism prevents concurrent agent calls
  but does not protect against external processes bypassing it.
- The `.tmp` + rename pattern ensures the registry is never left in a partially
  written state.
