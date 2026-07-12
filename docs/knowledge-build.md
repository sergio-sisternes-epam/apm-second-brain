# APM Knowledge Corpus Build

This document describes how to build and refresh the APM documentation corpus
used by the `apm-expert` package.

## Overview

The `apm-knowledge` skill is backed by a vendored OKF (Open Knowledge Format)
corpus derived from the APM documentation. The corpus is **not fetched at
install time or at runtime** -- it is a build artefact committed to the
repository under a write-once baseline key.

The active baseline is pointed to by:

```
packages/apm-expert/.apm/skills/apm-knowledge/references/knowledge/active
```

Until the pipeline runs, that file contains a placeholder key and the baseline
`concepts/` directory is empty. The `apm-knowledge` skill returns
`corpus_populated: false` in that state.

## Source

| Field | Value |
|-------|-------|
| Repository | microsoft/apm |
| Tag | v0.25.0 |
| Full commit SHA | d73e6ac3645d2b9c5c813095e2e58f020f38f17a |
| Licence | Apache-2.0 |

## Corpus directory structure

```
references/knowledge/
  active                   # pointer: contains baseline key string
  baselines/
    <tag>-<full-sha>/      # write-once; one dir per corpus version
      MANIFEST.json        # provenance: repo, tag, full SHA, build date, integrity hash
      LICENSE              # Apache-2.0 licence copied from the pinned commit
      index.md             # OKF bundle index
      log.md               # OKF build log
      concepts/            # one .md file per OKF concept/topic
  overlay/
    concepts/              # consumer-authored concepts (preserved across refreshes)
    tombstones/            # consumer-authored tombstone entries
  CORPUS.md                # human-readable status and provenance summary
```

## Prerequisites

- `git` in PATH
- `apm` CLI >= 0.25.0
- Network access to github.com (fetch step only)

## Step-by-step refresh procedure

### Step 1 -- Fetch and verify the pinned APM source

```bash
git clone --depth 1 \
  --branch v0.25.0 \
  https://github.com/microsoft/apm.git \
  /tmp/apm-source
```

**Verify the exact commit SHA before proceeding. Abort if it does not match.**

```bash
ACTUAL=$(git -C /tmp/apm-source rev-parse HEAD)
EXPECTED="d73e6ac3645d2b9c5c813095e2e58f020f38f17a"
if [ "$ACTUAL" != "$EXPECTED" ]; then
  echo "SHA mismatch: got $ACTUAL, expected $EXPECTED -- aborting"
  exit 1
fi
echo "SHA verified: $ACTUAL"
```

### Step 2 -- Prepare the new baseline directory

```bash
BASELINE_KEY="v0.25.0-d73e6ac3645d2b9c5c813095e2e58f020f38f17a"
BASELINE_DIR="packages/apm-expert/.apm/skills/apm-knowledge/references/knowledge/baselines/$BASELINE_KEY"

# If this exact baseline already exists, verify and return no-op.
if [ -d "$BASELINE_DIR/concepts" ] && [ "$(ls -A "$BASELINE_DIR/concepts")" ]; then
  echo "Baseline $BASELINE_KEY already exists and is populated -- no-op."
  exit 0
fi

mkdir -p "$BASELINE_DIR/concepts"
```

### Step 3 -- Copy the upstream licence

```bash
cp /tmp/apm-source/LICENSE "$BASELINE_DIR/LICENSE"
```

### Step 4 -- Invoke okf-bundle-create to convert the documentation

The `okf-bundle-create` skill converts a documentation tree to OKF format.
Invoke it via `apm run`:

```bash
apm run okf-bundle-create \
  --source /tmp/apm-source/docs \
  --output "$BASELINE_DIR" \
  --source-id "microsoft/apm@$EXPECTED" \
  --licence Apache-2.0
```

This produces the OKF v0.1 layout inside `$BASELINE_DIR`:

- `index.md` -- OKF bundle index (list of all concept entries)
- `log.md` -- build log
- `concepts/` -- one `.md` file per concept/topic

### Step 5 -- Validate the corpus

```bash
apm run okf-bundle-validate --bundle "$BASELINE_DIR"
```

The validator must exit 0. Fix any reported errors before proceeding.

### Step 6 -- Compute integrity hash and write MANIFEST.json

```bash
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
INTEGRITY=$(find "$BASELINE_DIR/concepts" -type f | sort | xargs sha256sum | sha256sum | awk '{print $1}')

cat > "$BASELINE_DIR/MANIFEST.json" <<EOF
{
  "repository": "microsoft/apm",
  "tag": "v0.25.0",
  "fullCommitSha": "$EXPECTED",
  "buildDate": "$BUILD_DATE",
  "integrityHash": "$INTEGRITY",
  "licence": "Apache-2.0",
  "status": "populated"
}
EOF
```

### Step 7 -- Activate the new baseline (atomic pointer promotion)

```bash
ACTIVE="packages/apm-expert/.apm/skills/apm-knowledge/references/knowledge/active"
echo "$BASELINE_KEY" > "${ACTIVE}.tmp"
mv "${ACTIVE}.tmp" "$ACTIVE"
```

Using `mv` makes the pointer promotion atomic on POSIX systems.

### Step 8 -- Update CORPUS.md

Edit `references/knowledge/CORPUS.md` to reflect the new build:

- Remove the "not yet generated" notice.
- Update `buildDate`, `integrityHash`, and `Baseline populated: Yes`.

### Step 9 -- Commit the corpus

Prior baselines are immutable -- never delete or overwrite them. Only commit
the new baseline directory, the updated `active` pointer, and `CORPUS.md`.

```bash
git add packages/apm-expert/.apm/skills/apm-knowledge/references/knowledge/
git commit -m "build(apm-expert): populate OKF corpus from microsoft/apm v0.25.0 ($EXPECTED)"
```

### Step 10 -- Run conformance tests

```bash
pytest packages/apm-expert/tests/conformance/test_apm_expert.py -v
```

All tests must pass before the corpus is considered ready.

## Pinning policy

When updating to a new APM version:

1. Update the `EXPECTED` SHA and `--branch` in Steps 1 and 2.
2. Generate a new `BASELINE_KEY` from the new tag + full commit SHA.
3. Run the full refresh procedure.
4. Update the corpus metadata in `.apm/skills/apm-knowledge/SKILL.md`.
5. Update this document.
6. Open a PR with the new baseline artefacts.

Prior baselines remain in `baselines/` and are never removed. The `active`
pointer is the only thing that changes.

## Licence compliance

The upstream APM documentation is Apache-2.0-licensed. The vendored corpus
inherits that licence. Do not vendor content from other repositories without
verifying licence compatibility.

## Clean-up

```bash
rm -rf /tmp/apm-source
```
