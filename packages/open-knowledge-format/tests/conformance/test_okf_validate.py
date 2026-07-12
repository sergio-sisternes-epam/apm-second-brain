"""
tests/conformance/test_okf_validate.py

Pytest conformance suite for the OKF v0.1 validator.

Runs okf_validator.py logic against the valid-bundle and invalid-bundle fixtures.
The validator is imported directly (no subprocess) for fast feedback.

OKF v0.1 specification:
  GoogleCloudPlatform/knowledge-catalog @ ee67a5ca, okf/SPEC.md (Apache-2.0)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PACKAGE_ROOT = Path(__file__).parents[2]
VALIDATOR = PACKAGE_ROOT / ".apm" / "skills" / "okf-bundle-validate" / "okf_validator.py"
FIXTURES = Path(__file__).parent.parent / "fixtures"
VALID_BUNDLE = FIXTURES / "valid-bundle"
INVALID_BUNDLE = FIXTURES / "invalid-bundle"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_validator(bundle_path: Path) -> dict:
    """Run the validator as a subprocess and return the parsed JSON report."""
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(bundle_path)],
        capture_output=True,
        text=True,
    )
    assert result.stdout, f"Validator produced no stdout. stderr: {result.stderr}"
    return json.loads(result.stdout)


def find_rule(results: list[dict], file_suffix: str, rule_id: str) -> dict | None:
    """Find a specific rule result for a file matching the given suffix."""
    for file_result in results:
        if file_result["file"].endswith(file_suffix):
            for rule in file_result["rules"]:
                if rule["rule"] == rule_id:
                    return rule
    return None


# ---------------------------------------------------------------------------
# Sanity
# ---------------------------------------------------------------------------

def test_validator_script_exists():
    """The validator script must be present in the package."""
    assert VALIDATOR.exists(), f"Validator not found at {VALIDATOR}"


def test_valid_bundle_exists():
    """The valid-bundle fixture must be present."""
    assert VALID_BUNDLE.is_dir(), f"valid-bundle not found at {VALID_BUNDLE}"


def test_invalid_bundle_exists():
    """The invalid-bundle fixture must be present."""
    assert INVALID_BUNDLE.is_dir(), f"invalid-bundle not found at {INVALID_BUNDLE}"


# ---------------------------------------------------------------------------
# Valid bundle
# ---------------------------------------------------------------------------

class TestValidBundle:
    """The valid-bundle fixture should be fully conformant with OKF v0.1."""

    @pytest.fixture(scope="class")
    def report(self):
        return run_validator(VALID_BUNDLE)

    def test_conformant(self, report):
        """valid-bundle must be reported as conformant."""
        assert report["conformant"] is True, (
            f"Expected conformant=True but got errors:\n"
            + json.dumps([r for r in report["results"] if r["status"] == "fail"], indent=2)
        )

    def test_no_errors(self, report):
        """valid-bundle must have zero rule errors."""
        assert report["summary"]["errors"] == 0

    def test_has_concept_files(self, report):
        """valid-bundle must contain at least one concept file."""
        assert report["summary"]["concept_files"] >= 1

    def test_has_index_file(self, report):
        """valid-bundle must contain at least one index.md."""
        assert report["summary"]["index_files"] >= 1

    def test_has_log_file(self, report):
        """valid-bundle must contain one log.md."""
        assert report["summary"]["log_files"] == 1

    def test_okf_version_declared(self, report):
        """Root index.md should declare okf_version."""
        rule = find_rule(report["results"], "index.md", "I2-index-root-okf-version")
        assert rule is not None, "I2-index-root-okf-version rule not found in results"
        assert rule["status"] == "pass", f"Expected pass for I2: {rule['message']}"

    def test_concept_has_type(self, report):
        """Concept files must have a non-empty type field (C2)."""
        for fr in report["results"]:
            if fr["kind"] == "concept":
                rule = next((r for r in fr["rules"] if r["rule"] == "C2-type-required"), None)
                assert rule is not None
                assert rule["status"] == "pass", (
                    f"Concept {fr['file']} failed C2-type-required: {rule['message']}"
                )

    def test_log_newest_first(self, report):
        """log.md must be newest-first (L2)."""
        rule = find_rule(report["results"], "log.md", "L2-log-newest-first")
        assert rule is not None, "L2-log-newest-first rule not found"
        assert rule["status"] == "pass", f"Log date order violation: {rule['message']}"

    def test_log_date_headings(self, report):
        """log.md headings must be valid ISO 8601 dates (L1)."""
        rule = find_rule(report["results"], "log.md", "L1-log-date-headings")
        assert rule is not None
        assert rule["status"] == "pass", f"Log date heading violation: {rule['message']}"

    def test_non_root_index_no_frontmatter(self, report):
        """Non-root index.md files must not have frontmatter (I1)."""
        for fr in report["results"]:
            if fr["kind"] == "index" and fr["file"] != "index.md":
                rule = next((r for r in fr["rules"] if r["rule"] == "I1-index-no-frontmatter"), None)
                if rule is not None:
                    assert rule["status"] == "pass", (
                        f"Non-root index {fr['file']} has frontmatter: {rule['message']}"
                    )

    def test_exit_code_zero(self):
        """Validator exits with code 0 for a conformant bundle."""
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(VALID_BUNDLE)],
            capture_output=True,
        )
        assert result.returncode == 0, (
            f"Expected exit code 0, got {result.returncode}. stderr: {result.stderr.decode()}"
        )


# ---------------------------------------------------------------------------
# Invalid bundle
# ---------------------------------------------------------------------------

class TestInvalidBundle:
    """The invalid-bundle fixture should be non-conformant with deliberate violations."""

    @pytest.fixture(scope="class")
    def report(self):
        return run_validator(INVALID_BUNDLE)

    def test_non_conformant(self, report):
        """invalid-bundle must be reported as non-conformant."""
        assert report["conformant"] is False, "Expected conformant=False for invalid-bundle"

    def test_has_errors(self, report):
        """invalid-bundle must have at least one rule error."""
        assert report["summary"]["errors"] >= 1

    def test_missing_type_detected(self, report):
        """concepts/missing-type.md must fail C2-type-required."""
        rule = find_rule(report["results"], "missing-type.md", "C2-type-required")
        assert rule is not None, "C2-type-required rule not found for missing-type.md"
        assert rule["status"] == "fail", (
            f"Expected fail for C2 on missing-type.md, got: {rule['status']}"
        )

    def test_no_frontmatter_detected(self, report):
        """no-frontmatter.md must fail C1-frontmatter-present."""
        rule = find_rule(report["results"], "no-frontmatter.md", "C1-frontmatter-present")
        assert rule is not None, "C1-frontmatter-present rule not found for no-frontmatter.md"
        assert rule["status"] == "fail", (
            f"Expected fail for C1 on no-frontmatter.md, got: {rule['status']}"
        )

    def test_non_root_index_frontmatter_detected(self, report):
        """concepts/index.md has frontmatter -- must fail I1-index-no-frontmatter."""
        rule = find_rule(report["results"], "concepts/index.md", "I1-index-no-frontmatter")
        assert rule is not None, "I1-index-no-frontmatter rule not found for concepts/index.md"
        assert rule["status"] == "fail", (
            f"Expected fail for I1 on concepts/index.md, got: {rule['status']}"
        )

    def test_log_order_violation_detected(self, report):
        """log.md dates are not newest-first -- must fail L2-log-newest-first."""
        rule = find_rule(report["results"], "log.md", "L2-log-newest-first")
        assert rule is not None, "L2-log-newest-first rule not found"
        assert rule["status"] == "fail", (
            f"Expected fail for L2 on log.md, got: {rule['status']}"
        )

    def test_exit_code_one(self):
        """Validator exits with code 1 for a non-conformant bundle."""
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(INVALID_BUNDLE)],
            capture_output=True,
        )
        assert result.returncode == 1, (
            f"Expected exit code 1, got {result.returncode}"
        )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_nonexistent_bundle(self, tmp_path):
        """Validator returns exit code 2 for a path that does not exist."""
        missing = tmp_path / "does-not-exist"
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(missing)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        report = json.loads(result.stdout)
        assert "error" in report

    def test_empty_bundle(self, tmp_path):
        """An empty directory has no files -- validator reports zero errors, conformant."""
        empty = tmp_path / "empty-bundle"
        empty.mkdir()
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(empty)],
            capture_output=True,
            text=True,
        )
        report = json.loads(result.stdout)
        assert report["conformant"] is True
        assert report["summary"]["total_files"] == 0

    def test_json_output_shape(self):
        """Validator output must have the required top-level keys."""
        report = run_validator(VALID_BUNDLE)
        required_keys = {"conformant", "okf_version", "bundle_path", "summary", "results"}
        assert required_keys.issubset(report.keys()), (
            f"Missing keys: {required_keys - set(report.keys())}"
        )
        summary_keys = {"total_files", "concept_files", "index_files", "log_files", "errors", "warnings"}
        assert summary_keys.issubset(report["summary"].keys())
