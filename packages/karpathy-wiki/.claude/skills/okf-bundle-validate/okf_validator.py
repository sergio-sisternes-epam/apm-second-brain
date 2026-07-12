#!/usr/bin/env python3
"""
okf_validator.py -- OKF v0.1 bundle conformance validator.

Validates a directory against the Open Knowledge Format v0.1 specification
(GoogleCloudPlatform/knowledge-catalog @ ee67a5ca, okf/SPEC.md, Apache-2.0).

Usage:
    python3 okf_validator.py <bundle-path>

Output: JSON to stdout.
Exit codes:
    0 -- conformant
    1 -- non-conformant (rule violations)
    2 -- script error (bad arguments, unreadable path)
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RESERVED_NAMES = {"index.md", "log.md"}
DATE_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")
LIST_ENTRY_RE = re.compile(r"^\*\s+\[.+\]\(.+\)\s+-\s+")


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    """Return (frontmatter_dict, body) or (None, full_text) if no frontmatter."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, text
    close = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            close = i
            break
    if close is None:
        return None, text
    yaml_block = "".join(lines[1:close])
    body = "".join(lines[close + 1:])
    try:
        import yaml  # type: ignore[import]
        data = yaml.safe_load(yaml_block) or {}
    except Exception:
        # If PyYAML is unavailable, do a minimal key extraction
        data = _minimal_yaml_parse(yaml_block)
    return data, body


def _minimal_yaml_parse(block: str) -> dict[str, Any]:
    """Very small YAML parser for simple key: value lines (no PyYAML fallback)."""
    result: dict[str, Any] = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


# ---------------------------------------------------------------------------
# Rule checkers
# ---------------------------------------------------------------------------

RuleResult = dict[str, str]  # {rule, status, message}


def _pass(rule: str, msg: str) -> RuleResult:
    return {"rule": rule, "status": "pass", "message": msg}


def _fail(rule: str, msg: str) -> RuleResult:
    return {"rule": rule, "status": "fail", "message": msg}


def _warn(rule: str, msg: str) -> RuleResult:
    return {"rule": rule, "status": "warn", "message": msg}


def check_concept(path: Path, rel: str) -> list[RuleResult]:
    results: list[RuleResult] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        return [_fail("C0-readable", f"Cannot read file: {exc}")]

    fm, _ = parse_frontmatter(text)

    # C1 -- frontmatter present
    if fm is None:
        results.append(_fail("C1-frontmatter-present", "No YAML frontmatter block found."))
        # C2 cannot be checked without frontmatter
        results.append(_fail("C2-type-required", "Cannot check: frontmatter absent."))
    else:
        results.append(_pass("C1-frontmatter-present", "Frontmatter block found."))
        # C2 -- type required and non-empty
        type_val = fm.get("type", "")
        if not type_val or not str(type_val).strip():
            results.append(_fail("C2-type-required", "Frontmatter `type` field is missing or empty."))
        else:
            results.append(_pass("C2-type-required", f"type = {type_val!r}"))

        # W1 -- title recommended
        if not fm.get("title"):
            results.append(_warn("W1-title-recommended", "`title` field is recommended by OKF v0.1 but absent."))
        else:
            results.append(_pass("W1-title-recommended", f"title = {fm['title']!r}"))

        # W2 -- timestamp recommended
        if not fm.get("timestamp"):
            results.append(_warn("W2-timestamp-recommended", "`timestamp` field is recommended by OKF v0.1 but absent."))
        else:
            results.append(_pass("W2-timestamp-recommended", f"timestamp = {fm['timestamp']!r}"))

    return results


def check_index(path: Path, rel: str, is_root: bool) -> list[RuleResult]:
    results: list[RuleResult] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        return [_fail("C0-readable", f"Cannot read file: {exc}")]

    fm, body = parse_frontmatter(text)

    if is_root:
        # Root index.md may have frontmatter with okf_version
        if fm is not None:
            okf_ver = fm.get("okf_version", "")
            if okf_ver:
                results.append(_pass("I2-index-root-okf-version", f"okf_version = {okf_ver!r}"))
            else:
                results.append(_warn("I2-index-root-okf-version", "Root index.md has frontmatter but no `okf_version` key."))
        else:
            results.append(_warn("I2-index-root-okf-version", "Root index.md SHOULD declare `okf_version: \"0.1\"` in frontmatter."))
    else:
        # Non-root index.md MUST NOT have frontmatter
        if fm is not None:
            results.append(_fail("I1-index-no-frontmatter", "Non-root index.md MUST NOT have a frontmatter block (OKF v0.1 §6)."))
        else:
            results.append(_pass("I1-index-no-frontmatter", "No frontmatter -- correct for non-root index.md."))

    # I3 -- index should have at least one list entry
    check_text = body if fm is not None else text
    has_list = any(LIST_ENTRY_RE.match(line) for line in check_text.splitlines())
    if has_list:
        results.append(_pass("I3-index-has-list-entries", "At least one `* [...](...) -` list entry found."))
    else:
        results.append(_warn("I3-index-has-list-entries", "index.md body SHOULD contain at least one `* [Title](url) - desc` entry."))

    return results


def check_log(path: Path, rel: str) -> list[RuleResult]:
    results: list[RuleResult] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        return [_fail("C0-readable", f"Cannot read file: {exc}")]

    dates: list[date] = []
    bad_headings: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            m = DATE_HEADING_RE.match(line)
            if m:
                try:
                    d = date.fromisoformat(m.group(1))
                    dates.append(d)
                except ValueError:
                    bad_headings.append(line.strip())
            else:
                bad_headings.append(line.strip())

    # L1 -- all ## headings must be valid ISO dates
    if bad_headings:
        results.append(_fail("L1-log-date-headings",
                             f"log.md has non-ISO-date ## headings: {bad_headings}"))
    else:
        results.append(_pass("L1-log-date-headings", "All ## headings are valid ISO 8601 dates."))

    # L2 -- dates must be newest-first (descending)
    if len(dates) >= 2:
        for i in range(len(dates) - 1):
            if dates[i] < dates[i + 1]:
                results.append(_fail("L2-log-newest-first",
                                     f"Dates are not in descending order: {dates[i]} appears before {dates[i+1]}."))
                break
        else:
            results.append(_pass("L2-log-newest-first", "Date headings are in descending (newest-first) order."))
    elif dates:
        results.append(_pass("L2-log-newest-first", "Only one date heading -- order trivially correct."))
    else:
        results.append(_warn("L2-log-newest-first", "No ## YYYY-MM-DD headings found in log.md."))

    return results


# ---------------------------------------------------------------------------
# Bundle walker
# ---------------------------------------------------------------------------

def validate_bundle(bundle_path: str) -> dict[str, Any]:
    root = Path(bundle_path).resolve()
    if not root.exists():
        return {
            "conformant": False,
            "okf_version": "0.1",
            "bundle_path": str(root),
            "error": f"Bundle path does not exist: {root}",
            "summary": {},
            "results": [],
        }

    file_results: list[dict[str, Any]] = []
    total_files = 0
    concept_count = 0
    index_count = 0
    log_count = 0
    errors = 0
    warnings = 0

    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in sorted(filenames):
            if not fname.endswith(".md"):
                continue
            total_files += 1
            abs_path = Path(dirpath) / fname
            rel = str(abs_path.relative_to(root))
            is_root_dir = Path(dirpath) == root

            if fname == "index.md":
                index_count += 1
                kind = "index"
                rules = check_index(abs_path, rel, is_root=is_root_dir)
            elif fname == "log.md":
                log_count += 1
                kind = "log"
                rules = check_log(abs_path, rel)
            else:
                concept_count += 1
                kind = "concept"
                rules = check_concept(abs_path, rel)

            file_errors = sum(1 for r in rules if r["status"] == "fail")
            file_warns = sum(1 for r in rules if r["status"] == "warn")
            errors += file_errors
            warnings += file_warns

            if file_errors > 0:
                status = "fail"
            elif file_warns > 0:
                status = "warn"
            else:
                status = "pass"

            file_results.append({
                "file": rel,
                "kind": kind,
                "status": status,
                "rules": rules,
            })

    conformant = errors == 0

    return {
        "conformant": conformant,
        "okf_version": "0.1",
        "bundle_path": str(root),
        "summary": {
            "total_files": total_files,
            "concept_files": concept_count,
            "index_files": index_count,
            "log_files": log_count,
            "errors": errors,
            "warnings": warnings,
        },
        "results": file_results,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({
            "conformant": False,
            "error": "Usage: okf_validator.py <bundle-path>",
        }), flush=True)
        return 2

    report = validate_bundle(sys.argv[1])
    print(json.dumps(report, indent=2, default=str), flush=True)

    if "error" in report and not report.get("results"):
        return 2
    return 0 if report["conformant"] else 1


if __name__ == "__main__":
    sys.exit(main())
