"""Router implementing `GET /v1/models`, mirroring the OpenAI endpoint."""

from fastapi import APIRouter

from inference_server.config import settings
from inference_server.llm import embedding_model, model
from inference_server.schemas import Model, ModelList

router = APIRouter()


@router.get("/models", response_model=ModelList)
def list_models() -> ModelList:
    """List the models available on this server."""
    data: list[Model] = []

    if model.available:
        data.append(Model(id=settings.model_identifier, owned_by="local"))
    if embedding_model.available:
        data.append(
            Model(id=settings.embedding_model_identifier, owned_by="local")
        )

    return ModelList(data=data)
