import os

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from llm.schemas import TriageInput, TriageOutput


router = APIRouter(prefix="/triage", tags=["Triage"])


def _invalid_field_response(error: ValidationError) -> JSONResponse:
    first_error = error.errors()[0]
    field_path = [str(part) for part in first_error.get("loc", []) if part != "body"]
    field_name = ".".join(field_path) if field_path else "body"
    return JSONResponse(
        status_code=400,
        content={"error": f"Invalid field: {field_name}"},
    )


@router.post("/", response_model=TriageOutput, summary="Classify a support message")
def triage_message(payload: dict = Body(...)):
    """Stage 1 endpoint: validate input and return deterministic stub output only."""
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

    return JSONResponse(
        status_code=503,
        content={
            "error": "LLM_STUB is disabled. Stage 1 only supports deterministic stub responses.",
            "field": "LLM_STUB",
        },
    )
