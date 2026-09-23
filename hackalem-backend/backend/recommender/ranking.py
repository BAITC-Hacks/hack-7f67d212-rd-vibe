"""Explainable deterministic ranking; hard constraints are applied upstream."""
from recommender.models import Contractor, RecommendationRequest


def calculate_budget_score(contractor: Contractor, request: RecommendationRequest) -> float:
    return max(0.0, min(1.0 - contractor.price_from_kzt / request.budget, 1.0))


def score_breakdown(contractor, request, semantic_match=None):
    budget = calculate_budget_score(contractor, request)
    similarity = semantic_match["similarity"] if semantic_match else None
    # E5 cosine scores are concentrated toward the upper end; this fixed,
    # documented scaling is an ordering score, never a probability of suitability.
    semantic = max(0.0, min(1.0, (similarity - 0.65) / 0.30)) if similarity is not None else None
    weights = {"semantic": 0.85, "budget": 0.15} if semantic is not None else {"semantic": 0.0, "budget": 1.0}
    semantic_points = (semantic or 0) * weights["semantic"] * 100
    budget_points = budget * weights["budget"] * 100
    return {"total": round(semantic_points + budget_points, 4), "semantic_points": round(semantic_points, 4), "budget_points": round(budget_points, 4), "cosine_similarity": similarity, "weights": weights}


def rank_contractors(contractors, request, matches=None):
    matches = matches or {}
    return sorted(contractors, key=lambda c: (-score_breakdown(c, request, matches.get(c.id))["total"], c.price_from_kzt, c.id))[:3]
