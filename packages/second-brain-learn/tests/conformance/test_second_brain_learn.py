"""
Conformance tests for the second-brain-learn package.

Verifies:
 1. All internal skills carry the disabled header as the first line.
 2. All internal skills contain a meaningful redirect instruction.
 3. Forget handler documents the tombstone-only constraint (no destructive deletion).
 4. Valid learn request fixture validates against second-brain-interfaces schema.
 5. Valid forget request fixture validates against second-brain-interfaces schema.
 6. Dependencies declared in apm.yml.
 7. Duplicate learn request fixture validates against schema.
 8. Learn response schema enforces source_id conditional requirement (R1).
 9. sb-forget-handler documents source_id-to-concept resolution.
10. sb-forget-validate documents traversal/path safety checks.
11. sb-forget-validate documents already-archived idempotency.
12. apm.yml and apm.lock.yaml use full 40-char commit SHAs (R5).

Run with: pytest packages/second-brain-learn/tests/conformance/ -v
Requirements: jsonschema>=4.0, pyyaml
"""

import json
import shutil
import re
from pathlib import Path

import pytest
import yaml
from jsonschema import validate, Draft202012Validator, ValidationError

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
PKG_ROOT = REPO_ROOT / "packages" / "second-brain-learn"
SKILLS_DIR = PKG_ROOT / ".apm" / "skills"
FIXTURES_DIR = PKG_ROOT / "tests" / "fixtures"
INTERFACES_SKILLS = (
    REPO_ROOT / "packages" / "second-brain-interfaces" / ".apm" / "skills"
)

DISABLED_HEADER = "<!-- direct-user-invocation: disabled -->"
REDIRECT_PATTERN = re.compile(
    r"(must only be called by|must not be invoked|decline and redirect|"
    r"decline.*redirect|redirect.*brain-|not.*invok.*direct)",
    re.IGNORECASE,
)

FULL_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")

INTERNAL_SKILL_NAMES = [
    "sb-learn-handler",
    "sb-forget-handler",
    "sb-forget-validate",
    "sb-learn-validate",
]


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_schema(skill: str, envelope: str) -> dict:
    return _load_json(INTERFACES_SKILLS / skill / "schema" / f"{envelope}.schema.json")


# ---------------------------------------------------------------------------
# 1. Disabled header is the first line
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("skill_name", INTERNAL_SKILL_NAMES)
def test_disabled_header_is_first_line(skill_name: str) -> None:
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    assert skill_path.exists(), f"Internal skill not found: {skill_path}"
    first_line = skill_path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.strip() == DISABLED_HEADER, (
        f"{skill_name}/SKILL.md: disabled header must be the first line, got: {first_line!r}"
    )


# ---------------------------------------------------------------------------
# 2. Redirect instruction present (meaningful direct-invocation language)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("skill_name", INTERNAL_SKILL_NAMES)
def test_redirect_instruction_present(skill_name: str) -> None:
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert REDIRECT_PATTERN.search(content), (
        f"{skill_name}/SKILL.md must contain a meaningful redirect instruction "
        "that explicitly tells the agent to decline direct user invocation and "
        "redirect to the appropriate public skill."
    )


# ---------------------------------------------------------------------------
# 3. Forget handler documents tombstone-only constraint
# ---------------------------------------------------------------------------

def test_forget_handler_documents_tombstone_only() -> None:
    skill_path = SKILLS_DIR / "sb-forget-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()
    has_tombstone_or_archive = "tombstone" in content or "archive" in content
    has_no_destructive = "no destructive" in content or "not delete" in content
    assert has_tombstone_or_archive, (
        "sb-forget-handler/SKILL.md must document the tombstone/archive nature of v1 forget"
    )
    assert has_no_destructive, (
        "sb-forget-handler/SKILL.md must explicitly state that v1 does no destructive deletion"
    )


# ---------------------------------------------------------------------------
# 4. Valid learn request fixture validates against schema
# ---------------------------------------------------------------------------

def test_valid_learn_request_fixture() -> None:
    schema = _load_schema("brain-learn", "request")
    fixture = _load_json(FIXTURES_DIR / "valid-learn-request.json")
    validate(instance=fixture, schema=schema, cls=Draft202012Validator)


# ---------------------------------------------------------------------------
# 5. Valid forget request fixture validates against schema
# ---------------------------------------------------------------------------

def test_valid_forget_request_fixture() -> None:
    schema = _load_schema("brain-forget", "request")
    fixture = _load_json(FIXTURES_DIR / "valid-forget-request.json")
    validate(instance=fixture, schema=schema, cls=Draft202012Validator)


# ---------------------------------------------------------------------------
# 6. Dependencies declared in apm.yml
# ---------------------------------------------------------------------------

def test_dependencies_declared_in_apm_yml() -> None:
    apm_yml_path = PKG_ROOT / "apm.yml"
    assert apm_yml_path.exists(), "apm.yml must exist in the package root"
    content = apm_yml_path.read_text(encoding="utf-8")
    assert "karpathy-wiki" in content, (
        "apm.yml must declare karpathy-wiki as a dependency"
    )
    assert "second-brain-interfaces" in content, (
        "apm.yml must declare second-brain-interfaces as a dependency"
    )


# ---------------------------------------------------------------------------
# 7. Duplicate learn request fixture validates against request schema (R6)
# ---------------------------------------------------------------------------

def test_duplicate_learn_request_fixture_validates() -> None:
    schema = _load_schema("brain-learn", "request")
    fixture = _load_json(FIXTURES_DIR / "duplicate-learn-request.json")
    validate(instance=fixture, schema=schema, cls=Draft202012Validator)


# ---------------------------------------------------------------------------
# 8. Learn response schema enforces conditional source_id requirement (R1)
# ---------------------------------------------------------------------------

def test_response_schema_requires_source_id_for_accepted() -> None:
    schema = _load_schema("brain-learn", "response")
    valid_accepted = {
        "correlation_id": "a1b2c3d4-e5f6-4789-abcd-ef1234567890",
        "status": "accepted",
        "source_id": "src-a1b2c3d4",
        "message": "Ingested.",
    }
    validate(instance=valid_accepted, schema=schema, cls=Draft202012Validator)


def test_response_schema_requires_source_id_for_duplicate() -> None:
    schema = _load_schema("brain-learn", "response")
    valid_duplicate = {
        "correlation_id": "a1b2c3d4-e5f6-4789-abcd-ef1234567890",
        "status": "duplicate",
        "source_id": "src-a1b2c3d4",
        "message": "Already ingested.",
    }
    validate(instance=valid_duplicate, schema=schema, cls=Draft202012Validator)


def test_response_schema_invalid_must_omit_source_id() -> None:
    schema = _load_schema("brain-learn", "response")
    invalid_with_source_id = {
        "correlation_id": "a1b2c3d4-e5f6-4789-abcd-ef1234567890",
        "status": "invalid",
        "source_id": "src-a1b2c3d4",
        "message": "Bad content.",
    }
    with pytest.raises(Exception):
        validate(instance=invalid_with_source_id, schema=schema, cls=Draft202012Validator)


def test_response_schema_accepted_without_source_id_fails() -> None:
    schema = _load_schema("brain-learn", "response")
    missing_source = {
        "correlation_id": "a1b2c3d4-e5f6-4789-abcd-ef1234567890",
        "status": "accepted",
        "message": "No source_id.",
    }
    with pytest.raises(Exception):
        validate(instance=missing_source, schema=schema, cls=Draft202012Validator)


# ---------------------------------------------------------------------------
# 9. sb-forget-handler documents source_id-to-concept resolution (R1)
# ---------------------------------------------------------------------------

def test_forget_handler_documents_source_id_resolution() -> None:
    skill_path = SKILLS_DIR / "sb-forget-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "source_id" in content, (
        "sb-forget-handler/SKILL.md must document source_id-to-concept resolution "
        "so forget-by-source_id is implementable."
    )
    assert "sb-forget-validate" in content, (
        "sb-forget-handler/SKILL.md must call sb-forget-validate before any archive."
    )


# ---------------------------------------------------------------------------
# 10. sb-forget-validate documents path safety (traversal rejection) (R2)
# ---------------------------------------------------------------------------

def test_forget_validate_documents_path_safety() -> None:
    skill_path = SKILLS_DIR / "sb-forget-validate" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()
    assert ".." in content or "traversal" in content or "parent traversal" in content, (
        "sb-forget-validate/SKILL.md must document parent path traversal rejection"
    )
    has_absolute = "absolute" in content or "starts with /" in content
    assert has_absolute, (
        "sb-forget-validate/SKILL.md must document rejection of absolute paths"
    )


# ---------------------------------------------------------------------------
# 11. sb-forget-validate documents already-archived idempotency (R2)
# ---------------------------------------------------------------------------

def test_forget_validate_or_handler_documents_idempotency() -> None:
    handler_content = (SKILLS_DIR / "sb-forget-handler" / "SKILL.md").read_text(encoding="utf-8").lower()
    validate_content = (SKILLS_DIR / "sb-forget-validate" / "SKILL.md").read_text(encoding="utf-8").lower()
    combined = handler_content + validate_content
    has_idempotency = (
        "already archived" in combined
        or "already-archived" in combined
        or "idempotent" in combined
        or "idempotency" in combined
    )
    assert has_idempotency, (
        "sb-forget-handler or sb-forget-validate must document already-archived idempotency"
    )


# ---------------------------------------------------------------------------
# 12. apm.yml and apm.lock.yaml use full 40-char commit SHAs (R5)
# ---------------------------------------------------------------------------

def test_apm_yml_uses_full_shas() -> None:
    content = (PKG_ROOT / "apm.yml").read_text(encoding="utf-8")
    matches = FULL_SHA_PATTERN.findall(content)
    assert len(matches) >= 2, (
        "apm.yml must reference dependencies with full 40-char commit SHAs "
        "(one per declared remote dependency)."
    )


def test_apm_lock_uses_full_shas() -> None:
    lock_path = PKG_ROOT / "apm.lock.yaml"
    assert lock_path.exists(), "apm.lock.yaml must exist after apm install"
    content = lock_path.read_text(encoding="utf-8")
    matches = FULL_SHA_PATTERN.findall(content)
    assert len(matches) >= 2, (
        "apm.lock.yaml must record full 40-char resolved_commit SHAs for each dependency."
    )



# ---------------------------------------------------------------------------
# 12. Executable: forget validation error returns error envelope, not receipt
# ---------------------------------------------------------------------------

def test_forget_validation_failure_returns_error_envelope() -> None:
    """Forget handler must return error envelope (VALIDATION_ERROR) on invalid input.

    The forget receipt schema has no invalid status. A malformed forget request
    must return {correlation_id, code: VALIDATION_ERROR, message} (the
    second-brain.error schema), not {target_id, status: not_found}.
    """
    skill_path = SKILLS_DIR / "sb-forget-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    # Must not say "return a receipt with status: not_found" for validation failures
    has_not_found_for_validation = (
        "status: not_found" in content
        and "VALIDATION_ERROR" not in content.split("status: not_found")[0]
        # Check the validation step specifically
    )
    # The correct pattern: VALIDATION_ERROR in the validation step output
    validation_step_idx = content.find("Validate envelope")
    assert validation_step_idx >= 0, "sb-forget-handler must have a Validate envelope step"
    section_after_validate = content[validation_step_idx: validation_step_idx + 800]
    assert "VALIDATION_ERROR" in section_after_validate, (
        "The Validate envelope step must specify VALIDATION_ERROR code -- not status: not_found. "
        "A malformed forget request is not the same as a not-found target."
    )


# ---------------------------------------------------------------------------
# 13. Executable: learn duplicate receipt has schema-valid source_id
# ---------------------------------------------------------------------------

def test_learn_duplicate_receipt_schema() -> None:
    """Duplicate learn receipt must include source_id (the existing matching raw stem)."""
    schema = _load_schema("brain-learn", "response")
    # Simulate a duplicate receipt
    duplicate_receipt = {
        "correlation_id": "00000000-0000-0000-0000-000000000001",
        "source_id": "src-a1b2c3d4",
        "status": "duplicate",
    }
    validate(instance=duplicate_receipt, schema=schema, cls=Draft202012Validator)


# ---------------------------------------------------------------------------
# 14. Executable: invalid learn receipt must NOT have source_id
# ---------------------------------------------------------------------------

def test_learn_invalid_receipt_no_source_id() -> None:
    """Invalid learn receipt must omit source_id (schema conditional enforces this)."""
    import jsonschema
    schema = _load_schema("brain-learn", "response")
    # source_id present on invalid receipt should fail validation (conditional schema)
    invalid_with_source = {
        "correlation_id": "00000000-0000-0000-0000-000000000001",
        "source_id": "src-a1b2c3d4",
        "status": "invalid",
        "message": "validation failed",
    }
    with pytest.raises(jsonschema.ValidationError):
        validate(instance=invalid_with_source, schema=schema, cls=Draft202012Validator)


# ---------------------------------------------------------------------------
# 15. Executable: apm pack dry-run succeeds (smoke test for packability)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("apm") is None, reason="apm CLI not in PATH")
def test_apm_pack_dry_run_succeeds() -> None:
    """apm pack --dry-run must succeed for second-brain-learn."""
    import subprocess
    result = subprocess.run(
        ["apm", "pack", "--dry-run"],
        capture_output=True, text=True, timeout=60,
        cwd=str(PKG_ROOT),
    )
    assert result.returncode == 0, (
        f"apm pack --dry-run failed for second-brain-learn:\n{result.stdout}\n{result.stderr}"
    )
