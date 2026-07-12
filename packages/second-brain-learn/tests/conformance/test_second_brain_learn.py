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
        "source_id": "src-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "message": "Ingested.",
    }
    validate(instance=valid_accepted, schema=schema, cls=Draft202012Validator)


def test_response_schema_requires_source_id_for_duplicate() -> None:
    schema = _load_schema("brain-learn", "response")
    valid_duplicate = {
        "correlation_id": "a1b2c3d4-e5f6-4789-abcd-ef1234567890",
        "status": "duplicate",
        "source_id": "src-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "message": "Already ingested.",
    }
    validate(instance=valid_duplicate, schema=schema, cls=Draft202012Validator)


def test_response_schema_invalid_must_omit_source_id() -> None:
    schema = _load_schema("brain-learn", "response")
    invalid_with_source_id = {
        "correlation_id": "a1b2c3d4-e5f6-4789-abcd-ef1234567890",
        "status": "invalid",
        "source_id": "src-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
        "source_id": "src-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
        "source_id": "src-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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


# ---------------------------------------------------------------------------
# 16. Provenance: learn handler documents post-ingest source_ids annotation
# ---------------------------------------------------------------------------

def test_learn_handler_documents_provenance_annotation() -> None:
    """sb-learn-handler must document the post-ingest source_ids annotation step.

    After kw-wiki-ingest, the handler must enumerate concept documents that
    link to the raw file and append source_ids frontmatter array.
    """
    skill_path = SKILLS_DIR / "sb-learn-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "source_ids" in content, (
        "sb-learn-handler must document writing source_ids to concept frontmatter"
    )
    assert "Annotate concept provenance" in content or "provenance" in content.lower(), (
        "sb-learn-handler must have a post-ingest provenance annotation step"
    )
    assert "deduplicate" in content.lower() or "dedup" in content.lower(), (
        "sb-learn-handler must document deduplication of source_ids on multi-source concepts"
    )


# ---------------------------------------------------------------------------
# 17. Provenance: source_id is 64 hex chars (full SHA-256), not 8
# ---------------------------------------------------------------------------

def test_source_id_uses_full_sha256() -> None:
    """source_id must be full SHA-256 (64 hex chars = 256 bits), not 8 chars (32 bits)."""
    import re

    schema = _load_schema("brain-learn", "response")
    pattern = schema.get("properties", {}).get("source_id", {}).get("pattern", "")
    assert re.search(r"\{64\}", pattern), (
        f"source_id schema pattern must require 64 hex chars (full SHA-256). Got: {pattern!r}"
    )

    skill_path = SKILLS_DIR / "sb-learn-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "64" in content and "8" not in content.split("64")[0].split("src-")[-1][:10], (
        "sb-learn-handler must document 64-char source_id, not 8-char truncation"
    )


# ---------------------------------------------------------------------------
# 18. Forget: handler must enumerate concept docs (not index) for source_id
# ---------------------------------------------------------------------------

def test_forget_handler_enumerates_concept_docs() -> None:
    """sb-forget-handler must enumerate concept documents to resolve source_id.

    wiki/index.md does not carry source_ids frontmatter -- the handler
    must scan individual concept files under wiki/concepts/.
    """
    skill_path = SKILLS_DIR / "sb-forget-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    # Must reference concept files enumeration
    has_enumerate = (
        "enumerate" in content.lower()
        or "wiki/concepts" in content
        or "concept files" in content.lower()
    )
    assert has_enumerate, (
        "sb-forget-handler must document enumerating concept files "
        "(NOT wiki/index.md) to find source_ids."
    )
    # Must NOT say scan wiki index for source_id lookup
    # (wiki/index.md doesn't carry provenance)
    lines_with_index_scan = [
        l for l in content.splitlines()
        if "wiki index" in l.lower() and "source_id" in l.lower()
    ]
    assert not lines_with_index_scan, (
        f"sb-forget-handler must not say scan wiki index for source_id: {lines_with_index_scan}"
    )


# ---------------------------------------------------------------------------
# 19. Forget: multi-source conservative tombstone documented
# ---------------------------------------------------------------------------

def test_forget_handler_documents_multi_source_conservative_tombstone() -> None:
    """Forget must document that multi-source concepts are tombstoned as a whole in v1."""
    skill_path = SKILLS_DIR / "sb-forget-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()
    assert "multi-source" in content or "multiple" in content, (
        "sb-forget-handler must document multi-source concept handling"
    )
    assert "conservative" in content or "as a whole" in content, (
        "sb-forget-handler must document that multi-source concepts are tombstoned as a whole in v1"
    )


# ---------------------------------------------------------------------------
# 20. No stale claim that kw-wiki-ingest writes source_id to concept frontmatter
# ---------------------------------------------------------------------------

def test_learn_handler_no_stale_ingest_writes_source_id() -> None:
    """sb-learn-handler must NOT claim kw-wiki-ingest writes source_id to concepts.

    kw-wiki-ingest (at pinned c4a074f) writes only id/title/type/created/modified.
    The post-ingest annotation step (step 6) is what writes source_ids array.
    """
    skill_path = SKILLS_DIR / "sb-learn-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    # Must explicitly state kw-wiki-ingest does NOT write source_id
    has_correct_claim = (
        "does NOT write source_id" in content
        or "does not write source_id" in content.lower()
    )
    assert has_correct_claim, (
        "sb-learn-handler must explicitly state kw-wiki-ingest does NOT write "
        "source_id into concept frontmatter"
    )
    # Must not say 'concept documents... also carry this field' (stale claim)
    stale_lines = [
        l for l in content.splitlines()
        if "kw-wiki-ingest also carry" in l.lower()
        or ("concept documents" in l.lower() and "carry this field" in l.lower())
    ]
    assert not stale_lines, f"Stale claim found: {stale_lines}"


# ---------------------------------------------------------------------------
# 21. Step 6 requires Markdown link parsing (not substring matching)
# ---------------------------------------------------------------------------

def test_learn_handler_step6_requires_link_parsing() -> None:
    """Step 6 must require parsing Markdown link destinations, not substring matching."""
    skill_path = SKILLS_DIR / "sb-learn-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    # Must document exact-match / link parsing requirement
    has_link_parsing = (
        "markdown link" in content.lower()
        or "parse markdown" in content.lower()
        or "link destination" in content.lower()
    )
    assert has_link_parsing, (
        "Step 6 must document Markdown link parsing for provenance annotation"
    )
    # Must explicitly forbid substring matching
    forbids_substring = (
        "substring matching" in content.lower()
        and ("not sufficient" in content.lower() or "must not" in content.lower())
    )
    assert forbids_substring, (
        "Step 6 must explicitly state that substring matching is NOT sufficient"
    )
    # Must require canonicalisation
    has_canonical = (
        "canonicalis" in content.lower()
        or "realpath" in content.lower()
        or "canonical" in content.lower()
    )
    assert has_canonical, (
        "Step 6 must require canonicalising resolved paths before comparison"
    )


# ---------------------------------------------------------------------------
# 22. Schema wording uses 'digest' not 'entropy'
# ---------------------------------------------------------------------------

def test_source_id_schema_uses_digest_not_entropy() -> None:
    """Schema description must say 'SHA-256 digest', not 'bits of entropy'."""
    schema = _load_schema("brain-learn", "response")
    desc = schema.get("properties", {}).get("source_id", {}).get("description", "")
    assert "entropy" not in desc, (
        "source_id schema must not use 'entropy' -- content hashes are not entropy. "
        "Use 'full 256-bit SHA-256 digest' instead."
    )
    assert "digest" in desc.lower(), (
        "source_id schema description must mention 'digest'"
    )
