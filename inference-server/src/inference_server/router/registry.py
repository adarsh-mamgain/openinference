"""Build the router's route set from application settings.

The default deployment serves a single local GGUF, which becomes one route. When
sibling GGUFs of the *same model* exist at a different quantization (e.g.
``...-q8_0.gguf`` next to the default ``...-q4_k_m.gguf``), each is registered as
its own route so the router can trade quality vs latency/cost across quants — the
quantization-sweep story (R3). Extra backends (provider endpoints) can also be
registered programmatically.
"""

import logging
import re
from pathlib import Path

from inference_server.config import settings
from inference_server.router.models import Route, RouteBackend

logger = logging.getLogger(__name__)


def default_route(available_check=None) -> Route:
    """The canonical route: the configured local GGUF model.

    ``available_check`` defaults to the static file check, but callers often
    pass the live ``model.available`` signal so route availability tracks the
    model backend actually in use (and stays correct when tests swap in fakes).
    """
    return Route(
        id=settings.model_identifier,
        backend=RouteBackend.LOCAL,
        model_path=settings.model_path,
        model_identifier=settings.model_identifier,
        n_ctx=settings.model_ctx,
        quality=0.5,
        cost_per_1k_tokens=0.0,
        latency_ms=1000.0,
        max_context=settings.model_ctx,
        available_check=available_check,
    )


_QUANT_QUALITY = {
    "q2_k": 0.35,
    "q3_k_m": 0.42,
    "q4_k_m": 0.55,
    "q4_k_s": 0.5,
    "q5_k_m": 0.65,
    "q5_k_s": 0.62,
    "q6_k": 0.78,
    "q8_0": 0.9,
    "f16": 0.95,
}


def _quant_label(path: Path) -> str | None:
    """Extract the quantization tag (e.g. ``q8_0``) from a GGUF filename."""
    match = re.search(r"-(q[0-9]_k_[ms]|q[0-9]_[0-9]|f16)\.gguf$", path.name)
    return match.group(1) if match else None


def build_routes(available_check=None, extra_models_dir: str | None = None) -> list[Route]:
    """Return the routes for this deployment.

    Includes the default local model plus any quantized siblings of the same
    model discovered in the models directory. ``extra_models_dir`` lets a caller
    point at a models dir other than the one implied by ``settings`` (tests,
    or a sweep against a separate directory).
    """
    routes = [default_route(available_check)]

    models_dir = Path(extra_models_dir or Path(settings.model_path).parent)
    base_name = Path(settings.model_path).stem  # e.g. qwen2.5-0.5b-instruct-q4_k_m
    base_stem = re.sub(r"-(q[0-9]_k_[ms]|q[0-9]_[0-9]|f16)$", "", base_name)
    if not models_dir.is_dir():
        return routes

    for path in sorted(models_dir.iterdir()):
        if path.suffix != ".gguf" or path.name == Path(settings.model_path).name:
            continue
        quant = _quant_label(path)
        if quant is None or not path.name.startswith(base_stem):
            continue  # different model entirely — not a sibling quant
        route_id = f"{settings.model_identifier}-{quant}"
        quality = _QUANT_QUALITY.get(quant, 0.5)
        # Higher-precision quants are slower (larger memory footprint) but
        # better quality; reflect that tradeoff in the estimated latency.
        latency = 1000.0 + (int(quant.split("_")[0][1:]) * 100)
        logger.info("registered quant route %s (quality=%.2f)", route_id, quality)
        routes.append(
            Route(
                id=route_id,
                backend=RouteBackend.LOCAL,
                model_path=str(path),
                model_identifier=route_id,
                n_ctx=settings.model_ctx,
                quality=quality,
                cost_per_1k_tokens=0.0,
                latency_ms=latency,
                max_context=settings.model_ctx,
                available_check=None,
            )
        )
    return routes
