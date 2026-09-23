"""Small hand-labelled smoke benchmark; not an independent accuracy estimate."""
import json
import re
import statistics
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from main import app, contractors, semantic
from recommender.config import PROJECT_DIR


def evaluate():
    queries = json.loads(Path(__file__).with_name("queries.json").read_text("utf-8"))
    started = perf_counter()
    semantic.initialize()
    startup_seconds = perf_counter() - started
    rows = []
    for case in queries:
        begin = perf_counter()
        matches = semantic.search(case["query"], [c.id for c in contractors])
        ranked = sorted(matches, key=lambda id_: (-matches[id_]["similarity"], id_))
        elapsed = (perf_counter() - begin) * 1000
        tokens = set(re.findall(r"\w+", case["query"].casefold()))
        lexical = sorted(contractors, key=lambda c: (-len(tokens & set(re.findall(r"\w+", c.description.casefold()))), c.id))
        relevant = set(case["relevant_ids"])
        rank = next((i + 1 for i, id_ in enumerate(ranked) if id_ in relevant), 999)
        lexical_rank = next((i + 1 for i, c in enumerate(lexical) if c.id in relevant), 999)
        rows.append({**case, "top3": ranked[:3], "rank_first_relevant": rank, "lexical_rank": lexical_rank, "ms": round(elapsed, 2), "top_evidence": matches[ranked[0]]["evidence"]["text"]})

    dense = {"city":"Алматы","date":"2026-10-15","category":"Ведущий","event_format":"корпоратив","budget":2000000,"language":"русский","duration":6,"preferences":"Спокойная ненавязчивая подача, интеллигентный юмор и уютная атмосфера"}
    examples = [dense, {**dense,"date":"2026-10-16","compare_date":"2026-10-15"}, {"city":"Алматы","date":"2026-10-15","category":"Флорист","event_format":"свадьба","budget":600000,"language":"русский","preferences":"Цветочные композиции под цветовую палитру свадьбы"}, {"city":"Алматы","date":"2026-12-31","category":"Флорист","event_format":"свадьба","budget":100000,"preferences":"Цветочное оформление свадьбы"}, {"city":"Зарубежье","date":"2026-10-15","category":"Флорист","event_format":"свадьба","budget":600000}]
    scenarios = []
    latencies = []
    with TestClient(app) as client:
        for request in examples:
            begin = perf_counter()
            response = client.post("/recommend", json=request)
            ms = (perf_counter() - begin) * 1000
            data = response.json()
            scenarios.append({"request":request,"http_status":response.status_code,"status":data.get("status"),"result_ids":[r["id"] for r in data.get("results",[])],"suggestions":data.get("suggestions"),"date_comparison":data.get("date_comparison"),"ms":round(ms,2)})
            for _ in range(4):
                begin = perf_counter()
                repeated = client.post("/recommend", json=request)
                latencies.append((perf_counter()-begin)*1000)
                assert repeated.json() == data
    count = len(rows)
    metrics = {"case_count":count,"hit_at_1":sum(r["rank_first_relevant"]==1 for r in rows)/count,"hit_at_3":sum(r["rank_first_relevant"]<=3 for r in rows)/count,"mrr_at_3":sum(1/r["rank_first_relevant"] if r["rank_first_relevant"]<=3 else 0 for r in rows)/count,"lexical_hit_at_1":sum(r["lexical_rank"]==1 for r in rows)/count,"lexical_hit_at_3":sum(r["lexical_rank"]<=3 for r in rows)/count,"model_startup_seconds":round(startup_seconds,3),"api_median_ms":round(statistics.median(latencies),2),"api_max_ms":round(max(latencies),2),"deterministic_repeats":len(latencies)}
    report = {"methodology":"12 вручную составленных диагностических запросов; семантический поиск по всем 66 профилям без фильтров и цены; не независимая оценка качества. Lexical baseline — пересечение точных слов. API отдельно проверен на пяти сценариях, по четыре повтора. Время без внешней сети, TestClient, текущий компьютер.","metrics":metrics,"cases":rows,"scenarios":scenarios}
    output = PROJECT_DIR / "docs" / "evaluation.json"
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),"utf-8")
    lines = ["# Проверка поиска", "", report["methodology"], "", "| Метрика | Значение |", "|---|---:|", *[f"| {key} | {value:.4f} |" if isinstance(value,float) else f"| {key} | {value} |" for key,value in metrics.items()], "", "Hit@3: хотя бы один размеченный подходящий профиль среди первых трёх. MRR@3: обратное место первого подходящего профиля, 0 за пределами топ-3. Это небольшой smoke-набор; оценки нельзя переносить на произвольные запросы.", "", "## Запросы", "", "| ID | Место подходящего | Топ-3 |", "|---|---:|---|", *[f"| {r['id']} | {r['rank_first_relevant']} | {', '.join(r['top3'])} |" for r in rows]]
    (PROJECT_DIR / "docs" / "evaluation.md").write_text("\n".join(lines)+"\n","utf-8")
    print(json.dumps(metrics,indent=2))
    for scenario in scenarios:
        print(scenario["status"],scenario["result_ids"],scenario["ms"])


if __name__ == "__main__":
    evaluate()
