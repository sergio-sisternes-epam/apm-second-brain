# APM Knowledge Corpus Build

This document describes how to build and refresh the APM documentation corpus
used by the `apm-expert` package.

## Overview

The `apm-knowledge` skill inside `apm-expert` is backed by a vendored OKF
(Open Knowledge Format) corpus derived from the APM documentation. The corpus
is **not fetched at install time or at runtime** -- it is a build artefact that
must be generated once and committed to the repository.

The corpus lives at:

```
packages/apm-expert/.apm/skills/apm-knowledge/references/knowledge/
```

Until the pipeline runs, that directory contains only a placeholder `CORPUS.md`
and the skill reports `corpus_populated: false`.

## Source

| Field | Value |
|-------|-------|
| Repository | microsoft/apm |
| Tag | v0.25.0 |
| Commit | d73e6ac3645d2b9c5c813095e2e58f020f38f17a |
| Licence | MIT |

## Prerequisites

- `git` in PATH
- `apm` CLI >= 0.25.0 (for `okf-bundle-create` and `okf-bundle-validate`)
- Python >= 3.11 (for the OKF validator script)
- Network access to github.com (for the initial fetch only)

## Step-by-step refresh procedure

### Step 1 -- Fetch the pinned APM source

```bash
git clone --depth 1 \
  --branch v0.25.0 \
  https://github.com/microsoft/apm.git \
  /tmp/apm-source
```

Verify the commit:

```bash
git -C /tmp/apm-source rev-parse HEAD
# Expected: d73e6ac3645d2b9c5c813095e2e58f020f38f17a
```

### Step 2 -- Convert documentation to OKF format

From the repository root:

```bash
apm skill run okf-import \
  --source /tmp/apm-source/docs \
  --output packages/apm-expert/.apm/skills/apm-knowledge/references/knowledge \
  --source-id "microsoft/apm@d73e6ac3" \
  --licence MIT
```

This produces:

- `index.json` -- OKF bundle index
- `entries/` -- individual OKF-format knowledge entries, one file per topic

### Step 3 -- Validate the corpus

```bash
apm skill run okf-bundle-validate \
  --bundle packages/apm-expert/.apm/skills/apm-knowledge/references/knowledge
```

The validator must exit 0 before the corpus is considered ready.

### Step 4 -- Update CORPUS.md

Edit `references/knowledge/CORPUS.md` to reflect the new build:

- Remove the "not yet generated" notice.
- Update the entry count and any other statistics from the validator output.

### Step 5 -- Commit the corpus

```bash
git add packages/apm-expert/.apm/skills/apm-knowledge/references/knowledge/
git commit -m "build(apm-expert): populate OKF corpus from microsoft/apm v0.25.0"
```

### Step 6 -- Verify end-to-end

Run the conformance tests to confirm the corpus is recognised:

```bash
pytest packages/apm-expert/tests/conformance/test_apm_expert.py -v
```

## Pinning policy

The corpus pin must match `apm.lock.yaml` in `packages/apm-expert/`. When
updating the pin:

1. Update the `--branch` / `--source-id` / commit in Steps 1 and 2.
2. Run the full refresh procedure.
3. Update the corpus metadata table in
   `.apm/skills/apm-knowledge/SKILL.md`.
4. Update this document.
5. Open a PR with the new corpus artefacts.

## Licence compliance

The upstream APM documentation is MIT-licensed. The vendored corpus inherits
that licence. Do not vendor content from other repositories without verifying
licence compatibility.

## Clean-up

Remove the temporary clone after building:

```bash
rm -rf /tmp/apm-source
```
