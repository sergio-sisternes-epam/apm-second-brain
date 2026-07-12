"""
Conformance test: private-context scanner policy.

Verifies the scoping rules that the CI Lint job enforces by executing the
production scanner script (scripts/scan-private-context.sh) against temporary
directory trees.  Testing the real script -- not a Python reimplementation --
means CI workflow changes that drift from the intended policy are caught here.

Regression (b): private marker in .github/ISSUE_TEMPLATE/ is detected;
                 same marker in .github/workflows/ is NOT flagged.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# Locate the shared scanner script relative to the repo root.
# Conformance tests are run from the repo root (pytest tests/conformance/).
REPO_ROOT = Path(__file__).parent.parent.parent
SCANNER = REPO_ROOT / "scripts" / "scan-private-context.sh"

# Private-context patterns that match the scanner.
# Strings are split with adjacent-literal concatenation so the scanner itself
# cannot false-positive on this test file.
PRIVATE_PATTERNS = [
    "epam-agent" "-forge",
    "Users/" "sergio_sisternes",
    "EPAM All Rights" " Reserved",
]


def _run_scanner(root: Path) -> subprocess.CompletedProcess:
    """Execute the production scanner script against *root* and return the result."""
    return subprocess.run(
        ["bash", str(SCANNER), str(root)],
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def mock_repo(tmp_path: Path) -> Path:
    """Return a minimal repo tree used by scanner regression tests."""
    (tmp_path / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @maintainer\n")
    (tmp_path / "apm_modules" / "some-pkg").mkdir(parents=True)
    return tmp_path


def test_scanner_script_exists() -> None:
    """Guard: the shared scanner script must be present and executable."""
    import os
    assert SCANNER.is_file(), f"Scanner script not found: {SCANNER}"
    assert os.access(SCANNER, os.X_OK), (
        f"Scanner script is not executable: {SCANNER}\n"
        "Run: git update-index --chmod=+x scripts/scan-private-context.sh"
    )


def test_scanner_detects_marker_in_issue_template(mock_repo: Path) -> None:
    """Regression (b-1): a private marker in .github/ISSUE_TEMPLATE/ must be flagged."""
    template = mock_repo / ".github" / "ISSUE_TEMPLATE" / "bug_report.md"
    template.write_text(f"<!-- This references {PRIVATE_PATTERNS[0]} -->\n")

    result = _run_scanner(mock_repo)

    assert result.returncode == 1, (
        "Scanner must exit 1 when a private-context marker is found in .github/ISSUE_TEMPLATE/"
    )
    assert "ISSUE_TEMPLATE" in result.stdout, (
        "Scanner output must name the offending file"
    )


def test_scanner_does_not_flag_workflows(mock_repo: Path) -> None:
    """Regression (b-2): workflow files embedding the pattern strings must NOT be flagged."""
    workflow = mock_repo / ".github" / "workflows" / "ci.yml"
    workflow.write_text(
        # Simulate the scanner's own grep pattern as it appears in the real ci.yml.
        f'grep -e "{PRIVATE_PATTERNS[0]}" -e "{PRIVATE_PATTERNS[1]}" .\n'
    )

    result = _run_scanner(mock_repo)

    assert result.returncode == 0, (
        "Scanner must NOT flag .github/workflows/ -- those files embed the patterns legitimately.\n"
        f"stdout: {result.stdout}"
    )


def test_scanner_does_not_flag_apm_modules(mock_repo: Path) -> None:
    """apm_modules/ is a CLI cache and must be excluded even if it contains pattern strings."""
    cached = mock_repo / "apm_modules" / "some-pkg" / "README.md"
    cached.write_text(f"Published by {PRIVATE_PATTERNS[0]}\n")

    result = _run_scanner(mock_repo)

    assert result.returncode == 0, (
        "Scanner must not traverse apm_modules/.\n"
        f"stdout: {result.stdout}"
    )


def test_scanner_clean_repo_returns_no_hits(mock_repo: Path) -> None:
    """A repo with no private markers produces a clean result."""
    (mock_repo / "README.md").write_text("# Public demo project\n")
    (mock_repo / "packages" / "foo" / ".apm").mkdir(parents=True)
    (mock_repo / "packages" / "foo" / ".apm" / "apm.yml").write_text("name: foo\n")

    result = _run_scanner(mock_repo)

    assert result.returncode == 0, (
        f"Expected clean result, got:\n{result.stdout}"
    )
    assert "Clean" in result.stdout
