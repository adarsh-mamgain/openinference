"""Router implementing `GET /v1/models`, mirroring the OpenAI endpoint."""

from fastapi import APIRouter

from inference_server.config import settings
from inference_server.llm import embedding_model, model
from inference_server.router import Router
from inference_server.router.registry import build_routes
from inference_server.schemas import Model, ModelList

router = APIRouter()

_router_engine = Router(routes=build_routes(available_check=lambda: model.available))


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

    for route in _router_engine.routes():
        if route.available() and route.id not in {m.id for m in data}:
            data.append(Model(id=route.id, owned_by="route"))

    return ModelList(data=data)


@router.get("/routes", response_model=None)
def list_routes() -> dict:
    """Diagnostic: the routing table and per-route health."""
    status = _router_engine.status()
    return {"router": {"enabled": True}, **status}
