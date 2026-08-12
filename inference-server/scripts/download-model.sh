#!/usr/bin/env bash
# Download the quantized GGUF weights used by the inference server.
#
# The model binaries are gitignored, so they are downloaded once and cached
# locally (or baked into the image at build time on Coolify/Nixpacks).
#
# Two models are fetched:
#   * the chat/instruct model  (Qwen2.5-0.5B-Instruct, ~490MB)
#   * the embedding model      (nomic-embed-text-v1.5, ~146MB)
set -euo pipefail

CHAT_URL="${CHAT_MODEL_URL:-https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf}"
CHAT_PATH="${CHAT_MODEL_PATH:-models/qwen2.5-0.5b-instruct-q4_k_m.gguf}"

EMBED_URL="${EMBED_MODEL_URL:-https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.Q8_0.gguf}"
EMBED_PATH="${EMBED_MODEL_PATH:-models/nomic-embed-text-v1.5.Q8_0.gguf}"

mkdir -p "$(dirname "$CHAT_PATH")"

if [ -f "$CHAT_PATH" ]; then
    echo "Chat model already present at $CHAT_PATH — skipping download."
else
    echo "Downloading $(basename "$CHAT_PATH") (~490MB) from Hugging Face..."
    curl -fL --retry 3 --progress-bar -o "$CHAT_PATH" "$CHAT_URL"
    echo "Chat model saved to $CHAT_PATH."
fi

if [ -f "$EMBED_PATH" ]; then
    echo "Embedding model already present at $EMBED_PATH — skipping download."
else
    echo "Downloading $(basename "$EMBED_PATH") (~146MB) from Hugging Face..."
    curl -fL --retry 3 --progress-bar -o "$EMBED_PATH" "$EMBED_URL"
    echo "Embedding model saved to $EMBED_PATH."
fi

echo "Done. Both models are ready."
