"""Phone validation rules."""

from pathlib import Path
from typing import Any, ClassVar

import phonenumbers
from phonenumbers import carrier, phonenumberutil

from applicant_validator.validators.base import (
    RuleResult,
    RuleSeverity,
    ValidationEvidence,
    ValidationRule,
)


class VoIPPhoneRule(ValidationRule):
    """Validates that phone number is not from a known VoIP carrier.

    This rule uses the phonenumbers library to parse and analyze phone
    numbers, checking the carrier against a list of known VoIP providers.
    """

    name = "voip_phone"
    description = "Check if phone number is from a VoIP carrier"
    category = "phone"
    default_severity = RuleSeverity.MEDIUM
    version = "1.0.0"

    # Known VoIP area codes in the US
    # These are area codes commonly used by VoIP services
    VOIP_AREA_CODES: ClassVar[set[str]] = {
        "456",  # Inbound international
        "500",  # Personal Communications Services
        "521",  # Reserved
        "522",  # Reserved
        "533",  # Reserved
        "544",  # Reserved
        "566",  # Reserved
        "577",  # Reserved
        "588",  # Reserved
    }

    def __init__(self) -> None:
        """Initialize the rule and load VoIP carriers."""
        self._voip_carriers: set[str] = set()
        self._load_voip_carriers()

    def _load_voip_carriers(self) -> None:
        """Load VoIP carrier names from the data file."""
        data_file = Path(__file__).parent.parent / "data" / "voip_carriers.txt"

        if not data_file.exists():
            # Fall back to a minimal set if file doesn't exist
            self._voip_carriers = {
                "google voice",
                "twilio",
                "bandwidth",
                "vonage",
                "ringcentral",
            }
            return

        with data_file.open(encoding="utf-8") as f:
            for raw_line in f:
                stripped = raw_line.strip()
                # Skip empty lines and comments
                if stripped and not stripped.startswith("#"):
                    self._voip_carriers.add(stripped.lower())

    def _is_voip_carrier(self, carrier_name: str) -> bool:
        """Check if the carrier name matches a known VoIP provider."""
        if not carrier_name:
            return False

        carrier_lower = carrier_name.lower()

        # Check for exact match
        if carrier_lower in self._voip_carriers:
            return True

        # Check for partial match (e.g., "Twilio, Inc." contains "twilio")
        for voip_carrier in self._voip_carriers:
            if voip_carrier in carrier_lower or carrier_lower in voip_carrier:
                return True

        return False

    def _is_voip_area_code(self, phone_number: phonenumbers.PhoneNumber) -> str | None:
        """Check if the phone number uses a known VoIP area code.

        Returns the area code if it's a VoIP code, None otherwise.
        """
        # Only check US numbers
        if phone_number.country_code != 1:
            return None

        # Get the national number and extract area code (first 3 digits)
        national_number = str(phone_number.national_number)
        if len(national_number) >= 3:
            area_code = national_number[:3]
            if area_code in self.VOIP_AREA_CODES:
                return area_code

        return None

    async def validate(self, data: dict[str, Any]) -> RuleResult:  # noqa: PLR0911
        """Validate that the phone number is not from a VoIP carrier.

        Args:
            data: Dictionary containing 'phone' key.

        Returns:
            RuleResult with pass/fail status and evidence.
        """
        phone = data.get("phone")

        # Handle missing or empty phone
        if not phone:
            return RuleResult.create_skip(self.name, "No phone number provided")

        phone = str(phone).strip()
        if not phone:
            return RuleResult.create_skip(self.name, "Empty phone number provided")

        # Try to parse the phone number
        try:
            # Default to US if no country code provided
            parsed_number = phonenumbers.parse(phone, "US")
        except phonenumberutil.NumberParseException as e:
            return RuleResult.create_skip(self.name, f"Could not parse phone number: {e}")

        # Check if it's a valid number
        if not phonenumbers.is_valid_number(parsed_number):
            return RuleResult.create_skip(self.name, "Invalid phone number format")

        evidence: list[ValidationEvidence] = []

        # Check for VoIP area codes (US only)
        voip_area_code = self._is_voip_area_code(parsed_number)
        if voip_area_code:
            evidence.append(
                ValidationEvidence(
                    evidence_type="voip_area_code",
                    key="area_code",
                    value=voip_area_code,
                    description=f"Area code {voip_area_code} is commonly used by VoIP services",
                )
            )

        # Try to get carrier information
        carrier_name = carrier.name_for_number(parsed_number, "en")

        if carrier_name:
            evidence.append(
                ValidationEvidence(
                    evidence_type="carrier_lookup",
                    key="carrier",
                    value=carrier_name,
                    description=f"Carrier identified as: {carrier_name}",
                )
            )

            if self._is_voip_carrier(carrier_name):
                evidence.append(
                    ValidationEvidence(
                        evidence_type="voip_carrier_match",
                        key="matched_carrier",
                        value=carrier_name,
                        description=f"Carrier '{carrier_name}' is a known VoIP provider",
                    )
                )

                return RuleResult.create_fail(
                    rule_name=self.name,
                    message=f"Phone number carrier '{carrier_name}' is a known VoIP provider",
                    severity=self.default_severity,
                    evidence=evidence,
                )

        # If we found a VoIP area code but no carrier match
        if voip_area_code:
            return RuleResult.create_fail(
                rule_name=self.name,
                message=f"Phone number uses VoIP area code {voip_area_code}",
                severity=RuleSeverity.LOW,  # Lower severity since it's just area code
                evidence=evidence,
            )

        # Format the number for the response
        formatted = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)

        return RuleResult.create_pass(
            self.name,
            f"Phone number {formatted} does not appear to be VoIP",
        )
