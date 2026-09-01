import os

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from llm.schemas import TriageInput, TriageOutput
from llm.triage_service import generate_triage_raw_output, get_prompt_version


router = APIRouter(prefix="/triage", tags=["Triage"])


def _invalid_field_response(error: ValidationError) -> JSONResponse:
    first_error = error.errors()[0]
    field_path = [str(part) for part in first_error.get("loc", []) if part != "body"]
    field_name = ".".join(field_path) if field_path else "body"
    return JSONResponse(
        status_code=400,
        content={"error": f"Invalid field: {field_name}"},
    )


@router.post("/", summary="Classify a support message")
def triage_message(payload: dict = Body(...)):
    """Stage 2 endpoint: validate input, then return either stub output or raw model text."""
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

    try:
        model_text = generate_triage_raw_output(request.text)
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=502, content={"error": f"Model call failed: {exc}"})

    return {
        "prompt_version": get_prompt_version(),
        "model_text": model_text,
    }
