#!/usr/bin/env bash
# scan-private-context.sh -- detect private-context markers in the repository.
#
# Usage:  bash scripts/scan-private-context.sh [DIR]
#   DIR  root directory to scan (default: current working directory)
#
# Exit codes:
#   0  no private-context markers found (clean)
#   1  one or more markers found (fail)
#
# Scoped exclusions:
#   .github/workflows/  -- workflow files legitimately embed the scanner's own
#                          pattern strings; excluding only this sub-directory
#                          means all other .github/ content (issue/PR templates,
#                          CODEOWNERS, convention files) IS scanned.
#   apm_modules/        -- CLI dependency cache; never committed.

set -euo pipefail

DIR="${1:-.}"

HITS=$(find "$DIR" \
  -not -path "$DIR/.github/workflows/*" \
  -not -path "$DIR/apm_modules/*" \
  -type f \
  \( -name "*.md" -o -name "*.yml" -o -name "*.yaml" \
     -o -name "*.json" -o -name "*.py" -o -name "*.mjs" \) \
  -print0 \
| xargs -0r grep -rl \
    -e "epam-agent-forge" \
    -e "Users/sergio_sisternes" \
    -e "EPAM All Rights Reserved" \
  2>/dev/null || true)

if [ -n "$HITS" ]; then
  echo "Private context found in:"
  echo "$HITS"
  echo "Remove before merging."
  exit 1
fi

echo "Clean"
