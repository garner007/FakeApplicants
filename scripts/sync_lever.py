"""Sync applicants from Lever API to local database."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import delete

from applicant_validator.clients.lever import LeverClient
from applicant_validator.config import get_settings
from applicant_validator.database.base import get_session
from applicant_validator.database.models import (
    Applicant,
    ApplicantSource,
    AuditLog,
    AuditLogChange,
    Flag,
    FlagEvidence,
    FlagType,
    LinkedInCertification,
    LinkedInEducation,
    LinkedInExperience,
    LinkedInProfile,
    LinkedInSkill,
    ValidationResult,
    ValidationResultEvidence,
    ValidationRun,
    ValidationRunConfig,
)


async def clear_database():
    """Clear all data from the database."""
    print("Clearing existing data...")

    async with get_session() as session:
        # Delete in order to respect foreign key constraints
        tables = [
            AuditLogChange,
            AuditLog,
            ValidationResultEvidence,
            ValidationResult,
            ValidationRunConfig,
            ValidationRun,
            FlagEvidence,
            Flag,
            FlagType,
            LinkedInSkill,
            LinkedInCertification,
            LinkedInEducation,
            LinkedInExperience,
            ApplicantSource,
            Applicant,
            LinkedInProfile,
        ]

        for table in tables:
            await session.execute(delete(table))
            print(f"  Cleared {table.__tablename__}")

        await session.commit()

    print("Database cleared.\n")


async def fetch_lever_applicants(client: LeverClient, days: int | None = None) -> list:
    """Fetch applicants from Lever with pagination.

    Args:
        client: LeverClient instance
        days: If provided, only fetch applicants created in the last N days
    """
    import time

    all_applicants = []
    offset = None
    page = 1

    # Build base params
    params: dict = {"limit": 100}
    if days is not None:
        created_at_start = int((time.time() - days * 24 * 60 * 60) * 1000)
        params["created_at_start"] = created_at_start
        print(f"  Filtering to last {days} days...", flush=True)

    while True:
        print(f"  Fetching page {page}...", flush=True)

        # Lever uses cursor-based pagination
        if offset:
            params["offset"] = offset

        response = await client._make_lever_request("GET", "/candidates", params=params)

        candidates = response.get("data", [])
        if not candidates:
            break

        all_applicants.extend(candidates)
        print(f"    Got {len(candidates)} candidates (total: {len(all_applicants)})", flush=True)

        # Check for next page
        if response.get("hasNext"):
            offset = response.get("next")
            page += 1
        else:
            break

    return all_applicants


async def import_applicants(applicants: list):
    """Import applicants into the database."""
    print(f"\nImporting {len(applicants)} applicants to database...")

    async with get_session() as session:
        for i, data in enumerate(applicants, 1):
            # Extract emails (take first)
            emails = data.get("emails", [])
            email = emails[0] if emails else f"unknown_{data['id']}@example.com"

            # Extract phones (take first value)
            phones = data.get("phones", [])
            phone = phones[0].get("value") if phones else None

            # Extract LinkedIn URL from links
            links = data.get("links", [])
            linkedin_url = None
            for link in links:
                if "linkedin.com" in link.lower():
                    linkedin_url = link
                    break

            # Convert timestamp (milliseconds to datetime)
            created_at_ms = data.get("createdAt", 0)
            lever_created_at = datetime.fromtimestamp(created_at_ms / 1000, tz=UTC)

            # Get opportunity ID (take first)
            opportunity_ids = data.get("opportunityIds", [])
            opportunity_id = opportunity_ids[0] if opportunity_ids else None

            # Get stage (from stage changes, take latest)
            stage_changes = data.get("stageChanges", [])
            stage = stage_changes[-1].get("toStageId") if stage_changes else None

            # Create applicant record
            applicant = Applicant(
                lever_id=data["id"],
                lever_opportunity_id=opportunity_id,
                name=data.get("name", "Unknown"),
                email=email,
                phone=phone,
                location=data.get("location"),
                headline=data.get("headline"),
                linkedin_url=linkedin_url,
                lever_stage=stage,
                lever_created_at=lever_created_at,
                risk_level=None,  # Will be set by validation
                validation_score=None,
                flag_count=0,
                is_reviewed=False,
            )
            session.add(applicant)
            await session.flush()  # Flush to get the applicant ID

            # Add sources
            sources = data.get("sources", [])
            for source in sources:
                source_record = ApplicantSource(
                    applicant_id=applicant.id,
                    source=source,
                )
                session.add(source_record)

            if i % 100 == 0:
                print(f"  Imported {i}/{len(applicants)} applicants...", flush=True)
                await session.flush()  # Periodic flush to avoid memory buildup

        await session.commit()

    print(f"Successfully imported {len(applicants)} applicants.\n")


async def main():
    """Main sync function."""
    import sys

    settings = get_settings()

    print("=" * 60, flush=True)
    print("Lever to Database Sync", flush=True)
    print("=" * 60, flush=True)
    print(f"Environment: {settings.lever_environment}", flush=True)
    print(f"Database: {settings.database_url.split('@')[-1]}", flush=True)
    print(flush=True)

    # Clear existing data
    await clear_database()

    # Fetch from Lever
    print("Fetching applicants from Lever API...", flush=True)
    sys.stdout.flush()
    client = LeverClient(
        api_key=settings.lever_api_key,
        environment=settings.lever_environment,
    )

    # Parse command line args for days filter
    days = 7  # Default to last 7 days
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print(f"Invalid days argument: {sys.argv[1]}, using default of 7")

    async with client:
        applicants = await fetch_lever_applicants(client, days=days)

    print(f"Fetched {len(applicants)} total applicants from Lever.\n")

    if not applicants:
        print("No applicants found. Exiting.")
        return

    # Import to database
    await import_applicants(applicants)

    print("=" * 60)
    print("Sync complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
