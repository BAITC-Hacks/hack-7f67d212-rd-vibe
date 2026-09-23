from recommender.models import Contractor, RecommendationRequest
from recommender.filters import get_rejection_reasons


def make_contractor():
    return Contractor(
        id="HK-TEST",
        anon_name="Test Contractor",
        categories=["Фотограф"],
        city="Алматы",
        city_imputed=False,
        synthetic=False,
        price_from_kzt=200000,
        price_imputed=False,
        event_formats=["свадьба"],
        languages=["русский"],
        max_hours=8,
        busy_dates=["2026-10-15"],
        description="Тестовый фотограф"
    )


def make_request():
    return RecommendationRequest(
        city="Алматы",
        date="2026-10-10",
        event_format="свадьба",
        category="Фотограф",
        budget=250000,
        duration=6,
        language="русский"
    )


def test_valid_contractor():
    contractor = make_contractor()
    request = make_request()

    reasons = get_rejection_reasons(
        contractor,
        request
    )

    assert reasons == []


def test_busy_contractor():
    contractor = make_contractor()
    request = make_request()

    request.date = "2026-10-15"

    reasons = get_rejection_reasons(
        contractor,
        request
    )

    assert "busy" in reasons


def test_over_budget():
    contractor = make_contractor()
    request = make_request()

    request.budget = 100000

    reasons = get_rejection_reasons(
        contractor,
        request
    )

    assert "over_budget" in reasons


def test_exact_budget_allowed():
    contractor = make_contractor()
    request = make_request()

    request.budget = 200000

    reasons = get_rejection_reasons(
        contractor,
        request
    )

    assert "over_budget" not in reasons


def test_duration_too_long():
    contractor = make_contractor()
    request = make_request()

    request.duration = 10

    reasons = get_rejection_reasons(
        contractor,
        request
    )

    assert "duration_too_long" in reasons


def test_none_max_hours_allowed():
    contractor = make_contractor()
    contractor.max_hours = None

    request = make_request()
    request.duration = 20

    reasons = get_rejection_reasons(
        contractor,
        request
    )

    assert "duration_too_long" not in reasons
