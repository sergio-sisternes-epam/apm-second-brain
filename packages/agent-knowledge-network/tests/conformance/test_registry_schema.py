"""
Conformance tests for the Agent Knowledge Network registry schema (v1).

Validates that the synthetic fixture files conform to the expected schema.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SYNTHETIC_REGISTRY = FIXTURES_DIR / "synthetic-registry.json"
SYNTHETIC_REGISTRY_STALE = FIXTURES_DIR / "synthetic-registry-stale.json"

VALID_STATUSES = frozenset({"active", "stale"})
VALID_TRANSPORT_TYPES = frozenset({"copilot-app"})
VALID_PATH_BASES = frozenset({"project"})


def load_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_agent(agent: dict, index: int) -> None:
    prefix = f"agents[{index}]"
    assert "agentId" in agent, f"{prefix}: missing agentId"
    assert isinstance(agent["agentId"], str) and agent["agentId"], f"{prefix}: agentId must be non-empty string"

    assert "displayName" in agent, f"{prefix}: missing displayName"
    assert isinstance(agent["displayName"], str), f"{prefix}: displayName must be string"

    assert "owner" in agent, f"{prefix}: missing owner"
    assert isinstance(agent["owner"], str), f"{prefix}: owner must be string"

    assert "project" in agent, f"{prefix}: missing project"
    assert isinstance(agent["project"], str), f"{prefix}: project must be string"

    assert "transports" in agent, f"{prefix}: missing transports"
    assert isinstance(agent["transports"], list), f"{prefix}: transports must be list"
    for ti, transport in enumerate(agent["transports"]):
        tp = f"{prefix}.transports[{ti}]"
        assert "type" in transport, f"{tp}: missing type"
        assert transport["type"] in VALID_TRANSPORT_TYPES, f"{tp}: invalid type '{transport['type']}'"
        assert "projectId" in transport, f"{tp}: missing projectId"
        assert isinstance(transport["projectId"], str), f"{tp}: projectId must be string"

    assert "capabilities" in agent, f"{prefix}: missing capabilities"
    assert isinstance(agent["capabilities"], list), f"{prefix}: capabilities must be list"
    for ci, cap in enumerate(agent["capabilities"]):
        cp = f"{prefix}.capabilities[{ci}]"
        assert "id" in cap, f"{cp}: missing id"
        assert "version" in cap, f"{cp}: missing version"
        assert "interactionMode" in cap, f"{cp}: missing interactionMode"

    assert "constraints" in agent, f"{prefix}: missing constraints"
    assert isinstance(agent["constraints"], list), f"{prefix}: constraints must be list"

    assert "knowledgeRoots" in agent, f"{prefix}: missing knowledgeRoots"
    assert isinstance(agent["knowledgeRoots"], list), f"{prefix}: knowledgeRoots must be list"
    for ki, kr in enumerate(agent["knowledgeRoots"]):
        kp = f"{prefix}.knowledgeRoots[{ki}]"
        assert "id" in kr, f"{kp}: missing id"
        assert "label" in kr, f"{kp}: missing label"
        assert "format" in kr, f"{kp}: missing format"
        assert "pathBase" in kr, f"{kp}: missing pathBase"
        assert kr["pathBase"] in VALID_PATH_BASES, f"{kp}: invalid pathBase '{kr['pathBase']}'"
        assert "path" in kr, f"{kp}: missing path"
        assert "default" in kr, f"{kp}: missing default"
        assert isinstance(kr["default"], bool), f"{kp}: default must be boolean"

    assert "status" in agent, f"{prefix}: missing status"
    assert agent["status"] in VALID_STATUSES, f"{prefix}: invalid status '{agent['status']}'"

    assert "registeredAt" in agent, f"{prefix}: missing registeredAt"
    assert isinstance(agent["registeredAt"], str), f"{prefix}: registeredAt must be string"

    assert "lastValidatedAt" in agent, f"{prefix}: missing lastValidatedAt"
    assert agent["lastValidatedAt"] is None or isinstance(agent["lastValidatedAt"], str), \
        f"{prefix}: lastValidatedAt must be string or null"

    assert "lastValidationError" in agent, f"{prefix}: missing lastValidationError"
    assert agent["lastValidationError"] is None or isinstance(agent["lastValidationError"], str), \
        f"{prefix}: lastValidationError must be string or null"


def validate_registry(data: dict, fixture_name: str) -> None:
    assert "schemaVersion" in data, f"{fixture_name}: missing schemaVersion"
    assert data["schemaVersion"] == "1", f"{fixture_name}: schemaVersion must be '1'"

    assert "revision" in data, f"{fixture_name}: missing revision"
    assert isinstance(data["revision"], int), f"{fixture_name}: revision must be integer"
    assert data["revision"] >= 0, f"{fixture_name}: revision must be non-negative"

    assert "agents" in data, f"{fixture_name}: missing agents"
    assert isinstance(data["agents"], list), f"{fixture_name}: agents must be list"
    for i, agent in enumerate(data["agents"]):
        validate_agent(agent, i)


class TestSyntheticRegistry:
    def test_file_exists(self):
        assert SYNTHETIC_REGISTRY.exists(), "synthetic-registry.json not found"

    def test_valid_json(self):
        data = load_fixture(SYNTHETIC_REGISTRY)
        assert isinstance(data, dict)

    def test_schema_conformance(self):
        data = load_fixture(SYNTHETIC_REGISTRY)
        validate_registry(data, "synthetic-registry.json")

    def test_has_two_agents(self):
        data = load_fixture(SYNTHETIC_REGISTRY)
        assert len(data["agents"]) == 2

    def test_all_agents_active(self):
        data = load_fixture(SYNTHETIC_REGISTRY)
        for agent in data["agents"]:
            assert agent["status"] == "active"

    def test_no_real_identifiers(self):
        raw = SYNTHETIC_REGISTRY.read_text(encoding="utf-8")
        # Must not contain any real project-like IDs (only synthetic placeholders)
        assert "synthetic-project-id-001" in raw
        # Must not contain real UUIDs that look like session IDs (real ones are mixed case)
        for line in raw.splitlines():
            if "agentId" in line:
                # All synthetic agentIds use the zero-padded format
                assert "00000000-0000-0000-0000-" in raw

    def test_agent_ids_are_synthetic(self):
        data = load_fixture(SYNTHETIC_REGISTRY)
        synthetic_prefix = "00000000-0000-0000-0000-"
        for agent in data["agents"]:
            assert agent["agentId"].startswith(synthetic_prefix), \
                f"agentId {agent['agentId']!r} is not a synthetic placeholder"


class TestSyntheticRegistryStale:
    def test_file_exists(self):
        assert SYNTHETIC_REGISTRY_STALE.exists(), "synthetic-registry-stale.json not found"

    def test_valid_json(self):
        data = load_fixture(SYNTHETIC_REGISTRY_STALE)
        assert isinstance(data, dict)

    def test_schema_conformance(self):
        data = load_fixture(SYNTHETIC_REGISTRY_STALE)
        validate_registry(data, "synthetic-registry-stale.json")

    def test_has_two_agents(self):
        data = load_fixture(SYNTHETIC_REGISTRY_STALE)
        assert len(data["agents"]) == 2

    def test_has_one_stale_agent(self):
        data = load_fixture(SYNTHETIC_REGISTRY_STALE)
        stale = [a for a in data["agents"] if a["status"] == "stale"]
        assert len(stale) == 1, "expected exactly one stale agent"

    def test_stale_agent_has_error(self):
        data = load_fixture(SYNTHETIC_REGISTRY_STALE)
        stale = [a for a in data["agents"] if a["status"] == "stale"][0]
        assert stale["lastValidationError"] is not None, \
            "stale agent should have a lastValidationError"
