import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI


# backend/
BASE_DIR = Path(__file__).resolve().parent.parent

# backend/.env
ENV_PATH = BASE_DIR / ".env"

# backend/data/embeddings.json
EMBEDDINGS_PATH = BASE_DIR / "data" / "embeddings.json"


load_dotenv(ENV_PATH)


def get_openai_client():
    api_key = os.getenv("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")

    if not api_key:
        print("OPENAI_API_KEY не найден в .env")
        return None

    return OpenAI(api_key=api_key)


def load_contractor_embeddings() -> dict[str, list[float]]:
    """
    Загружает embeddings подрядчиков.

    Возвращает:
    {
        "HK-39372": [...],
        "HK-XXXXX": [...]
    }
    """

    if not EMBEDDINGS_PATH.exists():
        print(
            f"Файл embeddings не найден: "
            f"{EMBEDDINGS_PATH}"
        )
        return {}

    try:
        with open(
            EMBEDDINGS_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(data, dict):
            print("embeddings.json должен содержать JSON object")
            return {}

        return {
            str(contractor_id): vector
            for contractor_id, vector in data.items()
            if isinstance(vector, list)
        }

    except Exception as error:
        print(
            f"Ошибка загрузки embeddings.json: "
            f"{error}"
        )
        return {}


def cosine_similarity(
    vector_a: list[float],
    vector_b: list[float]
) -> float:

    a = np.asarray(vector_a, dtype=float)
    b = np.asarray(vector_b, dtype=float)

    if a.shape != b.shape:
        return 0.0

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(
        np.dot(a, b)
        / (norm_a * norm_b)
    )


def get_semantic_scores(
    user_query: str
) -> dict[str, float]:
    """
    Возвращает:

    {
        "HK-39372": 0.74,
        "HK-XXXXX": 0.68
    }
    """

    embeddings = load_contractor_embeddings()

    if not embeddings:
        return {}

    if not user_query or not user_query.strip():
        return {
            contractor_id: 0.0
            for contractor_id in embeddings
        }

    client = get_openai_client()

    if client is None:
        return {}

    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=user_query.strip()
        )

        query_embedding = (
            response.data[0].embedding
        )

    except Exception as error:
        print(
            f"Ошибка OpenAI Embedding API: "
            f"{error}"
        )
        return {}

    scores = {}

    for contractor_id, contractor_embedding in embeddings.items():

        scores[contractor_id] = cosine_similarity(
            query_embedding,
            contractor_embedding
        )

    return scores
