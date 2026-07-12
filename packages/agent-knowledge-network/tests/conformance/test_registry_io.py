"""
Conformance tests for the registry_io.py script.

Tests: read, upsert (new), upsert (update existing), delete,
stale-revision conflict, and malformed input safety.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).parent.parent.parent
    / ".apm"
    / "skills"
    / "akn-registry-io"
    / "registry_io.py"
)

SYNTHETIC_AGENT = {
    "agentId": "00000000-0000-0000-0000-000000000001",
    "displayName": "Test Agent",
    "owner": "test-owner",
    "project": "test-project",
    "transports": [{"type": "copilot-app", "projectId": "synthetic-project-id-001"}],
    "capabilities": [
        {"id": "test.capability.v1", "version": "1.0.0", "interactionMode": "query"}
    ],
    "constraints": [],
    "knowledgeRoots": [
        {
            "id": "kr-test",
            "label": "Test Wiki",
            "format": "okf-v1",
            "pathBase": "project",
            "path": "wiki/",
            "default": True,
        }
    ],
    "status": "active",
    "registeredAt": "2025-01-01T00:00:00.000Z",
    "lastValidatedAt": None,
    "lastValidationError": None,
}


def run_op(operation: dict, apm_home: str) -> dict:
    """Run the registry_io.py script with the given operation and return parsed JSON output."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(operation),
        capture_output=True,
        text=True,
        env={**os.environ, "APM_HOME": apm_home},
    )
    assert result.returncode == 0, f"Script exited {result.returncode}: {result.stderr}"
    return json.loads(result.stdout.strip())


@pytest.fixture()
def apm_home(tmp_path: Path) -> str:
    """Provide a temporary APM_HOME directory for each test."""
    return str(tmp_path)


class TestScriptExists:
    def test_script_present(self):
        assert SCRIPT.exists(), f"registry_io.py not found at {SCRIPT}"

    def test_script_is_python(self):
        content = SCRIPT.read_text(encoding="utf-8")
        assert "def main" in content


class TestRead:
    def test_read_empty_registry(self, apm_home):
        result = run_op({"op": "read", "payload": {}}, apm_home)
        assert result["ok"] is True
        assert result["result"]["schemaVersion"] == "1"
        assert result["result"]["revision"] == 0
        assert result["result"]["agents"] == []

    def test_list_alias(self, apm_home):
        result = run_op({"op": "list", "payload": {}}, apm_home)
        assert result["ok"] is True
        assert result["result"]["agents"] == []


class TestUpsertNew:
    def test_upsert_creates_registry(self, apm_home):
        result = run_op(
            {
                "op": "upsert",
                "payload": {
                    "expectedRevision": 0,
                    "agents": [SYNTHETIC_AGENT],
                },
            },
            apm_home,
        )
        assert result["ok"] is True
        assert result["result"]["revision"] == 1

    def test_upsert_persists_agent(self, apm_home):
        run_op(
            {
                "op": "upsert",
                "payload": {"expectedRevision": 0, "agents": [SYNTHETIC_AGENT]},
            },
            apm_home,
        )
        read_result = run_op({"op": "read", "payload": {}}, apm_home)
        assert read_result["ok"] is True
        agents = read_result["result"]["agents"]
        assert len(agents) == 1
        assert agents[0]["agentId"] == SYNTHETIC_AGENT["agentId"]

    def test_registry_file_permissions(self, apm_home):
        run_op(
            {
                "op": "upsert",
                "payload": {"expectedRevision": 0, "agents": [SYNTHETIC_AGENT]},
            },
            apm_home,
        )
        registry = Path(apm_home) / "agent-knowledge-network" / "registry.json"
        mode = oct(registry.stat().st_mode)[-3:]
        assert mode == "600", f"Expected 600 permissions, got {mode}"


class TestUpsertUpdate:
    def test_upsert_updates_existing(self, apm_home):
        # First write
        run_op(
            {
                "op": "upsert",
                "payload": {"expectedRevision": 0, "agents": [SYNTHETIC_AGENT]},
            },
            apm_home,
        )
        # Update the agent
        updated = {**SYNTHETIC_AGENT, "displayName": "Updated Agent Name"}
        result = run_op(
            {
                "op": "upsert",
                "payload": {"expectedRevision": 1, "agents": [updated]},
            },
            apm_home,
        )
        assert result["ok"] is True
        assert result["result"]["revision"] == 2

    def test_upsert_update_reflects_in_read(self, apm_home):
        run_op(
            {
                "op": "upsert",
                "payload": {"expectedRevision": 0, "agents": [SYNTHETIC_AGENT]},
            },
            apm_home,
        )
        updated = {**SYNTHETIC_AGENT, "displayName": "Renamed Agent"}
        run_op(
            {
                "op": "upsert",
                "payload": {"expectedRevision": 1, "agents": [updated]},
            },
            apm_home,
        )
        read_result = run_op({"op": "read", "payload": {}}, apm_home)
        agent = read_result["result"]["agents"][0]
        assert agent["displayName"] == "Renamed Agent"


class TestDelete:
    def test_delete_removes_agent(self, apm_home):
        run_op(
            {
                "op": "upsert",
                "payload": {"expectedRevision": 0, "agents": [SYNTHETIC_AGENT]},
            },
            apm_home,
        )
        result = run_op(
            {
                "op": "delete",
                "payload": {
                    "expectedRevision": 1,
                    "agentId": SYNTHETIC_AGENT["agentId"],
                },
            },
            apm_home,
        )
        assert result["ok"] is True
        assert result["result"]["removed"] == SYNTHETIC_AGENT["agentId"]

    def test_delete_reflects_in_read(self, apm_home):
        run_op(
            {
                "op": "upsert",
                "payload": {"expectedRevision": 0, "agents": [SYNTHETIC_AGENT]},
            },
            apm_home,
        )
        run_op(
            {
                "op": "delete",
                "payload": {
                    "expectedRevision": 1,
                    "agentId": SYNTHETIC_AGENT["agentId"],
                },
            },
            apm_home,
        )
        read_result = run_op({"op": "read", "payload": {}}, apm_home)
        assert read_result["result"]["agents"] == []

    def test_delete_nonexistent_returns_error(self, apm_home):
        result = run_op(
            {
                "op": "delete",
                "payload": {
                    "expectedRevision": 0,
                    "agentId": "00000000-0000-0000-0000-nonexistent",
                },
            },
            apm_home,
        )
        assert result["ok"] is False
        assert "agent-not-found" in result["error"]


class TestStaleRevisionConflict:
    def test_upsert_wrong_revision(self, apm_home):
        result = run_op(
            {
                "op": "upsert",
                "payload": {
                    "expectedRevision": 99,  # wrong -- registry is at revision 0
                    "agents": [SYNTHETIC_AGENT],
                },
            },
            apm_home,
        )
        assert result["ok"] is False
        assert "stale-revision" in result["error"]

    def test_delete_wrong_revision(self, apm_home):
        run_op(
            {
                "op": "upsert",
                "payload": {"expectedRevision": 0, "agents": [SYNTHETIC_AGENT]},
            },
            apm_home,
        )
        result = run_op(
            {
                "op": "delete",
                "payload": {
                    "expectedRevision": 99,  # wrong -- registry is at revision 1
                    "agentId": SYNTHETIC_AGENT["agentId"],
                },
            },
            apm_home,
        )
        assert result["ok"] is False
        assert "stale-revision" in result["error"]

    def test_stale_revision_does_not_mutate(self, apm_home):
        run_op(
            {
                "op": "upsert",
                "payload": {"expectedRevision": 0, "agents": [SYNTHETIC_AGENT]},
            },
            apm_home,
        )
        # Attempt a bad write
        run_op(
            {
                "op": "upsert",
                "payload": {
                    "expectedRevision": 99,
                    "agents": [],
                },
            },
            apm_home,
        )
        # Registry should still have the original agent
        read_result = run_op({"op": "read", "payload": {}}, apm_home)
        assert len(read_result["result"]["agents"]) == 1


class TestMalformedInput:
    def test_empty_input(self, apm_home):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="",
            capture_output=True,
            text=True,
            env={**os.environ, "APM_HOME": apm_home},
        )
        output = json.loads(result.stdout.strip())
        assert output["ok"] is False

    def test_non_json_input(self, apm_home):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="not json at all",
            capture_output=True,
            text=True,
            env={**os.environ, "APM_HOME": apm_home},
        )
        output = json.loads(result.stdout.strip())
        assert output["ok"] is False
        assert "malformed" in output["error"].lower() or "json" in output["error"].lower()

    def test_unknown_op(self, apm_home):
        result = run_op({"op": "destroy_everything", "payload": {}}, apm_home)
        assert result["ok"] is False
        assert "unknown op" in result["error"]

    def test_missing_op(self, apm_home):
        result = run_op({"payload": {}}, apm_home)
        assert result["ok"] is False

    def test_non_object_input(self, apm_home):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input='["not", "an", "object"]',
            capture_output=True,
            text=True,
            env={**os.environ, "APM_HOME": apm_home},
        )
        output = json.loads(result.stdout.strip())
        assert output["ok"] is False

    def test_upsert_missing_expected_revision(self, apm_home):
        result = run_op(
            {"op": "upsert", "payload": {"agents": [SYNTHETIC_AGENT]}},
            apm_home,
        )
        assert result["ok"] is False
        assert "expectedRevision" in result["error"]

    def test_upsert_missing_agents(self, apm_home):
        result = run_op(
            {"op": "upsert", "payload": {"expectedRevision": 0}},
            apm_home,
        )
        assert result["ok"] is False
        assert "agents" in result["error"]

    def test_upsert_agents_not_a_list(self, apm_home):
        result = run_op(
            {
                "op": "upsert",
                "payload": {"expectedRevision": 0, "agents": "not-a-list"},
            },
            apm_home,
        )
        assert result["ok"] is False
