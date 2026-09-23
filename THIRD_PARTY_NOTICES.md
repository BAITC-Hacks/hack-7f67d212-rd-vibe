# Third-party notices

## multilingual-e5-small

- Original model: https://huggingface.co/intfloat/multilingual-e5-small
- Original implementation: https://github.com/microsoft/unilm/tree/master/e5
- ONNX conversion: https://huggingface.co/Xenova/multilingual-e5-small
- Pinned ONNX revision: `761b726dd34fb83930e26aab4e9ac3899aa1fa78`
- Upstream model license: MIT, as indicated in both model cards.
- Included files: quantized ONNX weights, tokenizer and associated configuration.
- Attribution: Microsoft / intfloat (E5); Xenova (ONNX conversion).
- The upstream MIT notice is included at `backend/models/multilingual-e5-small/LICENSE`.
- No affiliation with or endorsement by the model authors is implied.

The distribution bundles model files for offline inference. `manifest.json` records file sizes and SHA-256 checksums. Their data and model licenses are separate from the application code.

## Dataset

The user-provided anonymized hackathon dataset is included for the requested prototype and demonstration. It contains 66 profiles, including 13 already marked synthetic and fields marked imputed. No independent license for public redistribution was provided with the task; confirm the organizer's terms before publishing the dataset outside the hackathon. This notice does not relicense the dataset or certify the profile claims.

## Python dependencies

Dependencies are installed by pip from `backend/requirements.txt`; their own license files and notices remain with their installed distributions. The release ZIP does not include a Python interpreter or `.venv`.
