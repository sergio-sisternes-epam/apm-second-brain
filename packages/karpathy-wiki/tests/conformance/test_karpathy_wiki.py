"""
Conformance tests for the karpathy-wiki package.

Verifies the sample-wiki fixture and the internal skill files against
the Karpathy wiki layout rules and OKF v0.1 constraints.

Run with: pytest packages/karpathy-wiki/tests/conformance/
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
PKG_ROOT = REPO_ROOT / "packages" / "karpathy-wiki"
SAMPLE_WIKI = PKG_ROOT / "tests" / "fixtures" / "sample-wiki"
SKILLS_DIR = PKG_ROOT / ".apm" / "skills"

DISABLED_HEADER = "<!-- direct-user-invocation: disabled -->"
LOG_DATE_PATTERN = re.compile(r"^## \d{4}-\d{2}-\d{2}$", re.MULTILINE)
WIKILINK_PATTERN = re.compile(r"\[\[.+?\]\]")

REQUIRED_FRONTMATTER_FIELDS = {"id", "title", "type", "created", "modified"}

INTERNAL_SKILL_NAMES = [
    "kw-wiki-init",
    "kw-wiki-ingest",
    "kw-wiki-query",
    "kw-wiki-index",
    "kw-wiki-log",
    "kw-wiki-lint",
    "kw-wiki-archive",
]


def _parse_frontmatter(content: str) -> dict:
    """Extract key: value pairs from the first YAML frontmatter block."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, val = line.partition(":")
            fields[key.strip()] = val.strip()
    return fields


# ---------------------------------------------------------------------------
# 1. SCHEMA.md exists alongside wiki/, not inside it
# ---------------------------------------------------------------------------

def test_schema_md_alongside_wiki_not_inside():
    schema_alongside = SAMPLE_WIKI / "SCHEMA.md"
    schema_inside = SAMPLE_WIKI / "wiki" / "SCHEMA.md"
    assert schema_alongside.exists(), (
        "SCHEMA.md must exist alongside wiki/ in sample-wiki"
    )
    assert not schema_inside.exists(), (
        "SCHEMA.md must NOT appear inside wiki/"
    )


# ---------------------------------------------------------------------------
# 2. wiki/ contains only OKF-conformant files (no Karpathy-specific files)
# ---------------------------------------------------------------------------

def test_no_karpathy_files_inside_wiki():
    wiki_dir = SAMPLE_WIKI / "wiki"
    assert wiki_dir.exists(), "wiki/ directory must exist in sample-wiki"
    # SCHEMA.md must not be inside wiki/
    assert not (wiki_dir / "SCHEMA.md").exists(), (
        "SCHEMA.md must NOT be inside wiki/"
    )
    # raw/ must not be inside wiki/
    assert not (wiki_dir / "raw").exists(), (
        "raw/ directory must NOT be inside wiki/"
    )


# ---------------------------------------------------------------------------
# 3. All concept files have required OKF frontmatter
# ---------------------------------------------------------------------------

def _get_concept_files():
    concepts_dir = SAMPLE_WIKI / "wiki" / "concepts"
    if not concepts_dir.exists():
        return []
    return [
        f for f in concepts_dir.glob("*.md")
        if f.name != "index.md"
    ]


@pytest.mark.parametrize("concept_file", _get_concept_files())
def test_concept_frontmatter_fields(concept_file: Path):
    content = concept_file.read_text(encoding="utf-8")
    fields = _parse_frontmatter(content)
    missing = REQUIRED_FRONTMATTER_FIELDS - set(fields.keys())
    assert not missing, (
        f"{concept_file.name} is missing required frontmatter fields: {missing}"
    )
    for field in REQUIRED_FRONTMATTER_FIELDS:
        assert fields.get(field), (
            f"{concept_file.name}: frontmatter field '{field}' must not be empty"
        )


# ---------------------------------------------------------------------------
# 4. index.md and log.md present in wiki/
# ---------------------------------------------------------------------------

def test_index_md_present():
    assert (SAMPLE_WIKI / "wiki" / "index.md").exists(), (
        "wiki/index.md must be present in sample-wiki"
    )


def test_log_md_present():
    assert (SAMPLE_WIKI / "wiki" / "log.md").exists(), (
        "wiki/log.md must be present in sample-wiki"
    )


# ---------------------------------------------------------------------------
# 5. log.md uses newest-first ISO date groups
# ---------------------------------------------------------------------------

def test_log_md_date_groups_format_and_order():
    log_path = SAMPLE_WIKI / "wiki" / "log.md"
    content = log_path.read_text(encoding="utf-8")
    date_headings = LOG_DATE_PATTERN.findall(content)
    assert date_headings, "log.md must contain at least one ## YYYY-MM-DD heading"
    dates = [h.replace("## ", "") for h in date_headings]
    assert dates == sorted(dates, reverse=True), (
        f"log.md date headings must be newest-first, got: {dates}"
    )


# ---------------------------------------------------------------------------
# 6. No wikilinks in any wiki/ file
# ---------------------------------------------------------------------------

def _get_all_wiki_files():
    wiki_dir = SAMPLE_WIKI / "wiki"
    if not wiki_dir.exists():
        return []
    return list(wiki_dir.rglob("*.md"))


@pytest.mark.parametrize("wiki_file", _get_all_wiki_files())
def test_no_wikilinks(wiki_file: Path):
    content = wiki_file.read_text(encoding="utf-8")
    matches = WIKILINK_PATTERN.findall(content)
    assert not matches, (
        f"{wiki_file.relative_to(SAMPLE_WIKI)} contains wikilinks: {matches}"
    )


# ---------------------------------------------------------------------------
# 7. Internal skills all have the disabled header as first line
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("skill_name", INTERNAL_SKILL_NAMES)
def test_internal_skill_disabled_header(skill_name: str):
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    assert skill_path.exists(), f"Internal skill not found: {skill_path}"
    first_line = skill_path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.strip() == DISABLED_HEADER, (
        f"{skill_name}/SKILL.md: disabled header must be the first line, "
        f"got: {first_line!r}"
    )


# ---------------------------------------------------------------------------
# 8. raw/ is outside wiki/
# ---------------------------------------------------------------------------

def test_raw_directory_outside_wiki():
    raw_dir = SAMPLE_WIKI / "raw"
    raw_inside_wiki = SAMPLE_WIKI / "wiki" / "raw"
    assert raw_dir.exists(), "raw/ must exist in sample-wiki"
    assert not raw_inside_wiki.exists(), "raw/ must NOT appear inside wiki/"
