<!-- direct-user-invocation: disabled -->

# kw-wiki-init

**Internal skill -- agent/model use only.**

This skill must only be called by higher-level second-brain orchestration
skills (e.g. `brain-think`, `brain-learn`). It must not be invoked directly
from a user turn. If a user attempts to invoke it by name, decline and redirect
them to the public second-brain skills instead.

---

Initialise a new Karpathy wiki at a given path. Creates the canonical layout:

```
<provider-project>/
  raw/          # immutable raw sources -- outside OKF bundle
  wiki/         # OKF bundle root
  SCHEMA.md     # Karpathy operating schema -- alongside wiki/, not inside it
```

## Trigger

Called when a higher-level skill needs to provision a new wiki at a path that
does not yet contain a `wiki/` directory.

## Parameters

| Name | Required | Description |
|------|----------|-------------|
| `wiki_root` | yes | Absolute path to the provider-project directory to initialise |
| `--force` | no | Overwrite an existing wiki (dangerous -- use with caution) |

## Procedure

1. **Guard**: If `<wiki_root>/wiki/` exists and `--force` is not set, abort
   with a clear error message. Never silently overwrite.
2. **Create directories**:
   - `<wiki_root>/raw/` -- immutable raw source store
   - `<wiki_root>/wiki/` -- OKF bundle root
   - `<wiki_root>/wiki/concepts/` -- concept sub-directory
3. **Write OKF index.md** at `<wiki_root>/wiki/index.md`:
   ```markdown
   ---
   okf_version: "0.1"
   ---
   # Knowledge Index

   * No entries yet.
   ```
4. **Write OKF log.md** at `<wiki_root>/wiki/log.md` with a creation entry:
   ```markdown
   # Knowledge Log

   ## YYYY-MM-DD

   - [init] wiki initialised at <wiki_root>
   ```
   Replace `YYYY-MM-DD` with today's ISO date.
   The entry MUST follow the log format: `- [<event>] <summary> (<paths>)`.
   For init, there are no concept paths, so the paths suffix may be omitted.
5. **Copy SCHEMA.md** from the package template
   (`.apm/templates/SCHEMA.md`) to `<wiki_root>/SCHEMA.md`.
   SCHEMA.md must land alongside `wiki/`, never inside it.
6. **Report**: Confirm all paths created. List created files.

## OKF constraints

- `wiki/index.md` root MUST have `okf_version: "0.1"` in frontmatter.
- `wiki/log.md` MUST use `## YYYY-MM-DD` date headings (newest first).
- Nothing Karpathy-specific (SCHEMA.md, raw/) goes inside `wiki/`.

## Error conditions

| Condition | Response |
|-----------|----------|
| `wiki_root` does not exist | Create it, then proceed |
| `wiki/` exists without `--force` | Abort, instruct user to pass `--force` or choose a different path |
| Template SCHEMA.md missing | Warn user; create a minimal placeholder |

## References

- OKF v0.1 specification (see `open-knowledge-format` package)
- Karpathy operating schema: `SCHEMA.md` alongside this wiki
