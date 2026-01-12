"""Tests for validation rules API routes."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from applicant_validator.api.routes.rules import (
    ValidationRuleResponse,
    ValidationRulesListResponse,
    router,
)
from applicant_validator.models.validation import Severity


class TestRequestResponseModels:
    """Tests for Pydantic request/response models."""

    def test_validation_rule_response_model(self) -> None:
        """Should create ValidationRuleResponse with all fields."""
        resp = ValidationRuleResponse(
            name="email_domain_check",
            description="Check email domain validity",
            category="email",
            severity="high",
            version="1.0.0",
            checks_fields=["email"],
            trigger_examples=["disposable@temp.com"],
            rationale="Disposable emails indicate potential fraud",
            is_active=True,
        )
        assert resp.name == "email_domain_check"
        assert resp.description == "Check email domain validity"
        assert resp.category == "email"
        assert resp.severity == "high"
        assert resp.version == "1.0.0"
        assert "email" in resp.checks_fields
        assert resp.is_active is True

    def test_validation_rule_response_default_values(self) -> None:
        """Should use default values for optional fields."""
        resp = ValidationRuleResponse(
            name="test_rule",
            description="Test description",
            category="test",
            severity="low",
            version="1.0.0",
        )
        assert resp.checks_fields == []
        assert resp.trigger_examples == []
        assert resp.rationale == ""
        assert resp.is_active is True

    def test_validation_rules_list_response_model(self) -> None:
        """Should create ValidationRulesListResponse with rules list."""
        rules = [
            ValidationRuleResponse(
                name="rule1",
                description="Rule 1",
                category="cat1",
                severity="low",
                version="1.0.0",
            ),
            ValidationRuleResponse(
                name="rule2",
                description="Rule 2",
                category="cat2",
                severity="high",
                version="1.0.0",
            ),
        ]
        resp = ValidationRulesListResponse(rules=rules, total=2)
        assert len(resp.rules) == 2
        assert resp.total == 2

    def test_validation_rules_list_response_empty(self) -> None:
        """Should handle empty rules list."""
        resp = ValidationRulesListResponse(rules=[], total=0)
        assert len(resp.rules) == 0
        assert resp.total == 0


class TestRulesEndpoint:
    """Tests for GET /rules endpoint."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create test app with rules router."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.mark.asyncio
    async def test_list_rules_returns_all_rules(self, app: FastAPI) -> None:
        """Should return list of all validation rules."""
        mock_rule1 = MagicMock()
        mock_rule1.name = "disposable_email"
        mock_rule1.description = "Check for disposable email domains"
        mock_rule1.category = "email"
        mock_rule1.default_severity = Severity.HIGH
        mock_rule1.version = "1.0.0"
        mock_rule1.checks_fields = ["email"]
        mock_rule1.trigger_examples = ["temp@mailinator.com"]
        mock_rule1.rationale = "Disposable emails indicate potential fraud"

        mock_rule2 = MagicMock()
        mock_rule2.name = "voip_phone"
        mock_rule2.description = "Check for VoIP phone numbers"
        mock_rule2.category = "phone"
        mock_rule2.default_severity = Severity.MEDIUM
        mock_rule2.version = "1.0.0"
        mock_rule2.checks_fields = ["phone"]
        mock_rule2.trigger_examples = ["+1-800-555-0123"]
        mock_rule2.rationale = "VoIP numbers can be easily created"

        with patch("applicant_validator.api.routes.rules.ALL_RULES", [mock_rule1, mock_rule2]):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/rules")

            assert response.status_code == 200
            data = response.json()
            assert "rules" in data
            assert "total" in data
            assert data["total"] == 2
            assert len(data["rules"]) == 2

    @pytest.mark.asyncio
    async def test_list_rules_includes_all_metadata(self, app: FastAPI) -> None:
        """Should include all metadata for each rule."""
        mock_rule = MagicMock()
        mock_rule.name = "test_rule"
        mock_rule.description = "Test rule description"
        mock_rule.category = "test"
        mock_rule.default_severity = Severity.LOW
        mock_rule.version = "2.0.0"
        mock_rule.checks_fields = ["field1", "field2"]
        mock_rule.trigger_examples = ["example1", "example2"]
        mock_rule.rationale = "This is why we check"

        with patch("applicant_validator.api.routes.rules.ALL_RULES", [mock_rule]):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/rules")

            assert response.status_code == 200
            data = response.json()
            rule = data["rules"][0]

            assert rule["name"] == "test_rule"
            assert rule["description"] == "Test rule description"
            assert rule["category"] == "test"
            assert rule["severity"] == "low"
            assert rule["version"] == "2.0.0"
            assert rule["checks_fields"] == ["field1", "field2"]
            assert rule["trigger_examples"] == ["example1", "example2"]
            assert rule["rationale"] == "This is why we check"
            assert rule["is_active"] is True

    @pytest.mark.asyncio
    async def test_list_rules_empty_list(self, app: FastAPI) -> None:
        """Should handle empty rules list."""
        with patch("applicant_validator.api.routes.rules.ALL_RULES", []):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/rules")

            assert response.status_code == 200
            data = response.json()
            assert data["rules"] == []
            assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_rules_handles_missing_optional_attrs(self, app: FastAPI) -> None:
        """Should handle rules without optional attributes."""
        mock_rule = MagicMock()
        mock_rule.name = "minimal_rule"
        mock_rule.description = "Minimal rule"
        mock_rule.category = "misc"
        mock_rule.default_severity = Severity.LOW
        mock_rule.version = "1.0.0"
        # Remove optional attributes
        del mock_rule.checks_fields
        del mock_rule.trigger_examples
        del mock_rule.rationale

        with patch("applicant_validator.api.routes.rules.ALL_RULES", [mock_rule]):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/rules")

            assert response.status_code == 200
            data = response.json()
            rule = data["rules"][0]

            assert rule["name"] == "minimal_rule"
            # Optional fields should use defaults
            assert rule["checks_fields"] == []
            assert rule["trigger_examples"] == []
            assert rule["rationale"] == ""


class TestSeverityEnumUsage:
    """Tests for Severity enum in rules context."""

    def test_severity_values_match_expected(self) -> None:
        """Should have correct severity values."""
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"
        assert Severity.CRITICAL.value == "critical"
