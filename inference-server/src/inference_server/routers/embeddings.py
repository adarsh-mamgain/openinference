"""Router implementing `POST /v1/embeddings` using a real embedding model.

Embeddings come from a dedicated local model (nomic-embed-text, 768-dim) loaded
with ``embedding=True`` in llama-cpp-python, so the vectors are genuine
semantic embeddings rather than a heuristic.
"""

import asyncio

from fastapi import APIRouter

from inference_server.exceptions import ModelUnavailableError
from inference_server.llm import embedding_model
from inference_server.schemas import (
    EmbeddingData,
    EmbeddingRequest,
    EmbeddingResponse,
    Usage,
)

router = APIRouter()


@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embedding(request: EmbeddingRequest) -> EmbeddingResponse:
    """Create embeddings for a single string or a list of strings."""
    if not embedding_model.available:
        raise ModelUnavailableError(
            "Embedding model not downloaded. Run `./scripts/download-model.sh` and restart."
        )

    inputs = request.input if isinstance(request.input, list) else [request.input]
    vectors = await asyncio.to_thread(embedding_model.embed, inputs)

    data = [
        EmbeddingData(embedding=vector, index=i)
        for i, vector in enumerate(vectors)
    ]
    prompt_tokens = sum(embedding_model.count_tokens(t) for t in inputs)

    return EmbeddingResponse(
        data=data,
        model=request.model,
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            total_tokens=prompt_tokens,
        ),
    )
