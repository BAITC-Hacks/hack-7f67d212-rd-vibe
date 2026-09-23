import json
from pathlib import Path

from recommender.models import Contractor


DATA_PATH = Path(__file__).parent.parent / "data" / "contractors.jsonl"


def load_contractors() -> list[Contractor]:

    with open(DATA_PATH, "r", encoding="utf-8") as file:
        content = file.read().strip()

    contractors = []

    # Если это обычный JSON-массив
    if content.startswith("["):
        data = json.loads(content)

        for item in data:
            contractors.append(Contractor(**item))

    # Если это JSONL
    else:
        for line in content.splitlines():

            if not line.strip():
                continue

            data = json.loads(line)

            contractors.append(Contractor(**data))

    return contractors