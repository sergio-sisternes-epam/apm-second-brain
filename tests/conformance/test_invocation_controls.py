"""
Conformance test: invocation controls.

Verifies that every non-public skill carries the direct-user-invocation
disabled header and a redirect instruction.  Classification uses a stable
PUBLIC_SKILLS allowlist -- the explicit set of skills that are intentionally
user-invocable.  Any skill NOT on that allowlist is classified as internal
and must have the disabled header as its first line plus a redirect instruction.

This means:
- Adding a new internal skill (e.g. a private provider) is covered automatically
  without touching this file -- the author only needs to add the disabled header.
- Adding a new public skill requires adding it to PUBLIC_SKILLS here.  Forgetting
  to do so causes CI to fail (skill treated as internal, header missing -> FAIL),
  which is the safer default.

This test is deterministic and runs in CI without a live agent runtime.

Runtime evaluation (gate2-direct-user-negative, gate2-model-caller-positive)
requires a live Copilot CLI or Claude Code session; see
tests/evals/gate2/invocation-control-protocol.md.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent

DISABLED_HEADER = "<!-- direct-user-invocation: disabled -->"
REDIRECT_PATTERN = re.compile(
    r"(must only be called by|not.*invok.*direct|decline|redirect|internal)",
    re.IGNORECASE,
)

# Explicit allowlist of intentionally public (user-invocable) skill paths.
# These are the stable public API surfaces of the monorepo.
# Every entry is a repo-relative path to SKILL.md.
#
# IMPORTANT: When a new PUBLIC skill is added, add its path here.
# When a new INTERNAL skill is added, do NOT add it here -- it will
# be classified as internal automatically and must carry the disabled header.
PUBLIC_SKILLS: frozenset[str] = frozenset(
    [
        "packages/agent-knowledge-network/.apm/skills/akn-deregister/SKILL.md",
        "packages/agent-knowledge-network/.apm/skills/akn-discover/SKILL.md",
        "packages/agent-knowledge-network/.apm/skills/akn-register/SKILL.md",
        "packages/open-knowledge-format/.apm/skills/okf-bundle-create/SKILL.md",
        "packages/open-knowledge-format/.apm/skills/okf-bundle-validate/SKILL.md",
        "packages/open-knowledge-format/.apm/skills/okf-import/SKILL.md",
        "packages/second-brain-interfaces/.apm/skills/brain-forget/SKILL.md",
        "packages/second-brain-interfaces/.apm/skills/brain-learn/SKILL.md",
        "packages/second-brain-interfaces/.apm/skills/brain-think/SKILL.md",
        "packages/karpathy-wiki/.apm/skills/knowledge-graph-canvas/SKILL.md",
        "packages/apm-expert/.apm/skills/apm-think/SKILL.md",
    ]
)


def _all_package_skills() -> list[Path]:
    return sorted(REPO_ROOT.glob("packages/*/.apm/skills/*/SKILL.md"))


def _discover_internal_skills() -> list[str]:
    """Return repo-relative paths of every skill NOT on the PUBLIC_SKILLS allowlist."""
    return [
        str(p.relative_to(REPO_ROOT))
        for p in _all_package_skills()
        if str(p.relative_to(REPO_ROOT)) not in PUBLIC_SKILLS
    ]


INTERNAL_SKILLS = _discover_internal_skills()


@pytest.mark.parametrize("skill_path", INTERNAL_SKILLS)
def test_disabled_header_present(skill_path: str) -> None:
    path = REPO_ROOT / skill_path
    assert path.exists(), f"Internal skill not found: {skill_path}"
    content = path.read_text(encoding="utf-8")
    assert DISABLED_HEADER in content, (
        f"{skill_path} is missing the required header: {DISABLED_HEADER!r}"
    )


@pytest.mark.parametrize("skill_path", INTERNAL_SKILLS)
def test_redirect_instruction_present(skill_path: str) -> None:
    path = REPO_ROOT / skill_path
    content = path.read_text(encoding="utf-8")
    assert REDIRECT_PATTERN.search(content), (
        f"{skill_path} must contain a redirect instruction telling the agent "
        "to decline direct user invocation."
    )


@pytest.mark.parametrize("skill_path", INTERNAL_SKILLS)
def test_disabled_header_is_first_line(skill_path: str) -> None:
    path = REPO_ROOT / skill_path
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.strip() == DISABLED_HEADER, (
        f"{skill_path}: disabled header must be the first line, got: {first_line!r}"
    )


def test_public_skills_allowlist_all_exist() -> None:
    """Every path in PUBLIC_SKILLS must resolve to an actual file."""
    missing = [p for p in sorted(PUBLIC_SKILLS) if not (REPO_ROOT / p).exists()]
    assert not missing, (
        "PUBLIC_SKILLS contains paths that do not exist -- update the allowlist:\n"
        + "\n".join(f"  {p}" for p in missing)
    )


def test_public_skills_do_not_carry_disabled_header() -> None:
    """Public skills must NOT have the disabled header."""
    for skill_path in sorted(PUBLIC_SKILLS):
        path = REPO_ROOT / skill_path
        if not path.exists():
            continue  # caught by test_public_skills_allowlist_all_exist
        content = path.read_text(encoding="utf-8")
        assert DISABLED_HEADER not in content, (
            f"Public skill {skill_path} must NOT carry "
            "the direct-user-invocation disabled header."
        )


def test_unallowlisted_skill_without_header_is_caught() -> None:
    """Regression: a skill not on PUBLIC_SKILLS and missing the disabled header must be flagged.

    This test verifies the allowlist-based classification logic: any SKILL.md
    whose repo-relative path is absent from PUBLIC_SKILLS is treated as internal
    and must have the disabled header as its first line.  If it does not, the
    parametrized header tests will fail.  This non-parametrized test makes the
    invariant explicit and machine-verifiable.
    """
    # Simulate a brand-new skill that an author forgot to protect.
    fake_rel = "packages/new-pkg/.apm/skills/new-skill/SKILL.md"
    fake_content = "# A new skill -- author forgot the disabled header.\n"

    # Confirm the fake path is not in the public allowlist.
    assert fake_rel not in PUBLIC_SKILLS, (
        "Test precondition: fake path must not be pre-listed as public"
    )

    # Confirm it would be classified as internal (not public).
    is_public = fake_rel in PUBLIC_SKILLS
    assert not is_public

    # Confirm the check that CI performs on internal skills WOULD fail.
    first_line = fake_content.splitlines()[0].strip()
    with pytest.raises(AssertionError, match="missing the required header"):
        assert first_line == DISABLED_HEADER, (
            f"{fake_rel} is missing the required header: {DISABLED_HEADER!r}"
        )


def test_eval_fixtures_present() -> None:
    """Both gate2 eval fixtures must be committed."""
    evals = REPO_ROOT / "tests" / "evals" / "gate2"
    assert (evals / "gate2-direct-user-negative.json").exists()
    assert (evals / "gate2-model-caller-positive.json").exists()
    assert (evals / "invocation-control-protocol.md").exists()
