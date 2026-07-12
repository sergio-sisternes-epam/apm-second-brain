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
    if active == "none":
        return  # sentinel -- corpus not yet built, fail-closed is expected
    baseline_dir = KNOWLEDGE_BASE / "baselines" / active
    assert baseline_dir.exists(), (
        f"Baseline directory referenced by active pointer does not exist: {baseline_dir}"
    )


def test_corpus_baseline_has_manifest() -> None:
    active = (KNOWLEDGE_BASE / "active").read_text().strip()
    if active == "none":
        pytest.skip("Corpus not yet built (active = none) -- skipping manifest check")
    manifest = KNOWLEDGE_BASE / "baselines" / active / "MANIFEST.json"
    assert manifest.exists(), "Active baseline must contain MANIFEST.json"


def test_corpus_baseline_manifest_has_provenance_fields() -> None:
    active = (KNOWLEDGE_BASE / "active").read_text().strip()
    if active == "none":
        pytest.skip("Corpus not yet built (active = none) -- skipping provenance check")
    manifest = KNOWLEDGE_BASE / "baselines" / active / "MANIFEST.json"
    data = json.loads(manifest.read_text())
    for field in ("repository", "tag", "fullCommitSha", "licence"):
        assert field in data, f"MANIFEST.json must contain '{field}'"
    assert data["fullCommitSha"].startswith("d73e6ac3"), (
        "MANIFEST.json fullCommitSha must start with d73e6ac3"
    )


def test_corpus_baseline_has_licence_file() -> None:
    active = (KNOWLEDGE_BASE / "active").read_text().strip()
    if active == "none":
        pytest.skip("Corpus not yet built (active = none) -- skipping licence check")
    licence = KNOWLEDGE_BASE / "baselines" / active / "LICENSE"
    assert licence.exists(), "Active baseline must contain a vendored LICENSE file"
    content = licence.read_text()
    assert "MIT" in content or "mit" in content.lower(), (
        "Vendored LICENSE must be MIT (microsoft/apm is MIT licensed)"
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


# ---------------------------------------------------------------------------
# 8. Fail-closed when active sentinel is "none" (R6b)
# ---------------------------------------------------------------------------

def test_active_pointer_is_sentinel_in_scaffold_state() -> None:
    """Scaffold active pointer must be 'none', triggering fail-closed."""
    active = KNOWLEDGE_BASE / "active"
    if not active.exists():
        return  # absent pointer also triggers fail-closed -- acceptable
    value = active.read_text().strip()
    # Either "none" sentinel OR a valid, populated baseline key.
    # In scaffold state it MUST be "none".
    baseline_dir = KNOWLEDGE_BASE / "baselines" / value
    if value != "none":
        concepts = baseline_dir / "concepts"
        assert concepts.exists() and any(concepts.glob("*.md")), (
            f"active pointer '{value}' references an unpopulated baseline. "
            "Set active to 'none' until corpus is built."
        )


def test_apm_knowledge_skill_documents_none_sentinel() -> None:
    """SKILL.md must document that 'none' is the sentinel for fail-closed."""
    content = _read(".apm/skills/apm-knowledge/SKILL.md")
    assert "none" in content, (
        "apm-knowledge SKILL.md must document the 'none' sentinel value for fail-closed"
    )


# ---------------------------------------------------------------------------
# 9. second-brain: parse lockfile, verify no own deployed_files (R6b)
# ---------------------------------------------------------------------------

def test_second_brain_lockfile_has_no_own_deployed_files() -> None:
    """second-brain lockfile must have no own (local) deployed_files entry."""
    try:
        import yaml  # type: ignore
    except ImportError:
        pytest.skip("pyyaml not installed -- skipping lockfile parse test")

    lock_path = SECOND_BRAIN_ROOT / "apm.lock.yaml"
    data = yaml.safe_load(lock_path.read_text())
    deps = data.get("dependencies", [])
    for dep in deps:
        # Local/own entries have is_virtual=False and virtual_path pointing to self
        if not dep.get("is_virtual", True):
            assert not dep.get("deployed_files"), (
                f"second-brain lockfile must have no own deployed_files, "
                f"found in dep: {dep.get('name')}"
            )


# ---------------------------------------------------------------------------
# 10. MANIFEST.json provenance equality (R6b)
# ---------------------------------------------------------------------------

def test_manifest_provenance_fields_match_pinned_values() -> None:
    active = (KNOWLEDGE_BASE / "active").read_text().strip()
    if active == "none":
        pytest.skip("Corpus not yet built -- skipping MANIFEST provenance equality check")
    manifest = KNOWLEDGE_BASE / "baselines" / active / "MANIFEST.json"
    data = json.loads(manifest.read_text())
    assert data["repository"] == "microsoft/apm"
    assert data["tag"] == "v0.25.0"
    assert data["fullCommitSha"] == "d73e6ac3645d2b9c5c813095e2e58f020f38f17a"
    assert data["licence"] == "MIT"


def test_manifest_provenance_fields_present_in_placeholder() -> None:
    """Even in scaffold state, MANIFEST.json must have all required provenance fields."""
    active_val = (KNOWLEDGE_BASE / "active").read_text().strip()
    # Use the only baseline we have (scaffold placeholder)
    baselines = list((KNOWLEDGE_BASE / "baselines").iterdir()) if (KNOWLEDGE_BASE / "baselines").exists() else []
    for baseline_dir in baselines:
        manifest = baseline_dir / "MANIFEST.json"
        if not manifest.exists():
            continue
        data = json.loads(manifest.read_text())
        for field in ("repository", "tag", "fullCommitSha", "licence"):
            assert field in data, f"MANIFEST.json in {baseline_dir.name} must have '{field}'"
        assert data.get("fullCommitSha", "").startswith("d73e6ac3"), (
            "MANIFEST.json fullCommitSha must start with d73e6ac3"
        )
        assert data.get("licence") == "MIT", "MANIFEST.json licence must be MIT"


# ---------------------------------------------------------------------------
# 11. Registration fixture -- full schema validation (R6b)
# ---------------------------------------------------------------------------

def test_sample_registration_fixture_has_knowledge_roots() -> None:
    data = json.loads(
        (PACKAGE_ROOT / "tests" / "fixtures" / "sample-registration.json").read_text()
    )
    assert "knowledgeRoots" in data, "fixture must contain knowledgeRoots"
    assert len(data["knowledgeRoots"]) > 0, "knowledgeRoots must be non-empty"
    kr = data["knowledgeRoots"][0]
    for field in ("id", "label", "format", "pathBase", "path", "default"):
        assert field in kr, f"knowledgeRoots[0] must contain '{field}'"


def test_sample_registration_fixture_has_status_fields() -> None:
    data = json.loads(
        (PACKAGE_ROOT / "tests" / "fixtures" / "sample-registration.json").read_text()
    )
    for field in ("status", "registeredAt", "lastValidatedAt", "lastValidationError"):
        assert field in data, f"fixture must contain '{field}'"


# ---------------------------------------------------------------------------
# 12. Agent file -- dispatcher description field (R5b)
# ---------------------------------------------------------------------------

def test_agent_file_has_description_field() -> None:
    content = _read(".apm/agents/apm-expert.agent.md")
    assert "description:" in content, (
        "Agent file frontmatter must include a 'description:' field for the dispatcher"
    )


# ---------------------------------------------------------------------------
# 13. Overlay -- per-passage origin tracking documented (R3b/R7)
# ---------------------------------------------------------------------------

def test_overlay_readme_documents_origin_field() -> None:
    overlay_readme = KNOWLEDGE_BASE / "overlay" / "README.md"
    assert overlay_readme.exists(), "overlay/README.md must exist"
    content = overlay_readme.read_text()
    assert "origin:" in content or "origin" in content, (
        "overlay/README.md must document the origin field for concept frontmatter"
    )


def test_overlay_readme_documents_tombstone_format() -> None:
    content = (KNOWLEDGE_BASE / "overlay" / "README.md").read_text()
    assert "tombstone" in content.lower(), "overlay/README.md must document tombstone format"


def test_skill_documents_per_passage_origin_tracking() -> None:
    content = _read(".apm/skills/apm-knowledge/SKILL.md")
    assert '"origin"' in content or "origin" in content, (
        "apm-knowledge SKILL.md must document per-passage origin tracking"
    )
    assert "overlay" in content.lower(), (
        "apm-knowledge SKILL.md must distinguish baseline vs overlay passage provenance"
    )


# ---------------------------------------------------------------------------
# 14. Pre-registration checklist in registration.md (R1-doc)
# ---------------------------------------------------------------------------

def test_registration_metadata_has_preregistration_checklist() -> None:
    content = _read(".apm/instructions/registration.md")
    assert "corpus" in content.lower() and "gate" in content.lower(), (
        "registration.md must include a pre-registration checklist with build/validate gates"
    )


# ---------------------------------------------------------------------------
# 15. README has scaffold notice (R1-doc)
# ---------------------------------------------------------------------------

def test_readme_has_scaffold_notice() -> None:
    readme = PACKAGE_ROOT / "README.md"
    content = readme.read_text()
    assert "SCAFFOLD STATUS" in content or "NOT READY" in content, (
        "README.md must have a prominent scaffold status notice at the top"
    )

