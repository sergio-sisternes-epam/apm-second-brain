"""
Conformance tests for the second-brain meta-package.

Verifies that:
1. second-brain has no owned primitives (dependency-only)
2. apm.yml declares exactly second-brain-learn and second-brain-think as dependencies
3. apm.lock.yaml deploys learn+think trees (not empty)
4. No package-local generated .github/ or .agents/ or .claude/ dirs are committed
"""

import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
PKG_ROOT = REPO_ROOT / "packages" / "second-brain"


def test_no_own_primitives():
    """second-brain must have zero owned primitives -- dependency-only."""
    apm_dir = PKG_ROOT / ".apm"
    assert not apm_dir.exists() or list(apm_dir.rglob("SKILL.md")) == [], (
        "second-brain must not contain any .apm/skills/ -- it is dependency-only"
    )
    assert not apm_dir.exists() or list(apm_dir.rglob("*.agent.md")) == [], (
        "second-brain must not contain any .apm/agents/ -- it is dependency-only"
    )


def test_no_generated_targets_committed():
    """Generated .github/, .agents/, .claude/ must not be committed."""
    generated_dirs = [
        PKG_ROOT / ".github",
        PKG_ROOT / ".agents",
        PKG_ROOT / ".claude",
    ]
    for d in generated_dirs:
        assert not d.exists(), (
            f"Generated target dir must not be committed: {d.relative_to(REPO_ROOT)}. "
            "Add it to .gitignore and run: git rm -r --cached " + str(d.relative_to(REPO_ROOT))
        )


def test_dependencies_declare_learn_and_think():
    """apm.yml must declare second-brain-learn and second-brain-think as deps."""
    apm_yml = PKG_ROOT / "apm.yml"
    assert apm_yml.exists(), "apm.yml must exist"
    with open(apm_yml) as f:
        manifest = yaml.safe_load(f)
    deps = manifest.get("dependencies", {}).get("apm", [])
    dep_str = str(deps)
    assert "second-brain-learn" in dep_str, "apm.yml must declare second-brain-learn dependency"
    assert "second-brain-think" in dep_str, "apm.yml must declare second-brain-think dependency"


def test_lock_deploys_learn_and_think():
    """apm.lock.yaml must deploy second-brain-learn and second-brain-think trees."""
    lock_path = PKG_ROOT / "apm.lock.yaml"
    assert lock_path.exists(), "apm.lock.yaml must exist"
    lock_content = lock_path.read_text(encoding="utf-8")
    assert "second-brain-learn" in lock_content, (
        "apm.lock.yaml must contain second-brain-learn deployment"
    )
    assert "second-brain-think" in lock_content, (
        "apm.lock.yaml must contain second-brain-think deployment"
    )
    assert "sb-learn-handler" in lock_content, (
        "apm.lock.yaml must deploy sb-learn-handler from second-brain-learn"
    )
    assert "sb-think-handler" in lock_content, (
        "apm.lock.yaml must deploy sb-think-handler from second-brain-think"
    )


def test_dependency_pins_use_full_sha():
    """Dependency pins must use full 40-char SHA."""
    import re
    apm_yml = PKG_ROOT / "apm.yml"
    content = apm_yml.read_text(encoding="utf-8")
    sha_refs = re.findall(r'#([0-9a-f]+)', content)
    for sha in sha_refs:
        assert len(sha) == 40, (
            f"Dependency pin uses short SHA '{sha}' -- must be full 40-char SHA"
        )
