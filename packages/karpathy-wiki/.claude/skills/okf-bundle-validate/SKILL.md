# okf-bundle-validate

Invoke this skill when asked to **validate** an OKF bundle or **check conformance** of a directory of knowledge files.

## Trigger phrases

- "validate this OKF bundle"
- "check okf conformance"
- "run okf-bundle-validate on <path>"
- "is this bundle OKF-conformant?"

## What you do

1. Identify the `<bundle-path>` from the user's request (default: current working directory).
2. Locate `okf_validator.py` -- it is shipped alongside this skill at:
   `.apm/skills/okf-bundle-validate/okf_validator.py`
   If the file is not on disk, tell the user to re-install the package.
3. Run the validator:
   ```
   python3 .apm/skills/okf-bundle-validate/okf_validator.py <bundle-path>
   ```
4. The script writes a JSON report to stdout. Parse and present it to the user:
   - Show overall conformance status (conformant / non-conformant).
   - List any errors (rule violations) grouped by file.
   - List warnings (missing recommended fields) if present.
   - Offer to fix simple errors (missing frontmatter, missing `type`) if the user asks.

## JSON output contract

The validator outputs a single JSON object to stdout:

```json
{
  "conformant": true,
  "okf_version": "0.1",
  "bundle_path": "<resolved-absolute-path>",
  "summary": {
    "total_files": 5,
    "concept_files": 3,
    "index_files": 1,
    "log_files": 1,
    "errors": 0,
    "warnings": 2
  },
  "results": [
    {
      "file": "concepts/data-model.md",
      "kind": "concept",
      "status": "pass",
      "rules": [
        { "rule": "C1-frontmatter-present", "status": "pass", "message": "Frontmatter block found." },
        { "rule": "C2-type-required", "status": "pass", "message": "type = \"Reference\"" }
      ]
    }
  ]
}
```

`conformant` is `false` if any rule has `status: "fail"`. Warnings do not affect conformance.

## Rule reference

| Rule ID | Kind | Severity | Description |
|---------|------|----------|-------------|
| C1-frontmatter-present | concept | error | Every non-reserved .md file must have a parseable YAML frontmatter block. |
| C2-type-required | concept | error | Frontmatter must contain a non-empty `type` field. |
| I1-index-no-frontmatter | index | error | index.md files other than the bundle root MUST NOT have frontmatter. |
| I2-index-root-okf-version | index | warning | Root index.md SHOULD declare `okf_version: "0.1"` in frontmatter. |
| I3-index-has-list-entries | index | warning | index.md body SHOULD contain at least one `* [...](...) -` list entry. |
| L1-log-date-headings | log | error | log.md date headings MUST be ISO 8601 YYYY-MM-DD (`## YYYY-MM-DD`). |
| L2-log-newest-first | log | error | log.md date headings MUST be in descending order (newest first). |
| W1-title-recommended | concept | warning | `title` field is recommended by OKF v0.1. |
| W2-timestamp-recommended | concept | warning | `timestamp` field is recommended by OKF v0.1. |

## Running directly

You can run the validator yourself without the agent:
```bash
python3 .apm/skills/okf-bundle-validate/okf_validator.py /path/to/bundle
python3 .apm/skills/okf-bundle-validate/okf_validator.py /path/to/bundle | python3 -m json.tool
```

Exit code 0 = conformant; exit code 1 = non-conformant; exit code 2 = script error.

## References

OKF v0.1 specification -- GoogleCloudPlatform/knowledge-catalog @ ee67a5ca, okf/SPEC.md (Apache-2.0)
