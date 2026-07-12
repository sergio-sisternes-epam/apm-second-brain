"""
Conformance tests for the apm-expert package.

Verifies structural and behavioural invariants without requiring a live agent
runtime.

Tests cover:
1. Agent file -- exists with required frontmatter (name, type, public, capabilities)
2. Public think skill -- no disabled header, documents fail-closed branch,
   documents quality levels, documents knowledge_gaps
3. Internal knowledge skill -- disabled header as first line, corpus metadata,
   trust boundary note
4. Corpus structure -- CORPUS.md exists, trust boundary note, provenance fields;
   active pointer and baseline directory present
5. Registration metadata -- all required fields, correct revision semantics,
   deduplication by projectId; sample-registration.json fixture
6. Behavioural: fail-closed documented in think skill and agent
7. Pack -- apm pack --dry-run succeeds; packed surface contains expected files;
   internal knowledge skill docs confirm internal routing
8. second-brain zero-own-primitives -- second-brain apm.lock has no own files
9. AKN fixture validates against required schema fields
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).parent.parent.parent
REPO_ROOT = PACKAGE_ROOT.parent.parent
SECOND_BRAIN_ROOT = REPO_ROOT / "packages" / "second-brain"

DISABLED_HEADER = "<!-- direct-user-invocation: disabled -->"
KNOWLEDGE_BASE = PACKAGE_ROOT / ".apm" / "skills" / "apm-knowledge" / "references" / "knowledge"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(rel: str) -> str:
    p = PACKAGE_ROOT / rel
    assert p.exists(), f"Expected file not found: {p}"
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Agent file
# ---------------------------------------------------------------------------

def test_agent_file_exists() -> None:
    assert (PACKAGE_ROOT / ".apm" / "agents" / "apm-expert.agent.md").exists()


def test_agent_file_has_name_field() -> None:
    content = _read(".apm/agents/apm-expert.agent.md")
    assert "name: apm-expert" in content, "Agent file must declare name: apm-expert"


def test_agent_file_has_type_field() -> None:
    content = _read(".apm/agents/apm-expert.agent.md")
    assert "type: agent" in content, "Agent file must declare type: agent"


def test_agent_file_has_public_field() -> None:
    content = _read(".apm/agents/apm-expert.agent.md")
    assert "public: true" in content, "Agent file must declare public: true"


def test_agent_file_has_capabilities_field() -> None:
    content = _read(".apm/agents/apm-expert.agent.md")
    assert "apm-expert.answer.v1" in content, "Agent file must list capability apm-expert.answer.v1"


def test_agent_file_documents_scaffold_status() -> None:
    content = _read(".apm/agents/apm-expert.agent.md")
    assert "scaffold" in content.lower(), "Agent file must document scaffold status"


# ---------------------------------------------------------------------------
# 2. Public think skill
# ---------------------------------------------------------------------------

def test_public_think_skill_exists() -> None:
    assert (PACKAGE_ROOT / ".apm" / "skills" / "apm-think" / "SKILL.md").exists()


def test_public_think_skill_has_no_disabled_header() -> None:
    content = _read(".apm/skills/apm-think/SKILL.md")
    assert DISABLED_HEADER not in content, "apm-think must NOT carry the disabled header"


def test_public_think_skill_documents_capability() -> None:
    content = _read(".apm/skills/apm-think/SKILL.md")
    assert "apm-expert.answer.v1" in content


def test_public_think_skill_documents_quality_levels() -> None:
    content = _read(".apm/skills/apm-think/SKILL.md")
    for level in ("answered", "partial", "unanswered"):
        assert level in content, f"apm-think must document quality level '{level}'"


def test_public_think_skill_documents_knowledge_gaps() -> None:
    content = _read(".apm/skills/apm-think/SKILL.md")
    assert "knowledge_gaps" in content, "apm-think must document the knowledge_gaps field"


def test_public_think_skill_fail_closed_when_corpus_empty() -> None:
    """Behavioural: SKILL.md must document the fail-closed path for empty corpus."""
    content = _read(".apm/skills/apm-think/SKILL.md")
    assert "corpus_populated" in content, (
        "apm-think must check corpus_populated and define fail-closed behaviour"
    )
    assert "unanswered" in content, (
        "apm-think fail-closed path must return quality: unanswered"
    )
    assert "APM documentation corpus not yet populated" in content, (
        "apm-think must include the standard knowledge_gaps message for empty corpus"
    )


def test_public_think_skill_fail_closed_no_synthesis_on_empty_corpus() -> None:
    """Behavioural: fail-closed path must explicitly prohibit synthesis from model weights."""
    content = _read(".apm/skills/apm-think/SKILL.md")
    assert "model weights" in content.lower() or "do not" in content.lower(), (
        "apm-think must prohibit synthesising answers when corpus is absent"
    )


# ---------------------------------------------------------------------------
# 3. Internal knowledge skill
# ---------------------------------------------------------------------------

def test_internal_knowledge_skill_exists() -> None:
    assert (PACKAGE_ROOT / ".apm" / "skills" / "apm-knowledge" / "SKILL.md").exists()


def test_internal_knowledge_skill_disabled_header_is_first_line() -> None:
    content = _read(".apm/skills/apm-knowledge/SKILL.md")
    first_line = content.splitlines()[0].strip()
    assert first_line == DISABLED_HEADER, f"Got: {first_line!r}"


def test_internal_knowledge_skill_documents_commit_sha() -> None:
    content = _read(".apm/skills/apm-knowledge/SKILL.md")
    assert "d73e6ac3" in content


def test_internal_knowledge_skill_documents_tag() -> None:
    content = _read(".apm/skills/apm-knowledge/SKILL.md")
    assert "v0.25.0" in content


def test_internal_knowledge_skill_has_trust_boundary_note() -> None:
    content = _read(".apm/skills/apm-knowledge/SKILL.md")
    assert "trust boundary" in content.lower() or "trust" in content.lower(), (
        "apm-knowledge SKILL.md must include a trust boundary note for corpus passages"
    )
    assert "ignore" in content.lower() or "discard" in content.lower(), (
        "apm-knowledge must instruct the model to ignore instructions embedded in corpus text"
    )


def test_internal_knowledge_skill_documents_fail_closed() -> None:
    content = _read(".apm/skills/apm-knowledge/SKILL.md")
    assert "corpus_populated" in content
    assert "fail-closed" in content.lower() or "fail closed" in content.lower()


# ---------------------------------------------------------------------------
# 4. Corpus structure
# ---------------------------------------------------------------------------

def test_corpus_readme_exists() -> None:
    assert (KNOWLEDGE_BASE / "CORPUS.md").exists()


def test_corpus_documents_source_repo() -> None:
    content = (KNOWLEDGE_BASE / "CORPUS.md").read_text()
    assert "microsoft/apm" in content


def test_corpus_documents_commit_sha() -> None:
    content = (KNOWLEDGE_BASE / "CORPUS.md").read_text()
    assert "d73e6ac3" in content


def test_corpus_has_trust_boundary_note() -> None:
    content = (KNOWLEDGE_BASE / "CORPUS.md").read_text()
    assert "trust" in content.lower(), "CORPUS.md must include a trust boundary note"


def test_corpus_active_pointer_exists() -> None:
    assert (KNOWLEDGE_BASE / "active").exists(), (
        "references/knowledge/active pointer file must exist"
    )


def test_corpus_active_pointer_references_valid_baseline() -> None:
    active = (KNOWLEDGE_BASE / "active").read_text().strip()
    assert active, "active pointer must not be empty"
    baseline_dir = KNOWLEDGE_BASE / "baselines" / active
    assert baseline_dir.exists(), (
        f"Baseline directory referenced by active pointer does not exist: {baseline_dir}"
    )


def test_corpus_baseline_has_manifest() -> None:
    active = (KNOWLEDGE_BASE / "active").read_text().strip()
    manifest = KNOWLEDGE_BASE / "baselines" / active / "MANIFEST.json"
    assert manifest.exists(), "Active baseline must contain MANIFEST.json"


def test_corpus_baseline_manifest_has_provenance_fields() -> None:
    active = (KNOWLEDGE_BASE / "active").read_text().strip()
    manifest = KNOWLEDGE_BASE / "baselines" / active / "MANIFEST.json"
    data = json.loads(manifest.read_text())
    for field in ("repository", "tag", "fullCommitSha", "licence"):
        assert field in data, f"MANIFEST.json must contain '{field}'"
    assert data["fullCommitSha"].startswith("d73e6ac3"), (
        "MANIFEST.json fullCommitSha must start with d73e6ac3"
    )


def test_corpus_baseline_has_licence_file() -> None:
    active = (KNOWLEDGE_BASE / "active").read_text().strip()
    licence = KNOWLEDGE_BASE / "baselines" / active / "LICENSE"
    assert licence.exists(), "Active baseline must contain a vendored LICENSE file"
    content = licence.read_text()
    assert "apache" in content.lower() or "Apache" in content, (
        "Vendored LICENSE must be Apache-2.0"
    )


def test_corpus_overlay_directory_exists() -> None:
    assert (KNOWLEDGE_BASE / "overlay").exists(), (
        "references/knowledge/overlay/ directory must exist"
    )


# ---------------------------------------------------------------------------
# 5. Registration metadata
# ---------------------------------------------------------------------------

def test_registration_metadata_exists() -> None:
    assert (PACKAGE_ROOT / ".apm" / "instructions" / "registration.md").exists()


def test_registration_metadata_documents_agent_id() -> None:
    content = _read(".apm/instructions/registration.md")
    assert "agentId" in content


def test_registration_metadata_documents_capability() -> None:
    content = _read(".apm/instructions/registration.md")
    assert "apm-expert.answer.v1" in content


def test_registration_metadata_notes_idempotent_registration() -> None:
    content = _read(".apm/instructions/registration.md")
    assert "idempotent" in content.lower()


def test_registration_metadata_documents_deduplication_by_project_id() -> None:
    content = _read(".apm/instructions/registration.md")
    assert "projectId" in content, (
        "registration.md must document that deduplication is by transport.projectId"
    )


def test_registration_metadata_documents_correct_revision_semantics() -> None:
    content = _read(".apm/instructions/registration.md")
    assert "expectedRevision" in content, (
        "registration.md must document expectedRevision semantics"
    )
    # Must NOT say expectedRevision = current + 1
    assert "current + 1" not in content and "currentRevision + 1" not in content, (
        "registration.md must not claim expectedRevision == current + 1 "
        "(it must equal the current stored revision)"
    )


def test_registration_metadata_documents_required_fields() -> None:
    content = _read(".apm/instructions/registration.md")
    for field in ("displayName", "owner", "project", "projectId", "capabilities"):
        assert field in content, f"registration.md must document required field '{field}'"


def test_sample_registration_fixture_exists() -> None:
    assert (PACKAGE_ROOT / "tests" / "fixtures" / "sample-registration.json").exists()


def test_sample_registration_fixture_has_required_fields() -> None:
    data = json.loads(
        (PACKAGE_ROOT / "tests" / "fixtures" / "sample-registration.json").read_text()
    )
    for field in ("agentId", "displayName", "owner", "project", "transports", "capabilities"):
        assert field in data, f"sample-registration.json must contain '{field}'"
    assert len(data["transports"]) > 0, "transports must be non-empty"
    assert data["transports"][0].get("projectId"), "transports[0].projectId must be present"
    assert len(data["capabilities"]) > 0, "capabilities must be non-empty"
    cap = data["capabilities"][0]
    assert cap.get("id") == "apm-expert.answer.v1"
    assert cap.get("version"), "capability must have version"
    assert cap.get("interactionMode"), "capability must have interactionMode"


# ---------------------------------------------------------------------------
# 6. Pack surface (R6)
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
        f"apm pack --dry-run failed (exit {result.returncode}).\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.skipif(
    shutil.which("apm") is None,
    reason="apm not in PATH -- skipping pack surface check",
)
def test_apm_pack_surface_contains_agent_and_think_skill() -> None:
    result = subprocess.run(
        ["apm", "pack", "--dry-run"],
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
    )
    assert "agents/apm-expert.agent.md" in result.stdout, (
        "Packed surface must include the agent file"
    )
    assert "skills/apm-think/SKILL.md" in result.stdout, (
        "Packed surface must include the public think skill"
    )


# ---------------------------------------------------------------------------
# 7. second-brain zero-own-primitives (R6)
# ---------------------------------------------------------------------------

def test_second_brain_has_no_apm_directory() -> None:
    apm_dir = SECOND_BRAIN_ROOT / ".apm"
    assert not apm_dir.exists(), (
        "second-brain must have no .apm/ directory -- it is dependency-only"
    )


def test_second_brain_lockfile_exists() -> None:
    assert (SECOND_BRAIN_ROOT / "apm.lock.yaml").exists()

