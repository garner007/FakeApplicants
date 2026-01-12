"""Phone validation rules."""

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import phonenumbers
from phonenumbers import carrier, phonenumberutil

from applicant_validator.validators.base import (
    RuleResult,
    RuleSeverity,
    ValidationEvidence,
    ValidationRule,
)

if TYPE_CHECKING:
    from applicant_validator.clients.ipqualityscore import PhoneValidationResult

logger = logging.getLogger(__name__)


class VoIPPhoneRule(ValidationRule):
    """Validates that phone number is not from a known VoIP carrier.

    This rule uses multiple methods to detect VoIP numbers (in order):
    1. IPQualityScore API (if enabled) - most comprehensive, includes fraud score
    2. Twilio Lookup API (if enabled) - real-time carrier type detection
    3. Database of known VoIP carrier patterns
    4. Database of known VoIP area codes

    Falls back to local data if database/APIs are not available.
    """

    name = "voip_phone"
    description = "Check if phone number is from a VoIP carrier"
    category = "phone"
    default_severity = RuleSeverity.MEDIUM
    version = "2.1.0"  # Updated for IPQualityScore support
    checks_fields: ClassVar[list[str]] = ["phone"]
    trigger_examples: ClassVar[list[str]] = [
        "Google Voice numbers",
        "Twilio-provided numbers",
        "TextNow numbers",
        "Numbers with VoIP area codes (456, 500, etc.)",
    ]
    rationale = (
        "VoIP (Voice over IP) phone numbers are internet-based and can be easily created "
        "and disposed of. While many legitimate users have VoIP numbers, they are also "
        "commonly used by fraudulent applicants to maintain anonymity. "
        "This is a medium-severity flag as VoIP usage alone is not conclusive."
    )

    # Fallback VoIP area codes if database not available
    DEFAULT_VOIP_AREA_CODES: ClassVar[set[str]] = {
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
        """Initialize the rule."""
        self._voip_carriers: list[dict[str, Any]] | None = None
        self._voip_area_codes: set[str] | None = None
        self._use_database: bool = True
        self._twilio_client: Any | None = None
        self._twilio_checked: bool = False
        self._ipqs_checked: bool = False
        self._ipqs_enabled: bool | None = None

    async def _is_ipqs_enabled(self) -> bool:
        """Check if IPQualityScore is enabled and configured.

        Checks database settings first, falls back to environment variables.
        """
        if self._ipqs_checked:
            return self._ipqs_enabled or False

        self._ipqs_checked = True

        # Try database settings first
        try:
            from applicant_validator.database.base import get_session
            from applicant_validator.services.integration_settings import (
                get_integration_settings_service,
            )

            async with get_session() as session:
                service = await get_integration_settings_service(session)
                self._ipqs_enabled = await service.is_enabled("ipqualityscore")

                if self._ipqs_enabled:
                    logger.info("IPQualityScore is enabled via database settings")
                    return True

        except Exception as e:
            logger.debug(f"Could not check IPQS database settings: {e}")

        # Fall back to environment variables
        try:
            from applicant_validator.config import get_settings

            settings = get_settings()
            self._ipqs_enabled = (
                settings.ipqualityscore_enabled and settings.has_ipqualityscore_credentials
            )

            if self._ipqs_enabled:
                logger.info("IPQualityScore is enabled via environment variables")
            else:
                logger.debug("IPQualityScore not enabled or API key not configured")

            return self._ipqs_enabled

        except Exception as e:
            logger.warning(f"Could not check IPQualityScore config: {e}")
            self._ipqs_enabled = False
            return False

    async def _lookup_with_ipqs(self, phone_number: str) -> "PhoneValidationResult | None":
        """Perform IPQualityScore lookup for phone validation.

        Args:
            phone_number: E.164 formatted phone number.

        Returns:
            PhoneValidationResult or None if lookup fails/not configured.
        """
        if not await self._is_ipqs_enabled():
            return None

        try:
            from applicant_validator.clients.ipqualityscore import (
                validate_phone_with_ipqs,
            )

            result = await validate_phone_with_ipqs(phone_number)
            return result

        except Exception as e:
            logger.warning(f"IPQualityScore lookup failed: {e}")
            return None

    async def _get_twilio_client(self) -> Any | None:  # noqa: PLR0911
        """Get Twilio client if configured and enabled.

        Checks database settings first, falls back to environment variables.
        """
        if self._twilio_checked:
            return self._twilio_client

        self._twilio_checked = True

        # Try database settings first
        try:
            from applicant_validator.database.base import get_session
            from applicant_validator.services.integration_settings import (
                get_integration_settings_service,
            )

            async with get_session() as session:
                service = await get_integration_settings_service(session)
                credentials = await service.get_credentials("twilio")

                if credentials and credentials.get("account_id") and credentials.get("api_secret"):
                    from twilio.rest import Client  # type: ignore[import-not-found]

                    self._twilio_client = Client(
                        credentials["account_id"],
                        credentials["api_secret"],
                    )
                    logger.info("Twilio client initialized from database settings")
                    return self._twilio_client

        except ImportError:
            logger.warning("Twilio library not installed, skipping Twilio lookup")
            return None
        except Exception as e:
            logger.debug(f"Could not get Twilio from database: {e}")

        # Fall back to environment variables
        try:
            from applicant_validator.config import get_settings

            settings = get_settings()

            if not settings.twilio_enabled or not settings.has_twilio_credentials:
                logger.debug("Twilio not enabled or credentials not configured")
                return None

            from twilio.rest import Client

            self._twilio_client = Client(
                settings.twilio_account_sid,
                settings.twilio_auth_token,
            )
            logger.info("Twilio client initialized from environment variables")
            return self._twilio_client

        except ImportError:
            logger.warning("Twilio library not installed, skipping Twilio lookup")
            return None
        except Exception as e:
            logger.warning(f"Could not initialize Twilio client: {e}")
            return None

    async def _load_voip_carriers(self) -> list[dict[str, Any]]:
        """Load VoIP carrier patterns from database or fallback.

        Returns:
            List of carrier pattern dictionaries.
        """
        if self._voip_carriers is not None:
            return self._voip_carriers

        # Try database first
        if self._use_database:
            try:
                from applicant_validator.services.validation_data import (
                    get_validation_data_service,
                )

                service = get_validation_data_service()
                carriers = await service.get_voip_carriers()

                if carriers:
                    self._voip_carriers = carriers
                    logger.info(f"Loaded {len(carriers)} VoIP carriers from database")
                    return self._voip_carriers
                else:
                    logger.warning("No VoIP carriers in database, falling back to file")
            except Exception as e:
                logger.warning(f"Could not load carriers from database, falling back to file: {e}")
                self._use_database = False

        # Fallback to file
        self._voip_carriers = self._load_carriers_from_file()
        return self._voip_carriers

    def _load_carriers_from_file(self) -> list[dict[str, Any]]:
        """Load VoIP carrier names from the data file (fallback)."""
        data_file = Path(__file__).parent.parent / "data" / "voip_carriers.txt"
        carriers: list[dict[str, Any]] = []

        if not data_file.exists():
            # Fall back to a minimal set if file doesn't exist
            logger.warning("VoIP carriers file not found, using minimal fallback set")
            for name in ["google voice", "twilio", "bandwidth", "vonage", "ringcentral"]:
                carriers.append(
                    {
                        "name": name,
                        "match_type": "substring",
                        "confidence": "high",
                    }
                )
            return carriers

        with data_file.open(encoding="utf-8") as f:
            for raw_line in f:
                stripped = raw_line.strip()
                # Skip empty lines and comments
                if stripped and not stripped.startswith("#"):
                    carriers.append(
                        {
                            "name": stripped.lower(),
                            "match_type": "substring",
                            "confidence": "high",
                        }
                    )

        logger.info(f"Loaded {len(carriers)} VoIP carriers from file")
        return carriers

    async def _load_voip_area_codes(self) -> set[str]:
        """Load VoIP area codes from database or fallback.

        Returns:
            Set of VoIP area code strings.
        """
        if self._voip_area_codes is not None:
            return self._voip_area_codes

        # Try database first
        if self._use_database:
            try:
                from applicant_validator.services.validation_data import (
                    get_validation_data_service,
                )

                service = get_validation_data_service()
                codes = await service.get_voip_area_codes()

                if codes:
                    self._voip_area_codes = codes
                    logger.info(f"Loaded {len(codes)} VoIP area codes from database")
                    return self._voip_area_codes
                else:
                    logger.warning("No VoIP area codes in database, using defaults")
            except Exception as e:
                logger.warning(f"Could not load area codes from database: {e}")

        # Fallback to default set
        self._voip_area_codes = self.DEFAULT_VOIP_AREA_CODES.copy()
        return self._voip_area_codes

    async def _is_voip_carrier(self, carrier_name: str) -> tuple[bool, str | None]:
        """Check if the carrier name matches a known VoIP provider.

        Args:
            carrier_name: Carrier name from lookup.

        Returns:
            Tuple of (is_voip, matched_pattern).
        """
        if not carrier_name:
            return False, None

        carrier_lower = carrier_name.lower()
        carriers = await self._load_voip_carriers()

        for carrier_pattern in carriers:
            pattern_name = carrier_pattern["name"]
            match_type = carrier_pattern.get("match_type", "substring")

            if match_type == "exact":
                if carrier_lower == pattern_name:
                    return True, pattern_name
            elif match_type == "substring":
                if pattern_name in carrier_lower or carrier_lower in pattern_name:
                    return True, pattern_name
            elif match_type == "regex" and re.search(pattern_name, carrier_lower):
                return True, pattern_name

        return False, None

    async def _is_voip_area_code(self, phone_number: phonenumbers.PhoneNumber) -> str | None:
        """Check if the phone number uses a known VoIP area code.

        Args:
            phone_number: Parsed phone number.

        Returns:
            The area code if it's a VoIP code, None otherwise.
        """
        # Only check +1 numbers (US area codes for VoIP detection)
        if phone_number.country_code != 1:
            return None

        # Get the national number and extract area code (first 3 digits)
        national_number = str(phone_number.national_number)
        if len(national_number) >= 3:
            area_code = national_number[:3]
            voip_codes = await self._load_voip_area_codes()
            if area_code in voip_codes:
                return area_code

        return None

    async def _lookup_with_twilio(self, phone_number: str) -> dict[str, Any] | None:
        """Perform Twilio Lookup to get carrier type.

        Args:
            phone_number: E.164 formatted phone number.

        Returns:
            Dictionary with carrier info or None.
        """
        client = await self._get_twilio_client()
        if not client:
            return None

        try:
            # Twilio Lookup API call
            lookup = client.lookups.v1.phone_numbers(phone_number).fetch(type=["carrier"])

            if lookup.carrier:
                carrier_info = lookup.carrier
                return {
                    "carrier_name": carrier_info.get("name"),
                    "carrier_type": carrier_info.get("type"),  # voip, landline, mobile
                    "mobile_country_code": carrier_info.get("mobile_country_code"),
                    "mobile_network_code": carrier_info.get("mobile_network_code"),
                }
        except Exception as e:
            logger.warning(f"Twilio lookup failed: {e}")

        return None

    async def validate(self, data: dict[str, Any]) -> RuleResult:  # noqa: PLR0911, PLR0912, PLR0915
        """Validate that the phone number is not from a VoIP carrier.

        Uses multiple detection methods (in order of accuracy):
        1. IPQualityScore API (if configured) - most comprehensive with fraud score
        2. Twilio Lookup API (if configured) - real-time carrier type
        3. Phonenumbers library carrier lookup + pattern matching
        4. VoIP area code detection

        Args:
            data: Dictionary containing 'phone' key.

        Returns:
            RuleResult with pass/fail status and evidence.
        """
        phone = data.get("phone")
        is_manually_added = data.get("is_manually_added", False)

        # Handle missing or empty phone
        if not phone:
            # Skip with specific message for manually added applicants
            if is_manually_added:
                return RuleResult.create_skip(
                    self.name, "Manually added applicant - phone not provided"
                )
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
        e164_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)

        # Method 1: Try IPQualityScore (most comprehensive)
        ipqs_result = await self._lookup_with_ipqs(e164_number)
        if ipqs_result:
            # Add evidence from IPQS
            evidence.append(
                ValidationEvidence(
                    evidence_type="ipqs_lookup",
                    key="fraud_score",
                    value=str(ipqs_result.fraud_score),
                    description=f"IPQualityScore fraud score: {ipqs_result.fraud_score}/100",
                )
            )

            if ipqs_result.line_type:
                evidence.append(
                    ValidationEvidence(
                        evidence_type="ipqs_lookup",
                        key="line_type",
                        value=ipqs_result.line_type,
                        description=f"Line type: {ipqs_result.line_type}",
                    )
                )

            if ipqs_result.carrier:
                evidence.append(
                    ValidationEvidence(
                        evidence_type="ipqs_lookup",
                        key="carrier",
                        value=ipqs_result.carrier,
                        description=f"Carrier: {ipqs_result.carrier}",
                    )
                )

            # Add risk factors as evidence
            for risk_factor in ipqs_result.risk_factors:
                evidence.append(
                    ValidationEvidence(
                        evidence_type="ipqs_risk_factor",
                        key="risk_factor",
                        value=risk_factor,
                        description=risk_factor,
                    )
                )

            # Check if IPQS flagged as VoIP
            if ipqs_result.is_voip:
                # Determine severity based on fraud score
                if ipqs_result.fraud_score >= 85:
                    severity = RuleSeverity.HIGH
                elif ipqs_result.fraud_score >= 75:
                    severity = RuleSeverity.MEDIUM
                else:
                    severity = RuleSeverity.LOW

                carrier_name = ipqs_result.carrier or "unknown"
                return RuleResult.create_fail(
                    rule_name=self.name,
                    message=(
                        f"Phone number is VoIP (carrier: {carrier_name}, "
                        f"fraud score: {ipqs_result.fraud_score})"
                    ),
                    severity=severity,
                    evidence=evidence,
                )

            # Check if IPQS flagged as high risk even if not VoIP
            if ipqs_result.is_high_risk:
                high_risk_severity = (
                    RuleSeverity.HIGH if ipqs_result.fraud_score >= 85 else RuleSeverity.MEDIUM
                )
                return RuleResult.create_fail(
                    rule_name=self.name,
                    message=(
                        f"Phone number flagged as high risk "
                        f"(fraud score: {ipqs_result.fraud_score})"
                    ),
                    severity=high_risk_severity,
                    evidence=evidence,
                )

            # If IPQS says it's valid and not VoIP/risky, trust it
            if ipqs_result.valid and not ipqs_result.is_voip and not ipqs_result.risky:
                line_type = ipqs_result.line_type or "unknown"
                carrier_name = ipqs_result.carrier or "unknown"
                return RuleResult.create_pass(
                    self.name,
                    f"Phone number verified (type: {line_type}, "
                    f"carrier: {carrier_name}, fraud score: {ipqs_result.fraud_score})",
                )

        # Method 2: Try Twilio Lookup (if IPQS not available)
        twilio_result = await self._lookup_with_twilio(e164_number)
        if twilio_result:
            twilio_carrier_type = twilio_result.get("carrier_type", "unknown")
            evidence.append(
                ValidationEvidence(
                    evidence_type="twilio_lookup",
                    key="carrier_type",
                    value=twilio_carrier_type,
                    description=f"Twilio identified carrier type: {twilio_carrier_type}",
                )
            )

            if twilio_result.get("carrier_name"):
                evidence.append(
                    ValidationEvidence(
                        evidence_type="twilio_lookup",
                        key="carrier_name",
                        value=twilio_result["carrier_name"],
                        description=f"Carrier: {twilio_result['carrier_name']}",
                    )
                )

            # Twilio returns "voip" as carrier_type for VoIP numbers
            if twilio_result.get("carrier_type") == "voip":
                twilio_carrier_name = twilio_result.get("carrier_name", "unknown")
                return RuleResult.create_fail(
                    rule_name=self.name,
                    message=f"Phone number is VoIP (carrier: {twilio_carrier_name})",
                    severity=self.default_severity,
                    evidence=evidence,
                )

            # If Twilio says it's mobile or landline, trust it
            if twilio_result.get("carrier_type") in ("mobile", "landline"):
                return RuleResult.create_pass(
                    self.name,
                    f"Phone number is {twilio_result['carrier_type']} "
                    f"(carrier: {twilio_result.get('carrier_name', 'unknown')})",
                )

        # Method 3: Check for VoIP area codes (US only)
        voip_area_code = await self._is_voip_area_code(parsed_number)
        if voip_area_code:
            evidence.append(
                ValidationEvidence(
                    evidence_type="voip_area_code",
                    key="area_code",
                    value=voip_area_code,
                    description=f"Area code {voip_area_code} is commonly used by VoIP services",
                )
            )

        # Method 4: Try phonenumbers library carrier lookup
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

            is_voip, matched_pattern = await self._is_voip_carrier(carrier_name)
            if is_voip:
                evidence.append(
                    ValidationEvidence(
                        evidence_type="voip_carrier_match",
                        key="matched_pattern",
                        value=matched_pattern or carrier_name,
                        description=f"Carrier '{carrier_name}' matches known VoIP provider",
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

        return RuleResult.create_pass(
            self.name,
            f"Phone number {e164_number} does not appear to be VoIP",
        )


class NonUSPhoneRule(ValidationRule):
    """Validates that phone number is from a US number.

    This rule flags phone numbers that are not from the US (+1 country code
    with US area codes). Canadian and other international numbers are flagged.
    """

    name = "non_us_phone"
    description = "Check if phone number is from outside the US"
    category = "phone"
    default_severity = RuleSeverity.HIGH
    version = "1.1.0"  # Updated to US-only
    checks_fields: ClassVar[list[str]] = ["phone"]
    trigger_examples: ClassVar[list[str]] = [
        "Canadian numbers (+1 416, +1 604, etc.)",
        "UK numbers (+44)",
        "India numbers (+91)",
        "Nigeria numbers (+234)",
        "Philippines numbers (+63)",
    ]
    rationale = (
        "Phone numbers from outside the US may indicate an applicant is not currently "
        "located in the US. This is relevant for roles requiring US presence and work "
        "authorization, or for identifying potential overseas fraud operations."
    )

    # US and Canada share country code +1
    US_COUNTRY_CODE = 1

    # Canadian area codes (to distinguish from US)
    # Source: https://en.wikipedia.org/wiki/List_of_North_American_Numbering_Plan_area_codes
    CANADIAN_AREA_CODES: ClassVar[set[str]] = {
        # Alberta
        "403",
        "587",
        "780",
        "825",
        # British Columbia
        "236",
        "250",
        "604",
        "672",
        "778",
        # Manitoba
        "204",
        "431",
        # New Brunswick
        "506",
        # Newfoundland and Labrador
        "709",
        # Northwest Territories / Nunavut / Yukon (shared)
        "867",
        # Nova Scotia / Prince Edward Island (shared)
        "782",
        "902",
        # Ontario
        "226",
        "249",
        "289",
        "343",
        "365",
        "382",
        "416",
        "437",
        "519",
        "548",
        "613",
        "647",
        "683",
        "705",
        "742",
        "753",
        "807",
        "905",
        # Quebec
        "354",
        "367",
        "418",
        "438",
        "450",
        "468",
        "514",
        "579",
        "581",
        "819",
        "873",
        # Saskatchewan
        "306",
        "639",
    }

    async def validate(self, data: dict[str, Any]) -> RuleResult:  # noqa: PLR0911
        """Validate that the phone number is from the US.

        Args:
            data: Dictionary containing 'phone' key.

        Returns:
            RuleResult with pass/fail status and evidence.
        """
        phone = data.get("phone")
        is_manually_added = data.get("is_manually_added", False)

        # Handle missing or empty phone
        if not phone:
            if is_manually_added:
                return RuleResult.create_skip(
                    self.name, "Manually added applicant - phone not provided"
                )
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

        country_code = parsed_number.country_code
        e164_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)

        # Get the region/country for the phone number
        try:
            region = phonenumbers.region_code_for_number(parsed_number)
        except Exception:
            region = "Unknown"

        # Check if it's a +1 country code (need to distinguish US from Canada)
        if country_code == self.US_COUNTRY_CODE:
            # Extract area code to check if it's Canadian
            national_number = str(parsed_number.national_number)
            if len(national_number) >= 3:
                area_code = national_number[:3]

                if area_code in self.CANADIAN_AREA_CODES:
                    # Canadian number - flag it
                    evidence = [
                        ValidationEvidence(
                            evidence_type="area_code",
                            key="area_code",
                            value=area_code,
                            description=f"Area code {area_code} is a Canadian area code",
                        ),
                        ValidationEvidence(
                            evidence_type="region",
                            key="region",
                            value=region or "CA",
                            description="Phone number is from Canada",
                        ),
                        ValidationEvidence(
                            evidence_type="input_value",
                            key="phone",
                            value=e164_number,
                            description="The phone number that was validated",
                        ),
                    ]
                    return RuleResult.create_fail(
                        rule_name=self.name,
                        message=f"Phone number is from Canada (area code {area_code})",
                        severity=self.default_severity,
                        evidence=evidence,
                    )

            # US number - pass
            return RuleResult.create_pass(
                self.name,
                f"Phone number {e164_number} is from the US ({region})",
            )

        # Non-US number (international) - flag it
        # Try to get the country name
        try:
            from phonenumbers import geocoder

            country_name = geocoder.country_name_for_number(parsed_number, "en")
        except Exception:
            country_name = f"Country code +{country_code}"

        evidence = [
            ValidationEvidence(
                evidence_type="country_code",
                key="country_code",
                value=f"+{country_code}",
                description=f"Phone number country code is +{country_code}",
            ),
            ValidationEvidence(
                evidence_type="region",
                key="region",
                value=region or "Unknown",
                description=f"Phone number region: {region}",
            ),
            ValidationEvidence(
                evidence_type="country_name",
                key="country",
                value=country_name or "Unknown",
                description=f"Country: {country_name}",
            ),
            ValidationEvidence(
                evidence_type="input_value",
                key="phone",
                value=e164_number,
                description="The phone number that was validated",
            ),
        ]

        return RuleResult.create_fail(
            rule_name=self.name,
            message=f"Phone number is from outside the US ({country_name})",
            severity=self.default_severity,
            evidence=evidence,
        )
