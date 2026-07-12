#!/usr/bin/env bash
# scan-private-context.sh -- detect private-context markers in the repository.
#
# Usage:  bash scripts/scan-private-context.sh [DIR]
#   DIR  root directory to scan (default: current working directory)
#
# Exit codes:
#   0  no private-context markers found (clean)
#   1  one or more markers found (fail)
#   2  scanner error (bad scan root or find failure)
#
# Scoped exclusions:
#   .github/workflows/  -- workflow files legitimately embed the scanner's own
#                          pattern strings; excluding only this sub-directory
#                          means all other .github/ content (issue/PR templates,
#                          CODEOWNERS, convention files) IS scanned.
#   apm_modules/        -- CLI dependency cache; never committed.

set -euo pipefail

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
# Use find -exec grep -ql instead of find -print0 | xargs grep -rl to avoid
# the xargs exit-code wrapping: xargs exits 123 when grep exits 1 (no matches),
# making "clean" and "grep error" indistinguishable.  With -exec, each file is
# tested individually; grep exit codes affect the -exec chain per file, not the
# overall find exit code.  find exits non-zero only on genuine traversal errors.
HITS=$(cd "$DIR" && find . \
  -not -path './.github/workflows/*' \
  -not -path './apm_modules/*' \
  -type f \
  \( -name "*.md" -o -name "*.yml" -o -name "*.yaml" \
     -o -name "*.json" -o -name "*.py" -o -name "*.mjs" \) \
  -exec grep -ql \
    -e "epam-agent-forge" \
    -e "Users/sergio_sisternes" \
    -e "EPAM All Rights Reserved" \
    {} \; \
  -print \
  2>/dev/null)

if [ -n "$HITS" ]; then
  echo "Private context found in:"
  echo "$HITS"
  echo "Remove before merging."
  exit 1
fi

echo "Clean"
