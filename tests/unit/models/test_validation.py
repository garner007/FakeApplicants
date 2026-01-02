"""Tests for validation models (Severity, RiskLevel, ValidationResult, ValidationReport)."""

from datetime import UTC, datetime

import pytest

from applicant_validator.models.validation import (
    RiskLevel,
    Severity,
    ValidationReport,
    ValidationResult,
)


class TestSeverity:
    """Tests for Severity enum."""

    def test_severity_values(self) -> None:
        """Severity enum should have LOW, MEDIUM, HIGH, CRITICAL values."""
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"
        assert Severity.CRITICAL.value == "critical"

    def test_severity_from_string(self) -> None:
        """Severity enum should be creatable from string value."""
        assert Severity("low") == Severity.LOW
        assert Severity("medium") == Severity.MEDIUM
        assert Severity("high") == Severity.HIGH
        assert Severity("critical") == Severity.CRITICAL

    def test_severity_ordering(self) -> None:
        """Severity levels should be comparable for ordering."""
        assert Severity.LOW < Severity.MEDIUM
        assert Severity.MEDIUM < Severity.HIGH
        assert Severity.HIGH < Severity.CRITICAL
        assert Severity.LOW < Severity.CRITICAL

    def test_severity_equality(self) -> None:
        """Severity enum should support equality comparison."""
        assert Severity.LOW == Severity.LOW
        assert Severity.LOW != Severity.HIGH

    def test_severity_invalid_value(self) -> None:
        """Severity enum should raise ValueError for invalid input."""
        with pytest.raises(ValueError):
            Severity("invalid")


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_risk_level_values(self) -> None:
        """RiskLevel enum should have LOW, MEDIUM, HIGH values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"

    def test_risk_level_from_string(self) -> None:
        """RiskLevel enum should be creatable from string value."""
        assert RiskLevel("low") == RiskLevel.LOW
        assert RiskLevel("medium") == RiskLevel.MEDIUM
        assert RiskLevel("high") == RiskLevel.HIGH

    def test_risk_level_ordering(self) -> None:
        """RiskLevel levels should be comparable for ordering."""
        assert RiskLevel.LOW < RiskLevel.MEDIUM
        assert RiskLevel.MEDIUM < RiskLevel.HIGH
        assert RiskLevel.LOW < RiskLevel.HIGH

    def test_risk_level_equality(self) -> None:
        """RiskLevel enum should support equality comparison."""
        assert RiskLevel.LOW == RiskLevel.LOW
        assert RiskLevel.LOW != RiskLevel.HIGH

    def test_risk_level_invalid_value(self) -> None:
        """RiskLevel enum should raise ValueError for invalid input."""
        with pytest.raises(ValueError):
            RiskLevel("critical")  # RiskLevel doesn't have critical


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_validation_result_creation(self) -> None:
        """ValidationResult should be creatable with required fields."""
        result = ValidationResult(
            rule_name="linkedin_exists",
            passed=True,
            severity=Severity.MEDIUM,
            message="LinkedIn profile found",
        )
        assert result.rule_name == "linkedin_exists"
        assert result.passed is True
        assert result.severity == Severity.MEDIUM
        assert result.message == "LinkedIn profile found"
        assert result.details == {}

    def test_validation_result_with_details(self) -> None:
        """ValidationResult should store optional details."""
        details = {"url": "https://linkedin.com/in/johndoe", "status_code": 200}
        result = ValidationResult(
            rule_name="linkedin_exists",
            passed=True,
            severity=Severity.MEDIUM,
            message="LinkedIn profile found",
            details=details,
        )
        assert result.details == details

    def test_validation_result_failed(self) -> None:
        """ValidationResult should handle failed validation."""
        result = ValidationResult(
            rule_name="name_consistency",
            passed=False,
            severity=Severity.HIGH,
            message="Name mismatch detected",
            details={"lever_name": "John Doe", "linkedin_name": "Jane Smith"},
        )
        assert result.passed is False
        assert result.severity == Severity.HIGH

    def test_validation_result_serialization(self) -> None:
        """ValidationResult should serialize to dict correctly."""
        result = ValidationResult(
            rule_name="email_domain",
            passed=True,
            severity=Severity.LOW,
            message="Valid email domain",
        )
        data = result.model_dump()
        assert data["rule_name"] == "email_domain"
        assert data["passed"] is True
        assert data["severity"] == "low"
        assert data["message"] == "Valid email domain"

    def test_validation_result_deserialization(self) -> None:
        """ValidationResult should deserialize from dict correctly."""
        data = {
            "rule_name": "linkedin_exists",
            "passed": False,
            "severity": "high",
            "message": "LinkedIn URL not found",
            "details": {"error": "404"},
        }
        result = ValidationResult.model_validate(data)
        assert result.rule_name == "linkedin_exists"
        assert result.severity == Severity.HIGH


class TestValidationReport:
    """Tests for ValidationReport model."""

    @pytest.fixture
    def sample_results(self) -> list[ValidationResult]:
        """Create sample validation results for testing."""
        return [
            ValidationResult(
                rule_name="linkedin_exists",
                passed=True,
                severity=Severity.MEDIUM,
                message="LinkedIn profile found",
            ),
            ValidationResult(
                rule_name="name_consistency",
                passed=True,
                severity=Severity.HIGH,
                message="Names match",
            ),
            ValidationResult(
                rule_name="email_domain",
                passed=False,
                severity=Severity.LOW,
                message="Disposable email detected",
            ),
        ]

    def test_validation_report_creation(self, sample_results: list[ValidationResult]) -> None:
        """ValidationReport should be creatable with required fields."""
        timestamp = datetime.now(UTC)
        report = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=timestamp,
            results=sample_results,
            overall_score=85.0,
            risk_level=RiskLevel.LOW,
        )
        assert report.applicant_id == "abc123"
        assert report.applicant_name == "John Doe"
        assert report.timestamp == timestamp
        assert len(report.results) == 3
        assert report.overall_score == 85.0
        assert report.risk_level == RiskLevel.LOW

    def test_validation_report_with_flags(self, sample_results: list[ValidationResult]) -> None:
        """ValidationReport should store optional flags."""
        report = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=datetime.now(UTC),
            results=sample_results,
            overall_score=60.0,
            risk_level=RiskLevel.MEDIUM,
            flags=["disposable_email", "new_linkedin_profile"],
        )
        assert len(report.flags) == 2
        assert "disposable_email" in report.flags

    def test_validation_report_passed_property_low_risk(self) -> None:
        """ValidationReport.passed should return True for LOW risk."""
        report = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=datetime.now(UTC),
            results=[],
            overall_score=90.0,
            risk_level=RiskLevel.LOW,
        )
        assert report.passed is True

    def test_validation_report_passed_property_medium_risk(self) -> None:
        """ValidationReport.passed should return True for MEDIUM risk."""
        report = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=datetime.now(UTC),
            results=[],
            overall_score=70.0,
            risk_level=RiskLevel.MEDIUM,
        )
        assert report.passed is True

    def test_validation_report_passed_property_high_risk(self) -> None:
        """ValidationReport.passed should return False for HIGH risk."""
        report = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=datetime.now(UTC),
            results=[],
            overall_score=30.0,
            risk_level=RiskLevel.HIGH,
        )
        assert report.passed is False

    def test_validation_report_empty_flags_default(self) -> None:
        """ValidationReport should default to empty flags list."""
        report = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=datetime.now(UTC),
            results=[],
            overall_score=85.0,
            risk_level=RiskLevel.LOW,
        )
        assert report.flags == []

    def test_validation_report_serialization(self, sample_results: list[ValidationResult]) -> None:
        """ValidationReport should serialize to dict correctly."""
        timestamp = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        report = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=timestamp,
            results=sample_results,
            overall_score=85.0,
            risk_level=RiskLevel.LOW,
            flags=["test_flag"],
        )
        data = report.model_dump()
        assert data["applicant_id"] == "abc123"
        assert data["risk_level"] == "low"
        assert len(data["results"]) == 3
        assert data["flags"] == ["test_flag"]

    def test_validation_report_failed_count(self, sample_results: list[ValidationResult]) -> None:
        """ValidationReport should calculate failed result count."""
        report = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=datetime.now(UTC),
            results=sample_results,
            overall_score=85.0,
            risk_level=RiskLevel.LOW,
        )
        assert report.failed_count == 1

    def test_validation_report_passed_count(self, sample_results: list[ValidationResult]) -> None:
        """ValidationReport should calculate passed result count."""
        report = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=datetime.now(UTC),
            results=sample_results,
            overall_score=85.0,
            risk_level=RiskLevel.LOW,
        )
        assert report.passed_count == 2

    def test_validation_report_total_count(self, sample_results: list[ValidationResult]) -> None:
        """ValidationReport should calculate total result count."""
        report = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=datetime.now(UTC),
            results=sample_results,
            overall_score=85.0,
            risk_level=RiskLevel.LOW,
        )
        assert report.total_count == 3

    def test_validation_report_score_bounds(self) -> None:
        """ValidationReport overall_score should be between 0 and 100."""
        # Valid scores
        report = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=datetime.now(UTC),
            results=[],
            overall_score=50.0,
            risk_level=RiskLevel.MEDIUM,
        )
        assert 0 <= report.overall_score <= 100

        # Edge cases
        report_min = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=datetime.now(UTC),
            results=[],
            overall_score=0.0,
            risk_level=RiskLevel.HIGH,
        )
        assert report_min.overall_score == 0.0

        report_max = ValidationReport(
            applicant_id="abc123",
            applicant_name="John Doe",
            timestamp=datetime.now(UTC),
            results=[],
            overall_score=100.0,
            risk_level=RiskLevel.LOW,
        )
        assert report_max.overall_score == 100.0

    def test_validation_report_invalid_score_negative(self) -> None:
        """ValidationReport should reject negative scores."""
        with pytest.raises(ValueError):
            ValidationReport(
                applicant_id="abc123",
                applicant_name="John Doe",
                timestamp=datetime.now(UTC),
                results=[],
                overall_score=-10.0,
                risk_level=RiskLevel.HIGH,
            )

    def test_validation_report_invalid_score_over_100(self) -> None:
        """ValidationReport should reject scores over 100."""
        with pytest.raises(ValueError):
            ValidationReport(
                applicant_id="abc123",
                applicant_name="John Doe",
                timestamp=datetime.now(UTC),
                results=[],
                overall_score=101.0,
                risk_level=RiskLevel.LOW,
            )
