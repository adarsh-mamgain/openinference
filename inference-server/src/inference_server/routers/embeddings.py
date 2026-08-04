"""Router implementing `POST /v1/embeddings`."""

from fastapi import APIRouter

from inference_server.mock_model import count_tokens
from inference_server.schemas import (
    EmbeddingData,
    EmbeddingRequest,
    EmbeddingResponse,
    Usage,
)

router = APIRouter()

EMBEDDING_DIM = 128


def embed(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Deterministic bag-of-words-style embedding.

    Each character maps to a stable pseudo-random value via its hash, and the
    values are summed and normalized. The same input always yields the same
    vector, which is enough to explore the API surface and later to build a
    vector database on top.
    """
    vector = [0.0] * dim
    for ch in text:
        index = hash(ch) % dim
        vector[index] += 1.0
    norm = sum(v * v for v in vector) ** 0.5
    if norm == 0:
        return vector
    return [v / norm for v in vector]


@router.post("/embeddings", response_model=EmbeddingResponse)
def create_embedding(request: EmbeddingRequest) -> EmbeddingResponse:
    """Create embeddings for a single string or a list of strings."""
    inputs = request.input if isinstance(request.input, list) else [request.input]

    data = [
        EmbeddingData(embedding=embed(text), index=i)
        for i, text in enumerate(inputs)
    ]
    prompt_tokens = sum(count_tokens(text) for text in inputs)

    return EmbeddingResponse(
        data=data,
        model=request.model,
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            total_tokens=prompt_tokens,
        ),
    )
