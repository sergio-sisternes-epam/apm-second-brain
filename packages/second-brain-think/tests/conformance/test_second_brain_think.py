"""
Conformance tests for the second-brain-think package.

Verifies:
 1. Both internal skills carry the disabled header as the first line.
 2. Both internal skills contain a meaningful redirect instruction.
 3. think-handler SKILL.md does not reference any write operations.
 4. think-handler SKILL.md references citation-backed reasoning.
 5. Valid think request fixture validates against second-brain-interfaces schema.
 6. Dependencies declared in apm.yml.
 7. think-handler documents VALIDATION_ERROR code (R4).
 8. think-handler documents that quality:answered requires citations (R4).
 9. think-handler citations use source_id from frontmatter, not concept slugs (R4).
10. Deployed files include the read-only query skill (R3 architectural assertion).
11. apm.yml and apm.lock.yaml use full 40-char commit SHAs (R5).

Run with: pytest packages/second-brain-think/tests/conformance/ -v
Requirements: jsonschema>=4.0, pyyaml
"""

import json
import shutil
import re
from pathlib import Path

import pytest
import yaml
from jsonschema import validate, Draft202012Validator

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
PKG_ROOT = REPO_ROOT / "packages" / "second-brain-think"
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
    "sb-think-handler",
    "sb-think-validate",
]

# Write-capable skills that must NOT be referenced in sb-think-handler
FORBIDDEN_WRITE_SKILLS = [
    "kw-wiki-ingest",
    "kw-wiki-archive",
    "kw-wiki-log",
    "kw-wiki-index",
    "kw-wiki-init",
    "sb-learn",
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
# 3. think-handler does not reference write-capable skills
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("forbidden_term", FORBIDDEN_WRITE_SKILLS)
def test_think_handler_no_write_skill_references(forbidden_term: str) -> None:
    skill_path = SKILLS_DIR / "sb-think-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert forbidden_term not in content, (
        f"sb-think-handler/SKILL.md must not reference '{forbidden_term}' "
        "(think is strictly read-only; no write-capable skill references allowed)"
    )


# ---------------------------------------------------------------------------
# 4. think-handler references citations (citation-backed reasoning)
# ---------------------------------------------------------------------------

def test_think_handler_references_citations() -> None:
    skill_path = SKILLS_DIR / "sb-think-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()
    assert "citation" in content or "cite" in content, (
        "sb-think-handler/SKILL.md must reference citation-backed reasoning "
        "(contain 'citation' or 'cite')"
    )


# ---------------------------------------------------------------------------
# 5. Valid think request fixture validates against schema
# ---------------------------------------------------------------------------

def test_valid_think_request_fixture() -> None:
    schema = _load_schema("brain-think", "request")
    fixture = _load_json(FIXTURES_DIR / "valid-think-request.json")
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
# 7. think-handler documents VALIDATION_ERROR code (R4)
# ---------------------------------------------------------------------------

def test_think_handler_documents_validation_error_code() -> None:
    skill_path = SKILLS_DIR / "sb-think-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "VALIDATION_ERROR" in content, (
        "sb-think-handler/SKILL.md must document the VALIDATION_ERROR prefix "
        "used in knowledge_gaps when validation fails (R4)"
    )


# ---------------------------------------------------------------------------
# 8. think-handler documents that quality:answered requires citations (R4)
# ---------------------------------------------------------------------------

def test_think_handler_answered_requires_citations() -> None:
    skill_path = SKILLS_DIR / "sb-think-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()
    # Must document that 'answered' quality requires at least one citation
    has_citation_requirement = (
        ("answered" in content and "citation" in content and
         ("require" in content or "non-empty" in content or "at least one" in content))
    )
    assert has_citation_requirement, (
        "sb-think-handler/SKILL.md must document that quality:answered requires "
        "at least one citation (R4)"
    )


# ---------------------------------------------------------------------------
# 9. think-handler citations use source_id from frontmatter, not slug (R4, R1)
# ---------------------------------------------------------------------------

def test_think_handler_citations_use_source_id_from_frontmatter() -> None:
    skill_path = SKILLS_DIR / "sb-think-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "source_id" in content, (
        "sb-think-handler/SKILL.md must reference source_id in citation objects"
    )
    # Must NOT substitute slugs for source_ids
    assert "slug" not in content.lower() or "not substitute" in content.lower() or "do not substitute" in content.lower(), (
        "sb-think-handler/SKILL.md must warn against substituting slugs for source_id in citations"
    )
    assert "frontmatter" in content.lower(), (
        "sb-think-handler/SKILL.md must instruct reading source_id from concept frontmatter"
    )


# ---------------------------------------------------------------------------
# 10. Deployed files include the read-only query skill (R3 architectural assertion)
# ---------------------------------------------------------------------------

def test_lock_deployed_files_include_query_skill() -> None:
    lock_path = PKG_ROOT / "apm.lock.yaml"
    if not lock_path.exists():
        pytest.skip("apm.lock.yaml not present (run apm install first)")
    with lock_path.open(encoding="utf-8") as f:
        lock = yaml.safe_load(f)
    all_deployed: list[str] = []
    for dep in lock.get("dependencies", []):
        all_deployed.extend(dep.get("deployed_files", []))
    query_deployed = any("kw-wiki-query" in f for f in all_deployed)
    assert query_deployed, (
        "apm.lock.yaml must show kw-wiki-query deployed (read path must be available)"
    )


# ---------------------------------------------------------------------------
# 11. apm.yml and apm.lock.yaml use full 40-char commit SHAs (R5)
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
# 11. Executable: apm pack dry-run for second-brain-think succeeds
# ---------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("apm") is None, reason="apm CLI not in PATH")
def test_apm_pack_dry_run_succeeds() -> None:
    """apm pack --dry-run must succeed for second-brain-think."""
    import subprocess
    result = subprocess.run(
        ["apm", "pack", "--dry-run"],
        capture_output=True, text=True, timeout=60,
        cwd=str(PKG_ROOT),
    )
    assert result.returncode == 0, (
        f"apm pack --dry-run failed for second-brain-think:\n{result.stdout}\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# 12. Executable: packed own-primitives contain only think skills
# ---------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("apm") is None, reason="apm CLI not in PATH")
def test_apm_pack_own_primitives_are_think_only() -> None:
    """second-brain-think's own packed primitives (from .apm/) must be think skills only.

    APM 0.25 note: dependency skills (karpathy-wiki, second-brain-interfaces)
    are always deployed alongside own skills -- this is an APM design constraint
    (includes: controls own primitives only, not dependency primitives).
    This test verifies the OWN packaged surface is read-only.
    """
    import subprocess
    result = subprocess.run(
        ["apm", "pack", "--dry-run"],
        capture_output=True, text=True, timeout=60,
        cwd=str(PKG_ROOT),
    )
    assert result.returncode == 0, f"apm pack --dry-run failed: {result.stderr}"
    output = result.stdout

    # Own think skills must be present
    assert "sb-think-handler/SKILL.md" in output, "sb-think-handler must be in pack output"
    assert "sb-think-validate/SKILL.md" in output, "sb-think-validate must be in pack output"

    # Own write skills must NOT be present (no own write skills)
    own_write_skills = ["sb-learn-handler", "sb-forget-handler", "sb-learn-validate"]
    for skill in own_write_skills:
        assert skill not in output, (
            f"Pack output must not contain own write skill: {skill}. "
            "second-brain-think is a read-only package."
        )


# ---------------------------------------------------------------------------
# 13. Citations read source_ids array, not singular source_id field
# ---------------------------------------------------------------------------

def test_think_handler_reads_source_ids_array() -> None:
    """sb-think-handler must read source_ids array (not singular source_id field).

    kw-wiki-ingest does not write source_id to concept frontmatter.
    The learn handler's post-ingest annotation writes source_ids array.
    Citations must come from source_ids, not from a non-existent source_id field.
    """
    skill_path = SKILLS_DIR / "sb-think-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert "source_ids" in content, (
        "sb-think-handler must reference source_ids (plural array) not source_id singular field"
    )
    # Must not say 'extract the source_id: field' (singular -- kw-wiki-ingest doesn't write it)
    assert "source_ids:" in content.lower() or "source_ids array" in content.lower(), (
        "sb-think-handler must explicitly document reading source_ids: array from frontmatter"
    )


# ---------------------------------------------------------------------------
# 14. Citations: answered quality requires at least one citation
# ---------------------------------------------------------------------------

def test_think_handler_answered_requires_citations() -> None:
    """quality: answered must require at least one citation."""
    skill_path = SKILLS_DIR / "sb-think-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()
    has_invariant = (
        "answered" in content and "citation" in content
        and ("at least one" in content or "non-empty" in content)
    )
    assert has_invariant, (
        "sb-think-handler must state that quality:answered requires at least one citation"
    )
