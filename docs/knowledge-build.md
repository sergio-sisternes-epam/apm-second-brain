# APM Knowledge Corpus Build

This document describes how to build and refresh the APM documentation corpus
used by the `apm-expert` package.

## Overview

The `apm-knowledge` skill is backed by a vendored OKF (Open Knowledge Format)
corpus derived from the APM documentation. The corpus is **not fetched at
install time or at runtime**. It is a build artefact committed to the
repository under a write-once baseline key after successful validation.

The active baseline is identified by:

```
packages/apm-expert/.apm/skills/apm-knowledge/references/knowledge/active
```

When this file contains `none` (the scaffold sentinel), the `apm-knowledge`
skill returns `corpus_populated: false` and all queries return
`quality: unanswered`. This is the expected scaffold state until the build
pipeline runs.

## Source

| Field | Value |
|-------|-------|
| Repository | microsoft/apm |
| Tag | v0.25.0 |
| Full commit SHA | d73e6ac3645d2b9c5c813095e2e58f020f38f17a |
| Licence | MIT |

## Corpus directory structure

```
references/knowledge/
  active                   # pointer: "none" (sentinel) or active baseline key
  staging/                 # temporary build dirs; cleaned up after activation
    <key>-<timestamp>/     # in-progress baseline (deleted or promoted)
  baselines/
    <tag>-<full-sha>/      # write-once once activated; preserved forever
      MANIFEST.json        # provenance: repo, tag, full SHA, build date, integrity hash, licence
      LICENSE              # MIT licence copied from the pinned commit
      index.md             # OKF bundle index
      log.md               # OKF build log
      concepts/            # one .md file per OKF concept/topic
  overlay/
    concepts/              # consumer-authored concepts (preserved across refreshes)
    tombstones/            # consumer-authored tombstone entries
  CORPUS.md                # human-readable status and provenance summary
```

## Baseline key format

Keys must match the pattern: `v<semver>-<full-40-char-sha>`

```
v0.25.0-d73e6ac3645d2b9c5c813095e2e58f020f38f17a
```

Validation rules before activation:
- Must start with `v`
- SHA portion must be exactly 40 hex characters
- Key path must resolve inside `baselines/` (no path traversal: `..`, `/`, symlinks rejected)

## Step-by-step build procedure

### Step 1 -- Fetch and verify the pinned APM source

```bash
git clone --depth 1 \
  --branch v0.25.0 \
  https://github.com/microsoft/apm.git \
  /tmp/apm-source
```

**Verify the exact commit SHA. Abort if it does not match.**

```bash
EXPECTED="d73e6ac3645d2b9c5c813095e2e58f020f38f17a"
ACTUAL=$(git -C /tmp/apm-source rev-parse HEAD)
if [ "$ACTUAL" != "$EXPECTED" ]; then
  echo "SHA mismatch: got $ACTUAL, expected $EXPECTED -- aborting"
  exit 1
fi
echo "SHA verified: $ACTUAL"
```

### Step 2 -- Create a staging directory (NOT the final baseline)

```bash
BASELINE_KEY="v0.25.0-d73e6ac3645d2b9c5c813095e2e58f020f38f17a"
KNOWLEDGE_DIR="packages/apm-expert/.apm/skills/apm-knowledge/references/knowledge"
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
STAGING_DIR="${KNOWLEDGE_DIR}/staging/${BASELINE_KEY}-${TIMESTAMP}"

mkdir -p "${STAGING_DIR}/concepts"
```

Build ALWAYS goes into `staging/` first. The final `baselines/<key>/` is
written only after validation passes.

### Step 3 -- Copy the upstream licence

```bash
cp /tmp/apm-source/LICENSE "${STAGING_DIR}/LICENSE"
```

### Step 4 -- Convert documentation to OKF format

`okf-bundle-create` creates an OKF skeleton structure. The actual conversion
of microsoft/apm documentation is a **manual, one-time build artefact** process:

1. Invoke `okf-bundle-create` to initialise the OKF bundle:

   ```bash
   apm run okf-bundle-create \
     --source /tmp/apm-source/docs \
     --output "${STAGING_DIR}" \
     --source-id "microsoft/apm@${EXPECTED}" \
     --licence MIT
   ```

2. This produces the OKF v0.1 layout in the staging directory:
   - `index.md` -- OKF bundle index (must be non-empty after conversion)
   - `log.md` -- build log
   - `concepts/` -- one `.md` file per concept/topic (must be non-empty)

3. Each concept file must include OKF frontmatter:

   ```markdown
   ---
   id: <stable-concept-id>
   title: <concept title>
   source: microsoft/apm@d73e6ac3645d2b9c5c813095e2e58f020f38f17a
   origin: baseline
   ---

   <concept body>
   ```

   The `origin: baseline` field is required for per-passage provenance
   tracking. Consumer overlay concepts use `origin: overlay`.

4. Verify that `concepts/` contains at least one `.md` file before proceeding.
   An empty `concepts/` directory means the conversion failed -- do not activate.

### Step 5 -- Validate OKF conformance (in staging)

```bash
apm run okf-bundle-validate --bundle "${STAGING_DIR}"
```

The validator must exit 0. Fix reported errors before proceeding. Do not
skip this step.

### Step 6 -- Compute integrity hash and write MANIFEST.json (in staging)

```bash
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
INTEGRITY=$(find "${STAGING_DIR}/concepts" -type f | sort | xargs sha256sum | sha256sum | awk '{print $1}')

cat > "${STAGING_DIR}/MANIFEST.json" <<EOF
{
  "repository": "microsoft/apm",
  "tag": "v0.25.0",
  "fullCommitSha": "${EXPECTED}",
  "buildDate": "${BUILD_DATE}",
  "integrityHash": "${INTEGRITY}",
  "licence": "MIT",
  "status": "populated"
}
EOF
```

### Step 7 -- Atomic promotion: staging -> baseline

Only after Steps 5 and 6 pass atomically promote the staging directory to
the final baseline. Never write directly into `baselines/` during a build.

```bash
BASELINE_DIR="${KNOWLEDGE_DIR}/baselines/${BASELINE_KEY}"

# Abort if this exact baseline already exists (idempotency / no-overwrite).
if [ -d "${BASELINE_DIR}" ]; then
  echo "Baseline ${BASELINE_KEY} already exists -- not overwriting. " \
       "Use a new key for a new version."
  exit 1
fi

mv "${STAGING_DIR}" "${BASELINE_DIR}"
```

The `mv` is atomic on POSIX systems within the same filesystem.

### Step 8 -- Atomic active pointer update

Only after the baseline directory exists at its final path:

```bash
printf '%s' "${BASELINE_KEY}" > "${KNOWLEDGE_DIR}/active.tmp"
mv "${KNOWLEDGE_DIR}/active.tmp" "${KNOWLEDGE_DIR}/active"
```

### Step 9 -- Update CORPUS.md

Edit `references/knowledge/CORPUS.md`:
- Change active pointer line from `none` to the baseline key.
- Set `Baseline populated: Yes`.
- Fill in `buildDate` and `integrityHash` from MANIFEST.json.

### Step 10 -- Run conformance tests

```bash
pytest packages/apm-expert/tests/conformance/test_apm_expert.py -v
```

All tests must pass.

### Step 11 -- Commit the corpus

```bash
git add packages/apm-expert/.apm/skills/apm-knowledge/references/knowledge/
git commit -m "build(apm-expert): populate OKF corpus from microsoft/apm ${BASELINE_KEY}"
```

### Step 12 -- Clean up staging

```bash
rm -rf "${KNOWLEDGE_DIR}/staging/"
rm -rf /tmp/apm-source
```

## Rollback procedure

If a newly activated baseline is defective:

1. Do NOT delete the defective baseline (baselines are immutable records).
2. Build a corrected baseline under a new key (e.g. append a build iteration
   suffix: `v0.25.0-d73e6ac3...-r2`).
3. Atomically update the `active` pointer to the corrected baseline key.
4. The overlay (`overlay/concepts/`, `overlay/tombstones/`) is preserved
   automatically -- no changes needed.

## Automated build

The build steps above are also implemented as the `build-corpus` script in
`apm.yml`. Run with:

```bash
cd packages/apm-expert
apm run build-corpus
```

## Pinning policy

When updating to a new APM version:

1. Update `EXPECTED` SHA and `--branch` in Step 1.
2. Generate a new `BASELINE_KEY` using the new tag + full 40-character SHA.
3. Run the full procedure.
4. Update corpus metadata in `.apm/skills/apm-knowledge/SKILL.md`.
5. Update this document.
6. Open a PR with the new baseline artefacts.

Prior baselines are never removed.

## Licence compliance

The upstream APM documentation is MIT-licensed. The vendored corpus inherits
that licence. The `apm-expert` package code itself is Apache-2.0 (separate
from the corpus content). Do not vendor content from other repositories
without verifying licence compatibility.
