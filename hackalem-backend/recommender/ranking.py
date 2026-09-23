from recommender.models import Contractor, RecommendationRequest


def calculate_budget_score(
    contractor: Contractor,
    request: RecommendationRequest
) -> float:

    if request.budget <= 0:
        return 0.0

    score = 1 - (
        contractor.price_from_kzt / request.budget
    )

    return max(0.0, min(score, 1.0))


def rank_contractors(
    contractors: list[Contractor],
    request: RecommendationRequest
) -> list[Contractor]:

    ranked = sorted(
        contractors,
        key=lambda contractor: (
            -calculate_budget_score(contractor, request),
            contractor.id
        )
    )

    return ranked[:3]
