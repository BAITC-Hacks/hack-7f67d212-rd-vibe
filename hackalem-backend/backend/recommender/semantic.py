import json
import os
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DATA_DIR = os.path.join(os.path.dirname(MODULE_DIR), "data")
DATA_DIR = (
    BACKEND_DATA_DIR
    if os.path.basename(MODULE_DIR).casefold() == "recommender"
    and os.path.isdir(BACKEND_DATA_DIR)
    else MODULE_DIR
)
EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.json")

def load_contractor_embeddings():
    """Безопасная загрузка эмбеддингов с защитой от пустых файлов."""
    if os.path.exists(EMBEDDINGS_PATH):
        try:
            with open(EMBEDDINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Приводим все ключи к строкам на всякий случай
                return {str(k): v for k, v in data.items()}
        except Exception as e:
            print(f"Ошибка загрузки embeddings.json: {e}")
            return {}
    return {}

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def _get_field(record, name, default=None):
    if isinstance(record, dict):
        return record.get(name, default)
    return getattr(record, name, default)


def _make_embedding_query(user_query) -> str:
    """Accept plain text or the backend's RecommendationRequest model."""
    if isinstance(user_query, str):
        return user_query.strip()

    parts = []
    free_text = _get_field(user_query, "semantic_query")
    if not free_text:
        free_text = _get_field(user_query, "query")
    if free_text:
        parts.append(str(free_text).strip())

    event_format = _get_field(user_query, "event_format")
    category = _get_field(user_query, "category")
    if category:
        parts.append(f"Категория: {category}")
    if event_format:
        parts.append(f"Формат мероприятия: {event_format}")

    return ". ".join(part for part in parts if part)


def get_semantic_scores(user_query) -> dict:
    """
    Возвращает словарь {contractor_id (str): score} на основе семантической близости.
    """
    embeddings = load_contractor_embeddings()
    if not embeddings:
        return {}

    embedding_query = _make_embedding_query(user_query)
    if not embedding_query:
        return {cid: 0.5 for cid in embeddings}

    try:
        response = client.embeddings.create(
            input=embedding_query,
            model="text-embedding-3-small"
        )
        query_vec = response.data[0].embedding
    except Exception as e:
        print(f"Ошибка OpenAI Embedding API: {e}")
        return {}

    scores = {}
    for cid, c_vec in embeddings.items():
        scores[cid] = cosine_similarity(query_vec, c_vec)

    return scores
