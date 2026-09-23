"""Local E5 embeddings, exact source spans, and a dataset-versioned index."""
import hashlib
import json
import re
from functools import lru_cache
from threading import Lock

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from recommender.config import INDEX_PATH, MODEL_DIR, MODEL_REVISION

INDEX_VERSION = 1


def source_passages(text: str) -> list[dict]:
    """Keep literal source offsets, including for descriptions with bullets."""
    passages = []
    for match in re.finditer(r"[^.!?•\n]+(?:[.!?]+|$)", text):
        raw = match.group()
        start = match.start() + len(raw) - len(raw.lstrip())
        end = match.end() - len(raw) + len(raw.rstrip())
        while end - start > 320:
            cut = text.rfind(" ", start + 160, start + 320)
            if cut <= start:
                cut = start + 320
            passages.append({"text": text[start:cut], "start": start, "end": cut})
            start = cut
            while start < end and text[start].isspace():
                start += 1
        fragment = text[start:end]
        if len(fragment) >= 25 and not re.search(r"^(привет|всем привет|меня зовут|с уважением|дорогие друзья)", fragment, re.I):
            passages.append({"text": fragment, "start": start, "end": end})
    if not passages and text.strip():
        start = len(text) - len(text.lstrip())
        end = min(len(text.rstrip()), start + 320)
        passages = [{"text": text[start:end], "start": start, "end": end}]
    return passages


class SemanticIndex:
    def __init__(self, contractors, index_path=INDEX_PATH):
        self.ready = False
        self.error = None
        self.contractors = {c.id: c for c in contractors}
        self.index_path = index_path
        self.lock = Lock()
        self.dimension = 384

    def initialize(self):
        with self.lock:
            if self.ready:
                return
            model_path = MODEL_DIR / "model_quantized.onnx"
            if not model_path.exists() or not (MODEL_DIR / "tokenizer.json").exists():
                raise RuntimeError("Модель не установлена: запустите python download_model.py из backend.")
            self.tokenizer = Tokenizer.from_file(str(MODEL_DIR / "tokenizer.json"))
            self.tokenizer.enable_truncation(max_length=512)
            self.tokenizer.enable_padding(pad_id=1, pad_token="<pad>")
            options = ort.SessionOptions()
            options.intra_op_num_threads = 2
            options.inter_op_num_threads = 1
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            self.session = ort.InferenceSession(str(model_path), sess_options=options, providers=["CPUExecutionProvider"])
            self.inputs = {node.name for node in self.session.get_inputs()}
            fingerprint_data = [(c.id, c.description, c.categories) for c in self.contractors.values()]
            self.fingerprint = hashlib.sha256(json.dumps([INDEX_VERSION, MODEL_REVISION, fingerprint_data], ensure_ascii=False).encode()).hexdigest()
            cached = None
            try:
                cached = json.loads(self.index_path.read_text("utf-8"))
            except (FileNotFoundError, ValueError):
                pass
            if cached and cached.get("fingerprint") == self.fingerprint:
                self.passages = cached["passages"]
                self.vectors = np.array(cached["vectors"], dtype=np.float32)
                if self.vectors.shape != (len(self.passages), self.dimension) or not np.isfinite(self.vectors).all():
                    cached = None
            else:
                cached = None
            if cached is None:
                self.passages = []
                for c in self.contractors.values():
                    for passage in source_passages(c.description):
                        self.passages.append({"id": c.id, **passage})
                texts = ["passage: " + ", ".join(self.contractors[p["id"]].categories) + ". " + p["text"] for p in self.passages]
                self.vectors = self._encode(texts)
                self.index_path.parent.mkdir(parents=True, exist_ok=True)
                temp = self.index_path.with_suffix(".tmp")
                temp.write_text(json.dumps({"fingerprint": self.fingerprint, "model_revision": MODEL_REVISION, "dimension": self.dimension, "passages": self.passages, "vectors": self.vectors.tolist()}, ensure_ascii=False), "utf-8")
                temp.replace(self.index_path)
            self.rows = {id_: [i for i, p in enumerate(self.passages) if p["id"] == id_] for id_ in self.contractors}
            self.ready = True

    def _encode(self, texts):
        batches = []
        for offset in range(0, len(texts), 8):
            encodings = self.tokenizer.encode_batch(texts[offset:offset + 8])
            feeds = {
                "input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64),
                "token_type_ids": np.array([e.type_ids for e in encodings], dtype=np.int64),
            }
            outputs = self.session.run(None, {name: value for name, value in feeds.items() if name in self.inputs})
            hidden = outputs[0]
            mask = feeds["attention_mask"][..., None]
            pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
            normalized = pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
            batches.append(normalized.astype(np.float32))
        return np.concatenate(batches, axis=0)

    @lru_cache(maxsize=256)
    def _query(self, text):
        with self.lock:
            return self._encode(["query: " + text])[0]

    def search(self, preferences: str, ids: list[str]) -> dict:
        if not self.ready:
            raise RuntimeError(self.error or "Модель ещё не загружена")
        query = self._query(preferences)
        similarities = self.vectors @ query
        matches = {}
        for id_ in ids:
            rows = self.rows.get(id_, [])
            if not rows:
                matches[id_] = {"similarity": 0.0, "evidence": None}
                continue
            best = sorted(rows, key=lambda i: (-round(float(similarities[i]), 7), i))[0]
            matches[id_] = {"similarity": round(float(similarities[best]), 7), "evidence": self.passages[best]}
        return matches
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
