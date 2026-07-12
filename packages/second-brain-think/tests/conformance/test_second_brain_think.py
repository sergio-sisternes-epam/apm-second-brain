"""
Conformance tests for the second-brain-think package.

Verifies:
1. Both internal skills carry the disabled header as the first line.
2. Both internal skills contain a redirect instruction.
3. think-handler SKILL.md does not reference any modification operations.
4. think-handler SKILL.md references citations (read-only, citation-backed).
5. Valid think request fixture validates against second-brain-interfaces schema.
6. Dependencies declared in apm.yml.

Run with: pytest packages/second-brain-think/tests/conformance/ -v
Requirements: jsonschema>=4.0
"""

import json
import re
from pathlib import Path

import pytest
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
    r"(must only be called by|not.*invok.*direct|decline|redirect|internal)",
    re.IGNORECASE,
)

INTERNAL_SKILL_NAMES = [
    "sb-think-handler",
    "sb-think-validate",
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
# 3. think-handler does not reference modification operations
# ---------------------------------------------------------------------------

def test_think_handler_no_modification_operations() -> None:
    skill_path = SKILLS_DIR / "sb-think-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    forbidden_terms = ["kw-wiki-ingest", "kw-wiki-archive", "sb-learn", "write"]
    for term in forbidden_terms:
        assert term not in content, (
            f"sb-think-handler/SKILL.md must not reference '{term}' "
            "(think is read-only; no modification operations allowed)"
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
