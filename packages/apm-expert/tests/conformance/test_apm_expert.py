"""
Conformance tests for the apm-expert package.

Verifies structural invariants without requiring a live agent runtime:

1. Agent file exists at .apm/agents/apm-expert.agent.md
2. Public think skill (apm-think) exists and does NOT have the disabled header
3. Internal knowledge skill (apm-knowledge) has the disabled header as first line
4. Corpus placeholder exists at references/knowledge/CORPUS.md
5. Registration metadata documents agentId and capability
6. apm pack --dry-run succeeds (skipped if apm not in PATH)
"""

import shutil
import subprocess
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).parent.parent.parent
DISABLED_HEADER = "<!-- direct-user-invocation: disabled -->"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(rel: str) -> str:
    p = PACKAGE_ROOT / rel
    assert p.exists(), f"Expected file not found: {p}"
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1: agent file
# ---------------------------------------------------------------------------

def test_agent_file_exists() -> None:
    agent = PACKAGE_ROOT / ".apm" / "agents" / "apm-expert.agent.md"
    assert agent.exists(), f"Agent file not found: {agent}"


def test_agent_file_mentions_public_invocation() -> None:
    content = _read(".apm/agents/apm-expert.agent.md")
    assert "public" in content.lower() or "user-invokable" in content.lower(), (
        "Agent file should document that it is user-invokable"
    )


# ---------------------------------------------------------------------------
# Test 2: public think skill
# ---------------------------------------------------------------------------

def test_public_think_skill_exists() -> None:
    skill = PACKAGE_ROOT / ".apm" / "skills" / "apm-think" / "SKILL.md"
    assert skill.exists(), f"Public think skill not found: {skill}"


def test_public_think_skill_has_no_disabled_header() -> None:
    content = _read(".apm/skills/apm-think/SKILL.md")
    assert DISABLED_HEADER not in content, (
        "apm-think is a public skill and must NOT carry the disabled header"
    )


def test_public_think_skill_documents_capability() -> None:
    content = _read(".apm/skills/apm-think/SKILL.md")
    assert "apm-expert.answer.v1" in content, (
        "apm-think must document the apm-expert.answer.v1 capability identifier"
    )


def test_public_think_skill_documents_quality_levels() -> None:
    content = _read(".apm/skills/apm-think/SKILL.md")
    for level in ("answered", "partial", "unanswered"):
        assert level in content, (
            f"apm-think SKILL.md must document quality level '{level}'"
        )


# ---------------------------------------------------------------------------
# Test 3: internal knowledge skill
# ---------------------------------------------------------------------------

def test_internal_knowledge_skill_exists() -> None:
    skill = PACKAGE_ROOT / ".apm" / "skills" / "apm-knowledge" / "SKILL.md"
    assert skill.exists(), f"Internal knowledge skill not found: {skill}"


def test_internal_knowledge_skill_disabled_header_is_first_line() -> None:
    content = _read(".apm/skills/apm-knowledge/SKILL.md")
    first_line = content.splitlines()[0].strip()
    assert first_line == DISABLED_HEADER, (
        f"apm-knowledge/SKILL.md: disabled header must be the first line, "
        f"got: {first_line!r}"
    )


def test_internal_knowledge_skill_documents_corpus_metadata() -> None:
    content = _read(".apm/skills/apm-knowledge/SKILL.md")
    assert "d73e6ac3" in content, (
        "apm-knowledge SKILL.md must document the corpus commit (d73e6ac3)"
    )
    assert "v0.25.0" in content, (
        "apm-knowledge SKILL.md must document the corpus tag (v0.25.0)"
    )


# ---------------------------------------------------------------------------
# Test 4: corpus placeholder
# ---------------------------------------------------------------------------

def test_corpus_placeholder_exists() -> None:
    corpus = (
        PACKAGE_ROOT
        / ".apm"
        / "skills"
        / "apm-knowledge"
        / "references"
        / "knowledge"
        / "CORPUS.md"
    )
    assert corpus.exists(), f"Corpus placeholder not found: {corpus}"


def test_corpus_placeholder_documents_source() -> None:
    content = _read(
        ".apm/skills/apm-knowledge/references/knowledge/CORPUS.md"
    )
    assert "microsoft/apm" in content, (
        "CORPUS.md must document the source repository (microsoft/apm)"
    )
    assert "d73e6ac3" in content, (
        "CORPUS.md must document the pinned commit (d73e6ac3)"
    )


# ---------------------------------------------------------------------------
# Test 5: registration metadata
# ---------------------------------------------------------------------------

def test_registration_metadata_exists() -> None:
    reg = PACKAGE_ROOT / ".apm" / "instructions" / "registration.md"
    assert reg.exists(), f"Registration metadata not found: {reg}"


def test_registration_metadata_documents_agent_id() -> None:
    content = _read(".apm/instructions/registration.md")
    assert "agentId" in content, (
        "registration.md must document the agentId field"
    )


def test_registration_metadata_documents_capability() -> None:
    content = _read(".apm/instructions/registration.md")
    assert "apm-expert.answer.v1" in content, (
        "registration.md must document the apm-expert.answer.v1 capability"
    )


def test_registration_metadata_notes_idempotent_registration() -> None:
    content = _read(".apm/instructions/registration.md")
    assert "idempotent" in content.lower(), (
        "registration.md must note that registration is idempotent"
    )


# ---------------------------------------------------------------------------
# Test 6: apm pack --dry-run
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    shutil.which("apm") is None,
    reason="apm not in PATH -- skipping pack dry-run",
)
def test_apm_pack_dry_run_succeeds() -> None:
    result = subprocess.run(
        ["apm", "pack", "--dry-run"],
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"apm pack --dry-run failed with exit code {result.returncode}.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
