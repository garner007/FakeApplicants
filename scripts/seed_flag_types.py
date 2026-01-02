#!/usr/bin/env python
"""Seed initial flag types for the applicant validator."""

import asyncio

from applicant_validator.database import FlagCategory, FlagSeverity, FlagType, get_session

# Initial flag types to seed
FLAG_TYPES = [
    # Email flags
    {
        "code": "DISPOSABLE_EMAIL",
        "name": "Disposable Email Address",
        "description": "Email address is from a known disposable/temporary email provider",
        "category": FlagCategory.EMAIL.value,
        "default_severity": FlagSeverity.HIGH.value,
        "weight": 3.0,
    },
    {
        "code": "INVALID_EMAIL_FORMAT",
        "name": "Invalid Email Format",
        "description": "Email address does not match valid email format",
        "category": FlagCategory.EMAIL.value,
        "default_severity": FlagSeverity.CRITICAL.value,
        "weight": 5.0,
    },
    {
        "code": "EMAIL_DOMAIN_NO_MX",
        "name": "Email Domain Has No MX Record",
        "description": "The email domain does not have valid MX records",
        "category": FlagCategory.EMAIL.value,
        "default_severity": FlagSeverity.MEDIUM.value,
        "weight": 2.0,
    },
    # Phone flags
    {
        "code": "VOIP_PHONE",
        "name": "VoIP Phone Number",
        "description": "Phone number is from a known VoIP carrier",
        "category": FlagCategory.PHONE.value,
        "default_severity": FlagSeverity.MEDIUM.value,
        "weight": 2.0,
    },
    {
        "code": "INVALID_PHONE_FORMAT",
        "name": "Invalid Phone Format",
        "description": "Phone number does not match valid format for its country",
        "category": FlagCategory.PHONE.value,
        "default_severity": FlagSeverity.LOW.value,
        "weight": 1.0,
    },
    {
        "code": "PHONE_COUNTRY_MISMATCH",
        "name": "Phone Country Mismatch",
        "description": "Phone number country does not match stated location",
        "category": FlagCategory.PHONE.value,
        "default_severity": FlagSeverity.MEDIUM.value,
        "weight": 2.0,
    },
    # LinkedIn flags
    {
        "code": "LINKEDIN_PROFILE_NOT_FOUND",
        "name": "LinkedIn Profile Not Found",
        "description": "The provided LinkedIn URL does not resolve to a valid profile",
        "category": FlagCategory.LINKEDIN.value,
        "default_severity": FlagSeverity.HIGH.value,
        "weight": 3.0,
    },
    {
        "code": "LINKEDIN_NAME_MISMATCH",
        "name": "LinkedIn Name Mismatch",
        "description": "Name on LinkedIn profile does not match application name",
        "category": FlagCategory.LINKEDIN.value,
        "default_severity": FlagSeverity.HIGH.value,
        "weight": 4.0,
    },
    {
        "code": "LINKEDIN_EXPERIENCE_MISMATCH",
        "name": "LinkedIn Experience Mismatch",
        "description": "Work experience on LinkedIn does not match resume",
        "category": FlagCategory.LINKEDIN.value,
        "default_severity": FlagSeverity.HIGH.value,
        "weight": 4.0,
    },
    {
        "code": "LINKEDIN_EDUCATION_MISMATCH",
        "name": "LinkedIn Education Mismatch",
        "description": "Education on LinkedIn does not match resume",
        "category": FlagCategory.LINKEDIN.value,
        "default_severity": FlagSeverity.MEDIUM.value,
        "weight": 3.0,
    },
    {
        "code": "LINKEDIN_PROFILE_NEW",
        "name": "New LinkedIn Profile",
        "description": "LinkedIn profile appears to be recently created",
        "category": FlagCategory.LINKEDIN.value,
        "default_severity": FlagSeverity.LOW.value,
        "weight": 1.5,
    },
    {
        "code": "LINKEDIN_LOW_CONNECTIONS",
        "name": "Low LinkedIn Connections",
        "description": "LinkedIn profile has suspiciously few connections",
        "category": FlagCategory.LINKEDIN.value,
        "default_severity": FlagSeverity.LOW.value,
        "weight": 1.0,
    },
    # Resume flags
    {
        "code": "RESUME_KEYWORD_STUFFING",
        "name": "Resume Keyword Stuffing",
        "description": "Resume contains excessive keyword repetition",
        "category": FlagCategory.RESUME.value,
        "default_severity": FlagSeverity.MEDIUM.value,
        "weight": 2.0,
    },
    {
        "code": "RESUME_TIMELINE_GAP",
        "name": "Resume Timeline Gap",
        "description": "Resume has unexplained gaps in employment history",
        "category": FlagCategory.RESUME.value,
        "default_severity": FlagSeverity.LOW.value,
        "weight": 1.0,
    },
    {
        "code": "RESUME_SUSPICIOUS_DATES",
        "name": "Suspicious Resume Dates",
        "description": "Resume contains implausible or inconsistent dates",
        "category": FlagCategory.RESUME.value,
        "default_severity": FlagSeverity.MEDIUM.value,
        "weight": 2.5,
    },
    # Identity flags
    {
        "code": "DUPLICATE_APPLICANT",
        "name": "Duplicate Applicant",
        "description": "Applicant appears to be a duplicate of another application",
        "category": FlagCategory.IDENTITY.value,
        "default_severity": FlagSeverity.HIGH.value,
        "weight": 4.0,
    },
    {
        "code": "NAME_EMAIL_MISMATCH",
        "name": "Name Email Mismatch",
        "description": "Name in email address does not match applicant name",
        "category": FlagCategory.IDENTITY.value,
        "default_severity": FlagSeverity.LOW.value,
        "weight": 1.0,
    },
    # Location flags
    {
        "code": "LOCATION_INCONSISTENT",
        "name": "Inconsistent Location",
        "description": "Stated location is inconsistent across application materials",
        "category": FlagCategory.LOCATION.value,
        "default_severity": FlagSeverity.MEDIUM.value,
        "weight": 2.0,
    },
    # Behavior flags
    {
        "code": "RAPID_APPLICATION",
        "name": "Rapid Application",
        "description": "Application was submitted unusually quickly after viewing job",
        "category": FlagCategory.BEHAVIOR.value,
        "default_severity": FlagSeverity.LOW.value,
        "weight": 1.0,
    },
    {
        "code": "MULTIPLE_APPLICATIONS",
        "name": "Multiple Applications",
        "description": "Applicant has applied to many positions in short time",
        "category": FlagCategory.BEHAVIOR.value,
        "default_severity": FlagSeverity.INFO.value,
        "weight": 0.5,
    },
]


async def seed_flag_types() -> None:
    """Seed the flag types table with initial data."""
    async with get_session() as session:
        for flag_data in FLAG_TYPES:
            # Check if flag type already exists
            from sqlalchemy import select

            result = await session.execute(
                select(FlagType).where(FlagType.code == flag_data["code"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"Flag type '{flag_data['code']}' already exists, skipping...")
                continue

            flag_type = FlagType(**flag_data)
            session.add(flag_type)
            print(f"Created flag type: {flag_data['code']}")

        await session.commit()
        print(f"\nSeeded {len(FLAG_TYPES)} flag types.")


if __name__ == "__main__":
    asyncio.run(seed_flag_types())
