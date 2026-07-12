"""
Conformance tests for the second-brain-learn package.

Verifies:
1. All internal skills carry the disabled header as the first line.
2. All internal skills contain a redirect instruction.
3. Forget handler documents the tombstone-only constraint (no destructive deletion).
4. Valid learn request fixture validates against second-brain-interfaces schema.
5. Valid forget request fixture validates against second-brain-interfaces schema.
6. Dependencies declared in apm.yml.

Run with: pytest packages/second-brain-learn/tests/conformance/ -v
Requirements: jsonschema>=4.0
"""

import json
import re
from pathlib import Path

import pytest
from jsonschema import validate, Draft202012Validator

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
PKG_ROOT = REPO_ROOT / "packages" / "second-brain-learn"
SKILLS_DIR = PKG_ROOT / ".apm" / "skills"
FIXTURES_DIR = PKG_ROOT / "tests" / "fixtures"
INTERFACES_SKILLS = (
    REPO_ROOT / "packages" / "second-brain-interfaces" / ".apm" / "skills"
)

DISABLED_HEADER = "<!-- direct-user-invocation: disabled -->"
REDIRECT_PATTERN = re.compile(
    r"(must only be called by|not.*invok.*direct|decline|redirect|internal)",
    re.IGNORECASE,
)

INTERNAL_SKILL_NAMES = [
    "sb-learn-handler",
    "sb-forget-handler",
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
# 2. Redirect instruction present
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("skill_name", INTERNAL_SKILL_NAMES)
def test_redirect_instruction_present(skill_name: str) -> None:
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    assert REDIRECT_PATTERN.search(content), (
        f"{skill_name}/SKILL.md must contain a redirect instruction telling the agent "
        "to decline direct user invocation."
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
