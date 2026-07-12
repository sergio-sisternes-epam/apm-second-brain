"""
Conformance test: invocation controls.

Verifies that every declared internal skill carries the required
direct-user-invocation disabled header and the redirect instruction.
This test is deterministic and runs in CI without a live agent runtime.

Runtime evaluation (gate2-direct-user-negative, gate2-model-caller-positive)
requires a live Copilot CLI or Claude Code session; see
tests/evals/gate2/invocation-control-protocol.md.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent

# All internal skills across all packages.
# Each entry is a path relative to REPO_ROOT.
INTERNAL_SKILLS = [
    "packages/agent-knowledge-network/.apm/skills/akn-registry-io/SKILL.md",
]

DISABLED_HEADER = "<!-- direct-user-invocation: disabled -->"
REDIRECT_PATTERN = re.compile(
    r"(must only be called by|not.*invok.*direct|decline|redirect|internal)",
    re.IGNORECASE,
)


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


def test_public_skills_do_not_carry_disabled_header() -> None:
    """Public skills must NOT have the disabled header."""
    public_skill_dirs = [
        REPO_ROOT / "packages" / pkg / ".apm" / "skills"
        for pkg in [
            "open-knowledge-format",
            "second-brain-interfaces",
            "agent-knowledge-network",
        ]
    ]
    internal_paths = {REPO_ROOT / p for p in INTERNAL_SKILLS}

    for skills_dir in public_skill_dirs:
        if not skills_dir.exists():
            continue
        for skill_md in skills_dir.rglob("SKILL.md"):
            if skill_md in internal_paths:
                continue
            content = skill_md.read_text(encoding="utf-8")
            assert DISABLED_HEADER not in content, (
                f"Public skill {skill_md.relative_to(REPO_ROOT)} must NOT carry "
                "the direct-user-invocation disabled header."
            )


def test_eval_fixtures_present() -> None:
    """Both gate2 eval fixtures must be committed."""
    evals = REPO_ROOT / "tests" / "evals" / "gate2"
    assert (evals / "gate2-direct-user-negative.json").exists()
    assert (evals / "gate2-model-caller-positive.json").exists()
    assert (evals / "invocation-control-protocol.md").exists()
