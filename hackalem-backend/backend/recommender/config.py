from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
MODEL_DIR = BACKEND_DIR / "models" / "multilingual-e5-small"
INDEX_PATH = BACKEND_DIR / "data" / "embeddings.json"
MODEL_REPO = "Xenova/multilingual-e5-small"
MODEL_REVISION = "761b726dd34fb83930e26aab4e9ac3899aa1fa78"
CALENDAR_START = "2026-09-23"
CALENDAR_END = "2026-12-31"
