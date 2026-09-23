from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


DENSE_QUERY = {
    "city": "Алматы",
    "date": "2026-10-15",
    "event_format": "корпоратив",
    "category": "Ведущий",
    "budget": 2_000_000,
    "language": "русский",
    "duration": 6,
}


def test_healthcheck_reports_dataset():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["contractors_count"] == 66


def test_success_has_three_explained_cards_and_is_deterministic():
    first = client.post("/recommend", json=DENSE_QUERY)
    second = client.post("/recommend", json=DENSE_QUERY)

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["status"] == "ok"
    assert len(first.json()["results"]) == 3
    assert all(item["explanation"] for item in first.json()["results"])


def test_different_dates_change_results_and_explanations():
    first = client.post("/recommend", json=DENSE_QUERY).json()
    second_query = {**DENSE_QUERY, "date": "2026-10-16"}
    second = client.post("/recommend", json=second_query).json()

    assert [item["id"] for item in first["results"]] != [
        item["id"] for item in second["results"]
    ]
    assert "15 октября" in first["results"][0]["explanation"]
    assert "16 октября" in second["results"][0]["explanation"]


def test_rare_category_returns_available_count_and_reason():
    response = client.post(
        "/recommend",
        json={
            "city": "Алматы",
            "date": "2026-10-15",
            "event_format": "свадьба",
            "category": "Флорист",
            "budget": 600_000,
            "language": "русский",
        },
    )
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["results"]) == 2
    assert "только 2" in data["message"]


def test_no_matches_is_not_an_error():
    response = client.post(
        "/recommend",
        json={
            "city": "Алматы",
            "date": "2026-12-31",
            "event_format": "свадьба",
            "category": "Флорист",
            "budget": 100_000,
            "language": "русский",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "no_matches"
    assert response.json()["results"] == []


def test_date_outside_calendar_is_rejected():
    response = client.post(
        "/recommend",
        json={**DENSE_QUERY, "date": "2027-01-15"},
    )
    assert response.status_code == 422
