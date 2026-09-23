from datetime import date as calendar_date
from recommender.semantic import source_passages

MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")


def format_money(value):
    return f"{value:,}".replace(",", " ") + " ₸"


def format_date(value):
    parsed = calendar_date.fromisoformat(value)
    return f"{parsed.day} {MONTHS[parsed.month - 1]} {parsed.year} года"


def choose_evidence(contractor, semantic_match=None):
    passage = semantic_match.get("evidence") if semantic_match else None
    if not passage:
        passages = source_passages(contractor.description)
        passage = passages[0] if passages else None
    if not passage:
        return None
    return {"text": passage["text"], "start": passage["start"], "end": passage["end"], "source": "description", "selected_by": "semantic" if semantic_match else "profile"}


def generate_explanation(contractor, request, semantic_match=None):
    reserve = request.budget - contractor.price_from_kzt
    first = f"В календаре свободен {format_date(request.date)}, берёт формат «{request.event_format}»; цена от {format_money(contractor.price_from_kzt)} оставляет {format_money(reserve)} резерва по стартовой цене"
    if request.language:
        first += f", язык — {request.language}"
    if request.duration is not None:
        first += f", {request.duration} ч укладываются в максимум {contractor.max_hours} ч" if contractor.max_hours is not None else ", работа не привязана к часам присутствия"
    evidence = choose_evidence(contractor, semantic_match)
    second = ("К пожеланию ближе всего фрагмент профиля" if request.preferences else "Особенность из описания") + f": «{evidence['text']}»" if evidence else "Дополнительных сведений о стиле в профиле нет"
    return first + ". " + second.rstrip(".!?") + "."


def data_notes(contractor):
    notes = []
    if contractor.synthetic:
        notes.append("Синтетический профиль из исходного датасета организаторов")
    if contractor.price_imputed:
        notes.append("Цена проставлена при подготовке датасета, требуется уточнение")
    if contractor.city_imputed:
        notes.append("Город проставлен при подготовке датасета")
    return notes
