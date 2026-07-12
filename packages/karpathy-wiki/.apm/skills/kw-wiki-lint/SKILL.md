<!-- direct-user-invocation: disabled -->

# kw-wiki-lint

**Internal skill -- agent/model use only.**

This skill must only be called by higher-level second-brain orchestration
skills. It must not be invoked directly from a user turn. If a user attempts
to invoke it by name, decline and redirect them to the public second-brain
skills instead.

---

Check a Karpathy wiki for OKF conformance violations. Emits a structured
report listing each violation by file, type, and detail.

## Trigger

Called before any publish, sync, or share operation, or when an orchestrator
needs to validate wiki health.

## Parameters

| Name | Required | Description |
|------|----------|-------------|
| `wiki_root` | yes | Path to the provider-project directory |

## Procedure

1. **Presence checks** (structural):
   - `<wiki_root>/wiki/` exists
   - `<wiki_root>/wiki/index.md` exists
   - `<wiki_root>/wiki/log.md` exists
   - `<wiki_root>/raw/` exists
   - `<wiki_root>/SCHEMA.md` exists alongside `wiki/` (not inside it)

2. **Boundary check** -- nothing Karpathy-specific inside `wiki/`:
   - `SCHEMA.md` must NOT appear inside `wiki/`
   - `raw/` must NOT appear inside `wiki/`

3. **Concept frontmatter check** (for each `.md` in `wiki/concepts/` except `index.md`):
   - Frontmatter block present (`---` delimiters)
   - Required fields: `id`, `title`, `type`, `created`, `modified`
   - No empty values for required fields

4. **Wikilink check** -- scan all `.md` files in `wiki/` for `[[...]]` patterns.
   Standard Markdown links only. Any wikilink is a violation.

5. **Log format check**:
   - `log.md` date headings match `## YYYY-MM-DD` pattern
   - Date headings are in newest-first (descending) order

6. **Index check**:
   - `index.md` contains `okf_version: "0.1"` in frontmatter

## Report format

Emit a structured report:

```
OKF Conformance Report -- <wiki_root>
Status: PASS | FAIL

Violations:
  [ERROR] <file>: <violation-type> -- <detail>
  [WARN]  <file>: <violation-type> -- <detail>

Summary: <N> errors, <M> warnings
```

Return `PASS` only if there are zero errors (warnings do not affect pass/fail).

## Violation types

| ID | Severity | Description |
|----|----------|-------------|
| `kw-boundary-violation` | ERROR | Karpathy-specific file found inside wiki/ |
| `kw-frontmatter-missing` | ERROR | Concept file has no frontmatter |
| `kw-frontmatter-field-missing` | ERROR | Required frontmatter field absent |
| `kw-wikilink-found` | ERROR | [[...]] wikilink found in wiki/ file |
| `kw-log-heading-format` | ERROR | log.md heading does not match YYYY-MM-DD |
| `kw-log-order` | ERROR | log.md date headings not newest-first |
| `kw-index-missing-version` | WARN | index.md lacks okf_version frontmatter |
| `kw-schema-missing` | WARN | SCHEMA.md not found alongside wiki/ |

## Error conditions

| Condition | Response |
|-----------|----------|
| `wiki/` not found | Report single ERROR: wiki/ missing; abort further checks |
| File unreadable | Report ERROR for that file; continue checking others |

## References

- OKF v0.1 specification (see `open-knowledge-format` package)
- `okf-bundle-validate` for bundle-level validation
