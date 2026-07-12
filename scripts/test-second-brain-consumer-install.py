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

        # Assert both learn and think handler dirs materialised
        all_dirs = [p.name for p in Path(ws).rglob("*") if p.is_dir()]

        learn_found = any("sb-learn-handler" in d for d in all_dirs)
        think_found = any("sb-think-handler" in d for d in all_dirs)

        if not learn_found:
            print(f"FAIL: sb-learn-handler not found. Dirs: {all_dirs[:20]}", file=sys.stderr)
            sys.exit(1)
        if not think_found:
            print(f"FAIL: sb-think-handler not found. Dirs: {all_dirs[:20]}", file=sys.stderr)
            sys.exit(1)

        print("PASS: sb-learn-handler found after consumer install")
        print("PASS: sb-think-handler found after consumer install")


if __name__ == "__main__":
    main()
