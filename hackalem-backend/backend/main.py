from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from recommender.alternatives import suggestions
from recommender.config import CALENDAR_START, CALENDAR_END, MODEL_REVISION, PROJECT_DIR
from recommender.data_loader import load_contractors
from recommender.explanations import choose_evidence, data_notes, format_date, generate_explanation
from recommender.filters import filter_contractors, normalize
from recommender.models import RecommendationRequest
from recommender.ranking import rank_contractors, score_breakdown
from recommender.semantic import SemanticIndex

contractors = load_contractors()
semantic = SemanticIndex(contractors)


def load_semantic():
    try:
        semantic.initialize()
    except Exception as exc:
        semantic.error = str(exc)
        return False
    return True


@asynccontextmanager
async def lifespan(app):
    load_semantic()
    yield


app = FastAPI(title="EventMatch — объяснимый AI-подбор", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Accept"], expose_headers=["X-Response-Time-Ms"])


@app.get("/")
@app.get("/health")
def root():
    return {"status": "ok", "contractors_count": len(contractors), "semantic_ready": semantic.ready, "model": "multilingual-e5-small / ONNX int8", "model_revision": MODEL_REVISION, "calendar": {"start": CALENDAR_START, "end": CALENDAR_END}}


@app.get("/catalog")
def catalog():
    return {"cities": sorted({c.city for c in contractors}), "categories": sorted({v for c in contractors for v in c.categories}), "event_formats": sorted({v for c in contractors for v in c.event_formats}), "languages": sorted({v for c in contractors for v in c.languages}), "synthetic_count": sum(c.synthetic for c in contractors), "original_count": sum(not c.synthetic for c in contractors), "calendar": {"start": CALENDAR_START, "end": CALENDAR_END}}


@app.post("/recommend")
def recommend(request: RecommendationRequest, response: Response):
    started = perf_counter()
    pool = [c for c in contractors if normalize(c.city) == normalize(request.city) and normalize(request.category) in [normalize(v) for v in c.categories]]
    suitable, rejected = filter_contractors(pool, request)
    matches = {}
    if request.preferences and pool:
        if not semantic.ready and not load_semantic():
            raise HTTPException(503, "ИИ-модель недоступна. Запустите download_model.py и перезапустите сервер; поиск без пожелания доступен.")
        matches = semantic.search(request.preferences, [c.id for c in pool])

    ranked = rank_contractors(suitable, request, matches)
    results = []
    for c in ranked:
        match = matches.get(c.id)
        results.append({"id": c.id, "name": c.anon_name, "city": c.city, "categories": c.categories, "price_from_kzt": c.price_from_kzt, "event_formats": c.event_formats, "languages": c.languages, "max_hours": c.max_hours, "description": c.description, "synthetic": c.synthetic, "price_imputed": c.price_imputed, "city_imputed": c.city_imputed, "data_notes": data_notes(c), "explanation": generate_explanation(c, request, match), "evidence": choose_evidence(c, match), "score": score_breakdown(c, request, match)})

    if not pool:
        status = "category_not_found"
        message = "В выбранном городе нет профилей этой категории в датасете."
    elif not suitable:
        status = "no_matches"
        message = f"Всего профилей в этой категории и городе: {len(pool)}. Ни один не прошёл все условия."
    elif len(suitable) < 3:
        status = "ok"
        message = f"Найдено только {len(suitable)}. Всего профилей в этой категории и городе: {len(pool)}; отсеяно по условиям: {len(pool) - len(suitable)}."
    else:
        status = "ok"
        message = f"Показаны 3 из {len(suitable)} подходящих профилей."

    comparison = None
    if request.compare_date and request.compare_date != request.date:
        previous = request.model_copy(update={"date": request.compare_date, "compare_date": None})
        previous_pool, _ = filter_contractors(pool, previous)
        previous_top = rank_contractors(previous_pool, previous, matches)
        busy_now = [{"id": c.id, "name": c.anon_name} for c in previous_top if request.date in c.busy_dates]
        returned = [{"id": c.id, "name": c.anon_name} for c in ranked if request.compare_date in c.busy_dates]
        comparison = {"previous_date": request.compare_date, "current_date": request.date, "now_busy": busy_now, "now_available": returned, "message": f"Изменена только дата: {format_date(request.compare_date)} → {format_date(request.date)}; остальные условия сохранены."}

    output = {"status": status, "message": message, "results": results, "rejected": rejected, "rejection_scope": "Только выбранные город и категория; один профиль может иметь несколько причин отказа", "stats": {"catalog_count": len(pool), "matching_count": len(suitable), "rejected_count": len(pool) - len(suitable), "busy_count": rejected.get("busy", 0)}, "suggestions": suggestions(contractors, request, category_missing=not pool) if not suitable else [], "date_comparison": comparison, "ranking": {"mode": "semantic" if request.preferences else "budget", "description": "85% смысловая близость + 15% запас по стартовой цене" if request.preferences else "Порядок по запасу бюджета; при равенстве — цена и id", "score_note": "Баллы объясняют порядок, это не вероятность и не гарантия соответствия пожеланию"}}
    response.headers["X-Response-Time-Ms"] = f"{(perf_counter() - started) * 1000:.2f}"
    return output


app.mount("/app", StaticFiles(directory=PROJECT_DIR / "frontend", html=True), name="frontend")
