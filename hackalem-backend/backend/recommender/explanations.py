def _as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item is not None]
    return []


def _get_field(record, name, default=None):
    """Read a field from either a dict or a Pydantic/model object."""
    if isinstance(record, dict):
        return record.get(name, default)
    return getattr(record, name, default)


def _number(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _money(value):
    return f"{value:,}".replace(",", " ")


def generate_explanation(contractor: dict, user_request: dict) -> str:
    """Build a repeatable explanation from the contractor and request facts."""
    reasons = []

    price = _number(_get_field(contractor, "price_from_kzt"))
    budget = _number(_get_field(user_request, "budget"))
    if price is not None and price > 0:
        if budget is not None and budget > 0:
            difference = budget - price
            if difference >= 0:
                reasons.append(
                    f"Стартовая цена {_money(price)} ₸ укладывается в бюджет "
                    f"({_money(difference)} ₸ остаётся)."
                )
            else:
                reasons.append(
                    f"Стартовая цена {_money(price)} ₸ превышает бюджет "
                    f"на {_money(abs(difference))} ₸."
                )
        else:
            reasons.append(f"Стартовая цена — {_money(price)} ₸.")

    requested_format = _get_field(user_request, "event_format")
    requested_format = requested_format.strip() if isinstance(requested_format, str) else ""
    supported_formats = _as_list(_get_field(contractor, "event_formats"))
    if requested_format and any(
        requested_format.casefold() == item.casefold()
        for item in supported_formats
    ):
        reasons.append(f"Подрядчик работает с форматом «{requested_format}».")

    requested_category = _get_field(user_request, "category")
    requested_category = requested_category.strip() if isinstance(requested_category, str) else ""
    categories = _as_list(_get_field(contractor, "categories"))
    if requested_category and any(
        requested_category.casefold() == item.casefold()
        for item in categories
    ):
        reasons.append(f"Категория подрядчика — «{requested_category}».")

    requested_language = _get_field(user_request, "language")
    requested_language = requested_language.strip() if isinstance(requested_language, str) else ""
    languages = _as_list(_get_field(contractor, "languages"))
    if requested_language and any(
        requested_language.casefold() == item.casefold()
        for item in languages
    ):
        reasons.append(f"Работает на языке: {requested_language}.")

    duration = _number(_get_field(user_request, "duration"))
    max_hours = _number(_get_field(contractor, "max_hours"))
    if duration is not None and max_hours is not None and duration <= max_hours:
        reasons.append(f"Подходит длительность до {duration} ч.")

    requested_date = _get_field(user_request, "date")
    busy_dates = _as_list(_get_field(contractor, "busy_dates"))
    if requested_date and str(requested_date) not in busy_dates:
        reasons.append(f"Выбранная дата ({requested_date}) не указана среди занятых дат.")

    description = _get_field(contractor, "description")
    if isinstance(description, str):
        description = " ".join(description.split())
        if description and description != "Описание отсутствует":
            # Use source text directly so the individualized detail stays verifiable.
            sentence = description.split(". ", maxsplit=1)[0].rstrip(".")
            if len(sentence) > 180:
                sentence = sentence[:177].rsplit(" ", maxsplit=1)[0] + "…"
            if sentence:
                reasons.append(f"В описании: «{sentence}».")

    return " ".join(reasons) or "Недостаточно данных для подробного объяснения."
