#!/usr/bin/env python
"""Seed the database with fake applicant data for development."""

import asyncio
import random
import uuid
from datetime import UTC, timedelta

from faker import Faker
from sqlalchemy import select

from applicant_validator.database import (
    Applicant,
    Flag,
    FlagSeverity,
    FlagType,
    RiskLevel,
    get_session,
)

fake = Faker()

# Configuration
NUM_APPLICANTS = 50

# Risk level distribution (weights)
RISK_DISTRIBUTION = {
    RiskLevel.LOW.value: 0.4,
    RiskLevel.MEDIUM.value: 0.3,
    RiskLevel.HIGH.value: 0.2,
    RiskLevel.CRITICAL.value: 0.1,
}

# How many flags per risk level (min, max)
FLAGS_PER_RISK = {
    RiskLevel.LOW.value: (0, 1),
    RiskLevel.MEDIUM.value: (1, 3),
    RiskLevel.HIGH.value: (2, 5),
    RiskLevel.CRITICAL.value: (4, 8),
}


def generate_lever_id() -> str:
    """Generate a fake Lever ID."""
    return f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}"


def generate_linkedin_url(name: str) -> str:
    """Generate a fake LinkedIn URL from a name."""
    slug = name.lower().replace(" ", "-").replace(".", "")
    # Add some random numbers like real LinkedIn
    slug += f"-{random.randint(100, 999)}"
    return f"https://linkedin.com/in/{slug}"


def choose_risk_level() -> str:
    """Choose a risk level based on distribution weights."""
    levels = list(RISK_DISTRIBUTION.keys())
    weights = list(RISK_DISTRIBUTION.values())
    return random.choices(levels, weights=weights, k=1)[0]


def generate_validation_score(risk_level: str) -> float:
    """Generate a validation score based on risk level."""
    ranges = {
        RiskLevel.LOW.value: (75, 100),
        RiskLevel.MEDIUM.value: (50, 74),
        RiskLevel.HIGH.value: (25, 49),
        RiskLevel.CRITICAL.value: (0, 24),
    }
    min_score, max_score = ranges.get(risk_level, (50, 100))
    return round(random.uniform(min_score, max_score), 1)


def generate_applicant() -> dict:
    """Generate a fake applicant record."""
    name = fake.name()
    email_domain = random.choice(
        [
            "gmail.com",
            "yahoo.com",
            "hotmail.com",
            "outlook.com",
            fake.domain_name(),
            fake.domain_name(),
        ]
    )
    email = f"{name.lower().replace(' ', '.').replace('-', '')}@{email_domain}"

    risk_level = choose_risk_level()

    # Random date in the last 90 days
    created_at = fake.date_time_between(start_date="-90d", end_date="now", tzinfo=UTC)

    # Some applicants are reviewed
    is_reviewed = random.random() < 0.3
    reviewed_at = None
    reviewed_by = None
    if is_reviewed:
        reviewed_at = created_at + timedelta(days=random.randint(1, 7))
        reviewed_by = fake.name()

    return {
        "lever_id": generate_lever_id(),
        "lever_opportunity_id": generate_lever_id() if random.random() > 0.2 else None,
        "name": name,
        "email": email,
        "phone": fake.phone_number() if random.random() > 0.1 else None,
        "location": fake.city() + ", " + fake.state_abbr() if random.random() > 0.2 else None,
        "headline": fake.job() if random.random() > 0.3 else None,
        "linkedin_url": generate_linkedin_url(name) if random.random() > 0.2 else None,
        "lever_stage": random.choice(
            ["New", "Screening", "Interview", "Offer", "Hired", "Rejected"]
        ),
        "lever_created_at": created_at,
        "risk_level": risk_level,
        "validation_score": generate_validation_score(risk_level),
        "flag_count": 0,  # Will be updated after flags are created
        "last_validated_at": created_at + timedelta(hours=random.randint(1, 24)),
        "is_reviewed": is_reviewed,
        "reviewed_at": reviewed_at,
        "reviewed_by": reviewed_by,
        "created_at": created_at,
    }


def generate_flag_message(flag_code: str) -> str:
    """Generate a realistic flag message based on flag type."""
    messages = {
        "DISPOSABLE_EMAIL": [
            "Email domain 'tempmail.com' is a known disposable email provider",
            "Email uses temporary email service 'guerrillamail.com'",
            "Disposable email detected: mailinator.com domain",
        ],
        "VOIP_PHONE": [
            "Phone number is registered with Google Voice (VoIP carrier)",
            "Number identified as Twilio VoIP service",
            "VoIP carrier detected: TextNow",
        ],
        "LINKEDIN_PROFILE_NOT_FOUND": [
            "LinkedIn URL returns 404 - profile may have been deleted",
            "Unable to locate LinkedIn profile at provided URL",
            "LinkedIn profile does not exist or is private",
        ],
        "LINKEDIN_NAME_MISMATCH": [
            "Application name 'John Smith' does not match LinkedIn name 'Jonathan Smithson'",
            "Name discrepancy: Resume shows 'Michael Brown', LinkedIn shows 'Mike Browning'",
            "Significant name mismatch between application and LinkedIn profile",
        ],
        "LINKEDIN_EXPERIENCE_MISMATCH": [
            "Resume claims 5 years at Google, LinkedIn shows 2 years",
            "Job title discrepancy: Resume says 'Senior Engineer', LinkedIn shows 'Junior Developer'",
            "Employment dates don't match between resume and LinkedIn",
        ],
        "LINKEDIN_LOW_CONNECTIONS": [
            "LinkedIn profile has only 12 connections",
            "Suspiciously low connection count: 8 connections for 10+ year professional",
            "Profile has minimal network presence (15 connections)",
        ],
        "DUPLICATE_APPLICANT": [
            "Email matches previous applicant from 30 days ago",
            "Phone number found in another active application",
            "Potential duplicate: Same name and location as existing applicant",
        ],
        "PHONE_COUNTRY_MISMATCH": [
            "Phone number is US-based but applicant claims to be in Canada",
            "Location says 'London, UK' but phone has +1 country code",
            "Phone region doesn't match stated location",
        ],
        "RESUME_KEYWORD_STUFFING": [
            "Term 'machine learning' appears 47 times in resume",
            "Excessive repetition of 'Python' keyword detected",
            "Resume contains hidden text with repeated keywords",
        ],
    }

    if flag_code in messages:
        return random.choice(messages[flag_code])
    return f"Validation rule '{flag_code}' triggered"


async def seed_applicants() -> None:
    """Seed the database with fake applicants and flags."""
    async with get_session() as session:
        # First, get all flag types
        result = await session.execute(select(FlagType).where(FlagType.is_active == True))  # noqa: E712
        flag_types = result.scalars().all()

        if not flag_types:
            print("No flag types found! Run seed_flag_types.py first.")
            return

        flag_type_map = {ft.code: ft for ft in flag_types}
        print(f"Found {len(flag_types)} flag types")

        # Check for existing applicants
        existing = await session.execute(select(Applicant).limit(1))
        if existing.scalar_one_or_none():
            print("Applicants already exist. Clear the table first if you want to re-seed.")
            print("Use: DELETE FROM flags; DELETE FROM applicants;")
            return

        # Generate applicants
        applicants_created = 0
        flags_created = 0

        for i in range(NUM_APPLICANTS):
            applicant_data = generate_applicant()
            applicant = Applicant(**applicant_data)
            session.add(applicant)
            await session.flush()  # Get the applicant ID

            # Create flags based on risk level
            risk_level = applicant_data["risk_level"]
            min_flags, max_flags = FLAGS_PER_RISK[risk_level]
            num_flags = random.randint(min_flags, max_flags)

            if num_flags > 0:
                # Pick random flag types
                available_codes = list(flag_type_map.keys())
                selected_codes = random.sample(
                    available_codes, min(num_flags, len(available_codes))
                )

                for code in selected_codes:
                    flag_type = flag_type_map[code]

                    # Determine severity (use default or adjust based on risk)
                    severity = flag_type.default_severity
                    if risk_level == RiskLevel.CRITICAL.value and random.random() > 0.5:
                        severity = FlagSeverity.CRITICAL.value
                    elif risk_level == RiskLevel.HIGH.value and random.random() > 0.5:
                        severity = FlagSeverity.HIGH.value

                    flag = Flag(
                        applicant_id=applicant.id,
                        flag_type_id=flag_type.id,
                        severity=severity,
                        message=generate_flag_message(code),
                        is_active=True,
                    )
                    session.add(flag)
                    flags_created += 1

                # Update flag count
                applicant.flag_count = num_flags

            applicants_created += 1
            if (i + 1) % 10 == 0:
                print(f"Created {i + 1}/{NUM_APPLICANTS} applicants...")

        await session.commit()

        print("\nSeeding complete!")
        print(f"  Applicants created: {applicants_created}")
        print(f"  Flags created: {flags_created}")

        # Print summary by risk level
        print("\nRisk level distribution:")
        for risk in RiskLevel:
            result = await session.execute(
                select(Applicant).where(Applicant.risk_level == risk.value)
            )
            count = len(result.scalars().all())
            print(f"  {risk.value}: {count}")


async def main() -> None:
    """Main entry point."""
    print("Seeding database with fake applicants...")
    print(f"Target: {NUM_APPLICANTS} applicants\n")
    await seed_applicants()


if __name__ == "__main__":
    asyncio.run(main())
