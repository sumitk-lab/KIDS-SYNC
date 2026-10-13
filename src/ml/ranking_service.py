"""Autonomous Caregiver Matching and Neural Ranking Service."""

import uuid
from typing import List, Optional
import torch
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ResourceNotFoundError
from src.ml.models import (
    TwoTowerRankingModel,
    vectorize_caregiver,
    vectorize_family_request,
)
from src.ml.trust_engine import DynamicTrustEngine, TrustBreakdown
from src.models.booking import BookingModel
from src.models.caregiver import CaregiverModel
from src.models.audit import AuditLogEntryModel
from src.schemas.matching import (
    CaregiverMatchCandidate,
    CaregiverMatchRequest,
    CaregiverMatchResponse,
    TrustScoreResponse,
)


class AutonomousMatchingService:
    """
    Orchestration service combining database candidate retrieval,
    Dynamic Trust Score computation, and PyTorch Two-Tower neural ranking.
    """

    _model: Optional[TwoTowerRankingModel] = None

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.model = self._get_or_init_model()

    @classmethod
    def _get_or_init_model(cls) -> TwoTowerRankingModel:
        """Lazy singleton initialization of PyTorch neural ranking model."""
        if cls._model is None:
            # Set deterministic seed for consistent baseline inference
            torch.manual_seed(42)
            model = TwoTowerRankingModel()
            model.eval()
            cls._model = model
        return cls._model

    async def calculate_caregiver_trust(self, caregiver: CaregiverModel) -> TrustBreakdown:
        """Compute real-time Dynamic Trust Score factoring in verified bookings and audit history."""
        # 1. Query booking completion and cancellation statistics
        completed_res = await self.session.execute(
            select(func.count(BookingModel.id)).where(
                BookingModel.caregiver_id == caregiver.id,
                BookingModel.status == "COMPLETED",
            )
        )
        completed_count = completed_res.scalar() or 0

        cancelled_res = await self.session.execute(
            select(func.count(BookingModel.id)).where(
                BookingModel.caregiver_id == caregiver.id,
                BookingModel.status == "CANCELLED",
            )
        )
        cancelled_count = cancelled_res.scalar() or 0

        # 2. Query audit ledger for recorded safety incidents or infractions
        incident_res = await self.session.execute(
            select(func.count(AuditLogEntryModel.id)).where(
                AuditLogEntryModel.target_entity == "caregivers",
                AuditLogEntryModel.entity_id == caregiver.id,
                AuditLogEntryModel.event_type.in_(["SAFETY_INCIDENT", "DISPUTE_RAISED"]),
            )
        )
        incident_count = incident_res.scalar() or 0

        return DynamicTrustEngine.compute_trust_score(
            background_check_status=caregiver.background_check_status,
            background_checked_at=caregiver.background_checked_at,
            years_of_experience=caregiver.years_of_experience,
            certifications=caregiver.certifications,
            specialties=caregiver.specialties,
            rating_average=caregiver.rating_average,
            total_reviews=caregiver.total_reviews_count,
            completed_bookings=completed_count,
            cancelled_by_caregiver_bookings=cancelled_count,
            safety_incident_count=incident_count,
            is_identity_verified=caregiver.user.is_verified if caregiver.user else True,
        )

    async def get_caregiver_trust_breakdown(self, caregiver_id: uuid.UUID) -> TrustScoreResponse:
        """Fetch individual caregiver trust report."""
        res = await self.session.execute(
            select(CaregiverModel)
            .where(CaregiverModel.id == caregiver_id)
            .options(selectinload(CaregiverModel.user))
        )
        caregiver = res.scalars().first()
        if not caregiver:
            raise ResourceNotFoundError("Caregiver", caregiver_id)

        breakdown = await self.calculate_caregiver_trust(caregiver)
        return TrustScoreResponse(caregiver_id=caregiver.id, breakdown=breakdown)

    async def match_and_rank_caregivers(
        self,
        request: CaregiverMatchRequest,
    ) -> CaregiverMatchResponse:
        """
        Execute end-to-end autonomous matching:
        1. Retrieve available candidates from database
        2. Compute Dynamic Trust Score for each candidate
        3. Filter candidates below min_trust_score
        4. Vectorize candidates and family request into PyTorch tensors
        5. Run PyTorch Two-Tower forward pass
        6. Synthesize explainable recommendation notes and rank top-k
        """
        # 1. Fetch available caregivers
        query = (
            select(CaregiverModel)
            .where(CaregiverModel.is_available.is_(True))
            .options(selectinload(CaregiverModel.user))
        )
        result = await self.session.execute(query)
        candidates_raw: List[CaregiverModel] = list(result.scalars().all())

        if not candidates_raw:
            return CaregiverMatchResponse(
                total_candidates_evaluated=0,
                matched_candidates=[],
                top_match_id=None,
                query_summary="No available caregivers registered in the system.",
            )

        # 2. Vectorize family request
        fam_tensor = vectorize_family_request(
            child_age_years=request.child_age_years,
            has_special_needs=request.has_special_needs,
            required_specialties=request.required_specialties,
            max_hourly_rate_cents=request.max_hourly_rate_cents,
            session_duration_hours=request.session_duration_hours,
            min_trust_score=request.min_trust_score,
        )

        candidates_evaluated: List[CaregiverMatchCandidate] = []
        batch_fam_tensors = []
        batch_cg_tensors = []
        batch_ctx_tensors = []
        eligible_meta = []

        req_specs_set = {s.upper().strip() for s in (request.required_specialties or [])}

        for cg in candidates_raw:
            # Calculate Dynamic Trust
            trust_breakdown = await self.calculate_caregiver_trust(cg)

            # Pre-filter by trust threshold
            if trust_breakdown.overall_trust_score < request.min_trust_score:
                continue

            # Context features:
            # [trust_score_norm, budget_affordability, specialty_overlap_ratio]
            trust_norm = trust_breakdown.overall_trust_score / 100.0
            affordability = 1.0 if cg.hourly_rate_cents <= request.max_hourly_rate_cents else max(
                0.0, 1.0 - ((cg.hourly_rate_cents - request.max_hourly_rate_cents) / request.max_hourly_rate_cents)
            )

            cg_specs_set = {s.upper().strip() for s in (cg.specialties or [])}
            overlap = len(req_specs_set.intersection(cg_specs_set))
            specialty_overlap_ratio = (overlap / len(req_specs_set)) if req_specs_set else 1.0

            ctx_tensor = torch.tensor(
                [trust_norm, affordability, specialty_overlap_ratio],
                dtype=torch.float32,
            )

            cg_tensor = vectorize_caregiver(
                specialties=cg.specialties,
                years_of_experience=cg.years_of_experience,
                hourly_rate_cents=cg.hourly_rate_cents,
                rating_average=cg.rating_average,
                total_reviews_count=cg.total_reviews_count,
                trust_score=trust_breakdown.overall_trust_score,
                background_check_status=cg.background_check_status,
            )

            batch_fam_tensors.append(fam_tensor)
            batch_cg_tensors.append(cg_tensor)
            batch_ctx_tensors.append(ctx_tensor)
            eligible_meta.append((cg, trust_breakdown, specialty_overlap_ratio, affordability))

        if not eligible_meta:
            return CaregiverMatchResponse(
                total_candidates_evaluated=len(candidates_raw),
                matched_candidates=[],
                top_match_id=None,
                query_summary=f"Evaluated {len(candidates_raw)} caregivers, but none met the minimum trust score of {request.min_trust_score}.",
            )

        # 3. Neural Model Batch Inference
        with torch.no_grad():
            fam_batch = torch.stack(batch_fam_tensors)
            cg_batch = torch.stack(batch_cg_tensors)
            ctx_batch = torch.stack(batch_ctx_tensors)

            match_scores, cosine_sims = self.model(fam_batch, cg_batch, ctx_batch)

        for i, (cg, trust_breakdown, spec_overlap, afford) in enumerate(eligible_meta):
            neural_score = float(match_scores[i].item())
            sim = float(cosine_sims[i].item())

            # Combined match score (0 - 100)
            # Combines neural score (50%) + trust score (35%) + budget fit (15%)
            final_match_pct = round(
                (0.50 * (neural_score * 100.0) + 0.35 * trust_breakdown.overall_trust_score + 0.15 * (afford * 100.0)),
                2,
            )
            final_match_pct = max(0.0, min(100.0, final_match_pct))

            # Generate natural explanation
            reasons = []
            if trust_breakdown.trust_tier in ["PLATINUM", "GOLD"]:
                reasons.append(f"{trust_breakdown.trust_tier} Trust ({trust_breakdown.overall_trust_score} pts)")
            if spec_overlap >= 0.8 and req_specs_set:
                reasons.append("High specialty match")
            if afford >= 1.0:
                reasons.append("Within requested budget")
            if cg.years_of_experience >= 5:
                reasons.append(f"{cg.years_of_experience} yrs verified experience")

            recommendation_text = ", ".join(reasons) if reasons else "Compatible schedule and credentials."

            user = cg.user
            candidate = CaregiverMatchCandidate(
                caregiver_id=cg.id,
                user_id=cg.user_id,
                first_name=user.first_name if user else "Caregiver",
                last_name=user.last_name if user else "",
                hourly_rate_cents=cg.hourly_rate_cents,
                years_of_experience=cg.years_of_experience,
                specialties=cg.specialties,
                rating_average=cg.rating_average,
                total_reviews_count=cg.total_reviews_count,
                trust_breakdown=trust_breakdown,
                cosine_similarity=round(sim, 4),
                match_score=final_match_pct,
                recommendation_reason=recommendation_text,
            )
            candidates_evaluated.append(candidate)

        # 4. Sort descending by match score
        candidates_evaluated.sort(key=lambda c: c.match_score, reverse=True)
        top_candidates = candidates_evaluated[: request.top_k]

        return CaregiverMatchResponse(
            total_candidates_evaluated=len(candidates_raw),
            matched_candidates=top_candidates,
            top_match_id=top_candidates[0].caregiver_id if top_candidates else None,
            query_summary=(
                f"Evaluated {len(candidates_raw)} caregivers; matched top {len(top_candidates)} "
                f"ranked by Two-Tower neural embedding & Dynamic Trust."
            ),
        )
