#!/usr/bin/env bash
# scan-private-context.sh -- detect private-context markers in the repository.
#
# Usage:  bash scripts/scan-private-context.sh [DIR]
#   DIR  root directory to scan (default: current working directory)
#
# Exit codes:
#   0  no private-context markers found (clean)
#   1  one or more markers found (fail)
#   2  scanner error (bad scan root, find/grep failure)
#
# Scoped exclusions:
#   .github/workflows/  -- workflow files legitimately embed the scanner's own
#                          pattern strings; excluding only this sub-directory
#                          means all other .github/ content (issue/PR templates,
#                          CODEOWNERS, convention files) IS scanned.
#   apm_modules/        -- CLI dependency cache; never committed.

set -uo pipefail

DIR="${1:-.}"

# Validate scan root.
if [ ! -d "$DIR" ]; then
  echo "Error: scan root does not exist or is not a directory: $DIR" >&2
  exit 2
fi

# Run the scan from inside DIR so all -path exclusions are root-relative
# (e.g. ./.github/workflows/*).  This avoids fragility with trailing slashes
# or absolute-path prefix mismatches.
#
# set -e is intentionally absent here so we can inspect $SCAN_RC directly.
# grep exits 0 (matches found), 1 (no matches -- not an error), or 2+ (error).
# We only treat exit 1 as non-fatal; anything higher signals a real failure.
HITS=$(cd "$DIR" && find . \
  -not -path './.github/workflows/*' \
  -not -path './apm_modules/*' \
  -type f \
  \( -name "*.md" -o -name "*.yml" -o -name "*.yaml" \
     -o -name "*.json" -o -name "*.py" -o -name "*.mjs" \) \
  -print0 \
| xargs -0r grep -rl \
    -e "epam-agent-forge" \
    -e "Users/sergio_sisternes" \
    -e "EPAM All Rights Reserved" \
  2>/dev/null) || SCAN_RC=$?

if [ "${SCAN_RC:-0}" -gt 1 ]; then
  echo "Error: scanner failed with exit code ${SCAN_RC}." >&2
  exit 2
fi

if [ -n "$HITS" ]; then
  echo "Private context found in:"
  echo "$HITS"
  echo "Remove before merging."
  exit 1
fi

echo "Clean"
