"""Location validation rules."""

import logging
import re
from typing import Any, ClassVar

from applicant_validator.validators.base import (
    RuleResult,
    RuleSeverity,
    ValidationEvidence,
    ValidationRule,
)

logger = logging.getLogger(__name__)

# US state abbreviations
US_STATES = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    # US territories
    "DC",
    "PR",
    "VI",
    "GU",
    "AS",
    "MP",
}

# US state full names
US_STATE_NAMES = {
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
    # Territories
    "district of columbia",
    "puerto rico",
    "virgin islands",
    "guam",
    "american samoa",
    "northern mariana islands",
}

# Canadian province abbreviations (to flag as non-US)
CANADIAN_PROVINCES = {
    "AB",
    "BC",
    "MB",
    "NB",
    "NL",
    "NS",
    "NT",
    "NU",
    "ON",
    "PE",
    "QC",
    "SK",
    "YT",
}

# Canadian province full names (to flag as non-US)
CANADIAN_PROVINCE_NAMES = {
    "alberta",
    "british columbia",
    "manitoba",
    "new brunswick",
    "newfoundland",
    "newfoundland and labrador",
    "nova scotia",
    "northwest territories",
    "nunavut",
    "ontario",
    "prince edward island",
    "quebec",
    "saskatchewan",
    "yukon",
}

# Common non-US country indicators (including Canada)
INTERNATIONAL_INDICATORS = [
    # Canada
    "canada",
    "toronto",
    "vancouver",
    "montreal",
    "calgary",
    "ottawa",
    "edmonton",
    # Other country names
    "india",
    "nigeria",
    "pakistan",
    "philippines",
    "united kingdom",
    "uk",
    "china",
    "russia",
    "ukraine",
    "brazil",
    "mexico",
    "ghana",
    "kenya",
    "south africa",
    "australia",
    "germany",
    "france",
    "spain",
    "italy",
    "netherlands",
    "poland",
    "romania",
    "vietnam",
    "indonesia",
    "bangladesh",
    "egypt",
    "morocco",
    "tunisia",
    "algeria",
    "cameroon",
    "senegal",
    # Country-specific location patterns
    "lagos",
    "mumbai",
    "delhi",
    "bangalore",
    "hyderabad",
    "chennai",
    "kolkata",
    "karachi",
    "lahore",
    "islamabad",
    "manila",
    "cebu",
    "london",
    "manchester",
    "birmingham",
    "beijing",
    "shanghai",
    "moscow",
    "kiev",
    "kyiv",
    "sao paulo",
    "são paulo",
    "rio de janeiro",
    "rio janeiro",
    "accra",
    "nairobi",
    "johannesburg",
    "sydney",
    "melbourne",
]

# Patterns that strongly suggest US location
US_PATTERNS = [
    r"\b[A-Z]{2}\s*,?\s*USA?\b",  # State, USA or State, US
    r"\bUnited\s+States\b",
    r"\bU\.?S\.?A\.?\b",
]


class NonUSLocationRule(ValidationRule):
    """Validates that applicant location appears to be in the US.

    This rule analyzes the location field to determine if the applicant
    appears to be located outside the US. Canadian and other international
    locations are flagged. It looks for:
    - US state abbreviations or names
    - Canadian province abbreviations or names (flagged)
    - Known international city/country names (flagged)
    - "USA" or "United States" indicators
    """

    name = "non_us_location"
    description = "Check if location is outside the US"
    category = "location"
    default_severity = RuleSeverity.HIGH
    version = "1.1.0"  # Updated to US-only
    checks_fields: ClassVar[list[str]] = ["location"]
    trigger_examples: ClassVar[list[str]] = [
        "Toronto, ON, Canada",
        "Vancouver, BC",
        "Lagos, Nigeria",
        "Mumbai, India",
        "London, UK",
        "Manila, Philippines",
    ]
    rationale = (
        "For US-based positions, applicants located outside the US "
        "may not be eligible for the role or may need work authorization verification. "
        "This includes Canadian applicants who cannot be hired for US-only positions."
    )

    async def validate(self, data: dict[str, Any]) -> RuleResult:  # noqa: PLR0911, PLR0912
        """Validate that the location appears to be in the US.

        Args:
            data: Dictionary containing 'location' key.

        Returns:
            RuleResult with pass/fail status and evidence.
        """
        location = data.get("location")
        is_manually_added = data.get("is_manually_added", False)

        # Handle missing or empty location
        if not location:
            if is_manually_added:
                return RuleResult.create_skip(
                    self.name, "Manually added applicant - location not provided"
                )
            return RuleResult.create_skip(self.name, "No location provided")

        location = str(location).strip()
        if not location:
            return RuleResult.create_skip(self.name, "Empty location provided")

        location_lower = location.lower()
        location_upper = location.upper()

        evidence: list[ValidationEvidence] = [
            ValidationEvidence(
                evidence_type="input_value",
                key="location",
                value=location,
                description="The location that was validated",
            ),
        ]

        # Check for Canadian indicators first (before US check since they share some patterns)
        # Check for Canadian province abbreviations
        # Look for 2-letter codes after a comma, or at the end of the string
        # This avoids matching things like "St." or "de" in the middle of city names
        state_pattern = r"(?:,\s*|\s)([A-Z]{2})(?:\s*,|\s*$|\s+\d)"
        state_match = re.search(state_pattern, location_upper)
        if state_match:
            potential_state = state_match.group(1)
            if potential_state in CANADIAN_PROVINCES:
                evidence.append(
                    ValidationEvidence(
                        evidence_type="canadian_province",
                        key="province",
                        value=potential_state,
                        description=f"Found Canadian province: {potential_state}",
                    )
                )
                return RuleResult.create_fail(
                    rule_name=self.name,
                    message=f"Location is in Canada ({potential_state})",
                    severity=self.default_severity,
                    evidence=evidence,
                )

        # Check for Canadian province full names
        for province_name in CANADIAN_PROVINCE_NAMES:
            if province_name in location_lower:
                evidence.append(
                    ValidationEvidence(
                        evidence_type="canadian_province",
                        key="province",
                        value=province_name,
                        description=f"Found Canadian province name: {province_name}",
                    )
                )
                return RuleResult.create_fail(
                    rule_name=self.name,
                    message=f"Location is in Canada ({province_name})",
                    severity=self.default_severity,
                    evidence=evidence,
                )

        # Check for "Canada" explicitly
        if "canada" in location_lower:
            evidence.append(
                ValidationEvidence(
                    evidence_type="country",
                    key="country",
                    value="Canada",
                    description="Location explicitly mentions Canada",
                )
            )
            return RuleResult.create_fail(
                rule_name=self.name,
                message=f"Location is in Canada: {location}",
                severity=self.default_severity,
                evidence=evidence,
            )

        # Check for explicit US patterns
        for pattern in US_PATTERNS:
            if re.search(pattern, location, re.IGNORECASE):
                return RuleResult.create_pass(
                    self.name,
                    f"Location '{location}' contains US indicator",
                )

        # Check for US state abbreviations (formats: City comma ST, or with ZIP)
        if state_match:
            potential_state = state_match.group(1)
            if potential_state in US_STATES:
                evidence.append(
                    ValidationEvidence(
                        evidence_type="us_state",
                        key="state",
                        value=potential_state,
                        description=f"Found US state abbreviation: {potential_state}",
                    )
                )
                return RuleResult.create_pass(
                    self.name,
                    f"Location '{location}' contains US state ({potential_state})",
                )

        # Check for US state full names
        for state_name in US_STATE_NAMES:
            if state_name in location_lower:
                return RuleResult.create_pass(
                    self.name,
                    f"Location '{location}' contains US state name",
                )

        # Check for international indicators
        matched_indicators: list[str] = []
        for indicator in INTERNATIONAL_INDICATORS:
            if indicator in location_lower:
                matched_indicators.append(indicator)

        if matched_indicators:
            for indicator in matched_indicators:
                evidence.append(
                    ValidationEvidence(
                        evidence_type="international_indicator",
                        key="indicator",
                        value=indicator,
                        description=f"Found international location indicator: {indicator}",
                    )
                )

            return RuleResult.create_fail(
                rule_name=self.name,
                message=f"Location appears to be outside the US: {location}",
                severity=self.default_severity,
                evidence=evidence,
            )

        # Check for common international patterns
        # Pattern: "City, Country" where Country is not US
        # This is a heuristic - if we can't identify it as US, flag it

        # If location has a comma and no US state found, it might be international
        if "," in location:
            parts = [p.strip() for p in location.split(",")]
            # Check if any part looks like a US zip code (5 digits or 5+4)
            has_zip = any(re.match(r"^\d{5}(-\d{4})?$", p) for p in parts)
            if has_zip:
                return RuleResult.create_pass(
                    self.name,
                    f"Location '{location}' contains US ZIP code",
                )

        # If we couldn't identify it as US and it doesn't look like
        # a simple city name, flag it for review
        # Only flag if location has multiple parts (suggesting City, Country format)
        if "," in location and len(location) > 10:
            evidence.append(
                ValidationEvidence(
                    evidence_type="unrecognized_location",
                    key="reason",
                    value="Could not identify as US location",
                    description="Location format not recognized as US",
                )
            )
            return RuleResult.create_fail(
                rule_name=self.name,
                message=f"Location could not be verified as US: {location}",
                severity=RuleSeverity.LOW,  # Lower severity for uncertain cases
                evidence=evidence,
            )

        # Simple location (just city name) - pass with note
        return RuleResult.create_pass(
            self.name,
            f"Location '{location}' - insufficient data to determine country",
        )
