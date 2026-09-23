import json
import os
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMBEDDINGS_PATH = os.path.join(BASE_DIR, "embeddings.json")

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

def get_semantic_scores(user_query: str) -> dict:
    """
    Возвращает словарь {contractor_id (str): score} на основе семантической близости.
    """
    embeddings = load_contractor_embeddings()
    if not embeddings:
        return {}

    if not user_query or not user_query.strip():
        return {cid: 0.5 for cid in embeddings}

    try:
        response = client.embeddings.create(
            input=user_query,
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
