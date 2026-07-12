# Overlay README

This directory holds consumer-authored knowledge that extends or overrides
the active baseline corpus.

## Structure

```
overlay/
  concepts/      # consumer-authored OKF concept files
  tombstones/    # tombstone files to suppress baseline concepts
```

## Concept ID format

Overlay concept IDs must be stable and survive baseline upgrades. Use the
format:

```
overlay/<owner>/<slug>
```

Example: `overlay/acme-corp/custom-deploy-guide`

Baseline concept IDs use the form `<source-slug>/<topic>` (set by the build
pipeline). Do not reuse baseline concept IDs in the overlay -- create new IDs.

## Overlay concept frontmatter

Every concept file in `overlay/concepts/` must include:

```markdown
---
id: overlay/<owner>/<slug>
title: <concept title>
source: <consumer-defined source identifier>
origin: overlay
---

<concept body>
```

The `origin: overlay` field is required. The `source` field must use a
consumer-defined identifier -- it must NOT claim `microsoft/apm` provenance.

## Tombstone format

A tombstone file in `overlay/tombstones/` suppresses a baseline concept. Create
a `.json` file named after the baseline concept ID (with `/` replaced by `--`):

```json
{
  "id": "<baseline-concept-id>",
  "reason": "<why this concept is suppressed>",
  "tombstonedAt": "<ISO 8601 date>"
}
```

Example filename: `apm--publishing--packages.json`

## Query precedence

1. Overlay tombstones -- if a baseline concept is tombstoned, exclude it
   from results entirely.
2. Overlay concepts -- consumer-authored concepts take precedence over
   matching baseline concepts with the same topic.
3. Baseline concepts -- primary knowledge source from the active baseline.

## Lifecycle

The overlay is preserved across baseline refreshes. When a new baseline is
activated (by updating `active`), the overlay is untouched.

## Version-stable IDs

Concept IDs in the overlay must survive baseline upgrades. Stable IDs ensure
that tombstones and overlays continue to function correctly after a baseline
refresh. Use the `overlay/<owner>/<slug>` format to avoid collisions with
baseline concept IDs.
