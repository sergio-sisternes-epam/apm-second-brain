# okf-import

Invoke this skill when asked to **import** an existing Markdown corpus into OKF v0.1 format. The canonical source is a flat folder of `.md` files (such as an Obsidian vault export, a wiki dump, or any collection of unstructured markdown notes).

## Trigger phrases

- "import my markdown notes into OKF"
- "convert this folder of .md files to OKF format"
- "migrate obsidian vault to OKF"
- "run okf-import on <source-path>"

## What you do

### Step 1 -- Gather parameters

Ask the user (or read from arguments) for:
- `<source-path>` -- directory containing the source `.md` files.
- `<dest-path>` -- target OKF bundle root (must not already exist unless `--force` is given).
- `--type <default-type>` -- default `type` value to use for concepts that lack a `type` field (e.g., `Note`, `Reference`, `Playbook`). Defaults to `Note`.
- `--dry-run` -- preview changes without writing files.

### Step 2 -- Scan the source

List all `.md` files under `<source-path>` (recursively). For each file:
1. Attempt to parse existing YAML frontmatter.
2. Classify as:
   - **Has OKF-compatible frontmatter** -- has a `type` field. Minimal rewriting needed.
   - **Has partial frontmatter** -- has some YAML but no `type`. Add `type` using `--type` default.
   - **No frontmatter** -- needs a complete frontmatter block synthesised from filename and headings.
   - **Reserved name** -- `index.md` or `log.md` should be handled separately (see Step 4).
3. Report the scan summary to the user before writing anything.

### Step 3 -- Rewrite concept files

For each concept file, write the OKF-conformant version to `<dest-path>`:
1. **Frontmatter** -- ensure `type` is present. Add `title` from the first `# Heading` in the body if missing. Add `timestamp` from file mtime or today's date in ISO 8601 form.
2. **Links** -- convert Obsidian-style `[[wikilinks]]` to standard Markdown links:
   - `[[TargetTitle]]` -> `[TargetTitle](./target-title.md)` (slugify the target).
   - `[[TargetTitle|Alias]]` -> `[Alias](./target-title.md)`.
   - Warn if the target does not exist in the source corpus (broken link).
3. **Preserve** all other frontmatter keys and body content.
4. **Place** each file into a subdirectory matching its `type` (slugified), unless `--flat` is set.
   Example: `type: Playbook` -> `<dest-path>/playbooks/<filename>.md`.

### Step 4 -- Generate index.md

At the bundle root and in each subdirectory, generate an `index.md` listing all concepts in that scope:

```markdown
# <Directory or Bundle Name>

# <Type Group Heading>

* [Title 1](./file1.md) - description from frontmatter
* [Title 2](./file2.md) - description from frontmatter
```

### Step 5 -- Generate log.md

At the bundle root, generate a `log.md` with today's entry:

```markdown
# Bundle Update Log

## YYYY-MM-DD
* **Import**: Imported N concept(s) from <source-path> using okf-import.
```

### Step 6 -- Validate and report

After writing all files:
1. Run `okf-bundle-validate` on `<dest-path>` (see the `okf-bundle-validate` skill).
2. Present the validation report to the user.
3. List any warnings about skipped files, broken links, or ambiguous types.

## Supported source formats

| Format | Status | Notes |
|--------|--------|-------|
| Flat folder of `.md` files | Supported | Primary use case. |
| Nested folder of `.md` files | Supported | Directory structure preserved or flattened per `--flat`. |
| Obsidian vault (no plugins) | Supported | Wikilinks rewritten to standard Markdown links. |
| Files with YAML frontmatter | Supported | Existing keys preserved; `type` injected if missing. |
| Roam Research JSON export | Not supported | Convert to Markdown first using a third-party tool. |
| Notion export | Partial | Clean up Notion-specific frontmatter keys manually after import. |

## What is NOT supported

- Karpathy-specific or Obsidian-specific extensions inside the output bundle (e.g., `[[wikilinks]]`, `![[embeds]]`, dataview queries).
- Binary attachments -- skip silently and warn the user.
- Non-UTF-8 files -- skip silently and warn the user.

## References

OKF v0.1 specification -- GoogleCloudPlatform/knowledge-catalog @ ee67a5ca, okf/SPEC.md (Apache-2.0)
