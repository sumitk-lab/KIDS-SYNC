"""Audit endpoints for cryptographic verification and court-admissible audit trails."""

import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, require_roles
from src.schemas.audit import AuditChainVerificationResponse, AuditLogEntryResponse
from src.schemas.common import ApiResponse
from src.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Cryptographic Audit Ledger"])


@router.get(
    "/verify",
    response_model=ApiResponse[AuditChainVerificationResponse],
    summary="Verify cryptographic hash-chain integrity of the audit ledger",
    dependencies=[Depends(require_roles("PRIMARY_GUARDIAN", "ADMIN"))],
)
async def verify_audit_chain(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AuditChainVerificationResponse]:
    """
    Validate the HMAC-SHA256 cryptographic chain across all historical audit entries.
    Confirms zero tampering, insertions, omissions, or modifications.
    """
    service = AuditService(db)
    result = await service.verify_chain_integrity()
    return ApiResponse(
        success=result.is_valid,
        message=result.verification_message,
        data=result,
    )


@router.get(
    "/entity/{target_entity}/{entity_id}",
    response_model=ApiResponse[List[AuditLogEntryResponse]],
    summary="Get cryptographic audit trail for a specific entity",
    dependencies=[Depends(require_roles("PRIMARY_GUARDIAN", "ADMIN"))],
)
async def get_entity_audit_trail(
    target_entity: str,
    entity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[AuditLogEntryResponse]]:
    """Retrieve chronologically ordered cryptographic audit history for an entity."""
    service = AuditService(db)
    entries = await service.get_entity_audit_trail(target_entity=target_entity, entity_id=entity_id)
    dtos = [AuditLogEntryResponse.model_validate(e) for e in entries]
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(dtos)} audit records for {target_entity}:{entity_id}.",
        data=dtos,
    )
