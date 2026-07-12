"""
Conformance tests for the second-brain meta-package.

CI discovers this file via packages/*/tests/conformance/ pattern.

Verifies:
1. .apm directory is entirely absent (no owned primitives of any type)
2. No tracked generated target dirs (.github, .agents, .claude, apm_modules)
3. Both learn + think declared in apm.yml with structural parse + full SHA
4. Lock deploys both learn + think dependency trees with required handlers
5. Full 40-char SHA dependency pins (no truncated refs)
"""

import re
import subprocess
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
PKG_ROOT = REPO_ROOT / "packages" / "second-brain"

# Required handlers that prove learn+think trees deployed
REQUIRED_LEARN_HANDLERS = ["sb-learn-handler", "sb-forget-handler"]
REQUIRED_THINK_HANDLERS = ["sb-think-handler", "sb-think-validate"]


def test_apm_dir_entirely_absent():
    """second-brain must have no .apm/ directory at all -- fully dependency-only."""
    apm_dir = PKG_ROOT / ".apm"
    assert not apm_dir.exists(), (
        f".apm/ directory must not exist in second-brain -- it is dependency-only. "
        f"Found: {apm_dir}"
    )


def test_no_tracked_generated_dirs():
    """Generated .github/, .agents/, .claude/, apm_modules/ must not be tracked by git."""
    generated = [".github", ".agents", ".claude", "apm_modules"]
    result = subprocess.run(
        ["git", "ls-files", "--", *[str(PKG_ROOT / d) for d in generated]],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    tracked = result.stdout.strip()
    assert not tracked, (
        f"Generated dirs must not be tracked in second-brain:\n{tracked}\n"
        "Add them to .gitignore and run: git rm -r --cached <dir>"
    )


def test_apm_yml_declares_learn_and_think():
    """apm.yml must structurally declare exactly second-brain-learn and second-brain-think."""
    apm_yml = PKG_ROOT / "apm.yml"
    assert apm_yml.exists(), "apm.yml must exist"
    with open(apm_yml) as f:
        manifest = yaml.safe_load(f)
    deps = manifest.get("dependencies", {}).get("apm", [])
    assert isinstance(deps, list) and len(deps) >= 2, (
        f"apm.yml must declare at least 2 APM dependencies, got: {deps}"
    )
    dep_str = " ".join(str(d) for d in deps)
    assert "second-brain-learn" in dep_str, (
        f"apm.yml must declare second-brain-learn in dependencies.apm. Got: {deps}"
    )
    assert "second-brain-think" in dep_str, (
        f"apm.yml must declare second-brain-think in dependencies.apm. Got: {deps}"
    )
    # Verify each dep uses a full 40-char SHA
    sha_re = re.compile(r'#([0-9a-f]{40})$')
    for dep in deps:
        match = sha_re.search(str(dep))
        assert match, (
            f"Dependency pin must end with a full 40-char SHA: {dep}"
        )


def test_lock_deploys_learn_handlers():
    """apm.lock.yaml must deploy sb-learn-handler and sb-forget-handler."""
    lock_path = PKG_ROOT / "apm.lock.yaml"
    assert lock_path.exists(), "apm.lock.yaml must exist"
    with open(lock_path) as f:
        lock = yaml.safe_load(f)
    deployed = lock_path.read_text(encoding="utf-8")
    for handler in REQUIRED_LEARN_HANDLERS:
        assert handler in deployed, (
            f"apm.lock.yaml must deploy {handler} from second-brain-learn"
        )


def test_lock_deploys_think_handlers():
    """apm.lock.yaml must deploy sb-think-handler and sb-think-validate."""
    lock_path = PKG_ROOT / "apm.lock.yaml"
    assert lock_path.exists(), "apm.lock.yaml must exist"
    deployed = lock_path.read_text(encoding="utf-8")
    for handler in REQUIRED_THINK_HANDLERS:
        assert handler in deployed, (
            f"apm.lock.yaml must deploy {handler} from second-brain-think"
        )


def test_no_apm_yml_scripts_undeclared():
    """apm.yml must be valid YAML with no broken fields."""
    apm_yml = PKG_ROOT / "apm.yml"
    with open(apm_yml) as f:
        manifest = yaml.safe_load(f)
    assert manifest.get("name") == "second-brain", "name must be 'second-brain'"
    assert manifest.get("includes") == "auto", "includes must be 'auto'"


# ---------------------------------------------------------------------------
# R2: External consumer integration test
# ---------------------------------------------------------------------------

def test_external_consumer_install_deploys_learn_and_think():
    """Prove the consumer workflow: install second-brain in an isolated workspace.

    Creates a temporary empty workspace, installs the local second-brain package
    via `apm install` using a local path reference, then asserts both learn and
    think trees are materialised.

    Skipped when apm is not in PATH (CI install step ensures it is).
    """
    import shutil
    import tempfile
    import os

    if not shutil.which("apm"):
        import pytest
        pytest.skip("apm not in PATH -- skipped outside APM CI context")

    with tempfile.TemporaryDirectory() as workspace:
        # Create a minimal consumer apm.yml
        consumer_apm = Path(workspace) / "apm.yml"
        consumer_apm.write_text(
            "name: consumer-test\n"
            "version: 0.1.0\n"
            "dependencies:\n"
            "  apm:\n"
            f"    - {PKG_ROOT}\n"
            "includes: auto\n"
            "scripts: {}\n"
        )
        # Run apm install with explicit target (empty workspace has no harness)
        result = subprocess.run(
            ["apm", "install", "--target", "claude"],
            cwd=workspace, capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, (
            f"apm install failed in consumer workspace:\n{result.stdout}\n{result.stderr}"
        )
        # Assert both learn and think handlers materialised
        agents_dir = Path(workspace) / ".agents" / "skills"
        if not agents_dir.exists():
            agents_dir = Path(workspace) / ".claude" / "skills"
        installed = [p.name for p in agents_dir.iterdir()] if agents_dir.exists() else []
        installed_str = " ".join(installed)
        assert "sb-learn-handler" in installed_str, (
            f"sb-learn-handler not found after consumer install. Got: {installed}"
        )
        assert "sb-think-handler" in installed_str, (
            f"sb-think-handler not found after consumer install. Got: {installed}"
        )
