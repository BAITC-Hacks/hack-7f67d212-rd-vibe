import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

ENV_PATH = (
    BASE_DIR
    / ".env"
)

load_dotenv(ENV_PATH)


def get_openai_client():

    api_key = os.getenv(
        "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"
    )

    if not api_key:
        return None

    return OpenAI(
        api_key=api_key
    )


def normalize(
    value: str
) -> str:

    return (
        str(value)
        .strip()
        .casefold()
    )


def contains_value(
    values,
    target
) -> bool:

    if not target:
        return False

    if not values:
        return False

    return normalize(target) in {
        normalize(value)
        for value in values
    }


def build_factual_reasons(
    contractor: dict,
    user_request: dict
) -> list[str]:

    reasons = []

    # Цена
    raw_price = contractor.get(
        "price_from_kzt"
    )

    raw_budget = user_request.get(
        "budget"
    )

    if (
        raw_price is not None
        and raw_budget is not None
    ):

        price = int(
            raw_price
        )

        budget = int(
            raw_budget
        )

        if (
            price > 0
            and budget > 0
            and price <= budget
        ):

            difference = (
                budget - price
            )

            reasons.append(
                (
                    f"Стартовая цена "
                    f"{price:,} ₸ "
                    f"укладывается в бюджет "
                    f"{budget:,} ₸"
                )
                .replace(",", " ")
                + "."
            )

    # Дата
    request_date = user_request.get(
        "date"
    )

    busy_dates = contractor.get(
        "busy_dates"
    ) or []

    if (
        request_date
        and request_date
        not in busy_dates
    ):

        reasons.append(
            f"Свободен на выбранную дату "
            f"{request_date}."
        )

    # Категория
    category = user_request.get(
        "category"
    )

    categories = contractor.get(
        "categories"
    ) or []

    if contains_value(
        categories,
        category
    ):

        reasons.append(
            f"Работает в категории "
            f"«{category}»."
        )

    # Формат мероприятия
    event_format = user_request.get(
        "event_format"
    )

    event_formats = contractor.get(
        "event_formats"
    ) or []

    if contains_value(
        event_formats,
        event_format
    ):

        reasons.append(
            f"Поддерживает формат "
            f"«{event_format}»."
        )

    # Язык
    language = user_request.get(
        "language"
    )

    languages = contractor.get(
        "languages"
    ) or []

    if (
        language
        and contains_value(
            languages,
            language
        )
    ):

        reasons.append(
            f"Работает на языке "
            f"«{language}»."
        )

    # Продолжительность
    duration = user_request.get(
        "duration"
    )

    max_hours = contractor.get(
        "max_hours"
    )

    if (
        duration is not None
        and max_hours is not None
        and int(duration)
        <= int(max_hours)
    ):

        reasons.append(
            f"Может работать необходимую "
            f"продолжительность "
            f"{duration} ч."
        )

    return reasons


def generate_explanation(
    contractor: dict,
    user_request: dict
) -> str:

    """
    Создаёт объяснение:
    1. Проверенные факты кодом.
    2. Одно короткое AI-предложение
       на основе description.

    Если OpenAI недоступен,
    возвращает только факты.
    """

    reasons = build_factual_reasons(
        contractor,
        user_request
    )

    facts_text = " ".join(
        reasons
    )

    description = (
        contractor.get(
            "description"
        )
        or ""
    ).strip()

    if (
        not description
        or description
        == "Описание отсутствует"
    ):
        return facts_text

    client = get_openai_client()

    if client is None:
        return facts_text

    event_format = (
        user_request.get(
            "event_format"
        )
        or "мероприятие"
    )

    category = (
        user_request.get(
            "category"
        )
        or "услуга"
    )

    prompt = f"""
Ты объясняешь клиенту выбор подрядчика.

Используй СТРОГО информацию из описания подрядчика.
Не придумывай рейтинги, опыт, цены, услуги, даты,
награды или другие факты.

Напиши ОДНО короткое предложение о том,
чем подрядчик может быть интересен
для данного запроса.

Категория клиента:
{category}

Формат мероприятия:
{event_format}

Описание подрядчика:
{description}
""".strip()

    try:

        response = (
            client
            .chat
            .completions
            .create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=80
            )
        )

        ai_reason = (
            response
            .choices[0]
            .message
            .content
            or ""
        ).strip()

    except Exception as error:

        print(
            f"Ошибка генерации объяснения: "
            f"{error}"
        )

        ai_reason = ""

    if ai_reason and facts_text:
        return (
            f"{facts_text} "
            f"{ai_reason}"
        )

    if ai_reason:
        return ai_reason

    return facts_text
