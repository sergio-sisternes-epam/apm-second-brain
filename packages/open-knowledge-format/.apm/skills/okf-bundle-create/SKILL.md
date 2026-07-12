# okf-bundle-create

Invoke this skill when asked to **initialise** or **create** a new Open Knowledge Format (OKF) v0.1 bundle at a given path.

## Trigger phrases

- "create an OKF bundle"
- "initialise a knowledge bundle"
- "set up a new OKF bundle at <path>"
- "init okf bundle"

## What you do

1. Resolve the target `<bundle-path>` from the user's request.
2. **Existence check** -- if `<bundle-path>/index.md` or `<bundle-path>/log.md` already exist, stop and ask the user to confirm with `--force` before overwriting anything.
3. Create the directory if it does not exist.
4. Write `<bundle-path>/index.md` -- see the Index scaffold below.
5. Write `<bundle-path>/log.md` -- see the Log scaffold below.
6. Confirm success to the user with the bundle path and the two files created.

## Scaffolds

### index.md scaffold

```markdown
# Knowledge Bundle

> OKF v0.1 bundle. Add concept links below as you populate the bundle.

# Concepts

*(No concepts yet. Add entries as: `* [Title](path/to/concept.md) - short description`)*
```

The root `index.md` MAY include a YAML frontmatter block declaring the OKF version:

```markdown
---
okf_version: "0.1"
---

# Knowledge Bundle
...
```

Including the frontmatter block is recommended so validators can detect the declared version.

### log.md scaffold

Use today's ISO date (YYYY-MM-DD):

```markdown
# Bundle Update Log

## YYYY-MM-DD
* **Initialisation**: Created OKF v0.1 bundle structure (index.md, log.md).
```

## OKF v0.1 conformance rules (brief)

- Concept files: every `.md` that is not `index.md` or `log.md` MUST have a YAML frontmatter block with a non-empty `type` field.
- `index.md`: no frontmatter (except the optional `okf_version` block at the bundle root); body uses `# Heading` sections with `* [Title](url) - description` list entries.
- `log.md`: flat list of `## YYYY-MM-DD` headings, newest first.
- Links between concepts use standard Markdown links (not wiki-links).

## --force behaviour

When the user explicitly passes `--force` (or confirms overwrite):
- Overwrite existing `index.md` and `log.md` with fresh scaffolds.
- Append a log entry to the new `log.md` noting the reinitialisation.

## References

OKF v0.1 specification -- GoogleCloudPlatform/knowledge-catalog @ ee67a5ca, okf/SPEC.md (Apache-2.0)
