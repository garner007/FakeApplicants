"""Tests for the validation service."""

from applicant_validator.database import FlagCategory, FlagSeverity, RiskLevel
from applicant_validator.services.validation import (
    ALL_RULES,
    RISK_LEVEL_MAP,
    SEVERITY_MAP,
    _get_flag_category,
    _severity_rank,
)
from applicant_validator.validators import (
    DisposableEmailRule,
    NonUSLocationRule,
    NonUSPhoneRule,
    RuleSeverity,
    VoIPPhoneRule,
)


class TestSeverityMap:
    """Tests for the SEVERITY_MAP constant."""

    def test_severity_map_has_all_rule_severities(self) -> None:
        """SEVERITY_MAP should map all RuleSeverity values."""
        for rule_severity in RuleSeverity:
            assert rule_severity in SEVERITY_MAP

    def test_severity_map_returns_flag_severities(self) -> None:
        """SEVERITY_MAP should return FlagSeverity values."""
        for flag_severity in SEVERITY_MAP.values():
            assert isinstance(flag_severity, FlagSeverity)

    def test_severity_map_correct_mappings(self) -> None:
        """SEVERITY_MAP should have correct mappings."""
        assert SEVERITY_MAP[RuleSeverity.INFO] == FlagSeverity.INFO
        assert SEVERITY_MAP[RuleSeverity.LOW] == FlagSeverity.LOW
        assert SEVERITY_MAP[RuleSeverity.MEDIUM] == FlagSeverity.MEDIUM
        assert SEVERITY_MAP[RuleSeverity.HIGH] == FlagSeverity.HIGH
        assert SEVERITY_MAP[RuleSeverity.CRITICAL] == FlagSeverity.CRITICAL


class TestRiskLevelMap:
    """Tests for the RISK_LEVEL_MAP constant."""

    def test_risk_level_map_has_all_rule_severities(self) -> None:
        """RISK_LEVEL_MAP should map all RuleSeverity values."""
        for rule_severity in RuleSeverity:
            assert rule_severity in RISK_LEVEL_MAP

    def test_risk_level_map_returns_risk_levels(self) -> None:
        """RISK_LEVEL_MAP should return RiskLevel values."""
        for risk_level in RISK_LEVEL_MAP.values():
            assert isinstance(risk_level, RiskLevel)

    def test_risk_level_map_correct_mappings(self) -> None:
        """RISK_LEVEL_MAP should have correct mappings."""
        assert RISK_LEVEL_MAP[RuleSeverity.INFO] == RiskLevel.LOW
        assert RISK_LEVEL_MAP[RuleSeverity.LOW] == RiskLevel.LOW
        assert RISK_LEVEL_MAP[RuleSeverity.MEDIUM] == RiskLevel.MEDIUM
        assert RISK_LEVEL_MAP[RuleSeverity.HIGH] == RiskLevel.HIGH
        assert RISK_LEVEL_MAP[RuleSeverity.CRITICAL] == RiskLevel.CRITICAL


class TestAllRules:
    """Tests for the ALL_RULES list."""

    def test_all_rules_contains_expected_rules(self) -> None:
        """ALL_RULES should contain all expected validation rules."""
        rule_types = {type(rule) for rule in ALL_RULES}

        assert DisposableEmailRule in rule_types
        assert VoIPPhoneRule in rule_types
        assert NonUSPhoneRule in rule_types
        assert NonUSLocationRule in rule_types

    def test_all_rules_are_validation_rules(self) -> None:
        """ALL_RULES should only contain ValidationRule instances."""
        from applicant_validator.validators.base import ValidationRule

        for rule in ALL_RULES:
            assert isinstance(rule, ValidationRule)

    def test_all_rules_have_unique_names(self) -> None:
        """ALL_RULES should have unique rule names."""
        names = [rule.name for rule in ALL_RULES]
        assert len(names) == len(set(names))

    def test_all_rules_have_required_attributes(self) -> None:
        """ALL_RULES should have required metadata attributes."""
        for rule in ALL_RULES:
            assert hasattr(rule, "name")
            assert hasattr(rule, "description")
            assert hasattr(rule, "category")
            assert hasattr(rule, "default_severity")
            assert hasattr(rule, "version")
            assert hasattr(rule, "validate")


class TestGetFlagCategory:
    """Tests for the _get_flag_category function."""

    def test_email_category(self) -> None:
        """Should map 'email' to FlagCategory.EMAIL."""
        assert _get_flag_category("email") == FlagCategory.EMAIL.value

    def test_phone_category(self) -> None:
        """Should map 'phone' to FlagCategory.PHONE."""
        assert _get_flag_category("phone") == FlagCategory.PHONE.value

    def test_identity_category(self) -> None:
        """Should map 'identity' to FlagCategory.IDENTITY."""
        assert _get_flag_category("identity") == FlagCategory.IDENTITY.value

    def test_linkedin_category(self) -> None:
        """Should map 'linkedin' to FlagCategory.LINKEDIN."""
        assert _get_flag_category("linkedin") == FlagCategory.LINKEDIN.value

    def test_resume_category(self) -> None:
        """Should map 'resume' to FlagCategory.RESUME."""
        assert _get_flag_category("resume") == FlagCategory.RESUME.value

    def test_behavior_category(self) -> None:
        """Should map 'behavior' to FlagCategory.BEHAVIOR."""
        assert _get_flag_category("behavior") == FlagCategory.BEHAVIOR.value

    def test_location_category(self) -> None:
        """Should map 'location' to FlagCategory.LOCATION."""
        assert _get_flag_category("location") == FlagCategory.LOCATION.value

    def test_unknown_category_returns_other(self) -> None:
        """Should map unknown categories to FlagCategory.OTHER."""
        assert _get_flag_category("unknown") == FlagCategory.OTHER.value
        assert _get_flag_category("custom") == FlagCategory.OTHER.value
        assert _get_flag_category("") == FlagCategory.OTHER.value


class TestSeverityRank:
    """Tests for the _severity_rank function."""

    def test_info_rank(self) -> None:
        """INFO should have rank 0."""
        assert _severity_rank(RuleSeverity.INFO) == 0

    def test_low_rank(self) -> None:
        """LOW should have rank 1."""
        assert _severity_rank(RuleSeverity.LOW) == 1

    def test_medium_rank(self) -> None:
        """MEDIUM should have rank 2."""
        assert _severity_rank(RuleSeverity.MEDIUM) == 2

    def test_high_rank(self) -> None:
        """HIGH should have rank 3."""
        assert _severity_rank(RuleSeverity.HIGH) == 3

    def test_critical_rank(self) -> None:
        """CRITICAL should have rank 4."""
        assert _severity_rank(RuleSeverity.CRITICAL) == 4

    def test_severity_ordering(self) -> None:
        """Severities should be properly ordered."""
        assert _severity_rank(RuleSeverity.INFO) < _severity_rank(RuleSeverity.LOW)
        assert _severity_rank(RuleSeverity.LOW) < _severity_rank(RuleSeverity.MEDIUM)
        assert _severity_rank(RuleSeverity.MEDIUM) < _severity_rank(RuleSeverity.HIGH)
        assert _severity_rank(RuleSeverity.HIGH) < _severity_rank(RuleSeverity.CRITICAL)


class TestRuleCategories:
    """Tests to ensure ALL_RULES categories are properly mapped."""

    def test_disposable_email_rule_category(self) -> None:
        """DisposableEmailRule should have email category."""
        rule = DisposableEmailRule()
        assert rule.category == "email"
        assert _get_flag_category(rule.category) == FlagCategory.EMAIL.value

    def test_voip_phone_rule_category(self) -> None:
        """VoIPPhoneRule should have phone category."""
        rule = VoIPPhoneRule()
        assert rule.category == "phone"
        assert _get_flag_category(rule.category) == FlagCategory.PHONE.value

    def test_non_us_phone_rule_category(self) -> None:
        """NonUSPhoneRule should have phone category."""
        rule = NonUSPhoneRule()
        assert rule.category == "phone"
        assert _get_flag_category(rule.category) == FlagCategory.PHONE.value

    def test_non_us_location_rule_category(self) -> None:
        """NonUSLocationRule should have location category."""
        rule = NonUSLocationRule()
        assert rule.category == "location"
        assert _get_flag_category(rule.category) == FlagCategory.LOCATION.value

    def test_all_rules_categories_are_valid(self) -> None:
        """All rules in ALL_RULES should have valid categories."""
        for rule in ALL_RULES:
            # Category should map to a valid FlagCategory value
            category_value = _get_flag_category(rule.category)
            assert category_value in [c.value for c in FlagCategory]
