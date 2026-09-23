"""Restore the exact ONNX weights from small, losslessly compressed Git files."""
import hashlib
import json
import lzma
from pathlib import Path
import tempfile

from recommender.config import MODEL_DIR, MODEL_REPO, MODEL_REVISION

MODEL_NAME = "model_quantized.onnx"
BUNDLE_NAME = "model_bundle.json"
BLOCK_SIZE = 1024 * 1024


def file_matches(path: Path, expected: dict) -> bool:
    if not path.is_file() or path.stat().st_size != expected["size"]:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(BLOCK_SIZE):
            digest.update(block)
    return digest.hexdigest() == expected["sha256"]


def restore_bundled_model(model_dir: Path = MODEL_DIR) -> bool:
    """Return False for a code-only checkout; never download or alter valid weights."""
    bundle_path = model_dir / BUNDLE_NAME
    if not bundle_path.is_file():
        return False
    pinned = json.loads((model_dir / "manifest.json").read_text("utf-8"))
    if pinned["repo"] != MODEL_REPO or pinned["revision"] != MODEL_REVISION:
        raise RuntimeError("Версия модели в manifest.json не совпадает с настройками проекта.")
    expected = pinned["files"][MODEL_NAME]
    destination = model_dir / MODEL_NAME
    if file_matches(destination, expected):
        return True

    bundle = json.loads(bundle_path.read_text("utf-8"))
    if (bundle.get("format") != "xz-split-v1"
            or bundle.get("file") != MODEL_NAME
            or bundle.get("original") != expected
            or not bundle.get("parts")):
        raise RuntimeError("Неверное описание архива модели в model_bundle.json.")

    # Validate every part before creating or replacing the runtime model.
    parts = []
    for number, entry in enumerate(bundle["parts"], 1):
        name = f"{MODEL_NAME}.xz.part{number:03d}"
        if entry.get("name") != name:
            raise RuntimeError("Нарушен порядок частей архива модели.")
        part = model_dir / name
        if not file_matches(part, entry):
            raise RuntimeError(f"Часть модели отсутствует или повреждена: {name}. "
                               "Восстановите этот файл из репозитория и повторите запуск.")
        parts.append(part)

    print("Restoring bundled model (offline, lossless)...", flush=True)
    temporary = None
    try:
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
        digest = hashlib.sha256()
        size = 0
        with tempfile.NamedTemporaryFile(mode="wb", dir=model_dir,
                                         prefix=MODEL_NAME + ".", suffix=".partial",
                                         delete=False) as target:
            temporary = Path(target.name)
            for part in parts:
                with part.open("rb") as source:
                    while block := source.read(BLOCK_SIZE):
                        if decoder.eof:
                            raise RuntimeError("Лишние данные в архиве модели.")
                        output = decoder.decompress(block, max_length=BLOCK_SIZE)
                        while True:
                            size += len(output)
                            if size > expected["size"]:
                                raise RuntimeError("Размер распакованной модели превышает ожидаемый.")
                            target.write(output)
                            digest.update(output)
                            if decoder.eof or decoder.needs_input:
                                break
                            output = decoder.decompress(b"", max_length=BLOCK_SIZE)
                        if decoder.unused_data:
                            raise RuntimeError("Лишние данные в архиве модели.")
            if not decoder.eof:
                raise RuntimeError("Архив модели обрезан.")
            if size != expected["size"] or digest.hexdigest() != expected["sha256"]:
                raise RuntimeError("Контрольная сумма восстановленной модели не совпадает.")
        temporary.replace(destination)
    except lzma.LZMAError as exc:
        raise RuntimeError("Не удалось распаковать архив модели: данные повреждены.") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True
