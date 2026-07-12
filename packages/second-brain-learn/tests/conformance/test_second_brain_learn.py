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
# 7. Behavioural contract: learn receipt source_id equals correlation_id
# ---------------------------------------------------------------------------

def test_learn_receipt_source_id_lifecycle() -> None:
    """source_id in the learn receipt must equal correlation_id.

    This is the stable identifier callers use to reference the learning
    in future forget requests. It maps directly to the raw filename stem.
    """
    skill_path = SKILLS_DIR / "sb-learn-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    # The skill must document that source_id equals correlation_id
    assert "correlation_id" in content and "source_id" in content, (
        "sb-learn-handler must document both source_id and correlation_id"
    )
    # Must state the mapping explicitly
    has_lifecycle = (
        "equals correlation_id" in content
        or "equals the correlation_id" in content
        or "source_id" in content and "filename stem" in content
        or "filename stem" in content and "correlation_id" in content
    )
    assert has_lifecycle, (
        "sb-learn-handler must document that source_id equals the correlation_id "
        "and maps to the raw filename"
    )


# ---------------------------------------------------------------------------
# 8. Behavioural contract: forget handler is idempotent
# ---------------------------------------------------------------------------

def test_forget_handler_is_idempotent() -> None:
    """Forgetting an already-archived concept must succeed (not error).

    A second forget on the same concept must return status: tombstoned
    rather than raising an error. This guarantees at-least-once forget
    semantics with no side effects on the second call.
    """
    skill_path = SKILLS_DIR / "sb-forget-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()
    assert "idempoten" in content or "already archived" in content or "already tombstoned" in content, (
        "sb-forget-handler must document idempotency: a second forget on an "
        "already-archived concept must return tombstoned, not error."
    )


# ---------------------------------------------------------------------------
# 9. Behavioural contract: forget handler validates input before resolving
# ---------------------------------------------------------------------------

def test_forget_handler_validates_before_resolve() -> None:
    """Forget handler must validate the request envelope before any wiki access."""
    skill_path = SKILLS_DIR / "sb-forget-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    # Find the first numbered procedure step that mentions validate
    validate_steps = [
        i for i, line in enumerate(lines)
        if "validate" in line.lower() and any(c.isdigit() for c in line[:5])
    ]
    resolve_steps = [
        i for i, line in enumerate(lines)
        if "resolve" in line.lower() and any(c.isdigit() for c in line[:5])
    ]
    if validate_steps and resolve_steps:
        assert min(validate_steps) < min(resolve_steps), (
            "sb-forget-handler must validate the envelope (step 1) before "
            "resolving the target -- prevents wiki access on malformed input."
        )


# ---------------------------------------------------------------------------
# 10. Behavioural contract: forget containment check documented
# ---------------------------------------------------------------------------

def test_forget_handler_containment_check() -> None:
    """Forget handler must document path containment for concept path inputs."""
    skill_path = SKILLS_DIR / "sb-forget-handler" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()
    has_containment = (
        "containment" in content
        or "wiki root" in content
        or "traversal" in content
        or "outside" in content
    )
    assert has_containment, (
        "sb-forget-handler must document path containment checks for concept "
        "path inputs to prevent wiki root traversal."
    )

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
# 11. Dependency pins use full 40-character SHA
# ---------------------------------------------------------------------------

def test_dependency_pins_use_full_sha() -> None:
    """Remote dependency refs must use a full 40-char commit SHA for reproducibility."""
    import re
    apm_yml_path = PKG_ROOT / "apm.yml"
    content = apm_yml_path.read_text(encoding="utf-8")
    # Find all #<sha> refs
    sha_refs = re.findall(r'#([0-9a-f]+)', content)
    for sha in sha_refs:
        assert len(sha) == 40, (
            f"apm.yml dependency pin uses short SHA '{sha}' -- must be full 40-char SHA "
            "for reproducible builds."
        )
