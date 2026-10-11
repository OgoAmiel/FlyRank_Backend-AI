import os
import logging
import time

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from llm.cache_metrics import record_cache_lookup, get_cache_metrics

from llm.schemas import TriageInput, TriageOutput
from llm.cache import get_cached_triage_with_status, cache_triage
from llm.triage_service import (
    LLMProviderError,
    LLMTimeoutError,
    TriageProcessingError,
    generate_triage_output,
)


logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/triage", tags=["Triage"])


def _invalid_field_response(error: ValidationError) -> JSONResponse:
    first_error = error.errors()[0]
    field_path = [str(part) for part in first_error.get("loc", []) if part != "body"]
    field_name = ".".join(field_path) if field_path else "body"
    return JSONResponse(
        status_code=400,
        content={"error": f"Invalid field: {field_name}"},
    )


def _is_enabled(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


@router.post("/", response_model=TriageOutput, summary="Classify a support message")
def triage_message(payload: dict = Body(...)):
    """
    Validate input, check Redis cache, generate and validate
    model output when needed, and return structured JSON.
    """

    try:
        request = TriageInput.model_validate(payload)
    except ValidationError as exc:
        return _invalid_field_response(exc)

    if os.getenv("LLM_STUB", "0") == "1":
        return TriageOutput(
            category="other",
            urgency="normal",
            confidence=0.25,
            reason="Stub mode enabled: model call skipped.",
        )

    if not _is_enabled("LLM_ENABLED", default=True):
        return JSONResponse(
            status_code=503,
            content={
                "error": "LLM processing is disabled by configuration",
                "fallback": {
                    "category": "other",
                    "urgency": "low",
                    "confidence": 0.0,
                    "reason": "LLM disabled; returning deterministic fallback.",
                },
            },
        )
    # STEP 1: Check Redis cache
    start = time.perf_counter()

    cached_output, cache_status = get_cached_triage_with_status(request.text)

    lookup_duration = time.perf_counter() - start

    record_cache_lookup(cache_status, lookup_duration)

    if cache_status == "hit":
        logger.info("Redis cache HIT - returning cached classification")
        return cached_output

    if cache_status == "error":
        logger.warning("Redis cache ERROR - falling back to AI classification")
    else:
        logger.info("Redis cache MISS - generating AI classification")

    try:
        output = generate_triage_output(request.text)
    except TriageProcessingError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": exc.message},
        )
    except LLMTimeoutError as exc:
        return JSONResponse(
            status_code=504,
            content={"error": exc.message},
        )
    except LLMProviderError as exc:
        if exc.status_code == 401:
            return JSONResponse(
                status_code=502,
                content={
                    "error": "Provider authentication failed (check LLM_API_KEY)",
                    "provider_status": 401,
                },
            )
        return JSONResponse(
            status_code=502,
            content={
                "error": exc.message,
                "provider_status": exc.status_code,
            },
        )
    except RuntimeError as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Model call failed: {exc}"},
        )

    # STEP 3: Cache successful AI classification
    cache_triage(request.text, output)

    logger.info("AI classification completed - cache write attempted")

    return output

@router.get("/metrics", summary="View Redis cache metrics")
def triage_cache_metrics():
    return get_cache_metrics()
