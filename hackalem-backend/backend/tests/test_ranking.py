from recommender.models import Contractor, RecommendationRequest
from recommender.ranking import rank_contractors


def make_contractor(
    contractor_id,
    price
):
    return Contractor(
        id=contractor_id,
        anon_name=contractor_id,
        categories=["Фотограф"],
        city="Алматы",
        city_imputed=False,
        synthetic=False,
        price_from_kzt=price,
        price_imputed=False,
        event_formats=["свадьба"],
        languages=["русский"],
        max_hours=8,
        busy_dates=[],
        description="Фотограф"
    )


def make_request():
    return RecommendationRequest(
        city="Алматы",
        date="2026-10-10",
        event_format="свадьба",
        category="Фотограф",
        budget=500000,
        language="русский"
    )


def test_max_three_results():
    contractors = [
        make_contractor("HK-1", 100000),
        make_contractor("HK-2", 150000),
        make_contractor("HK-3", 200000),
        make_contractor("HK-4", 250000),
        make_contractor("HK-5", 300000),
    ]

    results = rank_contractors(
        contractors,
        make_request()
    )

    assert len(results) == 3


def test_deterministic_order():
    contractors = [
        make_contractor("HK-3", 200000),
        make_contractor("HK-1", 200000),
        make_contractor("HK-2", 200000),
    ]

    request = make_request()

    first = rank_contractors(
        contractors,
        request
    )

    second = rank_contractors(
        contractors,
        request
    )

    first_ids = [
        contractor.id
        for contractor in first
    ]

    second_ids = [
        contractor.id
        for contractor in second
    ]

    assert first_ids == second_ids
