from collections import Counter

from recommender.models import Contractor, RecommendationRequest


def normalize(text: str) -> str:
    return text.strip().casefold()


def get_rejection_reasons(
    contractor: Contractor,
    request: RecommendationRequest
) -> list[str]:

    reasons = []

    # Город
    if normalize(contractor.city) != normalize(request.city):
        reasons.append("wrong_city")

    # Категория
    categories = [
        normalize(category)
        for category in contractor.categories
    ]

    if normalize(request.category) not in categories:
        reasons.append("wrong_category")

    # Занятость
    if request.date in contractor.busy_dates:
        reasons.append("busy")

    # Формат мероприятия
    formats = [
        normalize(event_format)
        for event_format in contractor.event_formats
    ]

    if normalize(request.event_format) not in formats:
        reasons.append("wrong_format")

    # Бюджет
    if contractor.price_from_kzt > request.budget:
        reasons.append("over_budget")

    # Язык
    if request.language is not None:
        languages = [
            normalize(language)
            for language in contractor.languages
        ]

        if normalize(request.language) not in languages:
            reasons.append("wrong_language")

    # Продолжительность
    if (
        request.duration is not None
        and contractor.max_hours is not None
        and request.duration > contractor.max_hours
    ):
        reasons.append("duration_too_long")

    return reasons


def filter_contractors(
    contractors: list[Contractor],
    request: RecommendationRequest
):

    suitable = []
    rejection_stats = Counter()

    for contractor in contractors:

        reasons = get_rejection_reasons(
            contractor,
            request
        )

        if not reasons:
            suitable.append(contractor)

        else:
            for reason in reasons:
                rejection_stats[reason] += 1

    return suitable, dict(rejection_stats)
