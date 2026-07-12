#!/usr/bin/env python3
"""
External consumer integration test for second-brain meta-package.

Installs second-brain in an isolated empty workspace using the exact
commit SHA under test, then asserts both learn and think dependency
trees materialise (sb-learn-handler and sb-think-handler present).

Usage: python3 scripts/test-second-brain-consumer-install.py <sha>
"""

import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "sergio-sisternes-epam/apm-second-brain"


def main():
    if len(sys.argv) < 2:
        print("Usage: test-second-brain-consumer-install.py <commit-sha>", file=sys.stderr)
        sys.exit(1)

    sha = sys.argv[1]
    if len(sha) != 40 or not all(c in "0123456789abcdef" for c in sha):
        print(f"Expected a full 40-char lowercase hex SHA, got: {sha!r}", file=sys.stderr)
        sys.exit(1)

    print(f"Testing second-brain consumer install at {sha[:8]}...")

    with tempfile.TemporaryDirectory() as ws:
        # Consumer apm.yml pinned to the exact commit under test
        apm_yml = Path(ws) / "apm.yml"
        apm_yml.write_text(
            "name: consumer-test\n"
            "version: 0.1.0\n"
            "dependencies:\n"
            "  apm:\n"
            f"    - {REPO}/packages/second-brain#{sha}\n"
            "includes: auto\n"
            "scripts: {}\n"
        )

        print(f"  workspace: {ws}")
        print(f"  running: apm install --target claude")

        r = subprocess.run(
            ["apm", "install", "--target", "claude"],
            cwd=ws,
            capture_output=True,
            text=True,
            timeout=180,
        )

        if r.returncode != 0:
            print(r.stdout)
            print(r.stderr, file=sys.stderr)
            sys.exit(f"apm install failed with exit code {r.returncode}")

        # Assert exact canonical deployed paths for --target claude.
        # APM 0.25 deploys claude-target skills to .claude/skills/<name>/SKILL.md.
        # Using exact paths (not rglob across all dirs) prevents apm_modules/
        # or other non-target directories from satisfying the assertion.
        ws_path = Path(ws)
        learn_skill = ws_path / ".claude" / "skills" / "sb-learn-handler" / "SKILL.md"
        think_skill = ws_path / ".claude" / "skills" / "sb-think-handler" / "SKILL.md"

        if not learn_skill.is_file():
            sys.exit(
                f"FAIL: sb-learn-handler/SKILL.md not found at expected claude target path.\n"
                f"  Expected: {learn_skill}\n"
                f"  .claude/skills/ contents: {sorted(p.name for p in (ws_path / '.claude' / 'skills').iterdir()) if (ws_path / '.claude' / 'skills').exists() else 'directory not found'}"
            )
        if not think_skill.is_file():
            sys.exit(
                f"FAIL: sb-think-handler/SKILL.md not found at expected claude target path.\n"
                f"  Expected: {think_skill}\n"
                f"  .claude/skills/ contents: {sorted(p.name for p in (ws_path / '.claude' / 'skills').iterdir()) if (ws_path / '.claude' / 'skills').exists() else 'directory not found'}"
            )

        # Also verify the paths are regular files inside the workspace
        # (not symlinks escaping the workspace).
        assert learn_skill.resolve().is_relative_to(ws_path.resolve()), (
            f"sb-learn-handler/SKILL.md resolves outside workspace: {learn_skill.resolve()}"
        )
        assert think_skill.resolve().is_relative_to(ws_path.resolve()), (
            f"sb-think-handler/SKILL.md resolves outside workspace: {think_skill.resolve()}"
        )

        print(f"PASS: sb-learn-handler/SKILL.md at {learn_skill.relative_to(ws_path)}")
        print(f"PASS: sb-think-handler/SKILL.md at {think_skill.relative_to(ws_path)}")


if __name__ == "__main__":
    main()
