"""
Conformance tests for the knowledge-graph canvas extension.

Verifies the extension file, canvas skill, and canvas awareness instruction
against the Wave 3 requirements.

Run with: pytest packages/karpathy-wiki/tests/conformance/
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
PKG_ROOT = REPO_ROOT / "packages" / "karpathy-wiki"

EXTENSION_PATH = PKG_ROOT / ".apm" / "extensions" / "knowledge-graph" / "extension.mjs"
CANVAS_SKILL_PATH = PKG_ROOT / ".apm" / "skills" / "knowledge-graph-canvas" / "SKILL.md"
CANVAS_INSTRUCTION_PATH = PKG_ROOT / ".apm" / "instructions" / "canvas-awareness.md"

DISABLED_HEADER = "<!-- direct-user-invocation: disabled -->"

# The canvas skill is public (user-invokable). These are the expected public
# skills for the karpathy-wiki package; they must NOT carry the disabled header.
EXPECTED_PUBLIC_SKILLS = [
    "knowledge-graph-canvas",
]


# ---------------------------------------------------------------------------
# 1. Extension file exists at the correct path
# ---------------------------------------------------------------------------

def test_extension_file_exists():
    assert EXTENSION_PATH.exists(), (
        f"Canvas extension not found at: {EXTENSION_PATH}"
    )


# ---------------------------------------------------------------------------
# 2. Canvas skill exists and does NOT have the disabled header (it is public)
# ---------------------------------------------------------------------------

def test_canvas_skill_exists():
    assert CANVAS_SKILL_PATH.exists(), (
        f"Canvas skill not found at: {CANVAS_SKILL_PATH}"
    )


def test_canvas_skill_is_public_no_disabled_header():
    content = CANVAS_SKILL_PATH.read_text(encoding="utf-8")
    assert DISABLED_HEADER not in content, (
        f"Canvas skill must NOT carry the disabled header -- it is a public skill. "
        f"Found header in: {CANVAS_SKILL_PATH}"
    )


# ---------------------------------------------------------------------------
# 3. Canvas skill SKILL.md does not mention Claude Code as a supported target
# ---------------------------------------------------------------------------

def test_canvas_skill_does_not_claim_claude_code_support():
    content = CANVAS_SKILL_PATH.read_text(encoding="utf-8")
    # The skill should document that Claude Code is NOT supported for the canvas UI.
    # It must not claim the canvas is available in Claude Code.
    # We check that the word "Claude Code" is only mentioned in the context of
    # unavailability, not as a supported target.
    lines = content.splitlines()
    for line in lines:
        low = line.lower()
        if "claude code" in low:
            # Accept ONLY lines that explicitly deny canvas support for Claude Code.
            # Phrases like "only available" or "explain" are deliberately excluded
            # because they can appear in positive-sounding contexts.
            genuinely_negative = any(phrase in low for phrase in [
                "not supported",
                "not available",
                "unavailable",
                "cannot",
                "not in claude",
                "non-copilot",
                "no canvas",
                "(not supported",
            ])
            assert genuinely_negative, (
                f"Canvas skill mentions Claude Code in a way that may imply support. "
                f"Only mention it to state explicitly that it is unavailable. "
                f"Offending line: {line!r}"
            )


# ---------------------------------------------------------------------------
# 4. Canvas awareness instruction exists
# ---------------------------------------------------------------------------

def test_canvas_awareness_instruction_exists():
    assert CANVAS_INSTRUCTION_PATH.exists(), (
        f"Canvas awareness instruction not found at: {CANVAS_INSTRUCTION_PATH}"
    )


# ---------------------------------------------------------------------------
# 5. extension.mjs is read-only: no file-write operations in the source
# ---------------------------------------------------------------------------

WRITE_PATTERNS = [
    "fs.writeFile",
    "writeFileSync",
    "fs.appendFile",
    "appendFileSync",
    "fs.open(",
    ".write(",
    "createWriteStream",
]


@pytest.mark.parametrize("pattern", WRITE_PATTERNS)
def test_extension_has_no_file_write_operations(pattern: str):
    content = EXTENSION_PATH.read_text(encoding="utf-8")
    # .write( is used for HTTP response .write() -- only flag fs-related .write(
    if pattern == ".write(":
        # Check for fs.createWriteStream().write( or similar; res.write() is HTTP
        # We flag only if combined with stream or file context
        assert "createWriteStream" not in content, (
            f"extension.mjs must not use createWriteStream (read-only constraint)."
        )
        return
    assert pattern not in content, (
        f"extension.mjs must not contain file-write operation: {pattern!r}. "
        "The canvas is read-only."
    )


# ---------------------------------------------------------------------------
# 6. extension.mjs has path canonicalisation
# ---------------------------------------------------------------------------

def test_extension_has_path_canonicalisation():
    content = EXTENSION_PATH.read_text(encoding="utf-8")
    has_canonicalise = (
        "resolve(" in content or
        "realpath" in content or
        "normalize(" in content
    )
    assert has_canonicalise, (
        "extension.mjs must implement path canonicalisation (resolve, realpath, "
        "or normalize) to prevent path traversal."
    )


# ---------------------------------------------------------------------------
# 7. extension.mjs exports a default object (joinSession call present)
# ---------------------------------------------------------------------------

def test_extension_exports_default_via_join_session():
    content = EXTENSION_PATH.read_text(encoding="utf-8")
    assert "joinSession" in content, (
        "extension.mjs must call joinSession() -- the APM 0.25 canvas entry point."
    )
    assert "createCanvas" in content, (
        "extension.mjs must call createCanvas() to declare the canvas."
    )


# ---------------------------------------------------------------------------
# 8. extension.mjs excludes archived concepts from the normal graph view
# ---------------------------------------------------------------------------

def test_archived_concepts_excluded_from_normal_graph():
    """Regression: applyFilters must hide status=archived nodes by default.

    Implementation evidence: the filter engine guards on ``includeArchived``
    and filters out nodes whose status is ``"archived"`` unless that flag is
    explicitly set.  We verify two things from the source:
    (a) the source contains a check against the ``"archived"`` status string, and
    (b) the guard references ``includeArchived`` so an explicit opt-in is possible.
    """
    content = EXTENSION_PATH.read_text(encoding="utf-8")
    assert '"archived"' in content or "'archived'" in content, (
        "extension.mjs must exclude archived concepts from the default graph view. "
        'Expected a check against the string "archived" in applyFilters.'
    )
    assert "includeArchived" in content, (
        "extension.mjs must expose an includeArchived opt-in flag so callers can "
        "explicitly request archived concepts when needed."
    )
