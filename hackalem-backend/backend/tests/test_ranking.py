from recommender.models import Contractor, RecommendationRequest
from recommender.ranking import rank_contractors


def make_contractor(identifier: str, price: int, description: str) -> Contractor:
    return Contractor(
        id=identifier,
        anon_name=f"Профиль {identifier}",
        categories=["Ведущий"],
        city="Алматы",
        city_imputed=False,
        synthetic=True,
        price_from_kzt=price,
        price_imputed=False,
        event_formats=["корпоратив"],
        languages=["русский"],
        max_hours=8,
        busy_dates=[],
        description=description,
    )


def test_ranking_is_deterministic_and_limited_to_three():
    request = RecommendationRequest(
        city="Алматы",
        date="2026-10-15",
        event_format="корпоратив",
        category="Ведущий",
        budget=1_000_000,
        language="русский",
        duration=6,
    )
    profiles = [
        make_contractor("D", 800_000, "Профиль ведущего."),
        make_contractor("B", 500_000, "Ведущий корпоративов на русском языке."),
        make_contractor("A", 500_000, "Ведущий корпоративов на русском языке."),
        make_contractor("C", 650_000, "Ведущий корпоративов."),
    ]

    first = [item.id for item in rank_contractors(profiles, request)]
    second = [item.id for item in rank_contractors(list(reversed(profiles)), request)]

    assert first == second
    assert first == ["A", "B", "C"]
