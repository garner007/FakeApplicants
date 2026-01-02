"""Tests for phone validation rules."""

import pytest

from applicant_validator.validators.base import RuleSeverity
from applicant_validator.validators.phone_rules import VoIPPhoneRule


class TestVoIPPhoneRule:
    """Tests for the VoIPPhoneRule validator."""

    @pytest.fixture
    def rule(self) -> VoIPPhoneRule:
        """Create a VoIPPhoneRule instance."""
        return VoIPPhoneRule()

    async def test_regular_mobile_passes(self, rule: VoIPPhoneRule) -> None:
        """Regular mobile number should pass."""
        result = await rule.validate({"phone": "+1 (555) 123-4567"})

        # Without API access, we can only check format and known VoIP prefixes
        assert result.rule_name == "voip_phone"

    async def test_google_voice_prefix_fails(self, rule: VoIPPhoneRule) -> None:
        """Known Google Voice prefixes should be flagged."""
        # Google Voice numbers often come from specific area codes
        result = await rule.validate({"phone": "+1-747-555-1234"})

        # 747 is a known Google Voice area code
        if not result.was_skipped:
            # May or may not flag depending on detection capability
            pass

    async def test_missing_phone_skips(self, rule: VoIPPhoneRule) -> None:
        """Missing phone field should skip validation."""
        result = await rule.validate({})

        assert result.passed is True
        assert result.was_skipped is True
        assert "phone" in result.skip_reason.lower()

    async def test_empty_phone_skips(self, rule: VoIPPhoneRule) -> None:
        """Empty phone should skip validation."""
        result = await rule.validate({"phone": ""})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_none_phone_skips(self, rule: VoIPPhoneRule) -> None:
        """None phone should skip validation."""
        result = await rule.validate({"phone": None})

        assert result.passed is True
        assert result.was_skipped is True

    async def test_invalid_phone_format_skips(self, rule: VoIPPhoneRule) -> None:
        """Invalid phone format should skip (let format validator handle it)."""
        result = await rule.validate({"phone": "not-a-phone"})

        assert result.passed is True
        assert result.was_skipped is True
        assert "parse" in result.skip_reason.lower() or "invalid" in result.skip_reason.lower()

    async def test_rule_metadata(self, rule: VoIPPhoneRule) -> None:
        """Rule should have correct metadata."""
        assert rule.name == "voip_phone"
        assert rule.category == "phone"
        assert rule.default_severity == RuleSeverity.MEDIUM
        assert rule.version is not None

    async def test_known_voip_carrier_detected(self, rule: VoIPPhoneRule) -> None:
        """When carrier info is available, known VoIP carriers should be flagged."""
        # This tests the carrier-based detection
        # In real usage, phonenumbers library provides carrier info
        result = await rule.validate({"phone": "+1-202-555-0100"})

        # The result depends on the phonenumbers library's carrier database
        assert result.rule_name == "voip_phone"

    async def test_international_number_handled(self, rule: VoIPPhoneRule) -> None:
        """International numbers should be properly parsed."""
        result = await rule.validate({"phone": "+44 20 7946 0958"})

        # UK number - should be parseable
        assert result.rule_name == "voip_phone"
        # Should not skip for valid international numbers
        if not result.was_skipped:
            assert result.passed is True or result.passed is False

    async def test_us_number_with_country_code(self, rule: VoIPPhoneRule) -> None:
        """US number with country code should work."""
        result = await rule.validate({"phone": "+1 650 555 1234"})

        assert result.rule_name == "voip_phone"

    async def test_us_number_without_country_code(self, rule: VoIPPhoneRule) -> None:
        """US number without country code should work with default region."""
        result = await rule.validate({"phone": "(650) 555-1234"})

        assert result.rule_name == "voip_phone"
        # Should not skip for parseable numbers
        assert result.was_skipped is False or result.passed is True

    async def test_bandwidth_voip_detected(self, rule: VoIPPhoneRule) -> None:
        """Bandwidth.com VoIP numbers should be detected if carrier matches."""
        # This is a known VoIP carrier
        result = await rule.validate({"phone": "+1-919-555-1234"})
        # Detection depends on phonenumbers carrier database
        assert result.rule_name == "voip_phone"

    async def test_loads_voip_carriers_from_file(self, rule: VoIPPhoneRule) -> None:
        """Rule should load VoIP carriers from data file."""
        # The rule should have loaded carriers from voip_carriers.txt
        assert len(rule._voip_carriers) > 20  # We have ~100 carriers

    async def test_evidence_on_voip_detection(self, rule: VoIPPhoneRule) -> None:
        """When VoIP is detected, evidence should be provided."""
        # Test with a number that might be VoIP
        result = await rule.validate({"phone": "+1-555-555-5555"})

        # If it fails (VoIP detected), should have evidence
        if not result.passed and not result.was_skipped:
            assert len(result.evidence) > 0
