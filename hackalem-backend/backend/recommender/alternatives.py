"""Counterfactuals: re-run every hard filter before suggesting a change."""
from datetime import date, timedelta

from recommender.config import CALENDAR_START, CALENDAR_END
from recommender.filters import filter_contractors, normalize
from recommender.models import RecommendationRequest


def suggestions(contractors, request, category_missing=False):
    base = request.model_dump(exclude={"compare_date"})
    results = []
    seen = set()

    def add(changes, kind, title):
        key = tuple(sorted(changes.items()))
        if key in seen:
            return False
        new_request = RecommendationRequest(**{**base, **changes})
        suitable, _ = filter_contractors(contractors, new_request)
        if not suitable:
            return False
        seen.add(key)
        results.append({"kind": kind, "title": title, "changes": changes, "request": new_request.model_dump(exclude={"compare_date"}), "count": len(suitable), "min_price": min(c.price_from_kzt for c in suitable), "candidate_ids": sorted(c.id for c in suitable)})
        return True

    if category_missing:
        cities = sorted({c.city for c in contractors if any(normalize(v) == normalize(request.category) for v in c.categories)})
        for city in cities:
            add({"city": city}, "city", f"Выбрать город {city}")
        return results[:3]

    pool = [c for c in contractors if normalize(c.city) == normalize(request.city) and any(normalize(v) == normalize(request.category) for v in c.categories)]
    for price in sorted({c.price_from_kzt for c in pool if c.price_from_kzt > request.budget}):
        if add({"budget": price}, "budget", f"Увеличить бюджет на {price - request.budget:,} ₸".replace(",", " ")):
            break

    current = date.fromisoformat(request.date)
    dates = [date.fromisoformat(CALENDAR_START) + timedelta(days=i) for i in range(100)]
    dates = sorted((d for d in dates if d != current and d.isoformat() <= CALENDAR_END), key=lambda d: (abs((d-current).days), d < current, d))
    for day in dates:
        if add({"date": day.isoformat()}, "date", f"Перенести на {day.strftime('%d.%m.%Y')}"):
            break
    if request.duration:
        for hours in sorted({c.max_hours for c in pool if c.max_hours and c.max_hours < request.duration}, reverse=True):
            if add({"duration": hours}, "duration", f"Сократить длительность до {hours} ч"):
                break
    if request.language:
        add({"language": None}, "language", "Снять обязательное условие по языку")
    for event_format in sorted({v for c in pool for v in c.event_formats if normalize(v) != normalize(request.event_format)}):
        if add({"event_format": event_format}, "event_format", f"Изменить формат на «{event_format}»"):
            break
    if not results:
        for day in dates:
            for price in sorted({c.price_from_kzt for c in pool if c.price_from_kzt > request.budget}):
                if add({"date": day.isoformat(), "budget": price}, "date_budget", f"Дата {day.strftime('%d.%m.%Y')} и бюджет {price:,} ₸".replace(",", " ")):
                    return results
    return results[:3]
