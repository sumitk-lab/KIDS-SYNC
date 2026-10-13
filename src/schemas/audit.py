"""Audit log schemas and cryptographic verification results."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from src.schemas.common import KidSyncBaseSchema


class AuditLogEntryResponse(KidSyncBaseSchema):
    """Schema returned for an individual audit ledger record."""

    id: int
    entity_id: uuid.UUID
    target_entity: str
    event_type: str
    actor_id: uuid.UUID
    payload_snapshot: Dict[str, Any]
    client_ip_hash: str
    prev_entry_hash: str
    entry_hash: str
    created_at: datetime


class AuditChainVerificationResponse(KidSyncBaseSchema):
    """Schema for reporting cryptographic Merkle / hash-chain verification."""

    is_valid: bool
    total_entries_checked: int
    first_entry_id: Optional[int] = None
    last_entry_id: Optional[int] = None
    root_hash: Optional[str] = None
    compromised_entry_id: Optional[int] = None
    verification_message: str
