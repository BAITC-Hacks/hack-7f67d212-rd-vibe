from recommender.explanations import generate_explanation
from recommender.models import Contractor, RecommendationRequest


def test_explanation_contains_verified_personal_evidence():
    profile = Contractor(
        id="HK-TEST",
        anon_name="Тестовый профиль",
        categories=["Флорист"],
        city="Алматы",
        city_imputed=False,
        synthetic=True,
        price_from_kzt=250_000,
        price_imputed=False,
        event_formats=["свадьба"],
        languages=["русский"],
        max_hours=None,
        busy_dates=[],
        description="Собираем композиции из сезонных цветов под палитру свадьбы. Второе предложение.",
    )
    request = RecommendationRequest(
        city="Алматы",
        date="2026-10-15",
        event_format="свадьба",
        category="Флорист",
        budget=600_000,
        language="русский",
    )

    explanation = generate_explanation(profile, request)

    assert "15 октября 2026 года" in explanation
    assert "250 000 ₸" in explanation
    assert "350 000 ₸ резерва" in explanation
    assert "сезонных цветов" in explanation
    assert generate_explanation(profile, request) == explanation
