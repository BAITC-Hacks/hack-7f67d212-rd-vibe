from recommender.models import Contractor, RecommendationRequest


def calculate_budget_score(
    contractor: Contractor,
    request: RecommendationRequest
) -> float:

    if request.budget <= 0:
        return 0.0

    ratio = contractor.price_from_kzt / request.budget

    return max(0.0, min(1.0 - ratio, 1.0))


def rank_contractors(
    contractors: list[Contractor],
    request: RecommendationRequest,
    semantic_scores: dict[str, float] | None = None
) -> list[Contractor]:

    semantic_scores = semantic_scores or {}

    def final_score(contractor: Contractor):

        semantic_score = semantic_scores.get(
            contractor.id,
            0.0
        )

        budget_score = calculate_budget_score(
            contractor,
            request
        )

        return (
            semantic_score * 0.7
            + budget_score * 0.3
        )

    ranked = sorted(
        contractors,
        key=lambda contractor: (
            -final_score(contractor),
            contractor.id
        )
    )

    return ranked[:3]
