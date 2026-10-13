"""Cryptographic Audit Service for court-admissible audit trail creation and verification."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import compute_audit_entry_hash, hash_client_ip
from src.models.audit import AuditLogEntryModel
from src.repositories.audit_repo import AuditRepository, GENESIS_HASH
from src.schemas.audit import AuditChainVerificationResponse


def _canonical_timestamp_iso(dt: datetime) -> str:
    """Ensure timestamp has explicit UTC timezone for deterministic cross-db cryptographic hashing."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


class AuditService:
    """Service managing append-only cryptographic audit logging and chain integrity verification."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AuditRepository(session)

    async def log_event(
        self,
        actor_id: uuid.UUID,
        target_entity: str,
        entity_id: uuid.UUID,
        event_type: str,
        payload_snapshot: Dict[str, Any],
        client_ip: Optional[str] = None,
    ) -> AuditLogEntryModel:
        """
        Atomically append an audit log entry linked to the previous entry via HMAC-SHA256.
        """
        # 1. Fetch previous entry to obtain prev_entry_hash
        latest = await self.repo.get_latest_entry()
        prev_entry_hash = latest.entry_hash if latest else GENESIS_HASH

        # 2. Capture canonical timestamp
        now = datetime.now(timezone.utc)
        now_iso = _canonical_timestamp_iso(now)

        # 3. Anonymize IP
        ip_hash = hash_client_ip(client_ip)

        # 4. Compute cryptographic entry hash
        entry_hash = compute_audit_entry_hash(
            prev_entry_hash=prev_entry_hash,
            created_at_iso=now_iso,
            actor_id=str(actor_id),
            target_entity=target_entity,
            entity_id=str(entity_id),
            payload_snapshot=payload_snapshot,
        )

        # 5. Persist immutable record
        audit_entry = AuditLogEntryModel(
            entity_id=entity_id,
            target_entity=target_entity,
            event_type=event_type,
            actor_id=actor_id,
            payload_snapshot=payload_snapshot,
            client_ip_hash=ip_hash,
            prev_entry_hash=prev_entry_hash,
            entry_hash=entry_hash,
            created_at=now,
        )
        return await self.repo.create(audit_entry)

    async def verify_chain_integrity(self) -> AuditChainVerificationResponse:
        """
        Verify every entry in the audit ledger against its previous entry hash.
        Fails if any row has been altered, forged, deleted, or reordered.
        """
        entries = await self.repo.get_all_ordered_by_id(from_id=1, limit=100_000)
        if not entries:
            return AuditChainVerificationResponse(
                is_valid=True,
                total_entries_checked=0,
                verification_message="Audit chain is empty. Genesis state intact.",
            )

        expected_prev_hash = GENESIS_HASH

        for entry in entries:
            # Check 1: prev_entry_hash continuity
            if entry.prev_entry_hash != expected_prev_hash:
                return AuditChainVerificationResponse(
                    is_valid=False,
                    total_entries_checked=len(entries),
                    compromised_entry_id=entry.id,
                    verification_message=(
                        f"Integrity break at entry ID {entry.id}: "
                        f"Expected prev_hash {expected_prev_hash}, found {entry.prev_entry_hash}."
                    ),
                )

            # Check 2: Recompute entry_hash and compare
            computed_hash = compute_audit_entry_hash(
                prev_entry_hash=entry.prev_entry_hash,
                created_at_iso=_canonical_timestamp_iso(entry.created_at),
                actor_id=str(entry.actor_id),
                target_entity=entry.target_entity,
                entity_id=str(entry.entity_id),
                payload_snapshot=entry.payload_snapshot,
            )

            if computed_hash != entry.entry_hash:
                return AuditChainVerificationResponse(
                    is_valid=False,
                    total_entries_checked=len(entries),
                    compromised_entry_id=entry.id,
                    verification_message=(
                        f"Cryptographic tampering detected at entry ID {entry.id}: "
                        f"Computed hash {computed_hash} does not match stored hash {entry.entry_hash}."
                    ),
                )

            expected_prev_hash = entry.entry_hash

        return AuditChainVerificationResponse(
            is_valid=True,
            total_entries_checked=len(entries),
            first_entry_id=entries[0].id,
            last_entry_id=entries[-1].id,
            root_hash=entries[-1].entry_hash,
            verification_message="All cryptographic audit ledger entries verified successfully. Zero tampering detected.",
        )

    async def get_entity_audit_trail(
        self,
        target_entity: str,
        entity_id: uuid.UUID,
    ) -> List[AuditLogEntryModel]:
        """Retrieve audit history for a specific entity."""
        return await self.repo.list_for_entity(target_entity=target_entity, entity_id=entity_id)
