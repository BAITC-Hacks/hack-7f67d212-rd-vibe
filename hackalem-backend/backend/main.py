from recommender.data_loader import load_contractors
from recommender.filters import filter_contractors
from recommender.models import RecommendationRequest


contractors = load_contractors()


request = RecommendationRequest(
    city="Алматы",
    date="2026-10-10",
    event_format="свадьба",
    category="Флорист",
    budget=250000,
    language="русский"
)


results, rejected = filter_contractors(
    contractors,
    request
)


print("Всего подрядчиков:", len(contractors))

print("Подходящих:", len(results))

print("\nПричины отказа:")
print(rejected)


print("\nПодходящие подрядчики:")

for contractor in results:
    print(
        contractor.anon_name,
        "-",
        contractor.price_from_kzt,
        "₸"
    )
