"""One-time download of pinned ONNX weights. No profile or query is uploaded."""
import hashlib
import json
import urllib.request

from recommender.config import MODEL_DIR, MODEL_REPO, MODEL_REVISION

FILES = {
    "onnx/model_quantized.onnx": "model_quantized.onnx",
    "tokenizer.json": "tokenizer.json",
    "config.json": "config.json",
    "tokenizer_config.json": "tokenizer_config.json",
    "special_tokens_map.json": "special_tokens_map.json",
}


def download():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = MODEL_DIR / "manifest.json"
    existing = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {}
    manifest = {"repo": MODEL_REPO, "revision": MODEL_REVISION, "files": {}}
    for remote, local in FILES.items():
        path = MODEL_DIR / local
        expected = existing.get("files", {}).get(local, {}).get("sha256")
        if not (path.exists() and expected and hashlib.sha256(path.read_bytes()).hexdigest() == expected):
            url = f"https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REVISION}/{remote}"
            print(f"Downloading {local}...", flush=True)
            temp = path.with_suffix(path.suffix + ".partial")
            with urllib.request.urlopen(url, timeout=120) as source, temp.open("wb") as target:
                while block := source.read(1024 * 1024):
                    target.write(block)
            temp.replace(path)
        manifest["files"][local] = {"size": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Model ready: {MODEL_DIR}", flush=True)


if __name__ == "__main__":
    download()
