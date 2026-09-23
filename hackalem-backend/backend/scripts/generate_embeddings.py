import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# backend/
BASE_DIR = Path(__file__).resolve().parent.parent

# backend/data/contractors.jsonl
DATASET_PATH = (
    BASE_DIR
    / "data"
    / "contractors.jsonl"
)

# backend/data/embeddings.json
OUTPUT_PATH = (
    BASE_DIR
    / "data"
    / "embeddings.json"
)

# backend/.env
ENV_PATH = BASE_DIR / ".env"


def load_contractors(
    path: Path
) -> list[dict]:

    if not path.exists():
        raise FileNotFoundError(
            f"Датасет не найден: {path}"
        )

    content = path.read_text(
        encoding="utf-8-sig"
    ).strip()

    if not content:
        raise ValueError(
            "Файл датасета пустой"
        )

    # Если файл является обычным JSON массивом
    if content.startswith("["):

        data = json.loads(content)

        if not isinstance(data, list):
            raise ValueError(
                "JSON должен содержать список"
            )

        return data

    # Если файл JSONL
    contractors = []

    for line_number, line in enumerate(
        content.splitlines(),
        start=1
    ):

        line = line.strip()

        if not line:
            continue

        try:
            contractors.append(
                json.loads(line)
            )

        except json.JSONDecodeError as error:

            raise ValueError(
                f"Ошибка JSONL в строке "
                f"{line_number}: {error}"
            )

    return contractors


def main():

    load_dotenv(ENV_PATH)

    api_key = os.getenv(
        "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"
    )

    if not api_key:
        print(
            "Ошибка: OPENAI_API_KEY "
            "не найден в backend/.env"
        )
        return

    client = OpenAI(
        api_key=api_key
    )

    try:
        contractors = load_contractors(
            DATASET_PATH
        )

    except Exception as error:
        print(
            f"Ошибка загрузки датасета: "
            f"{error}"
        )
        return

    print(
        f"Всего подрядчиков: "
        f"{len(contractors)}"
    )

    embeddings = {}

    failed_ids = []

    for index, contractor in enumerate(
        contractors,
        start=1
    ):

        contractor_id = contractor.get(
            "id"
        )

        description = contractor.get(
            "description"
        )

        if contractor_id is None:

            print(
                f"[{index}] Нет ID"
            )

            failed_ids.append(
                f"record_{index}"
            )

            continue

        contractor_id = str(
            contractor_id
        )

        if not description:
            description = (
                "Описание отсутствует"
            )

        description = str(
            description
        ).strip()

        try:

            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=description
            )

            embedding = (
                response
                .data[0]
                .embedding
            )

            embeddings[
                contractor_id
            ] = embedding

            print(
                f"[{index}/{len(contractors)}] "
                f"OK: {contractor_id}"
            )

        except Exception as error:

            failed_ids.append(
                contractor_id
            )

            print(
                f"[{index}/{len(contractors)}] "
                f"ERROR {contractor_id}: "
                f"{error}"
            )

    if failed_ids:

        print(
            "\nEmbeddings созданы "
            "не для всех подрядчиков."
        )

        print(
            "Не удалось обработать:"
        )

        for contractor_id in failed_ids:
            print(
                "-",
                contractor_id
            )

        print(
            "\nembeddings.json НЕ обновлён."
        )

        return

    if (
        len(embeddings)
        != len(contractors)
    ):

        print(
            "Ошибка: количество embeddings "
            "не совпадает с количеством подрядчиков."
        )

        return

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            embeddings,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "\nГотово!"
    )

    print(
        f"Создано embeddings: "
        f"{len(embeddings)}"
    )

    print(
        f"Файл: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
