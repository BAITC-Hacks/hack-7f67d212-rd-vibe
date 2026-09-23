import json
import os
from dotenv import load_dotenv
from openai import OpenAI

def main():
    load_dotenv()
    client = OpenAI(api_key=os.getenv("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"))

    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(current_dir, "hackathon-dataset-anonymized.jsonl")
    output_path = os.path.join(current_dir, "embeddings.json")

    if not os.path.exists(dataset_path):
        print(f"Ошибка: Файл датасета {dataset_path} не найден!")
        return

    contractors = []
    
    # Пытаемся прочитать как JSON-массив или JSONL
    try:
        with open(dataset_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
            if isinstance(data, list):
                contractors = data
    except Exception:
        pass

    if not contractors:
        with open(dataset_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    contractors.append(json.loads(line))
                except Exception:
                    continue

    print(f"Всего найдено записей в датасете: {len(contractors)}")

    embeddings = {}
    success_count = 0

    for index, record in enumerate(contractors, start=1):
        contractor_id = record.get("id")
        if contractor_id is None:
            continue

        contractor_id_str = str(contractor_id)
        description = record.get("description")
        if not description or not description.strip():
            description = "Описание отсутствует"

        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=description,
            )
            embeddings[contractor_id_str] = response.data[0].embedding
            success_count += 1
            print(f"[{index}/{len(contractors)}] Обработан ID: {contractor_id_str}")
        except Exception as api_err:
            print(f"Ошибка OpenAI API на ID {contractor_id_str}: {api_err}")

    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(embeddings, output_file, ensure_ascii=False, indent=2)

    print(f"\n Успешно! Создано векторов: {success_count}. Сохранено в {output_path}")

if __name__ == "__main__":
    main()