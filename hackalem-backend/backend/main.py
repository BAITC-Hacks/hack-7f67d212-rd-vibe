from recommender.data_loader import load_contractors
from recommender.filters import filter_contractors
from recommender.ranking import rank_contractors
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

suitable, rejected = filter_contractors(
    contractors,
    request
)

results = rank_contractors(
    suitable,
    request
)


print("Всего подрядчиков:", len(contractors))
print("Прошли фильтры:", len(suitable))
print("Показано пользователю:", len(results))

print("\nTOP подрядчики:")

for index, contractor in enumerate(results, start=1):

    print(
        f"{index}. "
        f"{contractor.anon_name} - "
        f"{contractor.price_from_kzt} ₸"
    )
