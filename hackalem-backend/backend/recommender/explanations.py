import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("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"))

def generate_explanation(contractor: dict, user_request: dict) -> str:
    """
    Строит надежное объяснение: факты кодом + точечный AI-анализ стиля с защитой от типов None.
    """
    reasons = []

    # 1. Безопасная проверка бюджета и цен (защита от None)
    raw_price = contractor.get("price_from_kzt")
    price = int(raw_price) if raw_price is not None else 0
    
    raw_budget = user_request.get("budget")
    budget = int(raw_budget) if raw_budget is not None else 0
    
    if budget > 0 and price > 0:
        diff = budget - price
        if diff >= 0:
            reasons.append(f"Стартовая цена {price:,} ₸ укладывается в ваш бюджет (экономия {diff:,} ₸).".replace(",", " "))
        else:
            reasons.append(f"Стартовая цена {price:,} ₸ превышает бюджет на {abs(diff):,} ₸.".replace(",", " "))
    elif price > 0:
        reasons.append(f"Стартовая цена составляет {price:,} ₸.".replace(",", " "))

    # 2. Проверка даты
    req_date = user_request.get("date", "")
    if req_date:
        reasons.append(f"Свободен на выбранную дату ({req_date}).")

    # 3. AI-часть для описания стиля (строго без галлюцинаций)
    description = contractor.get("description", "").strip()
    ai_reason = ""

    if description and description != "Описание отсутствует":
        prompt = f"""
        Опираясь СТРОГО на текст описания ниже, напиши ОДНО короткое предложение, чем этот подрядчик выделяется по стилю или формату.
        Запрещено придумывать факты, цены, услуги или даты, которых нет в тексте.

        Описание подрядчика: "{description}"
        Запрос клиента: Формат - {user_request.get('event_format', 'мероприятие')}, Категория - {user_request.get('category', 'услуга')}.
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=50
            )
            ai_reason = response.choices[0].message.content.strip()
        except Exception:
            ai_reason = ""

    facts_text = " ".join(reasons)
    if ai_reason:
        return f"{facts_text} {ai_reason}"
    return facts_text