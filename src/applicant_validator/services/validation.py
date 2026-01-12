"""Validation service for running rules against applicants."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from applicant_validator.database import (
    Applicant,
    Flag,
    FlagCategory,
    FlagEvidence,
    FlagSeverity,
    FlagType,
    RiskLevel,
    ValidationResult,
    ValidationResultEvidence,
    ValidationRun,
    ValidationStatus,
)
from applicant_validator.validators import (
    DisposableEmailRule,
    InvalidLinkedInUrlRule,
    MassApplicantRule,
    NonUSLocationRule,
    NonUSPhoneRule,
    RuleSeverity,
    ValidationRule,
    VoIPPhoneRule,
)

# Map rule severity to flag severity
SEVERITY_MAP = {
    RuleSeverity.INFO: FlagSeverity.INFO,
    RuleSeverity.LOW: FlagSeverity.LOW,
    RuleSeverity.MEDIUM: FlagSeverity.MEDIUM,
    RuleSeverity.HIGH: FlagSeverity.HIGH,
    RuleSeverity.CRITICAL: FlagSeverity.CRITICAL,
}

# Map rule severity to risk level
RISK_LEVEL_MAP = {
    RuleSeverity.INFO: RiskLevel.LOW,
    RuleSeverity.LOW: RiskLevel.LOW,
    RuleSeverity.MEDIUM: RiskLevel.MEDIUM,
    RuleSeverity.HIGH: RiskLevel.HIGH,
    RuleSeverity.CRITICAL: RiskLevel.CRITICAL,
}

# All available validation rules
ALL_RULES: list[ValidationRule] = [
    DisposableEmailRule(),
    VoIPPhoneRule(),
    NonUSPhoneRule(),
    NonUSLocationRule(),
    InvalidLinkedInUrlRule(),
    MassApplicantRule(),
]


async def ensure_flag_types(session: AsyncSession) -> dict[str, FlagType]:
    """Ensure all flag types exist in the database.

    Returns a mapping of rule_name -> FlagType.
    """
    flag_types: dict[str, FlagType] = {}

    for rule in ALL_RULES:
        # Check if flag type exists
        result = await session.execute(select(FlagType).where(FlagType.code == rule.name))
        flag_type = result.scalar_one_or_none()

        if not flag_type:
            # Create the flag type
            flag_type = FlagType(
                code=rule.name,
                name=rule.name.replace("_", " ").title(),
                description=rule.description,
                category=_get_flag_category(rule.category),
                default_severity=rule.default_severity.value,
                is_active=True,
                auto_flag=True,
                weight=1.0,
            )
            session.add(flag_type)
            await session.flush()

        flag_types[rule.name] = flag_type

    return flag_types


def _get_flag_category(rule_category: str) -> str:
    """Map rule category to flag category."""
    category_map = {
        "email": FlagCategory.EMAIL.value,
        "phone": FlagCategory.PHONE.value,
        "identity": FlagCategory.IDENTITY.value,
        "linkedin": FlagCategory.LINKEDIN.value,
        "resume": FlagCategory.RESUME.value,
        "behavior": FlagCategory.BEHAVIOR.value,
        "location": FlagCategory.LOCATION.value,
    }
    return category_map.get(rule_category, FlagCategory.OTHER.value)


async def validate_applicant(
    session: AsyncSession,
    applicant: Applicant,
    flag_types: dict[str, FlagType],
    triggered_by: str = "sync",
) -> ValidationRun:
    """Run all validation rules against an applicant.

    Args:
        session: Database session
        applicant: The applicant to validate
        flag_types: Mapping of rule_name -> FlagType
        triggered_by: Who triggered the validation

    Returns:
        The completed ValidationRun
    """
    # Create validation run
    validation_run = ValidationRun(
        applicant_id=applicant.id,
        status=ValidationStatus.RUNNING.value,
        triggered_by=triggered_by,
        trigger_source="lever_sync",
        started_at=datetime.now(UTC),
        rules_passed=0,
        rules_failed=0,
        rules_skipped=0,
        flags_raised=0,
    )
    session.add(validation_run)
    await session.flush()

    # Prepare applicant data for validation
    applicant_data = {
        "email": applicant.email,
        "phone": applicant.phone,
        "name": applicant.name,
        "location": applicant.location,
        "linkedin_url": applicant.linkedin_url,
        "is_manually_added": getattr(applicant, "is_manually_added", False),
        "opportunity_count": getattr(applicant, "opportunity_count", 1),
    }

    # Track results
    highest_severity: RuleSeverity | None = None
    flag_count = 0

    # Run each rule
    for rule in ALL_RULES:
        result = await rule.validate(applicant_data)

        # Store validation result
        validation_result = ValidationResult(
            validation_run_id=validation_run.id,
            rule_name=result.rule_name,
            rule_version=rule.version,
            passed=result.passed,
            severity=result.severity.value if result.severity else None,
            message=result.message,
            was_skipped=result.was_skipped,
            skip_reason=result.skip_reason,
        )
        session.add(validation_result)
        await session.flush()

        # Store evidence for the result
        for evidence in result.evidence:
            result_evidence = ValidationResultEvidence(
                result_id=validation_result.id,
                evidence_type=evidence.evidence_type,
                key=evidence.key,
                value=evidence.value,
            )
            session.add(result_evidence)

        # Update counters
        if result.was_skipped:
            validation_run.rules_skipped += 1
        elif result.passed:
            validation_run.rules_passed += 1
        else:
            validation_run.rules_failed += 1

            # Create a flag for failed rules
            if rule.name in flag_types:
                flag = Flag(
                    applicant_id=applicant.id,
                    flag_type_id=flag_types[rule.name].id,
                    validation_run_id=validation_run.id,
                    severity=SEVERITY_MAP.get(
                        result.severity or rule.default_severity, FlagSeverity.MEDIUM
                    ).value,
                    message=result.message or f"Failed {rule.name} check",
                    is_active=True,
                    is_reviewed=False,
                    is_resolved=False,
                )
                session.add(flag)
                await session.flush()

                # Store flag evidence
                for evidence in result.evidence:
                    flag_evidence = FlagEvidence(
                        flag_id=flag.id,
                        evidence_type=evidence.evidence_type,
                        key=evidence.key,
                        value=evidence.value,
                        description=evidence.description,
                    )
                    session.add(flag_evidence)

                flag_count += 1
                validation_run.flags_raised += 1

            # Track highest severity
            if result.severity and (
                highest_severity is None
                or _severity_rank(result.severity) > _severity_rank(highest_severity)
            ):
                highest_severity = result.severity

    # Complete validation run
    validation_run.status = ValidationStatus.COMPLETED.value
    validation_run.completed_at = datetime.now(UTC)

    if validation_run.started_at:
        duration = validation_run.completed_at - validation_run.started_at
        validation_run.duration_ms = int(duration.total_seconds() * 1000)

    # Determine risk level from highest severity flag
    if highest_severity:
        validation_run.risk_level = RISK_LEVEL_MAP.get(highest_severity, RiskLevel.LOW).value
    else:
        validation_run.risk_level = None

    # Update applicant summary fields
    applicant.flag_count = flag_count
    applicant.risk_level = validation_run.risk_level
    applicant.last_validated_at = validation_run.completed_at

    return validation_run


def _severity_rank(severity: RuleSeverity) -> int:
    """Get numeric rank for severity comparison."""
    ranks = {
        RuleSeverity.INFO: 0,
        RuleSeverity.LOW: 1,
        RuleSeverity.MEDIUM: 2,
        RuleSeverity.HIGH: 3,
        RuleSeverity.CRITICAL: 4,
    }
    return ranks.get(severity, 0)


async def validate_applicants_batch(
    session: AsyncSession,
    applicants: list[Applicant],
    triggered_by: str = "sync",
) -> int:
    """Validate a batch of applicants.

    Args:
        session: Database session
        applicants: List of applicants to validate
        triggered_by: Who triggered the validation

    Returns:
        Number of applicants validated
    """
    # Ensure flag types exist
    flag_types = await ensure_flag_types(session)

    # Validate each applicant
    for applicant in applicants:
        await validate_applicant(session, applicant, flag_types, triggered_by)

    return len(applicants)
