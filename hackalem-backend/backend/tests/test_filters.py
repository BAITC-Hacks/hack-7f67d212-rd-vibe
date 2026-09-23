from recommender.filters import get_rejection_reasons
from recommender.models import Contractor, RecommendationRequest


def contractor(**overrides) -> Contractor:
    data = {
        "id": "HK-TEST",
        "anon_name": "Тестовый профиль",
        "categories": ["Ведущий"],
        "city": "Алматы",
        "city_imputed": False,
        "synthetic": True,
        "price_from_kzt": 500_000,
        "price_imputed": False,
        "event_formats": ["корпоратив"],
        "languages": ["русский"],
        "max_hours": 6,
        "busy_dates": ["2026-10-15"],
        "description": "Ведущий корпоративных событий.",
    }
    data.update(overrides)
    return Contractor(**data)


def request(**overrides) -> RecommendationRequest:
    data = {
        "city": "Алматы",
        "date": "2026-10-16",
        "event_format": "корпоратив",
        "category": "Ведущий",
        "budget": 700_000,
        "duration": 6,
        "language": "русский",
    }
    data.update(overrides)
    return RecommendationRequest(**data)


def test_matching_contractor_has_no_rejection_reasons():
    assert get_rejection_reasons(contractor(), request()) == []


def test_busy_contractor_is_rejected():
    assert "busy" in get_rejection_reasons(
        contractor(),
        request(date="2026-10-15"),
    )


def test_all_hard_constraints_are_reported():
    reasons = get_rejection_reasons(
        contractor(),
        request(
            city="Астана",
            event_format="свадьба",
            category="Фотограф",
            budget=100_000,
            duration=8,
            language="казахский",
        ),
    )
    assert set(reasons) == {
        "wrong_city",
        "wrong_category",
        "wrong_format",
        "over_budget",
        "wrong_language",
        "duration_too_long",
    }
