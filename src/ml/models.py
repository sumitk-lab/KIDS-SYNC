"""PyTorch Two-Tower Neural Ranking Model for Caregiver-Family Autonomous Matching."""

import math
from typing import Dict, List, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

KNOWN_SPECIALTIES: List[str] = [
    "INFANT_CARE",
    "TODDLER_CARE",
    "SPECIAL_NEEDS",
    "FIRST_AID",
    "HOMEWORK_TUTOR",
    "SENSORY_SUPPORT",
    "MEAL_PREP",
    "NEWBORN_OVERNIGHT",
]

EMBEDDING_DIM = 32


class FamilyTower(nn.Module):
    """Encodes family childcare requirements and constraints into a dense embedding."""

    def __init__(self, input_dim: int = 16, embedding_dim: int = EMBEDDING_DIM) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.GELU(),
            nn.LayerNorm(64),
            nn.Linear(64, embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raw_emb = self.net(x)
        return F.normalize(raw_emb, p=2, dim=-1)


class CaregiverTower(nn.Module):
    """Encodes caregiver credentials, experience, trust, and capabilities into a dense embedding."""

    def __init__(self, input_dim: int = 16, embedding_dim: int = EMBEDDING_DIM) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.GELU(),
            nn.LayerNorm(64),
            nn.Linear(64, embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raw_emb = self.net(x)
        return F.normalize(raw_emb, p=2, dim=-1)


class TwoTowerRankingModel(nn.Module):
    """
    Two-Tower Neural Matching & Ranking architecture.
    Calculates semantic cosine similarity between family query vector and caregiver profile vector,
    then combines with Dynamic Trust Score and Affordability via neural scoring head.
    """

    def __init__(self, embedding_dim: int = EMBEDDING_DIM) -> None:
        super().__init__()
        self.family_tower = FamilyTower(input_dim=16, embedding_dim=embedding_dim)
        self.caregiver_tower = CaregiverTower(input_dim=16, embedding_dim=embedding_dim)

        # Scoring Head combines: [cosine_similarity, trust_score_norm, budget_affordability, specialty_overlap]
        self.scoring_head = nn.Sequential(
            nn.Linear(4, 16),
            nn.GELU(),
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )

    def forward(
        self,
        family_features: torch.Tensor,
        caregiver_features: torch.Tensor,
        context_features: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            family_features: [batch_size, 16]
            caregiver_features: [batch_size, 16]
            context_features: [batch_size, 3] -> [trust_score_norm, budget_affordability, specialty_overlap]

        Returns:
            match_scores: [batch_size, 1] in range [0.0, 1.0]
            cosine_sims: [batch_size, 1] in range [-1.0, 1.0]
        """
        fam_emb = self.family_tower(family_features)
        cg_emb = self.caregiver_tower(caregiver_features)

        # Batch dot product cosine similarity
        cosine_sim = torch.sum(fam_emb * cg_emb, dim=-1, keepdim=True)

        combined = torch.cat([cosine_sim, context_features], dim=-1)
        match_scores = self.scoring_head(combined)
        return match_scores, cosine_sim


def vectorize_family_request(
    child_age_years: float,
    has_special_needs: bool,
    required_specialties: List[str],
    max_hourly_rate_cents: int,
    session_duration_hours: float,
    min_trust_score: float,
) -> torch.Tensor:
    """Transform family requirements dictionary into a normalized 16-D PyTorch tensor."""
    # 1. Age bucket one-hot (4 dims: <1, 1-3, 4-7, 8+)
    age_vec = [0.0, 0.0, 0.0, 0.0]
    if child_age_years < 1.0:
        age_vec[0] = 1.0
    elif child_age_years <= 3.0:
        age_vec[1] = 1.0
    elif child_age_years <= 7.0:
        age_vec[2] = 1.0
    else:
        age_vec[3] = 1.0

    # 2. Special needs (1 dim)
    sn_val = 1.0 if has_special_needs else 0.0

    # 3. Required specialties multi-hot (8 dims)
    req_upper = {s.upper().strip() for s in (required_specialties or [])}
    spec_vec = [1.0 if spec in req_upper else 0.0 for spec in KNOWN_SPECIALTIES]

    # 4. Continuous features (3 dims)
    budget_norm = min(1.0, max(0.0, max_hourly_rate_cents / 10000.0))  # $100 cap
    duration_norm = min(1.0, max(0.0, session_duration_hours / 12.0))
    min_trust_norm = min(1.0, max(0.0, min_trust_score / 100.0))

    feature_list = age_vec + [sn_val] + spec_vec + [budget_norm, duration_norm, min_trust_norm]
    return torch.tensor(feature_list, dtype=torch.float32)


def vectorize_caregiver(
    specialties: List[str],
    years_of_experience: int,
    hourly_rate_cents: int,
    rating_average: float,
    total_reviews_count: int,
    trust_score: float,
    background_check_status: str,
) -> torch.Tensor:
    """Transform caregiver profile attributes into a normalized 16-D PyTorch tensor."""
    # 1. Specialties multi-hot (8 dims)
    cg_specs = {s.upper().strip() for s in (specialties or [])}
    spec_vec = [1.0 if spec in cg_specs else 0.0 for spec in KNOWN_SPECIALTIES]

    # 2. Continuous features (5 dims)
    exp_norm = min(1.0, max(0.0, years_of_experience / 25.0))
    rate_norm = min(1.0, max(0.0, hourly_rate_cents / 10000.0))
    rating_norm = min(1.0, max(0.0, rating_average / 5.0))
    review_vol_norm = min(1.0, math.log1p(total_reviews_count) / 4.0)
    trust_norm = min(1.0, max(0.0, trust_score / 100.0))

    # 3. Background check status one-hot (3 dims: PASSED, PENDING, FAILED)
    status_upper = (background_check_status or "PENDING").upper()
    bg_vec = [
        1.0 if status_upper == "PASSED" else 0.0,
        1.0 if status_upper == "PENDING" else 0.0,
        1.0 if status_upper not in ["PASSED", "PENDING"] else 0.0,
    ]

    feature_list = spec_vec + [exp_norm, rate_norm, rating_norm, review_vol_norm, trust_norm] + bg_vec
    return torch.tensor(feature_list, dtype=torch.float32)
