from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from main import app, contractors, semantic
from recommender.filters import get_rejection_reasons
from recommender.models import RecommendationRequest


BASE = {"city":"Алматы","date":"2026-10-15","event_format":"корпоратив","category":"Ведущий","budget":2000000,"duration":6,"language":"русский","preferences":"Спокойная ненавязчивая подача, интеллигентный юмор и уютная атмосфера"}
PROFILES = {c.id:c for c in contractors}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as connection:
        assert semantic.ready, semantic.error
        yield connection


def test_real_embeddings_change_order_when_wish_changes(client):
    calm = client.post("/recommend", json=BASE).json()
    dance = client.post("/recommend", json={**BASE,"preferences":"Без долгих речей, только развлечения и танцы"}).json()
    assert [c["id"] for c in calm["results"]] != [c["id"] for c in dance["results"]]
    assert dance["results"][0]["id"] == "HK-29829"
    assert calm["ranking"]["mode"] == "semantic"


def test_real_semantic_paraphrase_and_source_evidence(client):
    ids = list(PROFILES)
    matches = semantic.search("Фотограф поможет невесте перестать стесняться камеры и подскажет как позировать", ids)
    top = sorted(matches,key=lambda id_:-matches[id_]["similarity"])[0]
    assert top in {"HK-98562","HK-61323"}
    evidence = matches[top]["evidence"]
    assert PROFILES[top].description[evidence["start"]:evidence["end"]] == evidence["text"]


def test_semantics_never_overrides_hard_filters_and_explanations_are_distinct(client):
    for day in ["2026-09-23","2026-10-15","2026-10-16","2026-12-31"]:
        query = {**BASE,"date":day,"budget":1000000}
        data = client.post("/recommend",json=query).json()
        assert len(data["results"]) <= 3
        explanations = []
        for card in data["results"]:
            assert get_rejection_reasons(PROFILES[card["id"]], RecommendationRequest(**query)) == []
            assert card["evidence"]["text"] in PROFILES[card["id"]].description
            assert round(card["score"]["semantic_points"]+card["score"]["budget_points"],3) == round(card["score"]["total"],3)
            explanations.append(card["explanation"])
        assert len(set(explanations)) == len(explanations)


def test_same_query_same_payload_and_flags(client):
    one = client.post("/recommend",json=BASE).json()
    two = client.post("/recommend",json=BASE).json()
    assert one == two
    for card in one["results"]:
        c = PROFILES[card["id"]]
        assert (card["synthetic"],card["city_imputed"],card["price_imputed"]) == (c.synthetic,c.city_imputed,c.price_imputed)


def test_rejections_use_only_city_category_pool(client):
    q = {"city":"Алматы","date":"2026-10-15","event_format":"свадьба","category":"Флорист","budget":600000}
    data = client.post("/recommend",json=q).json()
    assert data["stats"]["catalog_count"] == 2
    assert data["stats"]["matching_count"] == 2
    assert data["rejected"] == {}
    assert data["stats"]["busy_count"] == 0


@pytest.mark.parametrize("query", [
    {"city":"Алматы","date":"2026-12-31","event_format":"свадьба","category":"Флорист","budget":100000},
    {"city":"Алматы","date":"2026-10-15","event_format":"свадьба","category":"Флорист","budget":100000},
    {"city":"Зарубежье","date":"2026-10-15","event_format":"свадьба","category":"Флорист","budget":600000},
    {"city":"Алматы","date":"2026-12-31","event_format":"корпоратив","category":"Ведущий","budget":1000000,"language":"английский","duration":12},
])
def test_every_suggestion_really_unlocks_candidates(client, query):
    data = client.post("/recommend",json=query).json()
    assert data["status"] != "ok"
    for suggestion in data["suggestions"]:
        original = RecommendationRequest(**query).model_dump(exclude={"compare_date"})
        expected = {**original, **suggestion["changes"]}
        assert suggestion["request"] == expected
        req = RecommendationRequest(**expected)
        eligible = [c for c in contractors if not get_rejection_reasons(c,req)]
        assert suggestion["count"] == len(eligible) > 0
        assert suggestion["candidate_ids"] == sorted(c.id for c in eligible)
        assert suggestion["min_price"] == min(c.price_from_kzt for c in eligible)
        assert client.post("/recommend",json=expected).json()["status"] == "ok"
    if query["category"] == "Флорист":
        assert data["suggestions"]


def test_date_comparison_only_reports_real_busy_dates(client):
    data = client.post("/recommend",json={**BASE,"date":"2026-10-16","compare_date":"2026-10-15"}).json()
    compare = data["date_comparison"]
    assert compare["now_busy"] or compare["now_available"]
    for c in compare["now_busy"]:
        assert "2026-10-16" in PROFILES[c["id"]].busy_dates
        assert "2026-10-15" not in PROFILES[c["id"]].busy_dates
    for c in compare["now_available"]:
        assert "2026-10-15" in PROFILES[c["id"]].busy_dates
        assert "2026-10-16" not in PROFILES[c["id"]].busy_dates


@pytest.mark.parametrize("changes", [{"budget":True},{"budget":1.5},{"duration":-1},{"duration":1.5},{"preferences":"a"*601},{"date":"20261015"},{"date":"2026-10-15junk"},{"unknown":1}])
def test_bad_input_is_rejected(client, changes):
    assert client.post("/recommend",json={**BASE,**changes}).status_code == 422


def test_unavailable_model_never_silently_imitates_semantics(client, monkeypatch):
    import main
    monkeypatch.setattr(main.semantic,"ready",False)
    monkeypatch.setattr(main,"load_semantic",lambda:False)
    assert client.post("/recommend",json=BASE).status_code == 503
    assert client.post("/recommend",json={**BASE,"preferences":""}).status_code == 200


def test_frontend_is_served_by_backend(client):
    response = client.get("/app/")
    assert response.status_code == 200
    assert 'id="preferences"' in response.text
    assert client.get("/app/app.js").status_code == 200
