"""Service for managing validation data (disposable domains, VoIP patterns).

This module provides functionality to:
- Sync disposable email domains from external sources (GitHub lists)
- Manage VoIP carrier patterns and area codes
- Cache and query validation data from the database
"""

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from applicant_validator.database.base import get_session
from applicant_validator.database.models import (
    DataSourceType,
    DisposableEmailDomain,
    ValidationDataSync,
    VoIPAreaCode,
    VoIPCarrier,
)

logger = logging.getLogger(__name__)

# External sources for disposable email domains
DISPOSABLE_DOMAIN_SOURCES = {
    "disposable-email-domains": {
        "url": "https://raw.githubusercontent.com/disposable-email-domains/disposable-email-domains/master/disposable_email_blocklist.conf",
        "name": "Disposable Email Domains (GitHub)",
        "description": "Community-maintained list of disposable email domains",
    },
}

# Default VoIP carriers to seed
DEFAULT_VOIP_CARRIERS = [
    {"name": "google voice", "match_type": "substring", "confidence": "high"},
    {"name": "twilio", "match_type": "substring", "confidence": "high"},
    {"name": "bandwidth", "match_type": "substring", "confidence": "high"},
    {"name": "vonage", "match_type": "substring", "confidence": "high"},
    {"name": "ringcentral", "match_type": "substring", "confidence": "high"},
    {"name": "textnow", "match_type": "substring", "confidence": "high"},
    {"name": "textfree", "match_type": "substring", "confidence": "high"},
    {"name": "pinger", "match_type": "substring", "confidence": "high"},
    {"name": "magicjack", "match_type": "substring", "confidence": "high"},
    {"name": "ooma", "match_type": "substring", "confidence": "high"},
    {"name": "grasshopper", "match_type": "substring", "confidence": "high"},
    {"name": "nextiva", "match_type": "substring", "confidence": "medium"},
    {"name": "8x8", "match_type": "exact", "confidence": "high"},
    {"name": "dialpad", "match_type": "substring", "confidence": "high"},
    {"name": "voip", "match_type": "substring", "confidence": "medium"},
    {"name": "sip", "match_type": "substring", "confidence": "low"},
    {"name": "skype", "match_type": "substring", "confidence": "high"},
    {"name": "whatsapp", "match_type": "substring", "confidence": "medium"},
    {"name": "line2", "match_type": "substring", "confidence": "high"},
    {"name": "sideline", "match_type": "substring", "confidence": "high"},
    {"name": "burner", "match_type": "substring", "confidence": "high"},
    {"name": "hushed", "match_type": "substring", "confidence": "high"},
    {"name": "talkatone", "match_type": "substring", "confidence": "high"},
    {"name": "dingtone", "match_type": "substring", "confidence": "high"},
    {"name": "2ndline", "match_type": "substring", "confidence": "high"},
    {"name": "flyp", "match_type": "substring", "confidence": "high"},
    {"name": "telnyx", "match_type": "substring", "confidence": "high"},
    {"name": "plivo", "match_type": "substring", "confidence": "high"},
    {"name": "signalwire", "match_type": "substring", "confidence": "high"},
    {"name": "inteliquent", "match_type": "substring", "confidence": "high"},
]

# Default VoIP area codes (US)
DEFAULT_VOIP_AREA_CODES = [
    {"area_code": "456", "country_code": "1", "description": "Inbound international"},
    {"area_code": "500", "country_code": "1", "description": "Personal Communications Services"},
    {"area_code": "521", "country_code": "1", "description": "Reserved"},
    {"area_code": "522", "country_code": "1", "description": "Reserved"},
    {"area_code": "533", "country_code": "1", "description": "Reserved"},
    {"area_code": "544", "country_code": "1", "description": "Reserved"},
    {"area_code": "566", "country_code": "1", "description": "Reserved"},
    {"area_code": "577", "country_code": "1", "description": "Reserved"},
    {"area_code": "588", "country_code": "1", "description": "Reserved"},
]


class ValidationDataService:
    """Service for managing validation data."""

    async def sync_disposable_domains(
        self,
        source_key: str = "disposable-email-domains",
    ) -> dict[str, Any]:
        """Sync disposable email domains from an external source.

        Args:
            source_key: Key identifying the source to sync from.

        Returns:
            Dictionary with sync results.
        """
        if source_key not in DISPOSABLE_DOMAIN_SOURCES:
            raise ValueError(f"Unknown source: {source_key}")

        source = DISPOSABLE_DOMAIN_SOURCES[source_key]
        source_url = source["url"]
        source_name = source["name"]

        logger.info(f"Starting disposable domains sync from {source_name}")

        # Create sync record
        async with get_session() as session:
            sync_record = ValidationDataSync(
                data_type="disposable_domains",
                source_url=source_url,
                source_name=source_name,
                status="running",
                started_at=datetime.now(UTC),
            )
            session.add(sync_record)
            await session.flush()
            sync_id = sync_record.id

        try:
            # Fetch the domain list
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(source_url)
                response.raise_for_status()

            # Parse domains
            domains: list[str] = []
            for line in response.text.splitlines():
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    domains.append(line.lower())

            logger.info(f"Fetched {len(domains)} domains from {source_name}")

            # Upsert domains in batches
            added = 0
            updated = 0
            batch_size = 1000

            async with get_session() as session:
                for i in range(0, len(domains), batch_size):
                    batch = domains[i : i + batch_size]

                    # Use PostgreSQL upsert
                    stmt = pg_insert(DisposableEmailDomain).values(
                        [
                            {
                                "domain": domain,
                                "source": DataSourceType.EXTERNAL_LIST.value,
                                "source_url": source_url,
                                "is_active": True,
                            }
                            for domain in batch
                        ]
                    )

                    # On conflict, update the timestamp
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["domain"],
                        set_={
                            "updated_at": func.now(),
                            "source_url": source_url,
                        },
                    )

                    result = await session.execute(stmt)
                    # Note: PostgreSQL doesn't easily distinguish inserts vs updates
                    # in ON CONFLICT, so we'll just track total
                    added += len(batch)

                # Update sync record
                sync_record = await session.get(ValidationDataSync, sync_id)
                if sync_record:
                    sync_record.status = "completed"
                    sync_record.completed_at = datetime.now(UTC)
                    sync_record.records_added = added
                    sync_record.records_total = len(domains)

            logger.info(f"Sync completed: {len(domains)} domains processed")

            return {
                "status": "completed",
                "source": source_name,
                "records_processed": len(domains),
                "sync_id": str(sync_id),
            }

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            async with get_session() as session:
                sync_record = await session.get(ValidationDataSync, sync_id)
                if sync_record:
                    sync_record.status = "failed"
                    sync_record.completed_at = datetime.now(UTC)
                    sync_record.error_message = str(e)

            raise

    async def seed_voip_carriers(self) -> dict[str, Any]:
        """Seed the VoIP carriers table with default values.

        Returns:
            Dictionary with seed results.
        """
        logger.info("Seeding VoIP carriers")

        added = 0
        async with get_session() as session:
            for carrier_data in DEFAULT_VOIP_CARRIERS:
                stmt = pg_insert(VoIPCarrier).values(
                    name=carrier_data["name"],
                    match_type=carrier_data["match_type"],
                    confidence=carrier_data["confidence"],
                    source=DataSourceType.CUSTOM.value,
                    is_active=True,
                )
                stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
                result = await session.execute(stmt)
                if result.rowcount > 0:
                    added += 1

        logger.info(f"Seeded {added} VoIP carriers")
        return {"status": "completed", "carriers_added": added}

    async def seed_voip_area_codes(self) -> dict[str, Any]:
        """Seed the VoIP area codes table with default values.

        Returns:
            Dictionary with seed results.
        """
        logger.info("Seeding VoIP area codes")

        added = 0
        async with get_session() as session:
            for code_data in DEFAULT_VOIP_AREA_CODES:
                stmt = pg_insert(VoIPAreaCode).values(
                    area_code=code_data["area_code"],
                    country_code=code_data["country_code"],
                    description=code_data["description"],
                    source=DataSourceType.CUSTOM.value,
                    is_active=True,
                )
                stmt = stmt.on_conflict_do_nothing(index_elements=["area_code"])
                result = await session.execute(stmt)
                if result.rowcount > 0:
                    added += 1

        logger.info(f"Seeded {added} VoIP area codes")
        return {"status": "completed", "area_codes_added": added}

    async def get_disposable_domains(self, active_only: bool = True) -> set[str]:
        """Get all disposable email domains.

        Args:
            active_only: Whether to return only active domains.

        Returns:
            Set of domain strings.
        """
        async with get_session() as session:
            query = select(DisposableEmailDomain.domain)
            if active_only:
                query = query.where(DisposableEmailDomain.is_active == True)  # noqa: E712

            result = await session.execute(query)
            return {row[0] for row in result.fetchall()}

    async def get_voip_carriers(self, active_only: bool = True) -> list[dict[str, Any]]:
        """Get all VoIP carrier patterns.

        Args:
            active_only: Whether to return only active carriers.

        Returns:
            List of carrier dictionaries.
        """
        async with get_session() as session:
            query = select(VoIPCarrier)
            if active_only:
                query = query.where(VoIPCarrier.is_active == True)  # noqa: E712

            result = await session.execute(query)
            carriers = []
            for (carrier,) in result.fetchall():
                carriers.append(
                    {
                        "id": str(carrier.id),
                        "name": carrier.name,
                        "match_type": carrier.match_type,
                        "confidence": carrier.confidence,
                    }
                )
            return carriers

    async def get_voip_area_codes(self, active_only: bool = True) -> set[str]:
        """Get all VoIP area codes.

        Args:
            active_only: Whether to return only active codes.

        Returns:
            Set of area code strings.
        """
        async with get_session() as session:
            query = select(VoIPAreaCode.area_code)
            if active_only:
                query = query.where(VoIPAreaCode.is_active == True)  # noqa: E712

            result = await session.execute(query)
            return {row[0] for row in result.fetchall()}

    async def add_custom_domain(self, domain: str, notes: str | None = None) -> dict[str, Any]:
        """Add a custom disposable domain.

        Args:
            domain: The domain to add.
            notes: Optional notes about why this domain was added.

        Returns:
            Dictionary with the added domain info.
        """
        domain = domain.lower().strip()

        async with get_session() as session:
            stmt = pg_insert(DisposableEmailDomain).values(
                domain=domain,
                source=DataSourceType.CUSTOM.value,
                is_active=True,
                notes=notes,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["domain"],
                set_={
                    "is_active": True,
                    "notes": notes,
                    "updated_at": func.now(),
                },
            )
            await session.execute(stmt)

        return {"domain": domain, "status": "added"}

    async def remove_domain(self, domain: str) -> dict[str, Any]:
        """Deactivate a disposable domain (soft delete).

        Args:
            domain: The domain to deactivate.

        Returns:
            Dictionary with status.
        """
        domain = domain.lower().strip()

        async with get_session() as session:
            query = select(DisposableEmailDomain).where(DisposableEmailDomain.domain == domain)
            result = await session.execute(query)
            row = result.fetchone()

            if row:
                domain_record = row[0]
                domain_record.is_active = False
                return {"domain": domain, "status": "deactivated"}

        return {"domain": domain, "status": "not_found"}

    async def add_voip_carrier(
        self,
        name: str,
        match_type: str = "substring",
        confidence: str = "high",
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Add a custom VoIP carrier pattern.

        Args:
            name: The carrier name/pattern.
            match_type: How to match (exact, substring, regex).
            confidence: Confidence level (high, medium, low).
            notes: Optional notes.

        Returns:
            Dictionary with the added carrier info.
        """
        name = name.lower().strip()

        async with get_session() as session:
            stmt = pg_insert(VoIPCarrier).values(
                name=name,
                match_type=match_type,
                confidence=confidence,
                source=DataSourceType.CUSTOM.value,
                is_active=True,
                notes=notes,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["name"],
                set_={
                    "match_type": match_type,
                    "confidence": confidence,
                    "is_active": True,
                    "notes": notes,
                    "updated_at": func.now(),
                },
            )
            await session.execute(stmt)

        return {"name": name, "match_type": match_type, "status": "added"}

    async def get_domain_count(self) -> int:
        """Get count of active disposable domains."""
        async with get_session() as session:
            query = select(func.count(DisposableEmailDomain.id)).where(
                DisposableEmailDomain.is_active == True  # noqa: E712
            )
            result = await session.execute(query)
            return result.scalar() or 0

    async def get_last_sync(self, data_type: str = "disposable_domains") -> dict[str, Any] | None:
        """Get info about the last successful sync.

        Args:
            data_type: Type of data to check.

        Returns:
            Dictionary with sync info or None.
        """
        async with get_session() as session:
            query = (
                select(ValidationDataSync)
                .where(ValidationDataSync.data_type == data_type)
                .where(ValidationDataSync.status == "completed")
                .order_by(ValidationDataSync.completed_at.desc())
                .limit(1)
            )
            result = await session.execute(query)
            row = result.fetchone()

            if row:
                sync = row[0]
                return {
                    "id": str(sync.id),
                    "source_name": sync.source_name,
                    "completed_at": sync.completed_at.isoformat() if sync.completed_at else None,
                    "records_total": sync.records_total,
                }

        return None


# Singleton instance
_validation_data_service: ValidationDataService | None = None


def get_validation_data_service() -> ValidationDataService:
    """Get the validation data service singleton."""
    global _validation_data_service
    if _validation_data_service is None:
        _validation_data_service = ValidationDataService()
    return _validation_data_service
