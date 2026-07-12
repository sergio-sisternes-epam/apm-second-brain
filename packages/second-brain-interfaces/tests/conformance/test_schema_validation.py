"""
Conformance tests: validate fixture JSON files against their JSON Schemas.

Run with:  pytest tests/conformance/test_schema_validation.py -v
Requirements: jsonschema>=4.0 (pip install jsonschema)
"""

import json
import pathlib

import pytest
import jsonschema
from jsonschema import validate, Draft202012Validator

PACKAGE_ROOT = pathlib.Path(__file__).parent.parent.parent
SKILLS_DIR = PACKAGE_ROOT / ".apm" / "skills"
FIXTURES_DIR = PACKAGE_ROOT / "tests" / "fixtures"


def _load(path: pathlib.Path) -> dict:
    with path.open() as f:
        return json.load(f)


def _schema_for(skill: str, envelope: str) -> dict:
    return _load(SKILLS_DIR / skill / "schema" / f"{envelope}.schema.json")


# ---------------------------------------------------------------------------
# Think
# ---------------------------------------------------------------------------

class TestThinkRequest:
    schema = _schema_for("brain-think", "request")
    fixture = _load(FIXTURES_DIR / "sample-think-request.json")

    def test_fixture_is_valid(self):
        validate(instance=self.fixture, schema=self.schema,
                 cls=Draft202012Validator)

    def test_missing_required_question_fails(self):
        bad = {k: v for k, v in self.fixture.items() if k != "question"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)

    def test_missing_capability_fails(self):
        bad = {k: v for k, v in self.fixture.items() if k != "capability"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)

    def test_wrong_capability_value_fails(self):
        bad = {**self.fixture, "capability": "second-brain.think.v99"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)

    def test_additional_property_fails(self):
        bad = {**self.fixture, "unexpected_field": "oops"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)


class TestThinkResponse:
    schema = _schema_for("brain-think", "response")

    def _make_valid(self) -> dict:
        return {
            "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "quality": "answered",
            "answer": "Use immutable image tags in production.",
            "citations": [
                {
                    "source_id": "src-001",
                    "label": "Kubernetes image pull policy docs",
                    "excerpt": "IfNotPresent will not re-pull if the image already exists."
                }
            ],
            "knowledge_gaps": []
        }

    def test_valid_response(self):
        validate(instance=self._make_valid(), schema=self.schema,
                 cls=Draft202012Validator)

    def test_invalid_quality_value_fails(self):
        bad = {**self._make_valid(), "quality": "maybe"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)

    def test_unanswered_with_empty_answer_is_valid(self):
        obj = {**self._make_valid(), "quality": "unanswered", "answer": ""}
        validate(instance=obj, schema=self.schema, cls=Draft202012Validator)


# ---------------------------------------------------------------------------
# Learn
# ---------------------------------------------------------------------------

class TestLearnRequest:
    schema = _schema_for("brain-learn", "request")
    fixture = _load(FIXTURES_DIR / "sample-learn-request.json")

    def test_fixture_is_valid(self):
        validate(instance=self.fixture, schema=self.schema,
                 cls=Draft202012Validator)

    def test_invalid_category_fails(self):
        bad = {**self.fixture, "category": "gossip"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)

    def test_invalid_confidence_fails(self):
        bad = {**self.fixture, "confidence": "certain"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)

    def test_invalid_source_type_fails(self):
        bad = {**self.fixture, "source_type": "tweet"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)

    def test_missing_content_fails(self):
        bad = {k: v for k, v in self.fixture.items() if k != "content"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)


class TestLearnReceipt:
    schema = _schema_for("brain-learn", "response")

    def _make_valid(self) -> dict:
        return {
            "correlation_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            "source_id": "src-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "status": "accepted",
            "message": "Learning queued for ingestion."
        }

    def test_valid_receipt(self):
        validate(instance=self._make_valid(), schema=self.schema,
                 cls=Draft202012Validator)

    def test_invalid_status_fails(self):
        bad = {**self._make_valid(), "status": "pending"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)


# ---------------------------------------------------------------------------
# Forget
# ---------------------------------------------------------------------------

class TestForgetRequest:
    schema = _schema_for("brain-forget", "request")
    fixture = _load(FIXTURES_DIR / "sample-forget-request.json")

    def test_fixture_is_valid(self):
        validate(instance=self.fixture, schema=self.schema,
                 cls=Draft202012Validator)

    def test_missing_target_id_fails(self):
        bad = {k: v for k, v in self.fixture.items() if k != "target_id"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)

    def test_missing_reason_fails(self):
        bad = {k: v for k, v in self.fixture.items() if k != "reason"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)

    def test_wrong_capability_fails(self):
        bad = {**self.fixture, "capability": "second-brain.forget.v2"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)


class TestForgetReceipt:
    schema = _schema_for("brain-forget", "response")

    def _make_valid(self) -> dict:
        return {
            "correlation_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
            "target_id": "src-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "status": "tombstoned",
            "message": "Entry archived and excluded from future think results."
        }

    def test_valid_receipt(self):
        validate(instance=self._make_valid(), schema=self.schema,
                 cls=Draft202012Validator)

    def test_not_found_status_is_valid(self):
        obj = {**self._make_valid(), "status": "not_found",
               "message": "No entry matched the given target_id."}
        validate(instance=obj, schema=self.schema, cls=Draft202012Validator)

    def test_invalid_status_fails(self):
        bad = {**self._make_valid(), "status": "deleted"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)


# ---------------------------------------------------------------------------
# Standard error envelope (shared across all capabilities)
# ---------------------------------------------------------------------------

class TestErrorEnvelope:
    schema = _schema_for("brain-think", "error")

    def _make_valid(self) -> dict:
        return {
            "correlation_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
            "code": "TRANSIENT",
            "message": "Provider temporarily unavailable. Retry after 30 seconds."
        }

    def test_valid_error(self):
        validate(instance=self._make_valid(), schema=self.schema,
                 cls=Draft202012Validator)

    def test_invalid_code_fails(self):
        bad = {**self._make_valid(), "code": "HTTP_503"}
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=bad, schema=self.schema, cls=Draft202012Validator)

    def test_optional_detail_accepted(self):
        obj = {**self._make_valid(), "detail": {"retry_after": 30}}
        validate(instance=obj, schema=self.schema, cls=Draft202012Validator)
