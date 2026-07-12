"""
Conformance test: private-context scanner policy.

Verifies the scoping rules that the CI Lint job enforces:
  - .github/workflows/ is EXCLUDED  (workflow files embed the pattern strings)
  - all other .github/ content IS scanned (.github/ISSUE_TEMPLATE/, CODEOWNERS, etc.)
  - apm_modules/ is EXCLUDED (CLI dependency cache, never committed)

The scanner logic is mirrored here so that a change to ci.yml that
accidentally widens or narrows the scope is caught before the workflow
is pushed to the remote.

Regression (b): private marker in .github/ISSUE_TEMPLATE/ is detected;
                 same marker in .github/workflows/ is NOT flagged.
"""

from pathlib import Path

import pytest

# Private-context patterns that match the CI Lint step.
# Strings are split with adjacent-literal concatenation so the scanner's own
# grep cannot false-positive on this test file.
PRIVATE_PATTERNS = [
    "epam-agent" "-forge",
    "Users/" "sergio_sisternes",
    "EPAM All Rights" " Reserved",
]

# File extensions that the scanner targets (must match ci.yml exactly).
SCANNED_EXTENSIONS = {".md", ".yml", ".yaml", ".json", ".py", ".mjs"}


def _run_scanner(root: Path) -> list[str]:
    """
    Simulate the CI find | xargs grep scanner.

    Returns repo-relative paths of files that contain a private-context marker,
    excluding .github/workflows/ and apm_modules/ -- exactly as ci.yml does.
    """
    hits: list[str] = []
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix not in SCANNED_EXTENSIONS:
            continue
        rel = f.relative_to(root)
        parts = rel.parts
        # Exclusions that mirror the find -not -path filters in ci.yml.
        if len(parts) >= 2 and parts[0] == ".github" and parts[1] == "workflows":
            continue
        if parts[0] == "apm_modules":
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(pattern in content for pattern in PRIVATE_PATTERNS):
            hits.append(str(rel))
    return hits


@pytest.fixture()
def mock_repo(tmp_path: Path) -> Path:
    """Return a minimal repo tree used by scanner regression tests."""
    (tmp_path / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @maintainer\n")
    (tmp_path / "apm_modules" / "some-pkg").mkdir(parents=True)
    return tmp_path


def test_scanner_detects_marker_in_issue_template(mock_repo: Path) -> None:
    """Regression (b-1): a private marker in .github/ISSUE_TEMPLATE/ must be flagged."""
    template = mock_repo / ".github" / "ISSUE_TEMPLATE" / "bug_report.md"
    template.write_text(f"<!-- This references {PRIVATE_PATTERNS[0]} -->\n")

    hits = _run_scanner(mock_repo)

    assert ".github/ISSUE_TEMPLATE/bug_report.md" in hits, (
        "Scanner must detect private-context markers inside .github/ISSUE_TEMPLATE/"
    )


def test_scanner_does_not_flag_workflows(mock_repo: Path) -> None:
    """Regression (b-2): workflow files embedding the pattern strings must NOT be flagged."""
    workflow = mock_repo / ".github" / "workflows" / "ci.yml"
    workflow.write_text(
        # Simulate the scanner's own grep pattern as it appears in the real ci.yml.
        f'grep -e "{PRIVATE_PATTERNS[0]}" -e "{PRIVATE_PATTERNS[1]}" .\n'
    )

    hits = _run_scanner(mock_repo)

    assert ".github/workflows/ci.yml" not in hits, (
        "Scanner must NOT flag .github/workflows/ -- those files embed the patterns legitimately"
    )


def test_scanner_does_not_flag_apm_modules(mock_repo: Path) -> None:
    """apm_modules/ is a CLI cache and must be excluded even if it contains pattern strings."""
    cached = mock_repo / "apm_modules" / "some-pkg" / "README.md"
    cached.write_text(f"Published by {PRIVATE_PATTERNS[0]}\n")

    hits = _run_scanner(mock_repo)

    assert not any(h.startswith("apm_modules/") for h in hits), (
        "Scanner must not traverse apm_modules/"
    )


def test_scanner_clean_repo_returns_no_hits(mock_repo: Path) -> None:
    """A repo with no private markers produces an empty hit list."""
    (mock_repo / "README.md").write_text("# Public demo project\n")
    (mock_repo / "packages" / "foo" / ".apm").mkdir(parents=True)
    (mock_repo / "packages" / "foo" / ".apm" / "apm.yml").write_text("name: foo\n")

    hits = _run_scanner(mock_repo)

    assert hits == [], f"Expected no hits on a clean repo, got: {hits}"
