#!/usr/bin/env bash
# Download the quantized GGUF weights used by the inference server.
#
# The model binaries are gitignored, so they are downloaded once and cached
# locally (or baked into the image at build time on Coolify/Nixpacks).
# Skips the download entirely when MODEL_BACKEND=mock.
set -euo pipefail

MODEL_URL="${MODEL_URL:-https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf}"
MODEL_PATH="${MODEL_PATH:-models/qwen2.5-0.5b-instruct-q4_k_m.gguf}"
MODEL_BACKEND="${MODEL_BACKEND:-local}"

if [ "$MODEL_BACKEND" = "mock" ]; then
    echo "MODEL_BACKEND=mock — skipping model download."
    exit 0
fi

if [ -f "$MODEL_PATH" ]; then
    echo "Model already present at $MODEL_PATH — skipping download."
    exit 0
fi

mkdir -p "$(dirname "$MODEL_PATH")"
echo "Downloading $(basename "$MODEL_PATH") (~490MB) from Hugging Face..."
curl -fL --retry 3 --progress-bar -o "$MODEL_PATH" "$MODEL_URL"
echo "Model saved to $MODEL_PATH."
